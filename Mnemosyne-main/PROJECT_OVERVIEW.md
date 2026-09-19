# Mnemosyne

**A CLI companion that gives your codebase a long-term memory, so every AI-assisted coding session starts smart instead of starting blank.**

---

## 1. The Problem

Every AI coding assistant today has amnesia. You fix a null pointer bug in `UserService.java` on Monday. On Friday, a teammate (or you, on a different feature) writes the exact same bug in `PaymentService.java`. The assistant has no idea it already saw this pattern, because context resets every session and lives, at best, in a chat window that gets closed and lost.

The real knowledge of a codebase (why a decision was made, what broke last time someone touched this module, which conventions the team quietly enforces in code review) lives in scattered places: commit messages nobody reads, closed GitHub issues, Slack threads, a senior engineer's head. None of it is queryable at the moment a developer is about to make the same mistake again.

## 2. The Idea

Mnemosyne is a CLI tool that sits next to your normal git workflow and builds a persistent, evolving memory of your codebase using Cognee. It watches commits, ingests bug fixes and their root causes, and answers questions like "have we seen this before" or "why does this function look like this" using recall over that memory, not a fresh LLM context window.

The differentiator is not another AI autocomplete. It's the memory lifecycle underneath: what gets remembered, how related memories get consolidated into higher-level rules over time, and how stale memories get explicitly forgotten when the code that justified them is gone.

## 3. Why Cognee, Specifically

Mnemosyne is built to exercise the full Cognee memory lifecycle, not just use it as a vector store:

| Cognee primitive | How Mnemosyne uses it |
|---|---|
| **remember** | Every commit diff, every manually logged bug fix (root cause + fix + affected files), every code review comment resolved gets pushed into Cognee as structured memory, linked to the files and functions it touches. |
| **recall** | Before a commit, on file save (via a lightweight watcher), or on demand (`mnemosyne ask "..."`), Mnemosyne queries Cognee's graph for memories connected to the current file, function, or error signature, and surfaces the most relevant ones. |
| **memify / improve** | Run periodically (`mnemosyne reflect`) or after N new memories. Cognee consolidates near-duplicate bug reports across files into a single generalized rule ("null-check external API responses in the `services/` layer") and strengthens the confidence of frequently-recalled patterns. |
| **forget** | When a file is deleted, a function is removed, or a developer marks a memory as no longer applicable (`mnemosyne forget <id>`), Mnemosyne tells Cognee to decay or remove that memory so recall stops surfacing advice about code that no longer exists. |

The demo is built specifically to make this lifecycle visible: judges should see a memory get created, get recalled at the right moment, get merged with a related memory into a rule, and get forgotten when it's no longer relevant. Not one API call. All four.

## 4. Core User Flow (What a Judge Sees in the Demo)

1. **Setup**: `mnemosyne init` in a sample repo. Mnemosyne ingests the existing git history and README into Cognee as baseline memory.
2. **First bug**: A bug is fixed in `services/user_service.py` (a real null-check issue). Developer runs `mnemosyne remember-bug` and briefly describes root cause and fix. This gets stored via Cognee's `remember`, linked to the file and the pattern.
3. **Second bug, different file**: Weeks later (simulated), a similar issue is being written in `services/payment_service.py`. Mnemosyne's pre-commit hook fires `recall` automatically, and warns: "This looks similar to a bug fixed in `user_service.py` on [date]: unchecked external API response. Fix applied there: ..."
4. **Consolidation**: After a third similar case, `mnemosyne reflect` triggers `memify`, and Cognee merges the three related memories into one generalized team convention, visible in `mnemosyne rules`.
5. **Forgetting**: The developer refactors `user_service.py` entirely, removing the old pattern. `mnemosyne forget` (or an automatic staleness check tied to file deletion) removes the now-irrelevant memory so future recalls don't reference dead code.
6. **Free-form recall**: `mnemosyne ask "why do we always validate external responses in the service layer"` returns the consolidated rule with its provenance (which commits, which bugs).

## 5. Architecture (Weekend-Scope)

