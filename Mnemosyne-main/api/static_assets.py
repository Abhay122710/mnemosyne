# Static Assets for Mnemosyne Web Dashboard
# This file provides embedded fallbacks for Vercel, since Vercel's edge network
# handles static folders externally and doesn't bundle them inside python serverless functions.

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mnemosyne - Codebase Memory Graph Dashboard</title>
    <link rel="stylesheet" href="style.css">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Space+Grotesk:wght@400;700&display=swap" rel="stylesheet">
    <script src="https://d3js.org/d3.v7.min.js"></script>
</head>
<body>
    <div class="app-container">
        <!-- Sidebar Navigation -->
        <aside class="sidebar">
            <div class="logo">
                <span class="logo-icon">🧠</span>
                <h2>Mnemosyne</h2>
            </div>
            <nav class="nav-links">
                <a href="#" class="nav-item active" data-tab="dashboard">
                    <span class="icon">📊</span> Dashboard
                </a>
                <a href="#" class="nav-item" data-tab="remember">
                    <span class="icon">💾</span> Remember Bug
                </a>
                <a href="#" class="nav-item" data-tab="recall">
                    <span class="icon">🔍</span> Recall Search
                </a>
                <a href="#" class="nav-item" data-tab="rules">
                    <span class="icon">📜</span> Consolidated Rules
                </a>
                <a href="#" class="nav-item" data-tab="security">
                    <span class="icon">🛡️</span> Security Scan
                </a>
                <a href="#" class="nav-item" data-tab="visualizer">
                    <span class="icon">🕸️</span> Graph Visualizer
                </a>
            </nav>
            <div class="status-indicator">
                <span class="pulse-dot" id="system-pulse"></span>
                <span class="status-text" id="system-status">Checking backend...</span>
            </div>
        </aside>

        <!-- Main Content Area -->
        <main class="main-content">
            <!-- TAB: Dashboard -->
            <section id="dashboard" class="tab-content active">
                <div class="tab-header">
                    <h1>Memory Statistics</h1>
                    <p>Live health and statistics of the codebase memory graph</p>
                </div>
                <div class="stats-grid">
                    <div class="stat-card">
                        <span class="stat-icon">🕸️</span>
                        <div class="stat-info">
                            <span class="stat-num" id="stat-total-nodes">0</span>
                            <span class="stat-label">Total Graph Nodes</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <span class="stat-icon">🪲</span>
                        <div class="stat-info">
                            <span class="stat-num" id="stat-bug-fixes">0</span>
                            <span class="stat-label">Bug Fix Memories</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <span class="stat-icon">📜</span>
                        <div class="stat-info">
                            <span class="stat-num" id="stat-rules">0</span>
                            <span class="stat-label">Consolidated Rules</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <span class="stat-icon">💾</span>
                        <div class="stat-info">
                            <span class="stat-num" id="stat-commits">0</span>
                            <span class="stat-label">Commit Memories</span>
                        </div>
                    </div>
                </div>

                <div class="dashboard-details grid-2">
                    <div class="info-card">
                        <h3>🤖 AI Engine Capabilities</h3>
                        <ul class="capability-list">
                            <li><span class="check">✓</span> <strong>remember()</strong>: Ingests commit history & manual bugs into structured CodeKnowledgeGraph.</li>
                            <li><span class="check">✓</span> <strong>recall()</strong>: Traverses relational nodes using hybrid vector + graph strategy.</li>
                            <li><span class="check">✓</span> <strong>memify()</strong>: Clusters recurring bug fixes into generalized team rules.</li>
                            <li><span class="check">✓</span> <strong>forget()</strong>: Prunes stale connections and removes decayed nodes.</li>
                        </ul>
                    </div>
                    <div class="info-card">
                        <h3>🛡️ Connection Status</h3>
                        <div class="status-details">
                            <div class="status-row">
                                <span>Cognee DB Engine</span>
                                <span class="status-badge" id="status-cognee">Offline</span>
                            </div>
                            <div class="status-row">
                                <span>Cloud LLM Backend</span>
                                <span class="status-badge" id="status-llm">Offline</span>
                            </div>
                            <div class="status-row">
                                <span>Local Fallback Mode</span>
                                <span class="status-badge" id="status-fallback">Active</span>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- TAB: Remember Bug -->
            <section id="remember" class="tab-content">
                <div class="tab-header">
                    <h1>Log a Bug Fix</h1>
                    <p>Add a new bug pattern to the codebase memory graph</p>
                </div>
                <div class="card form-container">
                    <form id="bug-form">
                        <div class="form-group">
                            <label for="file_path">Affected File Path</label>
                            <input type="text" id="file_path" placeholder="e.g. services/user_service.py" required>
                        </div>
                        <div class="form-group">
                            <label for="title">Bug Summary / Title</label>
                            <input type="text" id="title" placeholder="e.g. NullPointerException on empty API result" required>
                        </div>
                        <div class="form-group">
                            <label for="root_cause">Root Cause Description</label>
                            <textarea id="root_cause" rows="3" placeholder="Why did the bug happen? (e.g. Missing check for response.status_code == 204)" required></textarea>
                        </div>
                        <div class="form-group">
                            <label for="fix_description">Fix Applied</label>
                            <textarea id="fix_description" rows="3" placeholder="How was it fixed? (e.g. Added guard clause and defensive dictionary .get() access)" required></textarea>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="severity">Severity</label>
                                <select id="severity">
                                    <option value="low">Low</option>
                                    <option value="medium" selected>Medium</option>
                                    <option value="high">High</option>
                                    <option value="critical">Critical</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="tags">Tags (comma-separated)</label>
                                <input type="text" id="tags" placeholder="e.g. null-check, api, user-service">
                            </div>
                        </div>
                        <button type="submit" class="btn primary-btn">Ingest into Graph Memory</button>
                    </form>
                    <div id="bug-result" class="alert-box hide"></div>
                </div>
            </section>

            <!-- TAB: Recall Search -->
            <section id="recall" class="tab-content">
                <div class="tab-header">
                    <h1>Recall Search</h1>
                    <p>Query codebase memory graph in natural language using semantic & graph search</p>
                </div>
                <div class="search-container">
                    <div class="search-bar card">
                        <input type="text" id="search-query" placeholder="Ask codebase memory (e.g., 'null check user API response' or 'sql injection risk')...">
                        <input type="text" id="search-context" placeholder="File context (optional)...">
                        <button id="btn-search" class="btn primary-btn">Search Memory</button>
                    </div>
                </div>
                <div class="results-container">
                    <h3>🔍 Recall Search Results</h3>
                    <div id="search-results-list" class="results-list">
                        <p class="placeholder-text">Enter a query to search codebase memory...</p>
                    </div>
                </div>
            </section>

            <!-- TAB: Consolidated Rules -->
            <section id="rules" class="tab-content">
                <div class="tab-header">
                    <h1>Discovered Coding Rules</h1>
                    <p>Rules consolidated by the Cognee memify() pipeline from recurring bug fixes</p>
                    <button id="btn-reflect" class="btn secondary-btn" style="margin-top: 15px;">Reflect & Generalize Rules</button>
                </div>
                <div class="card">
                    <table class="rules-table">
                        <thead>
                            <tr>
                                <th>Convention / Title</th>
                                <th>Actionable Guideline</th>
                                <th>Domain</th>
                                <th>Confidence</th>
                            </tr>
                        </thead>
                        <tbody id="rules-tbody">
                            <tr>
                                <td colspan="4" class="placeholder-text">No rules consolidated yet. Click "Reflect & Generalize Rules" or add more bug fixes to trigger consolidation.</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </section>

            <!-- TAB: Security Scan -->
            <section id="security" class="tab-content">
                <div class="tab-header">
                    <h1>Security Scanning Agent</h1>
                    <p>Scans staged git diffs or file contents for credentials, SQL injection, and vulnerabilities using past memory context</p>
                </div>
                <div class="grid-2">
                    <div class="card">
                        <h3>Scan Staged Git Diff</h3>
                        <p class="description">Scan all currently staged git modifications.</p>
                        <textarea id="security-diff" rows="10" placeholder="Paste your git diff patch here..."></textarea>
                        <button id="btn-scan-diff" class="btn primary-btn" style="margin-top: 15px;">Scan Staged Diff</button>
                    </div>
                    <div class="card">
                        <h3>Scan Specific File</h3>
                        <p class="description">Scan a specific file by its relative path inside the repository.</p>
                        <input type="text" id="security-file-path" placeholder="e.g. services/user_service.py" style="margin-top: 10px; margin-bottom: 15px; width: 100%;">
                        <button id="btn-scan-file" class="btn secondary-btn">Scan Code File</button>
                    </div>
                </div>
                <div class="security-results-container card hide" id="security-results-panel">
                    <h3>🛡️ Security Vulnerabilities Detected</h3>
                    <div id="security-issues-list" class="issues-list"></div>
                </div>
            </section>

            <!-- TAB: Visualizer -->
            <section id="visualizer" class="tab-content visualizer-tab">
                <div class="tab-header">
                    <h1>Interactive Memory Graph</h1>
                    <p>Visualizing files, bug fixes, consolidated rules, and relations</p>
                </div>
                <div class="visualizer-container card">
                    <svg id="graph-svg" width="100%" height="550"></svg>
                    <!-- Detail Side Drawer -->
                    <div id="drawer" class="drawer hide">
                        <div class="drawer-header">
                            <h3 id="drawer-title">Node Details</h3>
                            <button id="drawer-close" class="close-btn">&times;</button>
                        </div>
                        <div class="drawer-body" id="drawer-content"></div>
                    </div>
                </div>
            </section>
        </main>
    </div>
    <script src="app.js"></script>
