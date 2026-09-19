from typing import List, Optional, Dict, Any, Union
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.style import Style
from rich.markdown import Markdown
from rich.columns import Columns
from rich.rule import Rule
from mnemosyne.memory.schemas import MemoryRecord, MemoryType

console = Console()

# ---------------------------------------------------------------------------
# Search strategy → display badge
# ---------------------------------------------------------------------------

STRATEGY_COLORS = {
    "GRAPH_COMPLETION":  ("cyan",    "🕸"),
    "HYBRID_COMPLETION": ("magenta", "⚡"),
    "CODING_RULES":      ("green",   "📜"),
    "TEMPORAL":          ("yellow",  "📅"),
    "KEYWORD_FALLBACK":  ("dim",     "🔤"),
}


def render_search_strategy_badge(strategy: Optional[str]) -> str:
    """Return a Rich-formatted strategy badge for display in recall results."""
    if not strategy:
        return "[dim]unknown[/dim]"
    color, icon = STRATEGY_COLORS.get(strategy, ("white", "•"))
    return f"[{color}]{icon} {strategy}[/{color}]"


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

def render_banner() -> None:
    banner_text = r"""[bold cyan]
    _    _   _    _    __  __ _   _ _____ ____ ___ ____  
   / \  | \ | |  / \  |  \/  | \ | | ____/ ___|_ _/ ___| 
  / _ \ |  \| | / _ \ | |\/| |  \| |  _| \___ \| |\___ \ 
 / ___ \| |\  |/ ___ \| |  | | |\  | |___ ___) | | ___) |
/_/   \_\_| \_/_/   \_\_|  |_|_| \_|_____|____/___|____/ 
[/bold cyan]
[bold magenta]Powered by Cognee AI Memory Engine[/bold magenta] [dim](remember · recall · memify · improve · forget)[/dim]
[dim]Graph Schema: CodeKnowledgeGraph | Search: GRAPH_COMPLETION + HYBRID + CODING_RULES[/dim]
"""
    console.print(banner_text)


# ---------------------------------------------------------------------------
# Pre-commit warning panel
# ---------------------------------------------------------------------------

def render_memory_warning(record: MemoryRecord) -> Panel:
    file_info = f"[cyan]{record.file_path}[/cyan]" if record.file_path else "[dim]General[/dim]"
    type_badge = f"[bold yellow]{record.memory_type.value.upper()}[/bold yellow]"
    strategy_badge = render_search_strategy_badge(record.search_strategy)

    body = Text()
    body.append("Search Strategy: ", style="bold magenta")
    body.append(record.search_strategy or "keyword fallback", style="italic white")
    body.append("\n")
    body.append("Title: ", style="bold white")
    body.append(f"{record.title}\n", style="bold yellow")
    body.append(f"Scope: {file_info}\n\n", style="dim")

    meta = record.metadata or {}
    if meta.get("root_cause"):
        body.append("Root Cause: ", style="bold red")
        body.append(f"{meta['root_cause']}\n", style="bright_white")
    if meta.get("fix_description"):
        body.append("Fix Applied: ", style="bold green")
        body.append(f"{meta['fix_description']}\n", style="bright_white")
    if not meta.get("root_cause"):
        body.append(record.content[:300], style="bright_white")

    return Panel(
        body,
        title=f"⚠️  Memory Warning [{type_badge}] {strategy_badge} (ID: {record.id})",
        border_style="yellow",
        expand=True,
    )


# ---------------------------------------------------------------------------
# Ask/recall response
# ---------------------------------------------------------------------------

def render_recall_response(query: str, records: List[MemoryRecord]) -> None:
    console.print(
        f"\n[bold magenta]🔍 Cognee Graph Search for:[/bold magenta] [italic]\"{query}\"[/italic]\n"
        "[dim]  Strategies: GRAPH_COMPLETION (2-hop) + HYBRID_COMPLETION + CODING_RULES[/dim]\n"
    )

    if not records:
        console.print(Panel(
            "[dim]No relevant nodes found in Cognee knowledge graph.\n"
            "Try: mnemosyne remember-bug — to add memories first.[/dim]",
            border_style="dim",
        ))
        return

    for i, rec in enumerate(records, 1):
        file_badge = f" 📁 [cyan]{rec.file_path}[/cyan]" if rec.file_path else ""
        strategy_badge = render_search_strategy_badge(rec.search_strategy)
        panel_title = (
            f"[bold green]#{i} Match[/bold green] "
            f"[dim]({rec.id})[/dim]"
            f"{file_badge} {strategy_badge}"
        )

        content_text = Text()
        content_text.append(f"Type: {rec.memory_type.value}\n", style="dim magenta")

        meta = rec.metadata or {}
        if meta.get("root_cause"):
            content_text.append("Root Cause: ", style="bold red")
            content_text.append(f"{meta['root_cause']}\n", style="bright_white")
        if meta.get("fix_description"):
            content_text.append("Fix: ", style="bold green")
            content_text.append(f"{meta['fix_description']}\n", style="bright_white")
        if not meta.get("root_cause"):
            content_text.append(rec.content[:400])

        console.print(Panel(content_text, title=panel_title, border_style="green"))

    console.print(
        f"\n[dim]Found {len(records)} result(s). "
        "Run 'mnemosyne feedback --helpful' to improve future results.[/dim]\n"
    )


