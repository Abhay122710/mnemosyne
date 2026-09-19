from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict


class MemoryType(str, Enum):
    BUG_FIX = "bug_fix"
    COMMIT = "commit"
    RULE = "rule"
    DOCUMENTATION = "documentation"
    REVIEW_NOTE = "review_note"


class BugFixMemory(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    file_path: str = Field(..., description="Path to the file affected by the bug")
    function_name: Optional[str] = Field(None, description="Name of the function or method involved")
    title: str = Field(..., description="Short summary of the bug")
    root_cause: str = Field(..., description="Why the bug occurred")
    fix_description: str = Field(..., description="How the bug was resolved")
    severity: str = Field("medium", description="Bug severity: low, medium, high, critical")
    tags: List[str] = Field(default_factory=list, description="Tags or labels (e.g. null-check, api, payment)")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_memory_text(self) -> str:
        text = f"[BUG FIX] {self.title}\n"
        text += f"File: {self.file_path}\n"
        if self.function_name:
            text += f"Function: {self.function_name}\n"
        text += f"Root Cause: {self.root_cause}\n"
        text += f"Fix Applied: {self.fix_description}\n"
        if self.tags:
            text += f"Tags: {', '.join(self.tags)}\n"
        return text


class CodeRuleMemory(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    rule_title: str = Field(..., description="Concise rule title")
    description: str = Field(..., description="Detailed rule guideline")
    domain: str = Field("general", description="Module or layer affected (e.g. services, controllers)")
    origin_memory_ids: List[str] = Field(default_factory=list, description="IDs of source memories that created this rule")
    provenance_files: List[str] = Field(default_factory=list, description="Files where this rule pattern was observed")
    confidence: float = Field(0.9, description="Confidence score of consolidated rule (0.0 to 1.0)")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_memory_text(self) -> str:
        text = f"[CONSOLIDATED RULE] {self.rule_title}\n"
        text += f"Domain: {self.domain}\n"
        text += f"Rule: {self.description}\n"
        if self.provenance_files:
            text += f"Observed in files: {', '.join(self.provenance_files)}\n"
        text += f"Confidence: {self.confidence}\n"
        return text


class CommitMemory(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    commit_hash: str
    author: str
    summary: str
    files_changed: List[str]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_memory_text(self) -> str:
        text = f"[COMMIT {self.commit_hash[:7]}] {self.summary}\n"
        text += f"Author: {self.author}\n"
        text += f"Files Changed: {', '.join(self.files_changed)}\n"
        return text


class MemoryRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    memory_type: MemoryType
    title: str
    content: str
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    active: bool = True
    # Track which search strategy produced this result (for UI display)
    search_strategy: Optional[str] = Field(None, description="SearchType used to retrieve this record")


# ---------------------------------------------------------------------------
# Custom Cognee Knowledge Graph Schema for Code Memory
# ---------------------------------------------------------------------------

class CodeEntity(BaseModel):
    """
    A typed code entity node in the Cognee knowledge graph.

    When passed as graph_model to cognee.cognify(), Cognee's LLM extracts
    these typed nodes instead of generic KnowledgeGraph nodes — enabling
    structured graph traversal across files, functions, bug patterns, and rules.
    """
    id: UUID = Field(default_factory=uuid4)
    entity_type: Literal["file", "function", "class", "bug_pattern", "rule", "engineer", "module"]
    name: str = Field(..., description="Canonical name of the entity")
    file_path: Optional[str] = Field(None, description="Filesystem path, if applicable")
    description: str = Field(..., description="What this entity represents in the codebase")

    class Config:
        # Tell Cognee which fields to index for vector search
        json_schema_extra = {"index_fields": ["name", "entity_type", "description"]}


class CodeRelationship(BaseModel):
    """
    A typed edge between two CodeEntity nodes.

    These relationship types model the real structure of how bugs, files,
    functions, and rules are connected in a codebase's institutional memory.
    """
    source_node_id: UUID
    target_node_id: UUID
    relationship_name: Literal[
        "CONTAINS",         # file/module CONTAINS function/class
        "CAUSED_BY",        # bug CAUSED_BY a root-cause pattern
        "FIXED_BY",         # bug FIXED_BY a specific solution strategy
        "GENERALIZES_TO",   # specific bug instance GENERALIZES_TO a team rule
        "RECURS_IN",        # bug pattern RECURS_IN multiple files
        "AUTHORED_BY",      # commit/fix AUTHORED_BY an engineer
        "RELATED_TO",       # generic semantic relationship for novel patterns
    ]
    description: str = Field(..., description="Why this relationship exists")


class CodeKnowledgeGraph(BaseModel):
    """
    Domain-specific Cognee knowledge graph schema for codebase memory.

    Pass this as graph_model=CodeKnowledgeGraph to cognee.cognify() to
    override the generic KnowledgeGraph schema with code-aware typed nodes
    and semantically meaningful edges.

    Example:
        await cognee.cognify(
            datasets=["mnemosyne_codebase"],
            graph_model=CodeKnowledgeGraph,
            custom_prompt=CODE_ENTITY_EXTRACTION_PROMPT,
            temporal_cognify=True,
        )
    """
    nodes: List[CodeEntity]
    edges: List[CodeRelationship]


# ---------------------------------------------------------------------------
# Custom LLM Prompt for Code Entity Extraction
# ---------------------------------------------------------------------------

CODE_ENTITY_EXTRACTION_PROMPT = """
You are analyzing a software bug fix, commit, or coding document. Your task is to extract
structured code entities and their semantic relationships for a knowledge graph.

ENTITY TYPES to extract:
- "file"        → A source file (name = filename, file_path = full path)
- "function"    → A specific function or method (name = func_name)
- "class"       → A class or component (name = class_name)
- "bug_pattern" → The abstract root-cause pattern (name = pattern type, e.g. "NullPointerException", "RaceCondition")
- "rule"        → A generalizable coding rule or convention derived from this fix
- "engineer"    → A developer mentioned (name = their name/handle)
- "module"      → A package or module grouping

RELATIONSHIP TYPES to extract:
- CONTAINS      → A file or module contains a function/class
- CAUSED_BY     → A bug in a function was CAUSED_BY a bug_pattern
- FIXED_BY      → A bug was FIXED_BY a specific solution (described as a rule entity)
- GENERALIZES_TO → This specific bug instance GENERALIZES_TO an abstract coding rule
- RECURS_IN     → A bug_pattern RECURS_IN multiple files (if evidence suggests recurrence)
- AUTHORED_BY   → A commit or fix was AUTHORED_BY an engineer
- RELATED_TO    → Any other meaningful semantic relationship

INSTRUCTIONS:
1. Be specific — use actual function names, file names, and error types from the text.
2. Create a "bug_pattern" node for the root cause category, not just a description.
3. If the fix looks like it could prevent similar bugs elsewhere, create a GENERALIZES_TO edge
   from the bug_pattern to a "rule" node describing the generalized convention.
4. Link files to functions with CONTAINS edges.
5. Link the bug (as bug_pattern) to the fix strategy (as rule) with FIXED_BY.

This structured graph enables engineers to find related bugs across files via graph traversal.
"""