</body>
</html>
"""

CSS_CONTENT = """:root {
    --bg-dark: #fff5f8;
    --bg-sidebar: #ffe3ee;
    --card-bg: rgba(255, 255, 255, 0.75);
    --border-color: rgba(255, 0, 127, 0.15);
    --text-primary: #2d001e;
    --text-secondary: #7d5970;
    
    --primary: #ff007f;
    --primary-glow: rgba(255, 0, 127, 0.25);
    --primary-light: #ff4da6;
    --blue: #e0115f;
    --blue-glow: rgba(224, 17, 95, 0.2);
    
    --critical: #d0104c;
    --high: #d9531e;
    --medium: #b28500;
    --low: #d02090;
    --success: #008f55;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    background-color: var(--bg-dark);
    color: var(--text-primary);
    font-family: 'Outfit', sans-serif;
    overflow-x: hidden;
}

h1, h2, h3, .logo h2 {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
}

.app-container {
    display: flex;
    min-height: 100vh;
}

/* Sidebar Navigation */
.sidebar {
    width: 260px;
    background-color: var(--bg-sidebar);
    border-right: 1px solid var(--border-color);
    padding: 24px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.logo {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 40px;
}

.logo-icon {
    font-size: 28px;
}

.logo h2 {
    font-size: 22px;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, var(--text-primary) 0%, var(--primary) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.nav-links {
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex-grow: 1;
}

.nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    color: var(--text-secondary);
    text-decoration: none;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 500;
    transition: all 0.2s ease;
}

.nav-item:hover {
    color: var(--text-primary);
    background-color: rgba(255, 0, 127, 0.05);
}

.nav-item.active {
    color: #ffffff !important;
    background-color: var(--primary);
    box-shadow: 0 4px 15px var(--primary-glow);
}

.status-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px;
    border-radius: 10px;
    background: rgba(255, 0, 127, 0.04);
    border: 1px solid var(--border-color);
}

