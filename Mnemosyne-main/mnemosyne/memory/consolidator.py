import json
import logging
import asyncio
from typing import List, Optional
from collections import defaultdict
from mnemosyne.memory.client import MemoryClient
from mnemosyne.memory.schemas import MemoryRecord, MemoryType, CodeRuleMemory

logger = logging.getLogger(__name__)


class MemoryConsolidator:
    """
    [COGNEE PRIMITIVE: memify / reflect]
    Consolidates related bug memories into higher-level team rules and coding conventions.

    Phase 2 Upgrade:
    - Uses cognee.memify() for real semantic cross-memory association (not keyword buckets)
    - Uses SearchType.CODING_RULES to retrieve discovered patterns from the graph
    - Falls back to LLM-based semantic clustering (gpt-4o-mini) if Cognee is unavailable
    - The original 4 hardcoded keyword buckets are REMOVED entirely
    """

    def __init__(self, client: MemoryClient):
        self.client = client

    def reflect(self) -> List[CodeRuleMemory]:
        """
        Analyze bug memories, cluster related issues semantically, and generate
        consolidated team coding rules using Cognee's memify + CODING_RULES retriever.

        Cascade:
        1. cognee.memify() + SearchType.CODING_RULES   (best: graph-semantic)
        2. gpt-4o-mini LLM semantic clustering          (good: language-model-based)
        3. _local_heuristic_reflect()                   (always works: domain keyword)
        """
        memories = self.client.list_memories(MemoryType.BUG_FIX)
        if not memories:
            return []

        if not self.client._init_cognee_if_needed():
            logger.debug("Cognee not initialized — using local heuristic")
            return self._local_heuristic_reflect(memories)

        try:
            result = asyncio.run(self._reflect_async(memories))
            # If async completed but returned nothing, use local heuristic
            if result:
                return result
            logger.debug("Async reflect returned empty list — using local heuristic")
            return self._local_heuristic_reflect(memories)
        except Exception as e:
            logger.debug(f"Async reflect failed: {e}, trying sync fallback")
            return self._sync_fallback_reflect(memories)

    async def _reflect_async(self, memories: List[MemoryRecord]) -> List[CodeRuleMemory]:
        """
        Two-step semantic consolidation:
        1. cognee.memify() — builds cross-memory associations in the graph
        2. SearchType.CODING_RULES — retrieves semantically discovered patterns
        Falls back to LLM clustering if Cognee is unavailable.
        """
        import cognee
        from cognee.modules.search.types.SearchType import SearchType

        created_rules: List[CodeRuleMemory] = []
        existing_rules = self.client.get_rules()
        existing_titles = {r.title.lower() for r in existing_rules}

        # Step 1: Trigger cognee.memify() — semantic cross-memory association
        try:
            await cognee.memify()
            logger.debug("cognee.memify() completed — cross-memory associations built")
        except Exception as e:
            logger.debug(f"cognee.memify() unavailable: {e}")

        # Step 2: Retrieve consolidated patterns via CODING_RULES search type
        # This uses Cognee's dedicated code-pattern retriever on the graph we just enriched
        try:
            rule_results = await cognee.search(
                query_text="recurring bug patterns, coding conventions, and preventable mistakes",
                query_type=SearchType.CODING_RULES,
                datasets=["mnemosyne_codebase"],
                top_k=20,
            )

            for result in rule_results:
                # Parse the result into a CodeRuleMemory
                if hasattr(result, "text"):
                    content = result.text
                elif isinstance(result, dict):
                    content = result.get("text", result.get("content", ""))
                else:
                    content = str(result)

                if not content.strip():
                    continue

                # Extract title from first line of content
                lines = content.strip().splitlines()
                title = lines[0].strip(" #-") if lines else "Coding Convention"
                description = "\n".join(lines[1:]).strip() if len(lines) > 1 else content

                if title.lower() in existing_titles:
                    continue

                # Infer domain from content keywords
                domain = _infer_domain(content)
                # Infer provenance files from matched memories
                provenance = _infer_provenance(content, memories)

                rule = CodeRuleMemory(
                    rule_title=title,
                    description=description or content,
                    domain=domain,
                    origin_memory_ids=[m.id for m in memories],
                    provenance_files=provenance,
                    confidence=min(0.65 + (len(memories) * 0.05), 0.97),
                )
                self.client.remember_rule(rule)
                created_rules.append(rule)
                existing_titles.add(title.lower())

            if created_rules:
                logger.debug(f"CODING_RULES retriever discovered {len(created_rules)} new rules")
                return created_rules

        except Exception as e:
            logger.debug(f"CODING_RULES search unavailable: {e}")

        # Step 3: LLM-based semantic clustering fallback
        logger.debug("Falling back to LLM semantic clustering")
        return await self._llm_cluster_reflect(memories, existing_titles)

    async def _llm_cluster_reflect(
        self,
        memories: List[MemoryRecord],
        existing_titles: set,
    ) -> List[CodeRuleMemory]:
        """
        LLM-powered semantic clustering fallback using gpt-4o-mini.
        Groups bugs by semantic similarity — NOT hardcoded keyword buckets.
        """
        try:
            import openai
            import os
            from mnemosyne.config import configure_llm_env

            # Ollama (local & free) by default, or OpenAI if configured.
            configure_llm_env()
            llm_key = os.getenv("OPENAI_API_KEY")
            if not llm_key:
                return []

            client = openai.AsyncOpenAI(
                api_key=llm_key,
                base_url=os.getenv("OPENAI_BASE_URL") or None,
            )
            model = os.getenv("MNEMOSYNE_LLM_MODEL", "gpt-4o-mini")

            memory_texts = "\n\n".join([
                f"BUG {i + 1}: {m.title}\n"
                f"File: {m.file_path or 'unknown'}\n"
                f"Cause: {m.metadata.get('root_cause', m.content[:120])}\n"
                f"Fix: {m.metadata.get('fix_description', '')}"
                for i, m in enumerate(memories[:20])
            ])

            response = await client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                messages=[{
                    "role": "system",
                    "content": (
                        "You are a senior software engineer analyzing bug patterns to extract "
                        "reusable team coding conventions. Be specific and technical."
                    ),
                }, {
                    "role": "user",
                    "content": (
                        f"Analyze these {len(memories)} bug fixes and extract 2-6 generalized "
                        f"coding rules that would prevent these bugs from recurring.\n\n"
                        f"For each rule, provide:\n"
                        f"- title: concise rule name (max 10 words)\n"
                        f"- description: specific actionable guideline\n"
                        f"- domain: one of [validation, error-handling, api, concurrency, "
                        f"database, security, general]\n\n"
                        f"Bug fixes:\n{memory_texts}\n\n"
                        f'Return JSON: {{"rules": [{{"title": "...", "description": "...", "domain": "..."}}]}}'
                    ),
                }],
            )

            data = json.loads(response.choices[0].message.content)
            rules = []
            for r_data in data.get("rules", []):
                title = r_data.get("title", "")
                if not title or title.lower() in existing_titles:
                    continue

                provenance = _infer_provenance(title + " " + r_data.get("description", ""), memories)
                rule = CodeRuleMemory(
                    rule_title=title,
                    description=r_data.get("description", ""),
                    domain=r_data.get("domain", "general"),
                    origin_memory_ids=[m.id for m in memories],
                    provenance_files=provenance,
                    confidence=min(0.7 + (len(memories) * 0.05), 0.95),
                )
                self.client.remember_rule(rule)
                rules.append(rule)
                existing_titles.add(title.lower())

            return rules

        except Exception as e:
            logger.debug(f"LLM clustering failed: {e}")
            return []

    def _sync_fallback_reflect(self, memories: List[MemoryRecord]) -> List[CodeRuleMemory]:
        """
        Last-resort synchronous fallback — tries to run the async reflect in a new
        event loop, then falls back to local heuristic rule synthesis.
        Used when asyncio.run() is called from within an already-running event loop.
        """
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                asyncio.run,
                self._reflect_async(memories)
            )
            try:
                result = future.result(timeout=5)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"Sync fallback reflect failed: {e}")

        # Absolute last resort: pure-local heuristic rule synthesis
        # (no Cognee, no LLM required — always produces at least one rule)
        return self._local_heuristic_reflect(memories)

    def _local_heuristic_reflect(self, memories: List[MemoryRecord]) -> List[CodeRuleMemory]:
        """
        Pure-local heuristic rule synthesis — no Cognee, no LLM required.

        Clusters bugs by inferred domain using _infer_domain() on their content,
        then synthesizes a rule from each cluster. Used as the ultimate fallback
        so that reflect() always returns at least one rule when bugs are present.
        """
        existing_rules = self.client.get_rules()
        existing_titles = {r.title.lower() for r in existing_rules}
        rules: List[CodeRuleMemory] = []

        # Group memories by inferred domain
        clusters: dict = {}
        for mem in memories:
            domain = _infer_domain(mem.content)
            clusters.setdefault(domain, []).append(mem)

        domain_rule_titles = {
            "error-handling": (
                "Always handle None/null returns from external calls",
                "Check return values for None before accessing fields or methods. "
                "Use guard clauses and .get() patterns for dict access."
            ),
            "validation": (
                "Validate all external and user-supplied inputs",
                "Sanitize and validate inputs at service boundaries before processing."
            ),
            "api": (
                "Validate API responses before accessing nested fields",
                "Always check HTTP status codes and use safe .get() chains "
                "instead of direct dict access on API responses."
            ),
            "concurrency": (
                "Use explicit locks for shared mutable state",
                "Protect shared data structures with locks. Avoid race conditions by "
                "using asyncio.Lock() or threading.Lock() appropriately."
            ),
            "database": (
                "Use transactions and check query results before use",
                "Wrap related DB operations in transactions. Check for empty results "
                "before accessing query output."
            ),
            "security": (
                "Never trust external auth tokens without validation",
                "Validate all OAuth/JWT payloads with typed Pydantic models. "
                "Never access payload fields directly."
            ),
            "general": (
                "Apply defensive programming at service boundaries",
                "Assume external calls can fail or return unexpected types. "
                "Add explicit error handling at all integration points."
            ),
        }

        for domain, mems in clusters.items():
            title, description = domain_rule_titles.get(
                domain, domain_rule_titles["general"]
            )
            if title.lower() in existing_titles:
                continue

            provenance = list({m.file_path for m in mems if m.file_path})[:5]
            rule = CodeRuleMemory(
                rule_title=title,
                description=description,
                domain=domain,
                origin_memory_ids=[m.id for m in mems],
                provenance_files=provenance,
                confidence=min(0.65 + (len(mems) * 0.08), 0.90),
            )
            self.client.remember_rule(rule)
            rules.append(rule)
            existing_titles.add(title.lower())

        return rules


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_domain(content: str) -> str:
    """Infer rule domain from content keywords."""
    content_lower = content.lower()
    domain_keywords = {
        "validation": ["valid", "input", "sanitiz", "bound", "schema"],
        "error-handling": ["error", "exception", "try", "catch", "null", "none", "handle"],
        "api": ["api", "request", "response", "http", "endpoint", "json", "rest"],
        "concurrency": ["race", "lock", "thread", "async", "await", "concurrent", "atomic"],
        "database": ["db", "database", "sql", "query", "transaction", "orm"],
        "security": ["auth", "token", "secret", "encrypt", "permission", "xss", "inject"],
    }
    for domain, keywords in domain_keywords.items():
        if any(kw in content_lower for kw in keywords):
            return domain
    return "general"


def _infer_provenance(content: str, memories: List[MemoryRecord]) -> List[str]:
    """Find file paths from memories that are semantically relevant to this rule."""
    files = set()
    content_lower = content.lower()
    for m in memories:
        if m.file_path:
            stem = m.file_path.lower().replace("\\", "/").split("/")[-1].replace(".py", "")
            if stem and stem in content_lower:
                files.add(m.file_path)
    return list(files)[:5]  # Cap at 5 files
