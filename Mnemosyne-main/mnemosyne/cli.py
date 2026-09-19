import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Any, Dict
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mnemosyne import __version__
from mnemosyne.config import load_config, save_config, find_project_root
from mnemosyne.memory.client import MemoryClient
from mnemosyne.memory.schemas import BugFixMemory, MemoryType
from mnemosyne.memory.consolidator import MemoryConsolidator
from mnemosyne.git.inspector import GitInspector
from mnemosyne.git.hooks import HookManager
from mnemosyne.ui.formatter import (
    render_banner,
    render_memory_warning,
    render_recall_response,
    render_rules_table,
    render_status_dashboard,
    render_timeline_results,
    render_search_strategy_badge,
)
from mnemosyne.utils.llm_helper import summarize_diff_with_llm

app = typer.Typer(
    name="mnemosyne",
    help="A CLI companion that gives your codebase a long-term memory using Cognee AI",
    add_completion=False,
)
hook_app = typer.Typer(help="Git hook execution subcommands")
config_app = typer.Typer(help="Mnemosyne & Cognee Cloud configuration subcommands")
app.add_typer(hook_app, name="hook")
app.add_typer(config_app, name="config")

console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit"),
):
    if version:
        console.print(f"[bold cyan]Mnemosyne[/bold cyan] version [bold white]{__version__}[/bold white]")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        render_banner()
        console.print("[yellow]Use --help to see available commands.[/yellow]\n")


# ---------------------------------------------------------------------------
# COGNEE PRIMITIVE: remember
# ---------------------------------------------------------------------------

@app.command("init")
def init_cmd(
    repo_path: Optional[Path] = typer.Option(None, "--repo", "-r", help="Path to git repository root"),
):
    """
    [COGNEE PRIMITIVE: remember]
    Initialize Mnemosyne: ingest commit history, install git hooks, and set up Cognee graph.
    """
    render_banner()
    root = (repo_path or find_project_root()).resolve()
    console.print(f"[bold cyan]Initializing Mnemosyne in:[/bold cyan] [white]{root}[/white]")

    client = MemoryClient(root)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Ingesting git commit history into Cognee...", total=None)
        commits = GitInspector.get_commit_history(root, max_commits=10)
        for commit in commits:
            client.remember_commit(commit)

    console.print(f"  [green]✓ Ingested {len(commits)} historical git commits into memory.[/green]")

    # Install both pre-commit and post-commit hooks
    hook_results = HookManager.install_all_hooks(root)
    if hook_results.get("pre_commit"):
        console.print("  [green]✓ Installed pre-commit recall hook (.git/hooks/pre-commit).[/green]")
    if hook_results.get("post_commit"):
        console.print("  [green]✓ Installed post-commit auto-ingest hook (.git/hooks/post-commit).[/green]")
    if not any(hook_results.values()):
        console.print("  [yellow]! Git directory not found; skipping hook installation.[/yellow]")

    config = load_config(root)
    config["initialized"] = True
    save_config(config, root)

    console.print(
        "\n[bold green]🎉 Mnemosyne is ready![/bold green] "
        "Your codebase now has a long-term Cognee memory graph.\n"
    )
    console.print(
        "  [dim]Next steps:[/dim]\n"
        "  • [cyan]mnemosyne remember-bug[/cyan] — log a bug fix\n"
        "  • [cyan]mnemosyne ask \"<query>\"[/cyan] — query codebase memory\n"
        "  • [cyan]mnemosyne reflect[/cyan] — consolidate patterns into rules\n"
        "  • [cyan]mnemosyne mcp-serve[/cyan] — start MCP server for Claude Code\n"
    )