.pulse-dot {
    width: 8px;
    height: 8px;
    background-color: var(--success);
    border-radius: 50%;
    box-shadow: 0 0 10px var(--success);
    animation: pulse 1.8s infinite;
}

.pulse-dot.offline {
    background-color: var(--critical);
    box-shadow: 0 0 10px var(--critical);
}

.status-text {
    font-size: 12px;
    color: var(--text-secondary);
}

/* Main Content Area */
.main-content {
    flex-grow: 1;
    padding: 40px;
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
}

.tab-content {
    display: none;
    animation: fadeIn 0.3s ease-in-out forwards;
}

.tab-content.active {
    display: block;
}

.tab-header {
    margin-bottom: 30px;
}

.tab-header h1 {
    font-size: 32px;
    margin-bottom: 6px;
}

.tab-header p {
    color: var(--text-secondary);
    font-size: 15px;
}

/* Cards & Layout */
.card {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 24px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    margin-bottom: 24px;
    box-shadow: 0 8px 32px rgba(255, 0, 127, 0.06);
}

.grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
}

/* Stats Cards */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.stat-card {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    padding: 20px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    gap: 16px;
    backdrop-filter: blur(10px);
}

.stat-icon {
    font-size: 28px;
    padding: 10px;
    background: rgba(255, 0, 127, 0.05);
    border-radius: 10px;
    border: 1px solid rgba(255, 0, 127, 0.08);
}

.stat-info {
    display: flex;
    flex-direction: column;
}

.stat-num {
    font-size: 24px;
    font-weight: 700;
}

.stat-label {
    font-size: 13px;
    color: var(--text-secondary);
}

/* Capabilities & Dashboard Lists */
.info-card h3 {
    margin-bottom: 16px;
    font-size: 18px;
}

.capability-list {
    list-style: none;
}

.capability-list li {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 12px;
    font-size: 14px;
    color: var(--text-secondary);
}

.capability-list li strong {
    color: var(--text-primary);
}

.check {
    color: var(--success);
    font-weight: bold;
}

.status-details {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.status-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border-color);
    font-size: 14px;
}

