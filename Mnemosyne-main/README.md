# Mnemosyne — Codebase Memory Graph

> **Persistent memory for engineering teams.** Ingests git commits, recalls bug fixes, synthesizes team rules with Cognee AI, and guards against code regressions.

![Mnemosyne Preview](public/assets/logo.png)

---

## 🌟 Overview

Mnemosyne solves the "AI assistant amnesia" problem. Modern AI assistants lose context once a chat ends. When team members encounter or fix recurring architectural defects, those lessons are lost in commit logs or PR comments.

Mnemosyne acts as a persistent knowledge graph companion:
- **`remember()`**: Automatically ingests git commit diffs, bug reports, and root causes into an interconnected knowledge graph.
- **`recall()`**: Surfaces historical bug fixes and architectural context before code regressions occur using hybrid graph + vector search.
- **`memify()`**: Periodically clusters and synthesizes recurring patterns into consolidated team rules.
- **`forget()`**: Decays and prunes stale connections when code is refactored or deleted.

---

## 🚀 Key Features

1. **Memory Statistics & Graph Health**: Live telemetry of total nodes, bug fixes, synthesized rules, and commits.
2. **Bug Fix Memory Ingestion**: Fast logging of root causes, resolutions, severity levels, and tags.
3. **Recall Search**: Hybrid semantic embedding + knowledge graph traversal.
4. **Consolidated Rules**: Automated clustering of recurring bugs into actionable team conventions.
5. **Security & Anti-Pattern Scanner**: Real-time auditing of code diffs and files against consolidated rules.
6. **Interactive Knowledge Graph Visualizer**: D3.js-powered relational visualizer mapping tenants, files, bugs, commits, and rules with detailed node inspector.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn, Cognee memory graph engine
- **Frontend**: Single-viewport vanilla HTML5, CSS3, modern JavaScript (ES6+), D3.js v7
- **Design**: Frosted glassmorphism, retro dot-matrix display typography, high-contrast black headers, full-bleed cybernetic video backdrop

---

## 📦 Running Locally

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Mnemosyne Server**:
   ```bash
   python serve.py
   ```

3. **Open in Browser**:
   Navigate to [http://localhost:8085](http://localhost:8085)
