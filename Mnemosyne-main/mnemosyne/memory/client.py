import os
import uuid
import json
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from mnemosyne.config import get_mnemosyne_dir, load_config
from mnemosyne.memory.schemas import (
    MemoryRecord, MemoryType, BugFixMemory, CodeRuleMemory, CommitMemory,
    CodeKnowledgeGraph, CODE_ENTITY_EXTRACTION_PROMPT,
)

logger = logging.getLogger(__name__)


class MemoryClient:
    """
    Client interface connecting Mnemosyne CLI with Cognee memory primitives
    and local persistence metadata.

    Cognee Integration Strategy (Phase 2):
    - cognify() uses CodeKnowledgeGraph schema for typed entity extraction
    - recall() uses SearchType.GRAPH_COMPLETION + HYBRID_COMPLETION + CODING_RULES
    - temporal_cognify=True tracks bug pattern evolution over time
    - Auto-reflection fires when bug count hits reflection_threshold
    - session_id enables episodic memory for pre-commit context
    """

    def __init__(self, repo_root: Optional[Path] = None):
        self.mnemosyne_dir = get_mnemosyne_dir(repo_root)
        self.store_file = self.mnemosyne_dir / "memories.json"
        self._records: Dict[str, MemoryRecord] = {}
        self._load_records()
        self._cognee_initialized = False
        self._last_session_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Persistence (local JSON store — always-available ground truth)
    # ------------------------------------------------------------------

    def _load_records(self) -> None:
        if self.store_file.exists():
            try:
                with open(self.store_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        rec = MemoryRecord(**item)
                        if rec.active:
                            self._records[rec.id] = rec
            except Exception:
                self._records = {}

    def _save_records(self) -> None:
        data = [rec.model_dump() for rec in self._records.values() if rec.active]
        with open(self.store_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # ------------------------------------------------------------------
    # Cognee initialization
    # ------------------------------------------------------------------

    def _init_cognee_if_needed(self) -> bool:
        if os.getenv("MNEMOSYNE_OFFLINE") == "1":
            return False
        if self._cognee_initialized:
            return True
        try:
            import cognee
            from mnemosyne.config import load_config, configure_llm_env
            config = load_config()

            # Set up local cognee data directory inside .mnemosyne
            cognee_data_dir = str(self.mnemosyne_dir / "cognee_data")
            os.environ["COGNEE_DATA_DIR"] = cognee_data_dir

            # Cognee Cloud (optional) configuration
            cognee_key = os.getenv("COGNEE_API_KEY") or config.get("cognee_api_key")
            cognee_url = os.getenv("COGNEE_API_URL") or config.get("cognee_api_url", "https://api.cognee.ai")
            if cognee_key:
                os.environ["COGNEE_API_KEY"] = cognee_key
                os.environ["COGNEE_API_URL"] = cognee_url

            # LLM + embedding backend (Ollama by default — local & free).
            configure_llm_env(config)

            self._cognee_initialized = True
            return True
        except ImportError:
            return False
        except Exception as e:
            logger.debug(f"Cognee init failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Internal async helpers for Cognee operations
    # ------------------------------------------------------------------

    async def _cognee_add_and_cognify(self, content: str, dataset: str, use_temporal: bool = False) -> None:
        """
        Add content to Cognee and build the knowledge graph.

        The typed CodeKnowledgeGraph schema + temporal tracking give richer graphs,
        but require an LLM that reliably emits strict structured JSON (valid UUIDs,
        nested nodes). Small local models (llama3.2:3b) can't and will retry-hang, so
        those extras are gated behind config flags (`use_custom_graph_schema`,
        `use_temporal_cognify`, both OFF by default). If the fancy path is enabled but
        fails, we fall back to Cognee's robust built-in extraction so the graph is
        still populated.
        """
        import cognee
        from mnemosyne.config import load_config
        config = load_config()
        await cognee.add(content, dataset_name=dataset)

        if config.get("use_custom_graph_schema", False):
            temporal = use_temporal and config.get("use_temporal_cognify", False)
            try:
                await cognee.cognify(
                    datasets=[dataset],
                    graph_model=CodeKnowledgeGraph,
                    custom_prompt=CODE_ENTITY_EXTRACTION_PROMPT,
                    temporal_cognify=temporal,
                )
                return
            except Exception as e:
                logger.debug(
                    f"Custom-schema cognify failed ({e}); falling back to default cognify"
                )

        # Default extraction — robust across weak local models (Ollama).
        await cognee.cognify(datasets=[dataset])

    async def _recall_async(
        self,
        query: str,
        file_context: Optional[str] = None,
        top_k: int = 5,
        session_id: Optional[str] = None,
    ) -> List[MemoryRecord]:
        """
        Multi-strategy semantic recall using Cognee's SearchType hierarchy.

        Strategy 1: GRAPH_COMPLETION — deep graph traversal + LLM reasoning
                     Traverses 2-hop neighborhoods from matched nodes, ideal for
                     finding bugs related through shared code entities.

        Strategy 2: HYBRID_COMPLETION — vector chunks + graph entities + triplets
                     Broader coverage; picks up semantic similarity misses from
                     pure graph traversal.

        Strategy 3: CODING_RULES — dedicated retriever for rule/convention queries
                     Uses Cognee's code-aware retriever tuned for rule patterns.

        All strategies respect session_id for episodic memory priority.
        Falls back to local JSON keyword scoring ONLY if all Cognee calls fail.
        """
        import cognee
        from cognee.modules.search.types.SearchType import SearchType

        enhanced_query = f"In file {file_context}: {query}" if file_context else query
        raw_cognee_results: List[Any] = []

        # Strategy 1: Graph-completion — deep traversal, best for relational queries
        try:
            graph_results = await cognee.search(
                query_text=enhanced_query,
                query_type=SearchType.GRAPH_COMPLETION,
                datasets=["mnemosyne_codebase"],
                top_k=top_k,
                neighborhood_depth=2,
                only_context=True,
                session_id=session_id,
            )
            if graph_results:
                raw_cognee_results.extend(
                    [(r, "GRAPH_COMPLETION") for r in graph_results]
                )
                logger.debug(f"Graph search returned {len(graph_results)} results")
        except Exception as e:
            logger.debug(f"Graph search unavailable: {e}")

        # Strategy 2: Hybrid — vector + graph entities + triplets combined
        try:
            hybrid_results = await cognee.search(
                query_text=enhanced_query,
                query_type=SearchType.HYBRID_COMPLETION,
                datasets=["mnemosyne_codebase"],
                top_k=top_k,
                only_context=True,
                session_id=session_id,
            )
            if hybrid_results:
                raw_cognee_results.extend(
                    [(r, "HYBRID_COMPLETION") for r in hybrid_results]
                )
                logger.debug(f"Hybrid search returned {len(hybrid_results)} results")
        except Exception as e:
            logger.debug(f"Hybrid search unavailable: {e}")

        # Strategy 3: Coding rules — dedicated retriever for rules/conventions
        # Activated for any query mentioning rules, conventions, best practices, etc.
        rule_keywords = {"rule", "convention", "pattern", "practice", "standard", "guideline"}
        if any(kw in query.lower() for kw in rule_keywords):
            try:
                rule_results = await cognee.search(
                    query_text=enhanced_query,
                    query_type=SearchType.CODING_RULES,
                    datasets=["mnemosyne_codebase", "mnemosyne_rules"],
                    top_k=top_k,
                )
                if rule_results:
                    raw_cognee_results.extend(
                        [(r, "CODING_RULES") for r in rule_results]
                    )
                    logger.debug(f"Coding rules search returned {len(rule_results)} results")
            except Exception as e:
                logger.debug(f"Coding rules search unavailable: {e}")

        # Convert Cognee SearchResult objects to MemoryRecord format
        if raw_cognee_results:
            records = self._search_results_to_records(raw_cognee_results, top_k)
            # Only trust Cognee results if they found substantial, non-empty content.
            # Cognee returns empty-context completions for new/empty graphs — those
            # should not block the local keyword fallback from running.
            if records and any(len(r.content.strip()) >= 20 for r in records):
                return records

        # Fallback: local JSON keyword scoring (only if ALL Cognee strategies failed)
        logger.debug("All Cognee search strategies unavailable — using keyword fallback")
        return self._keyword_fallback(query, file_context, top_k)

    def _search_results_to_records(
        self,
        search_results: List[tuple],
        top_k: int,
    ) -> List[MemoryRecord]:
        """
        Convert Cognee SearchResult objects to MemoryRecord format.

        Unlike the original (which used brittle str() matching against local JSON),
        this creates MemoryRecord objects directly from the Cognee search results,
        preserving the semantic content and tagging the search strategy used.

        Synthetic records (not matched to local store) are only created when the
        content is substantial (>=20 chars). Empty completions from an empty graph
        are discarded so the keyword fallback can run instead.
        """
        seen_ids = set()
        records = []

        for result, strategy in search_results:
            if len(records) >= top_k:
                break

            # Extract content from various Cognee result formats
            content = ""
            title = "Cognee Memory Node"
            file_path = None
            mem_type = MemoryType.DOCUMENTATION

            if hasattr(result, "text"):
                content = result.text
            elif hasattr(result, "content"):
                content = result.content
            elif isinstance(result, dict):
                content = result.get("text", result.get("content", str(result)))
                title = result.get("title", title)
            else:
                content = str(result)

            # Skip empty or trivial completions (e.g. empty-graph responses)
            if len(content.strip()) < 20:
                logger.debug(f"Skipping trivial Cognee result (len={len(content.strip())}): {content[:50]!r}")
                continue

            # Try to match back to a local record for richer metadata
            matched_local = self._find_local_match(content, title)
            if matched_local:
                if matched_local.id in seen_ids:
                    continue
                seen_ids.add(matched_local.id)
                # Annotate which strategy found this
                matched_local.search_strategy = strategy
                records.append(matched_local)
            else:
                # Create a synthetic MemoryRecord from the Cognee result
                synthetic_id = f"cognee_{uuid.uuid4().hex[:8]}"
                if synthetic_id in seen_ids:
                    continue
                seen_ids.add(synthetic_id)
                records.append(MemoryRecord(
                    id=synthetic_id,
                    memory_type=mem_type,
                    title=title,
                    content=content,
                    file_path=file_path,
                    metadata={"source": "cognee_graph"},
                    search_strategy=strategy,
                ))

        return records

    def _find_local_match(self, content: str, title: str) -> Optional[MemoryRecord]:
        """Attempt to match a Cognee result back to a local JSON record by content overlap."""
        content_lower = content.lower()
        best_match = None
        best_score = 0

        for rec in self._records.values():
            if not rec.active:
                continue
            score = 0
            # Title substring match
            if rec.title.lower() in content_lower or content_lower[:100] in rec.content.lower():
                score += 5
            # File path match
            if rec.file_path and rec.file_path.lower() in content_lower:
                score += 3
            # ID match
            if rec.id in content:
                score += 10
            if score > best_score:
                best_score = score
                best_match = rec

        return best_match if best_score >= 3 else None

    def _keyword_fallback(
        self,
        query: str,
        file_context: Optional[str],
        top_k: int,
    ) -> List[MemoryRecord]:
        """
        Local JSON keyword scoring fallback.
        Used ONLY when all Cognee search strategies are unavailable.
        """
        query_terms = set(query.lower().replace("/", " ").replace("_", " ").split())
        scored: List[tuple] = []

        for rec in self._records.values():
            if not rec.active:
                continue
            score = 0
            rec_text = (rec.content + " " + rec.title + " " + (rec.file_path or "")).lower()

            if file_context and rec.file_path:
                norm_fc = file_context.lower().replace("\\", "/")
                norm_fp = rec.file_path.lower().replace("\\", "/")
                if norm_fc in norm_fp or norm_fp in norm_fc or Path(norm_fc).name == Path(norm_fp).name:
                    score += 5

            for term in query_terms:
                if len(term) > 2 and term in rec_text:
                    score += 2

            if score > 0:
                rec.search_strategy = "KEYWORD_FALLBACK"
                scored.append((score, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [rec for _, rec in scored[:top_k]]

    def get_last_session_id(self) -> Optional[str]:
        """Return the most recent session ID used by this client."""
        return self._last_session_id

    # ------------------------------------------------------------------
    # COGNEE PRIMITIVE: remember
    # ------------------------------------------------------------------

    def remember_bug(self, bug: BugFixMemory) -> MemoryRecord:
        """
        [COGNEE PRIMITIVE: remember]
        Ingests a bug fix into the Cognee knowledge graph with typed entity extraction.

        Upgrades:
        - Uses CodeKnowledgeGraph schema for structured node extraction
        - Uses CODE_ENTITY_EXTRACTION_PROMPT for code-aware LLM prompting
        - temporal_cognify=True to track bug pattern evolution over time
        - Auto-triggers reflect() when reflection_threshold is reached
        """
        mem_id = f"mem_bug_{uuid.uuid4().hex[:8]}"
        bug.id = mem_id
        content = bug.to_memory_text()

        record = MemoryRecord(
            id=mem_id,
            memory_type=MemoryType.BUG_FIX,
            title=bug.title,
            content=content,
            file_path=bug.file_path,
            metadata=bug.model_dump()
        )
        self._records[mem_id] = record
        self._save_records()

        # Push to Cognee with custom schema + temporal tracking
        if self._init_cognee_if_needed():
            try:
                asyncio.run(self._cognee_add_and_cognify(
                    content=content,
                    dataset="mnemosyne_codebase",
                    use_temporal=True,  # Track bug pattern evolution over time
                ))
                logger.debug(f"Bug {mem_id} ingested into Cognee graph with CodeKnowledgeGraph schema")
            except Exception as e:
                logger.debug(f"Cognee ingestion failed, local store used: {e}")

        # Auto-trigger reflection when threshold is reached
        self._check_reflection_threshold()

        return record

    def _check_reflection_threshold(self) -> None:
        """Auto-trigger consolidation when bug count hits reflection_threshold."""
        config = load_config()
        threshold = int(config.get("reflection_threshold", 3))
        active_bugs = [r for r in self._records.values()
                       if r.active and r.memory_type == MemoryType.BUG_FIX]
        count = len(active_bugs)
        if count > 0 and count % threshold == 0:
            logger.debug(f"Auto-reflection triggered at {count} bug fixes (threshold={threshold})")
            try:
                from mnemosyne.memory.consolidator import MemoryConsolidator
                consolidator = MemoryConsolidator(self)
                consolidator.reflect()
            except Exception as e:
                logger.debug(f"Auto-reflection failed: {e}")

    def remember_commit(self, commit: CommitMemory) -> MemoryRecord:
        """
        [COGNEE PRIMITIVE: remember]
        Ingests a git commit summary into memory.
        """
        mem_id = f"mem_commit_{commit.commit_hash[:7]}"
        commit.id = mem_id
        content = commit.to_memory_text()

        record = MemoryRecord(
            id=mem_id,
            memory_type=MemoryType.COMMIT,
            title=f"Commit: {commit.summary}",
            content=content,
            file_path=commit.files_changed[0] if commit.files_changed else None,
            metadata=commit.model_dump()
        )
        self._records[mem_id] = record
        self._save_records()

        if self._init_cognee_if_needed():
            try:
                import cognee
                asyncio.run(cognee.add(content, dataset_name="mnemosyne_codebase"))
            except Exception as e:
                logger.debug(f"Cognee commit ingestion failed: {e}")

        return record

    def remember_rule(self, rule: CodeRuleMemory) -> MemoryRecord:
        """
        [COGNEE PRIMITIVE: remember / memify]
        Stores a consolidated coding rule.
        """
        mem_id = f"rule_{uuid.uuid4().hex[:8]}"
        rule.id = mem_id
        content = rule.to_memory_text()

        record = MemoryRecord(
            id=mem_id,
            memory_type=MemoryType.RULE,
            title=rule.rule_title,
            content=content,
            metadata=rule.model_dump()
        )
        self._records[mem_id] = record
        self._save_records()

        if self._init_cognee_if_needed():
            try:
                asyncio.run(self._cognee_add_and_cognify(
                    content=content,
                    dataset="mnemosyne_rules",
                    use_temporal=False,
                ))
            except Exception as e:
                logger.debug(f"Cognee rule ingestion failed: {e}")

        return record

    def remember_doc(self, title: str, content: str, file_path: Optional[str] = None) -> MemoryRecord:
        """
        [COGNEE PRIMITIVE: remember]
        Ingests a general document, ADR, or design decision into memory.
        """
        mem_id = f"mem_doc_{uuid.uuid4().hex[:8]}"
        mem_text = f"[DOCUMENTATION] {title}\n"
        if file_path:
            mem_text += f"File Context: {file_path}\n"
        mem_text += f"Content:\n{content}\n"

        record = MemoryRecord(
            id=mem_id,
            memory_type=MemoryType.DOCUMENTATION,
            title=title,
            content=mem_text,
            file_path=file_path,
            metadata={"title": title, "file_path": file_path}
        )
        self._records[mem_id] = record
        self._save_records()

        if self._init_cognee_if_needed():
            try:
                asyncio.run(self._cognee_add_and_cognify(
                    content=mem_text,
                    dataset="mnemosyne_codebase",
                    use_temporal=False,
                ))
            except Exception as e:
                logger.debug(f"Cognee doc ingestion failed: {e}")

        return record

    # ------------------------------------------------------------------
    # COGNEE PRIMITIVE: recall
    # ------------------------------------------------------------------

    def recall(
        self,
        query: str,
        file_context: Optional[str] = None,
        top_k: int = 5,
        session_id: Optional[str] = None,
    ) -> List[MemoryRecord]:
        """
        [COGNEE PRIMITIVE: recall]
        Multi-strategy semantic recall using Cognee's graph and hybrid search.

        Uses SearchType.GRAPH_COMPLETION + HYBRID_COMPLETION + CODING_RULES
        instead of brittle str() matching on cognee.search() results.
        Session memory is prioritized when session_id is provided.
        """
        if session_id:
            self._last_session_id = session_id

        if self._init_cognee_if_needed():
            try:
                return asyncio.run(
                    self._recall_async(query, file_context, top_k, session_id)
                )
            except Exception as e:
                logger.debug(f"Cognee recall failed, using keyword fallback: {e}")

        return self._keyword_fallback(query, file_context, top_k)

    # ------------------------------------------------------------------
    # COGNEE PRIMITIVE: improve
    # ------------------------------------------------------------------

    def improve(self) -> bool:
        """
        [COGNEE PRIMITIVE: improve / memify]
        Runs post-ingestion graph enrichment, edge weight adaptation, and memory pruning.
        Re-cognifies with the updated CodeKnowledgeGraph schema.
        """
        if self._init_cognee_if_needed():
            try:
                import cognee
                from mnemosyne.config import load_config
                config = load_config()
                if hasattr(cognee, "memify"):
                    asyncio.run(cognee.memify())
                # Re-run cognify to enrich the graph. Use the custom schema only when
                # enabled (needs a strong LLM); otherwise the robust default extraction.
                if config.get("use_custom_graph_schema", False):
                    try:
                        asyncio.run(cognee.cognify(
                            datasets=["mnemosyne_codebase"],
                            graph_model=CodeKnowledgeGraph,
                            custom_prompt=CODE_ENTITY_EXTRACTION_PROMPT,
                            temporal_cognify=config.get("use_temporal_cognify", False),
                        ))
                        return True
                    except Exception as e:
                        logger.debug(f"Custom-schema improve failed ({e}); using default cognify")
                asyncio.run(cognee.cognify(datasets=["mnemosyne_codebase"]))
                return True
            except Exception as e:
                logger.debug(f"Cognee improve failed: {e}")
        return True

    # ------------------------------------------------------------------
    # COGNEE PRIMITIVE: forget
    # ------------------------------------------------------------------

    def forget(self, memory_id_or_path: str) -> List[str]:
        """
        [COGNEE PRIMITIVE: forget]
        Decays or removes specified memory by ID or associated file path.
        """
        removed_ids = []
        target = memory_id_or_path.strip()

        if target in self._records:
            self._records[target].active = False
            removed_ids.append(target)
        else:
            for rec_id, rec in list(self._records.items()):
                if rec.active and (rec.file_path and target in rec.file_path or target in rec.id):
                    rec.active = False
                    removed_ids.append(rec_id)

        if removed_ids:
            self._save_records()
            if self._init_cognee_if_needed():
                try:
                    import cognee
                    if hasattr(cognee, "prune"):
                        asyncio.run(cognee.prune.prune_data())
                except Exception as e:
                    logger.debug(f"Cognee prune failed: {e}")

        return removed_ids

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def list_memories(self, memory_type: Optional[MemoryType] = None) -> List[MemoryRecord]:
        recs = [r for r in self._records.values() if r.active]
        if memory_type:
            recs = [r for r in recs if r.memory_type == memory_type]
        return recs

    def get_rules(self, domain: Optional[str] = None) -> List[MemoryRecord]:
        rules = self.list_memories(MemoryType.RULE)
        if domain:
            rules = [r for r in rules if r.metadata.get("domain", "").lower() == domain.lower()]
        return rules

    def get_all_active(self) -> List[MemoryRecord]:
        return list(self._records.values())
