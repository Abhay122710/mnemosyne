document.addEventListener("DOMContentLoaded", () => {
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