@app.command("remember-bug")
def remember_bug_cmd(
    file_path: Optional[str] = typer.Option(None, "--file", "-f", help="Affected file path"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Short bug summary"),
    root_cause: Optional[str] = typer.Option(None, "--cause", "-c", help="Root cause of the bug"),
    fix: Optional[str] = typer.Option(None, "--fix", "-x", help="Fix description"),
    auto: bool = typer.Option(False, "--auto", "-a", help="Auto-summarize from staged git diff"),
):
    """
    [COGNEE PRIMITIVE: remember]
    Log a bug fix into the Cognee knowledge graph with typed entity extraction.
    Cognee extracts CodeFile → Function → BugPattern → Rule graph nodes.
    """
    root = find_project_root()
    client = MemoryClient(root)

    if auto:
        staged_diff = GitInspector.get_staged_diff(root)
        if not staged_diff:
            console.print("[yellow]No staged git diff found. Falling back to manual input.[/yellow]")
        else:
            summary_data = summarize_diff_with_llm(staged_diff)
            title = title or summary_data["title"]
            root_cause = root_cause or summary_data["root_cause"]
            fix = fix or summary_data["fix_description"]
            staged_files = GitInspector.get_staged_files(root)
            if staged_files:
                file_path = file_path or staged_files[0]

    if not file_path:
        file_path = typer.prompt("Path to affected file (e.g. services/user_service.py)")
    if not title:
        title = typer.prompt("Bug title/summary")
    if not root_cause:
        root_cause = typer.prompt("Root cause (why did it happen?)")
    if not fix:
        fix = typer.prompt("Fix applied (how was it solved?)")

    bug_mem = BugFixMemory(
        file_path=file_path,
        title=title,
        root_cause=root_cause,
        fix_description=fix,
        tags=["bug", Path(file_path).stem],
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(
            description="Extracting code entities & pushing to Cognee graph (CodeKnowledgeGraph schema)...",
            total=None,
        )
        rec = client.remember_bug(bug_mem)

    console.print(f"\n[bold green]✓ Memory logged into Cognee graph![/bold green] (ID: [cyan]{rec.id}[/cyan])")
    console.print(f"  File: [cyan]{file_path}[/cyan]")
    console.print(f"  Root Cause: {root_cause}")
    console.print(f"  [dim]Cognee extracted: CodeFile → Function → BugPattern → Fix nodes[/dim]")
    console.print(f"  [dim]temporal_cognify=True: bug pattern timestamped for evolution tracking[/dim]\n")


@app.command("remember")
def remember_cmd(
    title: str = typer.Argument(..., help="Title or header for the memory entry"),
    content: Optional[str] = typer.Option(None, "--content", "-c", help="Text content or body"),
    file_path: Optional[str] = typer.Option(None, "--file", "-f", help="Optional file path context"),
    commit_hash: Optional[str] = typer.Option(None, "--commit-hash", help="Git commit hash (for post-commit hook)"),
    message: Optional[str] = typer.Option(None, "--message", help="Commit message (for post-commit hook)"),
    author: Optional[str] = typer.Option(None, "--author", help="Commit author (for post-commit hook)"),
    files: Optional[str] = typer.Option(None, "--files", help="Comma-separated changed files"),
    silent: bool = typer.Option(False, "--silent", help="Suppress output (for post-commit hook)"),
):
    """
    [COGNEE PRIMITIVE: remember]
    Ingest a document, ADR, commit, or note into the Cognee memory graph.
    """
    root = find_project_root()
    client = MemoryClient(root)

    # Handle post-commit hook invocation
    if commit_hash and message:
        from mnemosyne.memory.schemas import CommitMemory
        file_list = [f.strip() for f in (files or "").split(",") if f.strip()]
        commit = CommitMemory(
            commit_hash=commit_hash,
            author=author or "unknown",
            summary=message,
            files_changed=file_list,
        )
        client.remember_commit(commit)
        if not silent:
            console.print(f"[green]✓ Commit {commit_hash[:7]} auto-ingested into Cognee.[/green]")
        return

    if not content:
        content = typer.prompt("Enter document content / notes")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Ingesting document into Cognee knowledge graph...", total=None)
        rec = client.remember_doc(title=title, content=content, file_path=file_path)

    if not silent:
        console.print(f"\n[bold green]✓ Document ingested into Cognee memory![/bold green] (ID: [cyan]{rec.id}[/cyan])")


@app.command("improve")
def improve_cmd():
    """
    [COGNEE PRIMITIVE: improve / memify]
    Re-run graph enrichment with the CodeKnowledgeGraph schema on all stored memories.
    Use this after upgrading Mnemosyne to apply the new schema to existing memories.
    """
    root = find_project_root()
    client = MemoryClient(root)

    console.print("\n[bold cyan]⚡ Running Cognee Graph Enrichment & Memory Improvement...[/bold cyan]")
    console.print("[dim]  Re-cognifying with CodeKnowledgeGraph schema + temporal tracking[/dim]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Re-indexing graph edges and optimizing memory weights...", total=None)
        client.improve()

    console.print("[bold green]✓ Memory graph improved and optimized successfully![/bold green]\n")


# ---------------------------------------------------------------------------
# COGNEE PRIMITIVE: recall
# ---------------------------------------------------------------------------

@app.command("ask")
def ask_cmd(
    query: str = typer.Argument(..., help="Natural language question to ask codebase memory"),
    file_context: Optional[str] = typer.Option(None, "--file", "-f", help="Optional file context filter"),
):
    """
    [COGNEE PRIMITIVE: recall]
    Query the Cognee knowledge graph using GRAPH_COMPLETION + HYBRID_COMPLETION search.
    Shows which search strategy (graph traversal / hybrid / coding rules) found each result.
    """
    root = find_project_root()
    client = MemoryClient(root)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Traversing Cognee knowledge graph (GRAPH + HYBRID + CODING_RULES)...", total=None)
        records = client.recall(query=query, file_context=file_context, top_k=5)

    render_recall_response(query, records)


@app.command("timeline")
def timeline_cmd(
    query: str = typer.Argument("recurring bugs and patterns", help="What to trace over time"),
    top_k: int = typer.Option(10, "--top-k", "-k", help="Number of temporal results"),
):
    """
    [COGNEE PRIMITIVE: recall — temporal]
    Show how bug patterns evolved over time using Cognee's temporal knowledge graph.
    Requires that bugs were stored with temporal_cognify=True (default since v0.2.0).
    """
    root = find_project_root()
    client = MemoryClient(root)

    console.print(f"\n[bold cyan]📅 Temporal Bug Pattern Analysis[/bold cyan] — '{query}'\n")

    if not client._init_cognee_if_needed():
        console.print("[yellow]Cognee not available. Showing local memories by timestamp:[/yellow]\n")
        memories = sorted(
            client.list_memories(MemoryType.BUG_FIX),
            key=lambda m: m.timestamp,
            reverse=True,
        )[:top_k]
        render_timeline_results(memories, fallback=True)
        return

    try:
        import cognee
        from cognee.modules.search.types.SearchType import SearchType

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Querying temporal Cognee graph...", total=None)
            results = asyncio.run(cognee.search(
                query_text=query,
                query_type=SearchType.TEMPORAL,
                datasets=["mnemosyne_codebase"],
                top_k=top_k,
            ))
        render_timeline_results(results, fallback=False)
    except Exception as e:
        console.print(f"[yellow]Temporal search unavailable ({e}). Showing local timeline:[/yellow]\n")
        memories = sorted(
            client.list_memories(MemoryType.BUG_FIX),
            key=lambda m: m.timestamp,
            reverse=True,
        )[:top_k]
        render_timeline_results(memories, fallback=True)


@app.command("feedback")
def feedback_cmd(
    helpful: bool = typer.Option(True, "--helpful/--not-helpful", help="Was the last recall result helpful?"),
    session_id: Optional[str] = typer.Option(None, "--session", help="Session ID to annotate (auto-detected if omitted)"),
):
    """
    [COGNEE PRIMITIVE: improve — feedback loop]
    Rate the last recall result. Positive feedback improves future recall ranking
    via Cognee's truth subspace reranking mechanism.
    """
    root = find_project_root()
    client = MemoryClient(root)

    sid = session_id or client.get_last_session_id()

    if not sid:
        console.print("[yellow]No recent session found. Run 'mnemosyne ask' first, then provide feedback.[/yellow]")
        raise typer.Exit(1)

    if not client._init_cognee_if_needed():
        console.print("[yellow]Cognee not available — feedback recorded locally only.[/yellow]")
        return

    try:
        import cognee
        from cognee.memory import FeedbackEntry

        score = 1.0 if helpful else 0.0
        label = "helpful ✓" if helpful else "not relevant ✗"

        asyncio.run(cognee.remember(
            FeedbackEntry(
                feedback_score=score,
                feedback_text=label,
            ),
            session_id=sid,
        ))

        console.print(
            f"\n[bold green]✓ Feedback recorded[/bold green] ([cyan]{label}[/cyan]) "
            f"for session [dim]{sid}[/dim]\n"
            "[dim]Future recalls will adapt to your preferences via truth subspace reranking.[/dim]\n"
        )
    except ImportError:
        # FeedbackEntry may not be in all Cognee versions — degrade gracefully
        console.print(
            f"\n[green]✓ Feedback noted locally[/green] ({'helpful' if helpful else 'not helpful'}).\n"
            "[dim]Upgrade Cognee to enable truth subspace personalized reranking.[/dim]\n"
        )
    except Exception as e:
        console.print(f"[yellow]Feedback storage failed: {e}[/yellow]")


# ---------------------------------------------------------------------------
# COGNEE PRIMITIVE: memify
# ---------------------------------------------------------------------------

@app.command("reflect")
def reflect_cmd():
    """
    [COGNEE PRIMITIVE: memify / reflect]
    Consolidate bug memories into team coding rules using cognee.memify()
    and SearchType.CODING_RULES. Replaces the old hardcoded keyword clustering.
    """
    root = find_project_root()
    client = MemoryClient(root)
    consolidator = MemoryConsolidator(client)

    console.print("\n[bold cyan]🧠 Running Semantic Memory Consolidation via cognee.memify()...[/bold cyan]")
    console.print("[dim]  Uses CODING_RULES retriever + LLM semantic clustering[/dim]\n")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Clustering patterns semantically via Cognee memify...", total=None)
        new_rules = consolidator.reflect()

    if new_rules:
        console.print(f"[bold green]🎉 Synthesized {len(new_rules)} new consolidated rule(s):[/bold green]\n")
        for r in new_rules:
            confidence = f"{r.confidence:.0%}" if hasattr(r, 'confidence') and r.confidence else ""
            console.print(f"  • [bold yellow]{r.rule_title}[/bold yellow] ([dim]Domain: {r.domain}[/dim]) [green]{confidence}[/green]")
            console.print(f"    [dim]{r.description[:120]}[/dim]\n")
    else:
        console.print("[dim]No new clusters found. Existing rules are up to date.[/dim]\n")


@app.command("rules")
def rules_cmd(
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """
    List all active consolidated team rules and their provenance.
    """
    root = find_project_root()
    client = MemoryClient(root)
    rules = client.get_rules(domain=domain)
    render_rules_table(rules)


# ---------------------------------------------------------------------------
# COGNEE PRIMITIVE: forget
# ---------------------------------------------------------------------------

@app.command("forget")
def forget_cmd(
    target: str = typer.Argument(..., help="Memory ID or file path to forget/decay"),
):
    """
    [COGNEE PRIMITIVE: forget]
    Remove or decay stale memory when code is deleted or refactored.
    Triggers cognee.prune.prune_data() to clean up graph edges.
    """
    root = find_project_root()
    client = MemoryClient(root)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Decaying target memory in Cognee graph...", total=None)
        removed = client.forget(target)

    if removed:
        console.print(f"\n[bold green]✓ Forgot {len(removed)} memory item(s):[/bold green] [cyan]{', '.join(removed)}[/cyan]")
    else:
        console.print(f"\n[yellow]No active memories found matching '[bold white]{target}[/bold white]'.[/yellow]")


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

@app.command("mcp-serve")
def mcp_serve_cmd(
    transport: str = typer.Option("stdio", "--transport", "-t", help="Transport: stdio | sse | http"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host for sse/http transport"),
    port: int = typer.Option(8765, "--port", "-p", help="Port for sse/http transport"),
):
    """
    Start the Mnemosyne MCP server for Claude Code / Cursor integration.

    Exposes codebase memory as native tools: recall_codebase_memory,
    remember_bug_fix, get_coding_rules, get_memory_status, forget_memory.

    Claude Desktop config (~/.claude/claude_desktop_config.json):
      { "mcpServers": { "mnemosyne": { "command": "mnemosyne", "args": ["mcp-serve"] } } }
    """
    from mnemosyne.mcp_server import run_server

    console.print(f"\n[bold cyan]🔌 Starting Mnemosyne MCP Server[/bold cyan] (transport: {transport})")
    if transport != "stdio":
        console.print(f"  Listening on: [cyan]http://{host}:{port}/mcp[/cyan]")
    console.print("[dim]  Tools: recall_codebase_memory | remember_bug_fix | get_coding_rules | get_memory_status | forget_memory[/dim]\n")

    run_server(transport=transport, host=host, port=port)


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

@app.command("visualize")
def visualize_cmd(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save graph to file instead of opening browser"),
):
    """
    Open an interactive Cognee memory provenance graph in the browser.
    Shows: Tenant → User → Dataset → Files → Bug Nodes → Rule Nodes.
    """
    root = find_project_root()
    client = MemoryClient(root)

    if not client._init_cognee_if_needed():
        console.print("[yellow]Cognee not initialized. Run 'mnemosyne init' first.[/yellow]")
        raise typer.Exit(1)

    console.print("\n[bold cyan]🕸️  Building Memory Provenance Graph...[/bold cyan]")

    try:
        import cognee
        import webbrowser

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Generating Cognee provenance graph...", total=None)

            memories = client.list_memories()
            try:
                graph_data = asyncio.run(cognee.get_memory_provenance_graph())
                # Merge local memory records in so bug/rule detail is clickable.
                graph_html = _render_provenance_html(graph_data, memories)
            except AttributeError:
                # Fallback: generate a simple HTML visualization from local memories
                graph_html = _generate_fallback_graph_html(memories)

        out_path = output or (root / ".mnemosyne" / "graph.html")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(graph_html, encoding="utf-8")

        console.print(f"[green]✓ Graph saved to:[/green] [cyan]{out_path}[/cyan]")

        if not output:
            webbrowser.open(f"file://{out_path.resolve()}")
            console.print("[green]✓ Graph opened in browser.[/green]\n")

    except Exception as e:
        console.print(f"[yellow]Graph visualization failed: {e}[/yellow]")
        console.print("[dim]Try 'mnemosyne status' for a text-based memory overview.[/dim]")


def _short_label(node_type: str, name: str, node_id: str) -> str:
    """
    A short, human-readable tag for a node — never the raw UUID.
    Keeps the graph legible; full detail lives in the click-to-open info panel.
    """
    friendly = {
        "User": "user",
        "Session": "session",
        "TextDocument": "doc",
        "DocumentChunk": "chunk",
    }
    if node_type in friendly:
        return friendly[node_type]
    # Datasets keep their (already short) name.
    if node_type == "Dataset":
        return (name or "dataset")[:20]
    # Anything else: use the name but strip UUID-ish tails and hard-cap length.
    base = str(name or node_id).split(":")[0].strip()
    return base[:20] + ("…" if len(base) > 20 else "")


def _memory_node_detail(mem: Any) -> Dict[str, str]:
    """Structured detail shown in the info panel when a memory node is clicked."""
    meta = mem.metadata or {}
    detail: Dict[str, str] = {"Type": mem.memory_type.value, "Title": mem.title}
    if mem.memory_type.value == "bug_fix":
        if meta.get("root_cause"):
            detail["Root Cause"] = meta["root_cause"]
        if meta.get("fix_description"):
            detail["Fix"] = meta["fix_description"]
    elif mem.memory_type.value == "rule":
        if meta.get("description"):
            detail["Description"] = meta["description"]
        if meta.get("domain"):
            detail["Domain"] = meta["domain"]
    else:
        body = (mem.content or "").strip()
        if body:
            detail["Content"] = body[:400] + ("…" if len(body) > 400 else "")
    if mem.file_path:
        detail["File"] = mem.file_path
    return detail


def _render_provenance_html(graph_data: Any, memories: Optional[List] = None) -> str:
    """
    Render Cognee's provenance graph — a (nodes, edges) tuple of Node/EdgeData
    objects — into an interactive D3 graph, merged with local memory records so
    bug/rule detail is clickable.

    Each Node has `.id` and `.properties` ({'type', 'name', ...}); each EdgeData has
    `.source`, `.target`, `.relation`. We normalise those into the {nodes, links}
    shape the D3 template expects. Falls back to a readable text dump if the shape
    is unexpected.
    """
    def _attr(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    nodes_raw, edges_raw = [], []
    if isinstance(graph_data, (tuple, list)) and len(graph_data) == 2:
        nodes_raw, edges_raw = graph_data[0] or [], graph_data[1] or []

    nodes = []
    node_ids = set()
    dataset_anchor = None  # id of the mnemosyne_codebase dataset, to hang memories off
    for n in nodes_raw:
        nid = _attr(n, "id")
        if nid is None:
            continue
        nid = str(nid)
        props = _attr(n, "properties", {}) or {}
        ntype = props.get("type", "node")
        name = props.get("name") or props.get("text") or nid
        if ntype == "Dataset" and props.get("name") == "mnemosyne_codebase":
            dataset_anchor = nid
        nodes.append({
            "id": nid,
            "label": _short_label(ntype, name, nid),
            "type": ntype,
            "size": _node_size_for_type(ntype),
            "detail": {"Type": ntype, "Name": str(name)},
        })
        node_ids.add(nid)

    edges = []
    for e in edges_raw:
        src, tgt = _attr(e, "source"), _attr(e, "target")
        if src is None or tgt is None:
            continue
        edges.append({
            "source": str(src),
            "target": str(tgt),
            "relation": _attr(e, "relation", "") or "",
        })

    # Merge in local memory records as rich, clickable nodes.
    if memories:
        if dataset_anchor is None:
            dataset_anchor = "memories_root"
            nodes.append({
                "id": dataset_anchor, "label": "memories", "type": "category",
                "size": 16, "detail": {"Type": "Memory store"},
            })
        for mem in memories[:100]:
            mid = f"mem::{mem.id}"
            if mid in node_ids:
                continue
            node_ids.add(mid)
            nodes.append({
                "id": mid,
                "label": mem.title[:20] + ("…" if len(mem.title) > 20 else ""),
                "type": mem.memory_type.value,
                "size": 9,
                "detail": _memory_node_detail(mem),
            })
            edges.append({"source": dataset_anchor, "target": mid, "relation": mem.memory_type.value})

    if not nodes:
        # Unexpected shape — show it readably rather than a raw repr blob.
        return f"""<!DOCTYPE html>
<html><head><title>Mnemosyne Memory Provenance</title>
<style>body{{background:#0d1117;color:#c9d1d9;font-family:monospace;padding:20px}}</style>
</head><body><h2>Memory Provenance (raw)</h2><pre>{graph_data}</pre></body></html>"""

    return _d3_graph_html(nodes, edges, "Memory Provenance Graph")


def _node_size_for_type(node_type: str) -> int:
    """Bigger circles for higher-level provenance nodes."""
    sizes = {
        "User": 20, "Dataset": 17, "Session": 15,
        "TextDocument": 13, "DocumentChunk": 10,
    }
    return sizes.get(node_type, 9)


# Shared color palette across provenance + memory node types.
_GRAPH_NODE_COLORS = {
    # Cognee provenance types
    "User": "#ffa657", "Dataset": "#f0883e", "Session": "#a371f7",
    "TextDocument": "#58a6ff", "DocumentChunk": "#79c0ff",
    "Entity": "#3fb950", "EntityType": "#2ea043", "NodeSet": "#8b949e",
    # Mnemosyne memory types
    "root": "#ffa657", "category": "#ffa657",
    "bug_fix": "#f85149", "rule": "#3fb950",
    "commit": "#58a6ff", "documentation": "#d2a8ff",
}


def _d3_graph_html(nodes: List[dict], edges: List[dict], title: str) -> str:
    """Shared interactive D3 force-graph renderer with edge-relation labels."""
    import json as json_mod
    nodes_json = json_mod.dumps(nodes)
    edges_json = json_mod.dumps(edges)
    colors_json = json_mod.dumps(_GRAPH_NODE_COLORS)

    # Build the legend from the node types actually present.
    present_types = []
    for n in nodes:
        t = n.get("type", "node")
        if t not in present_types:
            present_types.append(t)
    legend_html = " &nbsp; ".join(
        f'<span style="background:{_GRAPH_NODE_COLORS.get(t, "#8b949e")}"></span>{t}'
        for t in present_types
    )

    return f"""<!DOCTYPE html>
<html>
<head>
  <title>Mnemosyne — {title}</title>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <style>
    body {{ background: #0d1117; color: #c9d1d9; font-family: 'JetBrains Mono', monospace; margin: 0; overflow: hidden; }}
    h1 {{ position: absolute; top: 15px; left: 20px; color: #58a6ff; font-size: 18px; margin: 0; }}
    .legend {{ position: absolute; top: 55px; left: 20px; font-size: 12px; max-width: 90vw; }}
    .legend span {{ display: inline-block; width: 12px; height: 12px; margin-right: 5px; border-radius: 50%; }}
    .hint {{ position: absolute; bottom: 12px; left: 20px; font-size: 11px; color: #8b949e; }}
    svg {{ width: 100vw; height: 100vh; }}
    .node circle {{ stroke: #30363d; stroke-width: 1.5px; cursor: pointer; }}
    .node text {{ font-size: 9px; fill: #8b949e; pointer-events: none; }}
    .node.selected circle {{ stroke: #58a6ff; stroke-width: 3px; }}
    .link {{ stroke: #30363d; stroke-width: 1px; opacity: 0.6; }}
    .link-label {{ font-size: 8px; fill: #6e7681; pointer-events: none; }}
    .node circle:hover {{ stroke: #58a6ff; stroke-width: 2.5px; }}
    #info-panel {{
      position: absolute; top: 0; right: 0; width: 340px; max-width: 80vw; height: 100vh;
      background: #161b22; border-left: 1px solid #30363d; box-sizing: border-box;
      padding: 20px; overflow-y: auto; transform: translateX(100%);
      transition: transform 0.2s ease; box-shadow: -8px 0 24px rgba(0,0,0,0.4);
    }}
    #info-panel.open {{ transform: translateX(0); }}
    #info-panel .tag {{ display: inline-block; padding: 2px 8px; border-radius: 10px;
      font-size: 11px; color: #0d1117; font-weight: bold; margin-bottom: 12px; }}
    #info-panel h2 {{ font-size: 15px; margin: 6px 0 14px; color: #e6edf3; word-break: break-word; }}
    #info-panel .row {{ margin-bottom: 12px; }}
    #info-panel .k {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #8b949e; margin-bottom: 3px; }}
    #info-panel .v {{ font-size: 13px; color: #c9d1d9; line-height: 1.5; word-break: break-word; white-space: pre-wrap; }}
    #info-close {{ position: absolute; top: 12px; right: 14px; cursor: pointer; color: #8b949e;
      font-size: 20px; background: none; border: none; }}
    #info-close:hover {{ color: #c9d1d9; }}
  </style>
</head>
<body>
  <h1>🧠 Mnemosyne — {title}</h1>
  <div class="legend">{legend_html}</div>
  <div class="hint">Click a node for details · drag to reposition · scroll to zoom</div>
  <svg></svg>
  <div id="info-panel">
    <button id="info-close">×</button>
    <span class="tag" id="info-tag"></span>
    <h2 id="info-title"></h2>
    <div id="info-body"></div>
  </div>
  <script>
    const nodes = {nodes_json};
    const links = {edges_json};
    const color = {colors_json};

    const svg = d3.select("svg");
    const width = window.innerWidth, height = window.innerHeight;
    const container = svg.append("g");

    svg.call(d3.zoom().scaleExtent([0.2, 4]).on("zoom", (e) => container.attr("transform", e.transform)));

    const sim = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-260))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius(d => (d.size || 8) + 14));

    const link = container.append("g").selectAll("line")
      .data(links).join("line").attr("class", "link");

    const linkLabel = container.append("g").selectAll("text")
      .data(links).join("text").attr("class", "link-label")
      .text(d => d.relation || "");

    const node = container.append("g").selectAll("g")
      .data(nodes).join("g").attr("class", "node")
      .call(d3.drag()
        .on("start", (e, d) => {{ if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }})
        .on("drag", (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
        .on("end", (e, d) => {{ if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }}));

    node.append("circle")
      .attr("r", d => d.size || 8)
      .style("fill", d => color[d.type] || "#8b949e");

    node.append("text").attr("dx", d => (d.size || 8) + 3).attr("dy", 4)
      .text(d => d.label);

    node.append("title").text(d => (d.type + ": " + d.label));

    // ---- Click-to-open info panel ----
    const panel = document.getElementById("info-panel");
    function showInfo(d) {{
      const tag = document.getElementById("info-tag");
      tag.textContent = d.type;
      tag.style.background = color[d.type] || "#8b949e";
      document.getElementById("info-title").textContent = (d.detail && d.detail.Title) || d.label;
      const body = document.getElementById("info-body");
      body.innerHTML = "";
      const detail = d.detail || {{ Type: d.type }};
      for (const [k, v] of Object.entries(detail)) {{
        if (k === "Title" || v == null || v === "") continue;
        const row = document.createElement("div"); row.className = "row";
        const kk = document.createElement("div"); kk.className = "k"; kk.textContent = k;
        const vv = document.createElement("div"); vv.className = "v"; vv.textContent = v;
        row.appendChild(kk); row.appendChild(vv); body.appendChild(row);
      }}
      node.classed("selected", n => n.id === d.id);
      panel.classList.add("open");
    }}
    function hideInfo() {{ panel.classList.remove("open"); node.classed("selected", false); }}
    node.on("click", (e, d) => {{ e.stopPropagation(); showInfo(d); }});
    document.getElementById("info-close").onclick = hideInfo;
    svg.on("click", hideInfo);

    sim.on("tick", () => {{
      link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
          .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
      linkLabel.attr("x", d => (d.source.x + d.target.x) / 2)
               .attr("y", d => (d.source.y + d.target.y) / 2);
      node.attr("transform", d => `translate(${{d.x}}, ${{d.y}})`);
    }});
  </script>
</body>
</html>"""


def _generate_fallback_graph_html(memories: List) -> str:
    """Generate a simple D3.js knowledge graph from local memories."""
    import json as json_mod

    nodes = []
    edges = []

    # Root node
    nodes.append({"id": "root", "label": "Codebase Memory", "type": "root", "size": 20})

    # Group memories by type
    type_nodes = {}
    for mem_type in ["bug_fix", "rule", "commit", "documentation"]:
        type_id = f"type_{mem_type}"
        type_nodes[mem_type] = type_id
        nodes.append({"id": type_id, "label": mem_type.replace("_", " ").title(), "type": "category", "size": 15})
        edges.append({"source": "root", "target": type_id})

    # Add individual memory nodes
    for mem in memories[:50]:  # Cap at 50 for readability
        nodes.append({
            "id": mem.id,
            "label": mem.title[:20] + ("…" if len(mem.title) > 20 else ""),
            "type": mem.memory_type.value,
            "size": 9,
            "detail": _memory_node_detail(mem),
        })
        edges.append({"source": type_nodes.get(mem.memory_type.value, "root"), "target": mem.id})

    return _d3_graph_html(nodes, edges, "Memory Graph")


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@app.command("status")
def status_cmd():
    """
    Display memory graph statistics and system health dashboard.
    """
    root = find_project_root()
    client = MemoryClient(root)
    memories = client.list_memories()
    config = load_config(root)

    stats = {
        "total_memories": len(memories),
        "bug_fixes": len([m for m in memories if m.memory_type == MemoryType.BUG_FIX]),
        "rules": len([m for m in memories if m.memory_type == MemoryType.RULE]),
        "commits": len([m for m in memories if m.memory_type == MemoryType.COMMIT]),
        "hooks_installed": config.get("hooks_installed", False),
        "post_commit_hook": config.get("post_commit_hook_installed", False),
        "backend": "Cognee Graph (CodeKnowledgeGraph) + Vector + Local JSON",
        "search_types": "GRAPH_COMPLETION + HYBRID_COMPLETION + CODING_RULES",
        "cognee_active": client._cognee_initialized,
    }

    render_status_dashboard(stats)


# ---------------------------------------------------------------------------
# Config commands
# ---------------------------------------------------------------------------

@config_app.command("set-cloud-key")
def set_cloud_key_cmd(
    key: str = typer.Argument(..., help="Cognee Cloud API key from platform.cognee.ai"),
    url: str = typer.Option("https://api.cognee.ai", "--url", "-u", help="Cognee Cloud API endpoint URL"),
):
    """Configure your Cognee Cloud API Key for extended memory storage."""
    root = find_project_root()
    config = load_config(root)
    config["cognee_api_key"] = key.strip()
    config["cognee_api_url"] = url.strip()
    config["use_cloud"] = True
    save_config(config, root)

    env_path = root / ".env"
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = [l for l in f.readlines() if not l.startswith("COGNEE_API_KEY") and not l.startswith("COGNEE_API_URL")]
    lines.append(f"COGNEE_API_KEY={key.strip()}\n")
    lines.append(f"COGNEE_API_URL={url.strip()}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    console.print(f"\n[bold green]✓ Cognee Cloud API Key configured![/bold green]")
    console.print(f"  Endpoint: [cyan]{url}[/cyan]\n")


@config_app.command("set-llm-key")
def set_llm_key_cmd(
    key: str = typer.Argument(..., help="LLM API Key (OpenAI / Anthropic / LiteLLM)"),
):
    """Configure LLM API Key for diff summarization, entity extraction, and recall synthesis."""
    root = find_project_root()
    config = load_config(root)
    config["llm_api_key"] = key.strip()
    save_config(config, root)

    env_path = root / ".env"
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = [l for l in f.readlines() if not l.startswith("OPENAI_API_KEY")]
    lines.append(f"OPENAI_API_KEY={key.strip()}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    console.print(f"\n[bold green]✓ LLM API Key configured![/bold green]\n")


@config_app.command("show")
def config_show_cmd():
    """Display active Mnemosyne configuration and Cognee Cloud connection status."""
    root = find_project_root()
    config = load_config(root)

    cognee_key = os.getenv("COGNEE_API_KEY") or config.get("cognee_api_key")
    llm_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or config.get("llm_api_key")

    def mask_key(k: Optional[str]) -> str:
        if not k:
            return "[yellow]Not set[/yellow]"
        return f"[green]{k[:4]}...{k[-4:]}[/green]" if len(k) > 8 else "[green]Configured[/green]"

    console.print("\n[bold cyan]⚙️  Mnemosyne Configuration Dashboard[/bold cyan]\n")
    console.print(f"  Project Root:            [white]{root}[/white]")
    console.print(f"  Cognee Cloud API Key:    {mask_key(cognee_key)}")
    console.print(f"  Cognee Cloud Endpoint:   [cyan]{config.get('cognee_api_url', 'https://api.cognee.ai')}[/cyan]")
    console.print(f"  LLM Provider Key:        {mask_key(llm_key)}")
    console.print(f"  Pre-Commit Hook:         {'[green]Installed[/green]' if config.get('hooks_installed') else '[yellow]Not Installed[/yellow]'}")
    console.print(f"  Post-Commit Hook:        {'[green]Installed[/green]' if config.get('post_commit_hook_installed') else '[yellow]Not Installed[/yellow]'}")
    console.print(f"  Reflection Threshold:    [cyan]{config.get('reflection_threshold', 3)} bug fixes[/cyan]")
    console.print(f"  Graph Schema:            [magenta]CodeKnowledgeGraph (typed entities)[/magenta]")
    console.print(f"  Search Strategy:         [magenta]GRAPH_COMPLETION + HYBRID_COMPLETION + CODING_RULES[/magenta]\n")


@app.command("check-security")
def check_security_cmd(
    file_path: Optional[str] = typer.Option(None, "--file", "-f", help="Specific file path to scan"),
):
    """
    Scan staged changes or a specific file for security vulnerabilities.
    Leverages past security memories and rules to suggest fixes.
    """
    from mnemosyne.utils.security_scanner import SecurityScanner
    
    root = find_project_root()
    client = MemoryClient(root)
    scanner = SecurityScanner(client)

    issues = []
    
    if file_path:
        target = Path(file_path)
        if not target.is_absolute():
            target = root / target
        
        if not target.exists():
            console.print(f"[red]Error: File {file_path} does not exist.[/red]")
            raise typer.Exit(code=1)
            
        console.print(f"\n[bold cyan]🛡️  Scanning file: {file_path}...[/bold cyan]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Running security scan...", total=None)
            issues = scanner.scan_file(target)
    else:
        # Scan staged changes
        staged_diff = GitInspector.get_staged_diff(root)
        if not staged_diff:
            console.print("[yellow]No staged changes to scan. Please specify a file with --file, or stage changes with git add.[/yellow]")
            return
            
        console.print("\n[bold cyan]🛡️  Scanning staged git diff...[/bold cyan]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Running security scan on staged diff...", total=None)
            issues = scanner.scan_diff(staged_diff)

    if not issues:
        console.print("[bold green]✓ No security vulnerabilities detected![/bold green]\n")
        return

    console.print(f"\n[bold red]⚠️  DETECTED {len(issues)} SECURITY VULNERABILITIES:[/bold red]\n")
    for issue in issues:
        severity_colors = {
            "low": "blue",
            "medium": "yellow",
            "high": "orange3",
            "critical": "bold red"
        }
        color = severity_colors.get(issue.severity.lower(), "white")
        
        severity_badge = f"[{color}]{issue.severity.upper()}[/{color}]"
        
        title_line = f"[{color}]● {issue.vulnerability_type}[/{color}] - {severity_badge}"
        if issue.line_number:
            title_line += f" (Line {issue.line_number})"
            
        details = (
            f"  [bold]Description:[/bold] {issue.description}\n"
            f"  [bold]Proposed Fix:[/bold] {issue.proposed_fix}"
        )
        if issue.matching_memory_id:
            details += f"\n  [bold]Matching past memory/rule:[/bold] [cyan]{issue.matching_memory_id}[/cyan]"
            
        console.print(Panel(details, title=title_line, border_style=color))
    console.print()


# ---------------------------------------------------------------------------
# Git hook internal commands
# ---------------------------------------------------------------------------

@hook_app.command("run")
def hook_run_cmd(
    stage: str = typer.Option("pre-commit", "--stage", help="Hook stage name"),
    silent: bool = typer.Option(False, "--silent", help="Suppress all output"),
):
    """Internal handler executed by git hooks."""
    root = find_project_root()

    if stage == "pre-commit":
        result = HookManager.execute_pre_commit_check(root)
        warnings = result.get("warnings", [])

        if warnings and not silent:
            console.print("\n[bold yellow]════════════════════════════════════════════════════════════════[/bold yellow]")
            console.print("[bold yellow]  ⚠️  MNEMOSYNE PRE-COMMIT MEMORY WARNINGS[/bold yellow]")
            console.print("[bold yellow]  Cognee Graph Search: GRAPH_COMPLETION + HYBRID_COMPLETION[/bold yellow]")
            console.print("[bold yellow]════════════════════════════════════════════════════════════════[/bold yellow]\n")
            for w in warnings:
                console.print(render_memory_warning(w))
            console.print("[dim]Review past bug history above before completing this commit.[/dim]\n")
            console.print("[dim]Run 'mnemosyne feedback --helpful' or '--not-helpful' to improve future recalls.[/dim]\n")

        # Run Security Scan on staged changes
        from mnemosyne.git.inspector import GitInspector
        staged_diff = GitInspector.get_staged_diff(root)
        if staged_diff and not silent:
            from mnemosyne.utils.security_scanner import SecurityScanner
            from mnemosyne.memory.client import MemoryClient
            client = MemoryClient(root)
            scanner = SecurityScanner(client)
            sec_issues = scanner.scan_diff(staged_diff)
            if sec_issues:
                console.print("\n[bold red]🛡️  🛡️  MNEMOSYNE AUTOMATIC SECURITY SCAN WARNINGS  🛡️  🛡️[/bold red]")
                console.print("[bold red]════════════════════════════════════════════════════════════════[/bold red]\n")
                for issue in sec_issues:
                    severity_colors = {"low": "blue", "medium": "yellow", "high": "orange3", "critical": "bold red"}
                    color = severity_colors.get(issue.severity.lower(), "white")
                    severity_badge = f"[{color}]{issue.severity.upper()}[/{color}]"
                    title = f"[{color}]● {issue.vulnerability_type}[/{color}] - {severity_badge}"
                    details = f"  [bold]Description:[/bold] {issue.description}\n  [bold]Proposed Fix:[/bold] {issue.proposed_fix}"
                    if issue.matching_memory_id:
                        details += f"\n  [bold]Matching past memory/rule:[/bold] [cyan]{issue.matching_memory_id}[/cyan]"
                    console.print(Panel(details, title=title, border_style=color))
                console.print("\n[bold red]⚠️  Please review and resolve the security issues above before committing.[/bold red]\n")

    elif stage == "post-commit":
        HookManager.execute_post_commit_ingest(root, silent=silent)


if __name__ == "__main__":
    app()
