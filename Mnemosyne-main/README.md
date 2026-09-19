# Mnemosyne

> **A CLI companion that gives your codebase a long-term memory, so every AI-assisted coding session starts smart instead of starting blank.**

[![Powered By Cognee AI](https://img.shields.io/badge/Powered%20By-Cognee%20AI-6510F4?style=for-the-badge)](https://cognee.ai)
[![Local & Free via Ollama](https://img.shields.io/badge/LLM-Local%20%26%20Free%20(Ollama)-000000?style=for-the-badge)](https://ollama.com)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](#11-license)

---

## 🧠 Project Overview

Mnemosyne is a local **codebase memory infrastructure and security scanning assistant** built on **[Cognee AI](https://cognee.ai)**. By implementing the complete **Cognee Memory Lifecycle**, it captures historical bugs and team coding conventions in a persistent knowledge graph, helping developers prevent repeating past code mistakes. It runs **100% locally and free** using [Ollama](https://ollama.com) (no paid API keys required).

```
                  ┌───────────────────────────────────────────────┐
                  │          Cognee Memory Lifecycle Engine       │
                  └───────────────────────┬───────────────────────┘
                                          │
    ┌───────────────────────┬─────────────┴─────────┬───────────────────────┐
    ▼                       ▼                       ▼                       ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  remember()   │   │   recall()    │   │   memify()    │   │   forget()    │
│  ingests git  │   │ pre-commit    │   │ consolidates  │   │ decays dead   │
│ history & bugs│   │ graph query   │   │  team rules   │   │ code memory   │
└───────────────┘   └───────────────┘   └───────────────┘   └───────────────┘
```

| Cognee Primitive | Implementation | CLI Command |
|---|---|---|
| **`remember()`** | Ingests git commit diffs, bug root causes, and architecture decisions into the graph | `mnemosyne remember-bug`<br>`mnemosyne remember` |
| **`recall()`** | Hybrid graph traversal + vector search to surface contextual warnings | `mnemosyne ask`<br>`mnemosyne timeline`<br>Git pre-commit hook |
| **`memify()`** | Clusters near-duplicate bug reports into generalized team coding conventions | `mnemosyne reflect`<br>`mnemosyne rules` |
| **`improve()`** | Re-indexes graph relationships, adapts edge weights, and enriches nodes | `mnemosyne improve`<br>`mnemosyne feedback` |
| **`forget()`** | Decays stale memory nodes when code is deleted or refactored | `mnemosyne forget` |

---

## 1. The Problem

Every AI coding assistant today suffers from **amnesia**. You fix a subtle race condition or null pointer bug in `user_service.py` on Monday. On Friday, a teammate (or you, on a different feature branch) writes the exact same flaw in `payment_service.py`. The assistant has no idea it already saw this pattern, because LLM context resets every session and lives in isolated chat windows.

The true knowledge of a codebase — *why architectural decisions were made, what broke last time someone touched a module, and which conventions the team quietly enforces* — lives scattered across closed GitHub issues, old PR comments, Slack threads, or a senior engineer's head. None of it is queryable at the exact moment a developer is about to repeat the same mistake.

---

## 2. The Idea: Codebase Memory Infrastructure

**Mnemosyne** sits next to your standard git workflow and builds a **persistent, evolving knowledge graph** of your codebase using **[Cognee AI](https://cognee.ai)**. It watches git commits, ingests bug fixes and their root causes, and surfaces contextual warnings before a commit is finalized.

It exercises the full **Cognee Memory Lifecycle**:
1. **Remember** — Ingest git history, bug root causes, and architectural decisions into graph/vector memory.
2. **Recall** — Query the graph before committing or on-demand via natural language Q&A.
3. **Memify / Reflect** — Consolidate recurring bug patterns across files into team-wide coding rules.
4. **Improve** — Optimize memory weights and relationship edges post-ingestion.
5. **Forget** — Surgically decay or prune stale memories when code is refactored or deleted.

---

## 3. Architecture

```
┌───────────────────────────────────────┐
│          Git Repository (Local)       │
│      commits / diffs / staged files   │
└───────────────────┬───────────────────┘
                    │ Git hook (.git/hooks/pre-commit)
                    ▼
┌───────────────────────────────────────┐
│          Mnemosyne CLI (Python)       │
│    Typer commands + Rich UI + MCP     │
│  init · remember-bug · ask · reflect  │
│  visualize · timeline · forget · …    │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│           Cognee Memory Layer         │
│   remember / recall / memify / forget │
│   (Graph DB + Vector store engine)    │
└───────────────────┬───────────────────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
┌───────────────────┐  ┌───────────────────┐
│   Ollama (local)  │  │  OpenAI / Cognee  │
│  llama3.1:8b +    │  │  Cloud (optional) │
│  nomic-embed-text │  │                   │
└───────────────────┘  └───────────────────┘
```

**Local JSON store as ground truth.** Every memory is also written to `.mnemosyne/memories.json`. If Cognee/embeddings are ever unavailable, recall gracefully falls back to local keyword scoring, so the CLI never hard-fails.

---

## 4. Quickstart & Installation

### Prerequisites
- **Python 3.10+** and **Git**
- **[Ollama](https://ollama.com/download)** for the default local, free LLM + embeddings backend

### Step 1 — Install Mnemosyne

```bash
git clone https://github.com/your-username/Mnemosyne.git
cd Mnemosyne

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Step 2 — Set up the local LLM backend (Ollama)

Mnemosyne defaults to running everything locally and free via Ollama — no OpenAI key needed.

```bash
# 1. Install Ollama:  https://ollama.com/download   (or: brew install ollama)
# 2. Start the server (keep it running):
ollama serve

# 3. Pull the models (one-time, ~5 GB total):
ollama pull llama3.1:8b        # chat / entity extraction
ollama pull nomic-embed-text   # embeddings
```

> The `transformers` package (installed via `requirements.txt`) is required — Cognee's local Ollama embedder uses a HuggingFace tokenizer for token counting.

### Step 3 — Initialize in your target repo

```bash
mnemosyne init
```
*Ingests recent git commit history into Cognee memory and installs the Git pre-commit hook.*

### Step 4 — Try it

```bash
mnemosyne remember-bug \
  --file "services/user_service.py" \
  --title "NullPointerException in fetch_user_profile" \
  --cause "Unchecked response.json() on 204 status" \
  --fix "Added HTTP status check and defensive .get() chaining"

mnemosyne ask "null pointer api response"
mnemosyne visualize
```

---

## 5. Configuration

Configuration lives in `.mnemosyne/config.json` (per-repo) with environment overrides from `.env`. **Environment variables always win**, so `.env` overrides `config.json`.

### LLM / embedding backend

| Setting (`config.json`) | Default | Purpose |
|---|---|---|
| `llm_provider` | `ollama` | `ollama` (local & free) or `openai` (paid) |
| `llm_model` | `llama3.1:8b` | Chat / entity-extraction model |
| `embedding_model` | `nomic-embed-text` | Embedding model |
| `embedding_dimensions` | `768` | Embedding vector size |
| `ollama_base_url` | `http://localhost:11434/v1` | Ollama endpoint |
| `use_custom_graph_schema` | `false` | Use the typed `CodeKnowledgeGraph` schema (needs a strong LLM) |
| `use_temporal_cognify` | `false` | Track bug-pattern evolution over time (needs a strong LLM) |
| `reflection_threshold` | `3` | Auto-consolidate rules after every N bug fixes |

> **Why the graph flags default off:** the typed `CodeFile → Function → BugPattern → Fix` schema and temporal event extraction require an LLM that reliably emits strict structured JSON. Small local models (e.g. `llama3.2:3b`) can't, so Mnemosyne uses Cognee's robust built-in extraction by default and gracefully falls back if the typed schema fails. Turn both flags on with a strong model (OpenAI, or a large local model) to get the richer typed graph.

### Example `.env` (local Ollama — the default)

```env
# LLM + embeddings: local & free via Ollama
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
LLM_ENDPOINT=http://localhost:11434/v1
LLM_API_KEY=ollama

EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
# NOTE: /api/embed (batch API), NOT /api/embeddings
EMBEDDING_ENDPOINT=http://localhost:11434/api/embed
EMBEDDING_DIMENSIONS=768
HUGGINGFACE_TOKENIZER=nomic-ai/nomic-embed-text-v1.5

# Raw OpenAI-SDK calls (diff summaries, rule clustering) route to Ollama too
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
```

### Optional: OpenAI or Cognee Cloud

```bash
# Use a paid OpenAI key instead of Ollama
mnemosyne config set-llm-key <your_openai_key>   # then set llm_provider=openai

# Team-wide shared memory via Cognee Cloud (platform.cognee.ai)
mnemosyne config set-cloud-key <your_cognee_api_key>
```

---

## 6. CLI Command Reference

### `mnemosyne init`
Ingests commit history into Cognee memory and installs `.git/hooks/pre-commit`.
```bash
mnemosyne init
```

### `mnemosyne remember-bug`
Logs a bug fix, its root cause, and fix details into codebase memory. Supports explicit flags or auto-summarization from the staged `git diff`.
```bash
mnemosyne remember-bug --file services/user_service.py \
  --title "Unchecked API crash" --cause "Missing null check" --fix "Added guard clause"

mnemosyne remember-bug --auto   # summarize the staged diff
```

### `mnemosyne remember`
Ingests a general document, ADR, or PR note into the knowledge graph.
```bash
mnemosyne remember "Use the service layer for DB queries" \
  --content "All direct DB queries must pass through services." --file services/base.py
```

### `mnemosyne ask`
Query codebase memory in natural language (GRAPH_COMPLETION + HYBRID_COMPLETION + CODING_RULES). Shows which strategy found each result.
```bash
mnemosyne ask "Why do we validate external API responses in the service layer?"
```

### `mnemosyne timeline`
Temporal recall — shows how bug patterns evolved over time (requires `use_temporal_cognify`; falls back to local timestamp ordering otherwise).
```bash
mnemosyne timeline "recurring null pointer bugs" --top-k 10
```

### `mnemosyne reflect`
Clusters related bug reports across files into consolidated team rules (`memify`).
```bash
mnemosyne reflect
```

### `mnemosyne rules`
Displays a Rich table of all active consolidated team rules and their provenance links.
```bash
mnemosyne rules
```

### `mnemosyne improve`
Post-ingestion graph enrichment, edge-weight adaptation, and node optimization.
```bash
mnemosyne improve
```

### `mnemosyne feedback`
Rate the last recall result to improve future ranking (Cognee truth-subspace reranking).
```bash
mnemosyne feedback --helpful
mnemosyne feedback --not-helpful
```

### `mnemosyne forget`
Decays or removes stale memory by ID or file path.
```bash
mnemosyne forget mem_bug_8cec331b
mnemosyne forget services/user_service.py
```

### `mnemosyne visualize`
Opens an **interactive provenance graph** in your browser (D3 force graph). Merges the Cognee provenance graph (User → Dataset → File → Session) with your local memory records, so **clicking any node opens a detail panel** with the bug's type, root cause, fix, and file. Nodes use short tags; the graph supports zoom, pan, and drag.
```bash
mnemosyne visualize                 # open in browser
mnemosyne visualize -o graph.html   # save to a file instead
```

### `mnemosyne status`
Dashboard of memory statistics, active rule counts, and Git hook status.
```bash
mnemosyne status
```

### `mnemosyne config`
Manage LLM provider and Cognee Cloud settings.
```bash
mnemosyne config show                       # active configuration dashboard
mnemosyne config set-llm-key <openai_key>   # configure a paid LLM key
mnemosyne config set-cloud-key <cognee_key> # configure Cognee Cloud
```

### `mnemosyne mcp-serve`
Runs Mnemosyne as an **MCP server** so Claude Code / Cursor can use codebase memory as native tools (`recall_codebase_memory`, `remember_bug_fix`, `get_coding_rules`, `get_memory_status`, `forget_memory`).
```bash
mnemosyne mcp-serve                       # stdio (default)
mnemosyne mcp-serve -t http --port 8765   # HTTP transport
```
Claude Desktop config (`~/.claude/claude_desktop_config.json`):
```json
{ "mcpServers": { "mnemosyne": { "command": "mnemosyne", "args": ["mcp-serve"] } } }
```

---

## 7. Visualizing the Memory Graph

`mnemosyne visualize` renders an interactive graph of everything Mnemosyne knows:

- **Nodes** — `user`, `dataset`, `doc`, `session` (from Cognee provenance) plus your `bug_fix`, `rule`, `commit`, and `documentation` memories, color-coded by type with a legend.
- **Click a node** → a side panel shows structured detail:
  ```
  Type: bug_fix
  Root Cause: Unchecked response.json() on 204 status
  Fix: Added HTTP status check and defensive .get() chaining
  File: services/user_service.py
  ```
- **Interactions** — scroll to zoom, drag the background to pan, drag nodes to reposition.

The page is a self-contained HTML file, so you can also commit or share `graph.html`.

---

## 7. Web Dashboard & Security Scanner Agent

Mnemosyne features a gorgeous, light-pink themed **Glassmorphic Web Dashboard** that hosts the local memory engine and security scanning capabilities in a user-friendly browser interface.

### Running the Web Dashboard

To launch the dashboard server locally:
```bash
python -m uvicorn api.index:app --host 127.0.0.1 --port 8000 --reload
```
Then, open your web browser and navigate to:
👉 **`http://127.0.0.1:8000`**

### Features:
1. **Interactive Memory Graph**: Powered by D3.js, visualizing your files, bug fixes, consolidated rules, and commit history. Clicking any node opens a details drawer.
2. **Remember Bug Ingestor**: Log bug titles, functions, file paths, root causes, and fixes directly into the memory graph.
3. **Recall Search**: Query your codebase memory in natural language using semantic search.
4. **Discovered Coding Rules**: Clusters bug fixes and generates generalized coding guidelines using our consolidator pipeline.
5. **Security Scan Agent**: Analyze staged git diffs or raw files for security vulnerabilities (e.g. hardcoded secrets, SQL injection, eval blocks, subprocess command injection). The scanner references **past bug fixes in memory** to detect if you are repeating previous coding mistakes!

---

## 8. Live Interactive Demo

Run the self-contained demo to watch all 5 Cognee primitives in action:

```bash
python demo/run_demo.py
```

It ingests baseline history, logs a bug (`remember`), fires a pre-commit warning on a similar flaw (`recall`), consolidates rules (`memify/reflect`), decays stale memory (`forget`), and answers a natural-language query (`ask`).

---

## 9. How It Works (Internals)

- **`mnemosyne/cli.py`** — Typer CLI + Rich UI, including the D3 graph renderer for `visualize`.
- **`mnemosyne/config.py`** — config loading and `configure_llm_env()`, which wires Cognee/LiteLLM and the OpenAI SDK to the chosen provider (Ollama by default).
- **`mnemosyne/memory/client.py`** — `MemoryClient`: the Cognee integration and local JSON store, with robust cognify fallback for weak local models.
- **`mnemosyne/memory/consolidator.py`** — bug-pattern clustering into team rules.
- **`mnemosyne/git/`** — commit inspection and pre-commit hook installation.
- **`mnemosyne/mcp_server.py`** — MCP server exposing memory as tools.

---

## 10. Running Tests

```bash
pytest tests/
```

---

## 11. License

Licensed under the **MIT License**.
