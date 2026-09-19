"""
Mnemosyne MCP Server — Exposes codebase memory as MCP tools for Claude Code / Cursor.

This server lets AI coding assistants query and update codebase memory natively,
turning Mnemosyne into an always-on knowledge layer for your AI pair programmer.

Usage:
    mnemosyne mcp-serve                       # stdio transport (Claude Desktop)
    mnemosyne mcp-serve --transport sse       # SSE transport (web clients)
    mnemosyne mcp-serve --transport http      # Streamable HTTP

Claude Desktop config (~/.claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "mnemosyne": {
          "command": "mnemosyne",
          "args": ["mcp-serve"],
          "cwd": "/path/to/your/project"
        }
      }
    }
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def create_mcp_server():
    """
    Create and configure the Mnemosyne MCP server.
    Returns the FastMCP instance with all tools registered.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        raise ImportError(
            "MCP server requires the 'mcp' package. Install it with:\n"
            "  pip install mcp\n"
            "or:\n"
            "  uv add mcp"
        )

    from mnemosyne.memory.client import MemoryClient
    from mnemosyne.memory.schemas import BugFixMemory, MemoryType
    from mnemosyne.config import find_project_root

    mcp = FastMCP(
        "Mnemosyne Codebase Memory",
        instructions=(
            "You have access to this project's persistent codebase memory — a knowledge graph "
            "of past bug fixes, coding rules, and commit history. "
            "ALWAYS call recall_codebase_memory before writing code in a file that has had "
            "past bugs. Call remember_bug_fix after fixing any non-trivial bug."
        ),
    )

    _client_cache: dict = {}

    def get_client() -> MemoryClient:
        root = str(find_project_root())
        if root not in _client_cache:
            _client_cache[root] = MemoryClient(repo_root=Path(root))
        return _client_cache[root]

    @mcp.tool()
    async def recall_codebase_memory(
        query: str,
        file_path: Optional[str] = None,
    ) -> str:
        """
        Search the codebase knowledge graph for past bugs, fixes, and patterns
        related to the query. Call this BEFORE writing code to check institutional memory.

        Uses Cognee GRAPH_COMPLETION + HYBRID_COMPLETION for semantic traversal —
        not simple keyword matching.

        Args:
            query: What you're looking for (e.g. "null pointer exceptions in API layer")
            file_path: Optional file being edited, for file-specific context
        """
        client = get_client()
        results = client.recall(query=query, file_context=file_path, top_k=5)

        if not results:
            return (
                f"No relevant memories found for: '{query}'\n"
                "Tip: If you fix a bug, call remember_bug_fix to store it for the future."
            )

        output = f"🧠 **Codebase Memory** — {len(results)} result(s) for: '{query}'\n\n"
        for i, r in enumerate(results, 1):
            strategy = r.search_strategy or "local"
            output += f"### {i}. {r.title}\n"
            if r.file_path:
                output += f"**File:** `{r.file_path}`\n"
            output += f"**Type:** {r.memory_type.value} | **Search:** {strategy}\n"

            meta = r.metadata or {}
            if meta.get("root_cause"):
                output += f"**Root Cause:** {meta['root_cause']}\n"
            if meta.get("fix_description"):
                output += f"**Fix Applied:** {meta['fix_description']}\n"
            if not meta.get("root_cause"):
                output += f"{r.content[:300]}\n"
            output += "\n"

        return output

    @mcp.tool()
    async def remember_bug_fix(
        title: str,
        root_cause: str,
        fix_description: str,
        file_path: str,
        function_name: Optional[str] = None,
        severity: str = "medium",
        tags: str = "",
    ) -> str:
        """
        Permanently store a bug fix in the Cognee knowledge graph.
        Call this after fixing any non-trivial bug so the team never has to rediscover it.

        The fix is stored with typed CodeEntity extraction — Cognee will build
        graph nodes for the file, function, bug pattern, and fix strategy.

        Args:
            title: Short description of the bug (e.g. "NullPointerException in payment processor")
            root_cause: What actually caused the bug
            fix_description: How it was fixed
            file_path: File where the bug occurred (e.g. "services/payment_service.py")
            function_name: Specific function (optional)
            severity: low | medium | high | critical
            tags: Comma-separated tags (e.g. "null-check,api,payment")
        """
        client = get_client()
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        bug = BugFixMemory(
            title=title,
            root_cause=root_cause,
            fix_description=fix_description,
            file_path=file_path,
            function_name=function_name,
            severity=severity,
            tags=tag_list,
        )
        record = client.remember_bug(bug)

        msg = (
            f"✅ **Stored in codebase memory** (ID: `{record.id}`)\n"
            f"- Title: {title}\n"
            f"- File: `{file_path}`\n"
            f"- Severity: {severity}\n"
            f"\nCognee will extract typed graph entities (file→function→bug_pattern→fix) "
            f"and track this bug's pattern temporally."
        )
        return msg

    @mcp.tool()
    async def get_coding_rules(domain: Optional[str] = None) -> str:
        """
        Retrieve consolidated team coding rules for this codebase.
        These rules are synthesized by cognee.memify() from recurring bug patterns.

        Args:
            domain: Optional filter: validation | error-handling | api | concurrency |
                    database | security | general
        """
        client = get_client()
        rules = client.get_rules(domain=domain)

        if not rules:
            hint = " for domain '" + domain + "'" if domain else ""
            return (
                f"No coding rules found{hint}.\n"
                "Run `mnemosyne reflect` after storing several bug fixes to "
                "auto-generate team coding conventions via cognee.memify()."
            )

        output = f"📜 **{len(rules)} Coding Rule(s)**"
        if domain:
            output += f" (domain: {domain})"
        output += "\n\n"

        for rule in rules:
            meta = rule.metadata or {}
            conf = float(meta.get("confidence", 0.9))
            domain_label = meta.get("domain", "general")
            output += f"### {rule.title}\n"
            output += f"{rule.content.strip()}\n"
            output += f"*Domain: {domain_label} | Confidence: {conf:.0%}*\n\n"

        return output

    @mcp.tool()
    async def get_memory_status() -> str:
        """
        Get a summary of what's stored in codebase memory.
        Shows counts of bug fixes, rules, commits, and Cognee backend status.
        """
        client = get_client()
        all_memories = client.list_memories()
        bugs = [m for m in all_memories if m.memory_type == MemoryType.BUG_FIX]
        rules = [m for m in all_memories if m.memory_type == MemoryType.RULE]
        commits = [m for m in all_memories if m.memory_type == MemoryType.COMMIT]
        docs = [m for m in all_memories if m.memory_type == MemoryType.DOCUMENTATION]

        cognee_status = "✅ Active (Graph + Vector)" if client._cognee_initialized else "⚠️ Not initialized"

        return (
            f"📊 **Mnemosyne Codebase Memory Status**\n\n"
            f"| Category | Count |\n"
            f"|---|---|\n"
            f"| 🐛 Bug Fix Memories | {len(bugs)} |\n"
            f"| 📜 Coding Rules (memify) | {len(rules)} |\n"
            f"| 📝 Commit Memories | {len(commits)} |\n"
            f"| 📚 Documentation | {len(docs)} |\n"
            f"| **Total Graph Nodes** | **{len(all_memories)}** |\n\n"
            f"**Cognee Engine:** {cognee_status}\n"
            f"**Search Strategies:** GRAPH_COMPLETION + HYBRID_COMPLETION + CODING_RULES\n"
        )

    @mcp.tool()
    async def forget_memory(target: str) -> str:
        """
        Remove a memory from the codebase knowledge graph.
        Use when code is refactored or deleted and old memories are stale.

        Args:
            target: Memory ID (e.g. mem_bug_abc123) or file path substring
        """
        client = get_client()
        removed = client.forget(target)
        if removed:
            return f"✅ Forgot {len(removed)} memory item(s): {', '.join(removed)}"
        return f"No active memories matched '{target}'."

    return mcp


def run_server(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8765) -> None:
    """
    Start the Mnemosyne MCP server.

    Args:
        transport: "stdio" | "sse" | "http"
        host: Host for sse/http transport
        port: Port for sse/http transport
    """
    mcp = create_mcp_server()

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "sse":
        mcp.run(transport="sse", host=host, port=port)
    elif transport == "http":
        mcp.run(transport="streamable-http", host=host, port=port, path="/mcp")
    else:
        raise ValueError(f"Unknown transport: {transport}. Use stdio, sse, or http.")