# ---------------------------------------------------------------------------
# Rules table
# ---------------------------------------------------------------------------

def render_rules_table(rules: List[MemoryRecord]) -> None:
    if not rules:
        console.print(Panel(
            "[dim]No consolidated rules yet.\n"
            "Run 'mnemosyne reflect' to execute cognee.memify() + CODING_RULES analysis.[/dim]",
            border_style="dim",
        ))
        return

    table = Table(
        title="📜 Consolidated Team Rules (via cognee.memify + CODING_RULES)",
        border_style="magenta",
        show_lines=True,
    )
    table.add_column("Rule ID", style="dim cyan", no_wrap=True)
    table.add_column("Rule Title", style="bold white", max_width=35)
    table.add_column("Domain", style="magenta")
    table.add_column("Provenance Files", style="green", max_width=30)
    table.add_column("Confidence", style="bold yellow", justify="right")

    for rule in rules:
        meta = rule.metadata or {}
        provenance = ", ".join(meta.get("provenance_files", [])) or "—"
        conf = f"{float(meta.get('confidence', 0.9)):.0%}"
        table.add_row(
            rule.id,
            rule.title,
            meta.get("domain", "general"),
            provenance[:30],
            conf,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Status dashboard
# ---------------------------------------------------------------------------

def render_status_dashboard(stats: Dict[str, Any]) -> None:
    stats_table = Table(
        title="📊 Mnemosyne × Cognee Dashboard",
        border_style="magenta",
        show_lines=False,
    )
    stats_table.add_column("Metric", style="bold white")
    stats_table.add_column("Value / Status", style="bold cyan")

    stats_table.add_row("Cognee Primitives", "[magenta]remember · recall · memify · improve · forget[/magenta]")
    stats_table.add_row("Graph Schema", "[cyan]CodeKnowledgeGraph (typed entities + edges)[/cyan]")
    stats_table.add_row("Search Strategies", "[cyan]GRAPH_COMPLETION + HYBRID_COMPLETION + CODING_RULES[/cyan]")
    stats_table.add_row("Cognee Engine", "[green]Active[/green]" if stats.get("cognee_active") else "[yellow]Offline (local fallback)[/yellow]")
    stats_table.add_row("Total Graph Nodes", str(stats.get("total_memories", 0)))
    stats_table.add_row("Bug Fix Nodes", str(stats.get("bug_fixes", 0)))
    stats_table.add_row("Rule Nodes (memify)", str(stats.get("rules", 0)))
    stats_table.add_row("Commit Memories", str(stats.get("commits", 0)))
    stats_table.add_row(
        "Pre-Commit Hook",
        "[green]Installed[/green]" if stats.get("hooks_installed") else "[yellow]Not Installed[/yellow]",
    )
    stats_table.add_row(
        "Post-Commit Hook (auto-ingest)",
        "[green]Installed[/green]" if stats.get("post_commit_hook") else "[yellow]Not Installed[/yellow]",
    )
    stats_table.add_row("Backend", stats.get("backend", "Cognee Hybrid Vector + Knowledge Graph"))

    console.print(stats_table)


# ---------------------------------------------------------------------------
# Timeline (temporal graph results)
# ---------------------------------------------------------------------------

def render_timeline_results(results: Union[List[Any], List[MemoryRecord]], fallback: bool = False) -> None:
    """
    Render temporal search results as a timeline.
    Works with both Cognee SearchResult objects and local MemoryRecord objects.
    """
    if not results:
        console.print(Panel(
            "[dim]No temporal data found.\n"
            "Bugs logged after v0.2.0 are tracked with temporal_cognify=True.[/dim]",
            border_style="dim",
        ))
        return

    source_label = "local JSON (fallback)" if fallback else "Cognee TEMPORAL graph"
    console.print(f"[dim]Source: {source_label} | {len(results)} event(s)[/dim]\n")
    console.print(Rule(style="dim cyan"))

    for item in results:
        # Handle both MemoryRecord and Cognee SearchResult
        if isinstance(item, MemoryRecord):
            timestamp = item.timestamp[:10] if item.timestamp else "unknown date"
            title = item.title
            content = item.content[:200]
            file_info = f"[cyan]{item.file_path}[/cyan] " if item.file_path else ""
            type_badge = f"[yellow]{item.memory_type.value}[/yellow]"
        else:
            # Cognee SearchResult object
            timestamp = getattr(item, "timestamp", "")[:10] if hasattr(item, "timestamp") else "unknown"
            title = getattr(item, "title", str(item)[:60])
            content = getattr(item, "text", getattr(item, "content", str(item)))[:200]
            file_info = ""
            type_badge = "[cyan]graph node[/cyan]"

        console.print(
            f"  [bold cyan]{timestamp}[/bold cyan]  {file_info}"
            f"[bold white]{title}[/bold white]  [{type_badge}]"
        )
        console.print(f"  [dim]{content}[/dim]")
        console.print(Rule(style="dim"))

    console.print()