.status-badge {
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    background: rgba(255, 0, 127, 0.06);
}

.status-badge.active {
    background-color: rgba(16, 185, 129, 0.15);
    color: var(--success);
    border: 1px solid rgba(16, 185, 129, 0.2);
}

.status-badge.offline {
    background-color: rgba(239, 68, 68, 0.15);
    color: var(--critical);
    border: 1px solid rgba(239, 68, 68, 0.2);
}

/* Forms */
.form-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 20px;
}

.form-group label {
    font-size: 14px;
    font-weight: 500;
    color: var(--text-secondary);
}

input[type="text"], select, textarea {
    background-color: rgba(255, 255, 255, 0.95);
    border: 1px solid var(--border-color);
    padding: 12px 16px;
    border-radius: 10px;
    color: var(--text-primary);
    font-family: inherit;
    font-size: 14px;
    transition: all 0.2s ease;
}

input[type="text"]:focus, select:focus, textarea:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 10px rgba(255, 0, 127, 0.15);
    background-color: #ffffff;
}

.form-row {
    display: grid;
    grid-template-columns: 1fr 2fr;
    gap: 20px;
}

/* Buttons */
.btn {
    border: none;
    padding: 12px 24px;
    border-radius: 10px;
    font-family: inherit;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
}

.primary-btn {
    background-color: var(--primary);
    color: white;
    box-shadow: 0 4px 15px var(--primary-glow);
}

.primary-btn:hover {
    background-color: var(--primary-light);
    transform: translateY(-1px);
}

.secondary-btn {
    background-color: rgba(255, 0, 127, 0.04);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
}

.secondary-btn:hover {
    background-color: rgba(255, 0, 127, 0.08);
    border-color: rgba(255, 0, 127, 0.15);
}

/* Search Interface */
.search-bar {
    display: flex;
    gap: 16px;
}

.search-bar input[type="text"] {
    flex-grow: 1;
}

.search-bar input#search-context {
    width: 200px;
    flex-grow: 0;
}

.results-container h3 {
    margin-bottom: 16px;
}

.results-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.placeholder-text {
    color: var(--text-secondary);
    font-style: italic;
    text-align: center;
    padding: 40px;
    font-size: 14px;
}

/* Result Cards */
.result-card {
    background: rgba(255, 255, 255, 0.6);
    border: 1px solid var(--border-color);
    padding: 20px;
    border-radius: 12px;
}

.result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}

.result-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--primary);
}

.strategy-tag {
    font-size: 10px;
    font-weight: 700;
    background: var(--blue-glow);
    color: var(--blue);
    padding: 2px 8px;
    border-radius: 4px;
    border: 1px solid rgba(59, 130, 246, 0.2);
}

.result-file {
    font-size: 13px;
    color: var(--text-secondary);
    margin-bottom: 12px;
}

.result-meta {
    font-size: 14px;
    line-height: 1.5;
}

/* Rules Table */
.rules-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}

.rules-table th, .rules-table td {
    padding: 16px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
}

.rules-table th {
    color: var(--text-secondary);
    font-weight: 600;
}

.rules-table tr:hover td {
    background-color: rgba(255, 0, 127, 0.02);
}

.rule-title-cell {
    font-weight: 600;
    color: var(--primary);
}

.rules-table td.placeholder-text {
    text-align: center;
    padding: 40px 0;
}

/* Security Scan Results */
.issues-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.issue-card {
    border-left: 4px solid var(--border-color);
    padding: 16px;
    background: rgba(255, 0, 127, 0.02);
    border-radius: 0 10px 10px 0;
}

.issue-card.critical { border-left-color: var(--critical); }
.issue-card.high { border-left-color: var(--high); }
.issue-card.medium { border-left-color: var(--medium); }
.issue-card.low { border-left-color: var(--low); }

.issue-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.issue-title {
    font-weight: 600;
    font-size: 15px;
}

.issue-severity {
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
}

.issue-severity.critical { background: rgba(239, 68, 68, 0.15); color: var(--critical); }
.issue-severity.high { background: rgba(249, 115, 22, 0.15); color: var(--high); }
.issue-severity.medium { background: rgba(234, 179, 8, 0.15); color: var(--medium); }
.issue-severity.low { background: rgba(59, 130, 246, 0.15); color: var(--low); }

.issue-desc {
    font-size: 13.5px;
    color: var(--text-secondary);
    margin-bottom: 8px;
}

.issue-fix {
    font-size: 13px;
    background: rgba(255, 255, 255, 0.85);
    padding: 8px 12px;
    border-radius: 6px;
    border: 1px solid var(--border-color);
}