```
┌─────────────────────────┐
│   Git repo (local)      │
│  commits / diffs        │
└───────────┬──────────────┘
            │ git hooks (post-commit, pre-commit)
            ▼
┌─────────────────────────┐
│   Mnemosyne CLI (Python) │
│   Typer-based commands   │
│   init / remember-bug /  │
│   ask / reflect / forget │
└───────────┬──────────────┘
            │
            ▼
┌─────────────────────────┐
│   Cognee memory layer    │
│  remember / recall /     │
│  memify / forget         │
│  (local vector + graph)  │
└───────────┬──────────────┘
            │
            ▼
┌─────────────────────────┐
│  LLM (Claude API)        │
│  summarizes diffs into   │
│  structured memory text; │
│  drafts recall responses │
└─────────────────────────┘
```

**Stack**
- Python 3.11, Typer for the CLI surface
- Cognee (`pip install cognee`) for the full memory lifecycle, local backend for the hackathon (no external DB dependency to manage in 48 hours)
- GitPython for reading commit diffs and hooking into `post-commit` / `pre-commit`
- Claude API (Sonnet) for turning raw diffs into concise structured memory entries before they go into `remember`, and for phrasing recall answers naturally
- Rich (Python lib) for CLI output formatting, since first impressions matter for a demo

## 6. MVP Cut Line for 24 to 48 Hours

**Must ship**
- `mnemosyne init`: ingest current repo's commit history as baseline memory
- `mnemosyne remember-bug`: manual structured logging of a bug fix into Cognee
- `mnemosyne ask "<question>"`: recall-based Q&A over the memory graph
- Pre-commit hook that runs recall against the diff being committed and prints relevant warnings
- `mnemosyne reflect`: triggers memify to consolidate related memories into a rule
- `mnemosyne forget <id>`: explicit forget
- A scripted demo repo with 2 to 3 seeded "historical" bugs so the recall moment is guaranteed to hit during the live demo

**Cut if short on time**
- Automatic diff-to-memory summarization (fall back to asking the developer to type a one-line description)
- File-watcher for live recall on save (keep it to pre-commit hook only)
- Any UI beyond the terminal

**Stretch, if time remains**
- `mnemosyne rules`: a clean view of consolidated team conventions with provenance links back to source commits
- Team mode: shared Cognee memory across a repo (multiple devs contribute to the same graph) instead of single-developer local memory
- VS Code extension shim that calls the same CLI under the hood, for a flashier demo surface

## 7. Why This Scores Well on "Depth of Cognee Usage"

Most hackathon submissions will use Cognee as a fancy RAG store: remember and recall, nothing else. Mnemosyne is designed so that memify and forget are not decorative, they are structurally required for the tool to make sense. A memory tool for a codebase that never forgets stale patterns becomes noise within a week; a memory tool that never consolidates never produces team-level rules, only isolated facts. Building the demo around the full lifecycle (create, recall, merge, decay) is the strongest way to show Cognee is being used as an actual memory system rather than a search index with extra steps.

## 8. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Cognee's local setup has friction in a fresh environment | Test `pip install cognee` and a minimal remember/recall round trip first, before building anything else, so setup risk is retired early |
| Live demo depends on recall firing at exactly the right moment | Use a seeded, scripted demo repo with pre-written bug histories rather than relying on live improvisation |
| memify behavior might not be fully controllable/predictable | Have a fallback: if automatic consolidation output is unpredictable, show the "before" (3 separate memories) and "after" (1 rule) as a clear manual-triggered step rather than promising real-time magic |
| Scope creep toward a VS Code extension or team mode eating the 48 hours | Treat those explicitly as stretch goals, only started after the CLI MVP demo path works end to end |

## 9. Open Questions to Settle Before Building

- Single-developer local memory only, or worth simulating a shared team graph for a stronger demo story
- Whether `remember-bug` should require manual free-text entry or attempt automatic diff summarization from the start
- Whether the pre-commit hook should block the commit with a warning, or just print advisory output (advisory is safer for a live demo)

---

*Positioning note for submission writing: frame this less as "an AI coding assistant" and more as infrastructure, a memory layer that any coding tool (human or AI) can query. That framing separates it from the wave of generic AI-pair-programmer submissions and puts the emphasis squarely on the memory lifecycle, which is what this track is actually judging.*