.issue-fix strong {
    color: var(--primary);
}

/* Visualizer D3 Canvas */
.visualizer-container {
    padding: 0;
    position: relative;
    overflow: hidden;
}

#graph-svg {
    background-color: #fff9fb;
    cursor: grab;
}

#graph-svg:active {
    cursor: grabbing;
}

/* Detail Side Drawer */
.drawer {
    position: absolute;
    top: 0;
    right: 0;
    width: 320px;
    height: 100%;
    background: rgba(7, 4, 32, 0.95);
    border-left: 1px solid var(--border-color);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    box-shadow: -10px 0 30px rgba(0, 0, 0, 0.4);
    z-index: 10;
    display: flex;
    flex-direction: column;
    transition: transform 0.3s cubic-bezier(0.1, 0.9, 0.2, 1);
    transform: translateX(0);
}

.drawer.hide {
    transform: translateX(100%);
}

.drawer-header {
    padding: 20px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.drawer-header h3 {
    font-size: 16px;
}

.close-btn {
    background: none;
    border: none;
    color: var(--text-secondary);
    font-size: 24px;
    cursor: pointer;
    line-height: 1;
}

.close-btn:hover {
    color: var(--text-primary);
}

.drawer-body {
    padding: 20px;
    overflow-y: auto;
    flex-grow: 1;
}

.detail-row {
    margin-bottom: 16px;
}

.detail-label {
    font-size: 11px;
    text-transform: uppercase;
    color: var(--text-secondary);
    font-weight: 600;
    margin-bottom: 4px;
}

.detail-value {
    font-size: 14px;
    line-height: 1.5;
    word-break: break-word;
}

/* Node Colors */
.node-circle.tenant { fill: #ffffff; stroke: var(--primary-light); }
.node-circle.file { fill: var(--blue); stroke: #ffffff; }
.node-circle.bug_fix { fill: var(--critical); stroke: var(--high); }
.node-circle.rule { fill: var(--success); stroke: #ffffff; }
.node-circle.commit { fill: var(--medium); stroke: #ffffff; }

/* Alert Boxes & Hide classes */
.hide {
    display: none !important;
}

.alert-box {
    margin-top: 15px;
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 14px;
}

.alert-box.success {
    background-color: rgba(16, 185, 129, 0.15);
    color: var(--success);
    border: 1px solid rgba(16, 185, 129, 0.2);
}

.alert-box.error {
    background-color: rgba(239, 68, 68, 0.15);
    color: var(--critical);
    border: 1px solid rgba(239, 68, 68, 0.2);
}

/* Animations */
@keyframes pulse {
    0% {
        transform: scale(0.95);
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5);
    }
    70% {
        transform: scale(1);
        box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
    }
    100% {
        transform: scale(0.95);
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
    }
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
"""

JS_CONTENT = """document.addEventListener("DOMContentLoaded", () => {
    // API base URL helper (handles local vs hosted automatically)
    const API_BASE = window.location.origin.startsWith("file") ? "http://127.0.0.1:8000" : window.location.origin;

    // Elements
    const navItems = document.querySelectorAll(".nav-item");
    const tabContents = document.querySelectorAll(".tab-content");
    const systemPulse = document.getElementById("system-pulse");
    const systemStatus = document.getElementById("system-status");

    // Dashboard Elements
    const statTotalNodes = document.getElementById("stat-total-nodes");
    const statBugFixes = document.getElementById("stat-bug-fixes");
    const statRules = document.getElementById("stat-rules");
    const statCommits = document.getElementById("stat-commits");
    const statusCognee = document.getElementById("status-cognee");
    const statusLlm = document.getElementById("status-llm");
    const statusFallback = document.getElementById("status-fallback");

    // Bug Form Elements
    const bugForm = document.getElementById("bug-form");
    const bugResult = document.getElementById("bug-result");

    // Search Elements
    const searchInput = document.getElementById("search-query");
    const searchContext = document.getElementById("search-context");
    const btnSearch = document.getElementById("btn-search");
    const searchResultsList = document.getElementById("search-results-list");

    // Rules Elements
    const btnReflect = document.getElementById("btn-reflect");
    const rulesTbody = document.getElementById("rules-tbody");

    // Security Scan Elements
    const securityDiff = document.getElementById("security-diff");
    const securityFilePath = document.getElementById("security-file-path");
    const btnScanDiff = document.getElementById("btn-scan-diff");
    const btnScanFile = document.getElementById("btn-scan-file");
    const securityResultsPanel = document.getElementById("security-results-panel");
    const securityIssuesList = document.getElementById("security-issues-list");

    // Visualizer Drawer Elements
    const drawer = document.getElementById("drawer");
    const drawerTitle = document.getElementById("drawer-title");
    const drawerContent = document.getElementById("drawer-content");
    const drawerClose = document.getElementById("drawer-close");

    // ---------------------------------------------------------
    // Navigation / Tab Handler
    // ---------------------------------------------------------
    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const tabId = item.getAttribute("data-tab");
            
            navItems.forEach(nav => nav.classList.remove("active"));
            item.classList.add("active");
            
            tabContents.forEach(tab => tab.classList.remove("active"));
            document.getElementById(tabId).classList.add("active");

            // Close side drawer on tab change
            drawer.classList.add("hide");

            // Load tab specific data
            if (tabId === "dashboard") refreshDashboard();
            if (tabId === "rules") refreshRules();
            if (tabId === "visualizer") initD3Graph();
        });
    });

    // ---------------------------------------------------------
    // API Helper Call
    // ---------------------------------------------------------
    async function apiCall(endpoint, method = "GET", body = null) {
        const options = {
            method,
            headers: {
                "Content-Type": "application/json"
            }
        };
        if (body) {
            options.body = JSON.stringify(body);
        }

        try {
            const res = await fetch(`${API_BASE}${endpoint}`, options);
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "API request failed");
            }
            return await res.json();
        } catch (e) {
            console.error(`API Error (${endpoint}):`, e);
            throw e;
        }
    }

    // ---------------------------------------------------------
    // Dashboard Status Refresher
    // ---------------------------------------------------------
    async function refreshDashboard() {
        try {
            const data = await apiCall("/api/status");
            
            // Set pulses
            systemPulse.classList.remove("offline");
            systemStatus.textContent = data.offline_mode ? "Local Fallback Mode Active" : "Cognee Cloud Active";
            
            // Set stats
            statTotalNodes.textContent = data.total_memories + data.rule_nodes;
            statBugFixes.textContent = data.bug_fixes;
            statRules.textContent = data.rule_nodes;
            statCommits.textContent = data.commit_memories;

            // Set Badges
            updateBadge(statusCognee, data.cognee_active);
            updateBadge(statusLlm, data.llm_active);
            updateBadge(statusFallback, data.offline_mode);

        } catch (e) {
            systemPulse.classList.add("offline");
            systemStatus.textContent = "Cannot connect to backend";
            updateBadge(statusCognee, false);
            updateBadge(statusLlm, false);
            updateBadge(statusFallback, true);
        }
    }

    function updateBadge(el, active) {
        el.textContent = active ? "Active" : "Offline";
        el.className = `status-badge ${active ? "active" : "offline"}`;
    }

    // ---------------------------------------------------------
    // Remember Bug Form Ingestion
    // ---------------------------------------------------------
    bugForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        bugResult.className = "alert-box hide";
        
        const tagsInput = document.getElementById("tags").value;
        const tags = tagsInput ? tagsInput.split(",").map(t => t.trim()) : [];

        const body = {
            file_path: document.getElementById("file_path").value,
            title: document.getElementById("title").value,
            root_cause: document.getElementById("root_cause").value,
            fix_description: document.getElementById("fix_description").value,
            severity: document.getElementById("severity").value,
            tags: tags
        };

        try {
            const res = await apiCall("/api/remember-bug", "POST", body);
            bugResult.textContent = `✓ Bug successfully logged into Graph Memory! (ID: ${res.id})`;
            bugResult.className = "alert-box success";
            bugForm.reset();
            refreshDashboard();
        } catch (err) {
            bugResult.textContent = `Error: ${err.message}`;
            bugResult.className = "alert-box error";
        }
    });

    // ---------------------------------------------------------
    // Recall Search
    // ---------------------------------------------------------
    async function performRecall() {
        const query = searchInput.value.trim();
        const file_context = searchContext.value.trim() || null;
        if (!query) return;

        searchResultsList.innerHTML = '<p class="placeholder-text">Searching codebase memory graph...</p>';

        try {
            const data = await apiCall("/api/recall", "POST", { query, file_context });
            searchResultsList.innerHTML = "";

            if (!data.results || data.results.length === 0) {
                searchResultsList.innerHTML = '<p class="placeholder-text">No matching memories found for this query.</p>';
                return;
            }

            data.results.forEach(rec => {
                const card = document.createElement("div");
                card.className = "result-card";
                
                const meta = rec.metadata || {};
                const strategy = rec.search_strategy || "KEYWORD_FALLBACK";

                card.innerHTML = `
                    <div class="result-header">
                        <span class="result-title">${rec.title}</span>
                        <span class="strategy-tag">${strategy}</span>
                    </div>
                    <div class="result-file">File: ${rec.file_path || "N/A"}</div>
                    <div class="result-meta">
                        ${meta.root_cause ? `<p><strong>Root Cause:</strong> ${meta.root_cause}</p>` : ""}
                        ${meta.fix_description ? `<p style="margin-top: 8px;"><strong>Fix Applied:</strong> ${meta.fix_description}</p>` : ""}
                        ${!meta.root_cause && rec.content ? `<p>${rec.content}</p>` : ""}
                    </div>
                `;
                searchResultsList.appendChild(card);
            });
        } catch (err) {
            searchResultsList.innerHTML = `<div class="alert-box error">Search failed: ${err.message}</div>`;
        }
    }

    btnSearch.addEventListener("click", performRecall);
    searchInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") performRecall();
    });

    // ---------------------------------------------------------
    // Consolidated Rules
    // ---------------------------------------------------------
    async function refreshRules() {
        try {
            const data = await apiCall("/api/rules");
            rulesTbody.innerHTML = "";

            if (!data.rules || data.rules.length === 0) {
                rulesTbody.innerHTML = `
                    <tr>
                        <td colspan="4" class="placeholder-text">No rules consolidated yet. Click "Reflect & Generalize Rules" or add more bug fixes to trigger consolidation.</td>
                    </tr>
                `;
                return;
            }

            data.rules.forEach(rule => {
                const tr = document.createElement("tr");
                const meta = rule.metadata || {};
                const title = meta.rule_title || rule.rule_title || rule.title || "No Title";
                const desc = meta.description || rule.description || rule.content || "No Description";
                const domain = meta.domain || rule.domain || "general";
                const conf = meta.confidence !== undefined ? meta.confidence : (rule.confidence !== undefined ? rule.confidence : 0.9);

                tr.innerHTML = `
                    <td class="rule-title-cell">${title}</td>
                    <td>${desc}</td>
                    <td><span class="status-badge active" style="font-size: 10px;">${domain.toUpperCase()}</span></td>
                    <td><strong>${(conf * 100).toFixed(0)}%</strong></td>
                `;
                rulesTbody.appendChild(tr);
            });
        } catch (e) {
            rulesTbody.innerHTML = `
                <tr>
                    <td colspan="4" class="placeholder-text" style="color: var(--critical)">Failed to load coding rules.</td>
                </tr>
            `;
        }
    }

    btnReflect.addEventListener("click", async () => {
        const originalText = btnReflect.textContent;
        btnReflect.textContent = "Consolidating graph patterns...";
        btnReflect.disabled = true;

        try {
            await apiCall("/api/reflect", "POST");
            refreshRules();
        } catch (err) {
            alert(`Consolidation failed: ${err.message}`);
        } finally {
            btnReflect.textContent = originalText;
            btnReflect.disabled = false;
        }
    });

    // ---------------------------------------------------------
    // Security Scanning Agent
    // ---------------------------------------------------------
    async function renderSecurityIssues(issues) {
        securityResultsPanel.classList.remove("hide");
        securityIssuesList.innerHTML = "";

        if (!issues || issues.length === 0) {
            securityIssuesList.innerHTML = '<p class="placeholder-text" style="color: var(--success);">✓ No security vulnerabilities detected!</p>';
            return;
        }

        issues.forEach(issue => {
            const card = document.createElement("div");
            card.className = `issue-card ${issue.severity.lower || issue.severity.toLowerCase()}`;
            
            card.innerHTML = `
                <div class="issue-header">
                    <span class="issue-title">● ${issue.vulnerability_type}</span>
                    <span class="issue-severity ${issue.severity.toLowerCase()}">${issue.severity.toUpperCase()}</span>
                </div>
                <div class="issue-desc">
                    File: <strong>${issue.file_path}</strong> ${issue.line_number ? `(Line ${issue.line_number})` : ""}<br>
                    ${issue.description}
                </div>
                <div class="issue-fix">
                    <strong>Proposed Fix:</strong> ${issue.proposed_fix}
                </div>
            `;
            securityIssuesList.appendChild(card);
        });
    }

    btnScanDiff.addEventListener("click", async () => {
        const diffText = securityDiff.value.trim();
        if (!diffText) return;

        btnScanDiff.disabled = true;
        try {
            const data = await apiCall("/api/scan-security", "POST", { diff_text: diffText });
            renderSecurityIssues(data.issues);
        } catch (err) {
            alert(`Scan failed: ${err.message}`);
        } finally {
            btnScanDiff.disabled = false;
        }
    });

    btnScanFile.addEventListener("click", async () => {
        const filePath = securityFilePath.value.trim();
        if (!filePath) return;

        btnScanFile.disabled = true;
        try {
            const data = await apiCall("/api/scan-security", "POST", { file_path: filePath });
            renderSecurityIssues(data.issues);
        } catch (err) {
            alert(`Scan failed: ${err.message}`);
        } finally {
            btnScanFile.disabled = false;
        }
    });

    // ---------------------------------------------------------
    // D3.js Graph Visualizer
    // ---------------------------------------------------------
    let simulation = null;
    async function initD3Graph() {
        const svg = d3.select("#graph-svg");
        svg.selectAll("*").remove(); // Reset canvas

        const width = svg.node().getBoundingClientRect().width;
        const height = svg.node().getBoundingClientRect().height;

        try {
            const data = await apiCall("/api/graph-data");

            if (!data.nodes || data.nodes.length === 0) {
                svg.append("text")
                    .attr("x", width / 2)
                    .attr("y", height / 2)
                    .attr("text-anchor", "middle")
                    .attr("fill", "var(--text-secondary)")
                    .text("Memory graph is currently empty. Ingest some bugs or commits!");
                return;
            }

            // Create arrow marker for directed relations
            svg.append("defs").append("marker")
                .attr("id", "arrow")
                .attr("viewBox", "0 -5 10 10")
                .attr("refX", 20)
                .attr("refY", 0)
                .attr("markerWidth", 6)
                .attr("markerHeight", 6)
                .attr("orient", "auto")
                .append("path")
                .attr("fill", "rgba(255, 0, 127, 0.4)")
                .attr("d", "M0,-5L10,0L0,5");

            const gContainer = svg.append("g");

            // Pan and Zoom
            svg.call(d3.zoom().on("zoom", (event) => {
                gContainer.attr("transform", event.transform);
            }));

            // Force layout setup
            simulation = d3.forceSimulation(data.nodes)
                .force("link", d3.forceLink(data.links).id(d => d.id).distance(120))
                .force("charge", d3.forceManyBody().strength(-200))
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force("collision", d3.forceCollide().radius(25));

            // Draw link lines
            const link = gContainer.append("g")
                .selectAll("line")
                .data(data.links)
                .join("line")
                .attr("stroke", "rgba(255, 0, 127, 0.25)")
                .attr("stroke-width", 1.5)
                .attr("marker-end", "url(#arrow)");

            // Draw node groups
            const node = gContainer.append("g")
                .selectAll("g")
                .data(data.nodes)
                .join("g")
                .attr("cursor", "pointer")
                .call(drag(simulation));

            // Circle shapes
            node.append("circle")
                .attr("r", d => d.type === "tenant" ? 14 : (d.type === "file" ? 10 : 8))
                .attr("class", d => `node-circle ${d.type}`);

            // Text labels
            node.append("text")
                .attr("dy", 20)
                .attr("text-anchor", "middle")
                .attr("fill", "var(--text-secondary)")
                .attr("font-size", "10px")
                .text(d => {
                    const maxLen = 16;
                    return d.label.length > maxLen ? d.label.substring(0, maxLen) + "..." : d.label;
                });

            // Hover tooltip
            node.append("title")
                .text(d => `${d.label} [Type: ${d.type}]`);

            // Node Click Drawer Toggle
            node.on("click", (event, d) => {
                event.stopPropagation();
                drawer.classList.remove("hide");
                drawerTitle.textContent = d.label;
                
                drawerContent.innerHTML = "";
                const details = d.details || {};
                
                // Construct details body
                for (const [key, val] of Object.entries(details)) {
                    const row = document.createElement("div");
                    row.className = "detail-row";
                    row.innerHTML = `
                        <div class="detail-label">${key}</div>
                        <div class="detail-value">${val}</div>
                    `;
                    drawerContent.appendChild(row);
                }
                
                if (Object.keys(details).length === 0) {
                    drawerContent.innerHTML = `<p class="placeholder-text" style="padding: 10px 0;">No details metadata for this node type.</p>`;
                }
            });

            // Close Drawer click listener
            svg.on("click", () => drawer.classList.add("hide"));
            drawerClose.addEventListener("click", () => drawer.classList.add("hide"));

            // Simulation ticking
            simulation.on("tick", () => {
                link
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);

                node.attr("transform", d => `translate(${d.x},${d.y})`);
            });

        } catch (e) {
            console.error("D3 loading failed", e);
        }
    }

    // Drag behavior helper
    function drag(simulation) {
        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }
        
        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }
        
        function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }
        
        return d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended);
    }

    // Initialize Dashboard on load
    refreshDashboard();
});
"""
