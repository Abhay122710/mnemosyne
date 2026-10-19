document.addEventListener("DOMContentLoaded", () => {
  const API_BASE = window.location.origin.startsWith("file") ? "http://127.0.0.1:8085" : window.location.origin;

  // =========================================================
  // API Call Helper
  // =========================================================
  async function apiCall(endpoint, method = "GET", body = null) {
    const options = {
      method,
      headers: { "Content-Type": "application/json" }
    };
    if (body) {
      options.body = JSON.stringify(body);
    }
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, options);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Request failed with status ${res.status}`);
      }
      return await res.json();
    } catch (e) {
      console.error(`API Error (${endpoint}):`, e);
      throw e;
    }
  }

  // =========================================================
  // Viewport Section Navigation (Seamless UI matching Pic 2)
  // =========================================================
  const navLinks = document.querySelectorAll(".nav-link");
  const mobileLinks = document.querySelectorAll(".mobile-link");
  const pageViews = document.querySelectorAll(".page-view");
  const logoBtn = document.querySelector(".logo-btn");
  const heroGetStartedBtn = document.getElementById("hero-get-started-btn");
  const headerStatusBtn = document.getElementById("header-status-btn");

  let currentTab = "home";

  function switchTab(tabName) {
    if (!tabName) tabName = "home";
    currentTab = tabName;

    // 1. Sync Header Nav Links
    navLinks.forEach((link) => {
      if (link.getAttribute("data-tab") === tabName) {
        link.classList.add("active");
      } else {
        link.classList.remove("active");
      }
    });

    // 2. Sync Mobile Menu Links
    mobileLinks.forEach((link) => {
      if (link.getAttribute("data-tab") === tabName) {
        link.classList.add("active");
      } else {
        link.classList.remove("active");
      }
    });

    // 3. Show Corresponding Viewport Section
    pageViews.forEach((view) => {
      if (view.id === `view-${tabName}`) {
        view.classList.add("active");
      } else {
        view.classList.remove("active");
      }
    });

    // Close mobile sheet if open
    closeMobileMenu();

    // 4. Trigger Section Loaders
    if (tabName === "dashboard") refreshDashboard();
    if (tabName === "rules") refreshRules();
    if (tabName === "visualizer") {
      // Delay slightly for container size to settle
      setTimeout(initD3Graph, 50);
    }
  }

  // Attach click listeners to all tab buttons
  navLinks.forEach((link) => {
    link.addEventListener("click", () => {
      const tab = link.getAttribute("data-tab");
      switchTab(tab);
    });
  });

  if (logoBtn) {
    logoBtn.addEventListener("click", () => {
      switchTab("home");
    });
  }

  if (heroGetStartedBtn) {
    heroGetStartedBtn.addEventListener("click", () => {
      switchTab("dashboard");
    });
  }

  if (headerStatusBtn) {
    headerStatusBtn.addEventListener("click", () => {
      switchTab("dashboard");
    });
  }

  // =========================================================
  // Mobile Menu Interactions
  // =========================================================
  const burgerBtn = document.getElementById("burger-btn");
  const mobileOverlay = document.getElementById("mobile-overlay");
  const mobileSheet = document.getElementById("mobile-sheet");

  function openMobileMenu() {
    if (!burgerBtn) return;
    burgerBtn.setAttribute("aria-expanded", "true");
    if (mobileOverlay) mobileOverlay.removeAttribute("hidden");
    if (mobileSheet) mobileSheet.removeAttribute("hidden");
  }

  function closeMobileMenu() {
    if (!burgerBtn) return;
    burgerBtn.setAttribute("aria-expanded", "false");
    if (mobileOverlay) mobileOverlay.setAttribute("hidden", "");
    if (mobileSheet) mobileSheet.setAttribute("hidden", "");
  }

  function toggleMobileMenu() {
    const isExpanded = burgerBtn && burgerBtn.getAttribute("aria-expanded") === "true";
    if (isExpanded) closeMobileMenu();
    else openMobileMenu();
  }

  if (burgerBtn && mobileOverlay && mobileSheet) {
    burgerBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleMobileMenu();
    });

    mobileOverlay.addEventListener("click", closeMobileMenu);

    mobileLinks.forEach((link) => {
      link.addEventListener("click", () => {
        const tab = link.getAttribute("data-tab");
        switchTab(tab);
      });
    });
  }

  // Keyboard Escape Handler
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (burgerBtn && burgerBtn.getAttribute("aria-expanded") === "true") {
        closeMobileMenu();
      } else if (currentTab !== "home") {
        switchTab("home");
      }
    }
  });

  // Resize Handler
  window.addEventListener("resize", () => {
    if (window.innerWidth > 720 && burgerBtn && burgerBtn.getAttribute("aria-expanded") === "true") {
      closeMobileMenu();
    }
  });

  // =========================================================
  // 1. Dashboard Status & Telemetry
  // =========================================================
  const dashTotalNodes = document.getElementById("dash-total-nodes");
  const dashBugFixes = document.getElementById("dash-bug-fixes");
  const dashRules = document.getElementById("dash-rules");
  const dashCommits = document.getElementById("dash-commits");
  const badgeCognee = document.getElementById("badge-cognee");
  const badgeLlm = document.getElementById("badge-llm");
  const badgeFallback = document.getElementById("badge-fallback");

  const systemPulseDot = document.getElementById("system-pulse-dot");
  const systemStatusText = document.getElementById("system-status-text");
  const mobilePulseDot = document.getElementById("mobile-pulse-dot");
  const mobileStatusText = document.getElementById("mobile-status-text");

  function setBadge(el, active) {
    if (!el) return;
    el.textContent = active ? "Active" : "Offline";
    el.className = `badge ${active ? "active" : "offline"}`;
  }

  async function refreshDashboard() {
    try {
      const data = await apiCall("/api/status");

      const totalNodes = (data.total_memories || 0) + (data.rule_nodes || 0);
      const bugFixes = data.bug_fixes || 0;
      const rules = data.rule_nodes || 0;
      const commits = data.commit_memories || 0;

      // Update Dashboard view counters
      if (dashTotalNodes) dashTotalNodes.textContent = totalNodes;
      if (dashBugFixes) dashBugFixes.textContent = bugFixes;
      if (dashRules) dashRules.textContent = rules;
      if (dashCommits) dashCommits.textContent = commits;

      // Sync Front Page Footer Stats
      const statTotalNodesEl = document.getElementById("stat-total-nodes-val");
      const statBugFixesEl = document.getElementById("stat-bug-fixes-val");
      const statRulesEl = document.getElementById("stat-rules-val");
      const statCommitsEl = document.getElementById("stat-commits-val");

      if (statTotalNodesEl) {
        statTotalNodesEl.setAttribute("data-target", totalNodes);
        statTotalNodesEl.textContent = totalNodes;
      }
      if (statBugFixesEl) {
        statBugFixesEl.setAttribute("data-target", bugFixes);
        statBugFixesEl.textContent = bugFixes;
      }
      if (statRulesEl) {
        statRulesEl.setAttribute("data-target", rules);
        statRulesEl.textContent = rules;
      }
      if (statCommitsEl) {
        statCommitsEl.setAttribute("data-target", commits);
        statCommitsEl.textContent = commits;
      }

      // Update Badges
      setBadge(badgeCognee, data.cognee_active);
      setBadge(badgeLlm, data.llm_active);
      setBadge(badgeFallback, data.offline_mode);

      // Status labels
      const statusLabel = data.cognee_active ? "Cognee Active" : "Fallback Active";
      if (systemStatusText) systemStatusText.textContent = statusLabel;
      if (mobileStatusText) mobileStatusText.textContent = statusLabel;

      const heroPulseDot = document.getElementById("hero-pulse-dot");
      const heroStatusText = document.getElementById("hero-status-text");
      if (heroStatusText) {
        heroStatusText.textContent = data.cognee_active ? "Code Knowledge Graph Active" : "Codebase Memory Graph (Local Fallback)";
      }
      if (heroPulseDot) {
        heroPulseDot.className = `status-pulse-dot ${data.cognee_active ? "" : "offline"}`;
      }

      if (systemPulseDot) systemPulseDot.className = `status-pulse-dot ${data.cognee_active ? "" : "offline"}`;
      if (mobilePulseDot) mobilePulseDot.className = `status-pulse-dot ${data.cognee_active ? "" : "offline"}`;
    } catch (e) {
      if (systemStatusText) systemStatusText.textContent = "Fallback Active";
      if (mobileStatusText) mobileStatusText.textContent = "Fallback Active";
      if (systemPulseDot) systemPulseDot.className = "status-pulse-dot offline";
      if (mobilePulseDot) mobilePulseDot.className = "status-pulse-dot offline";
      setBadge(badgeCognee, false);
      setBadge(badgeLlm, false);
      setBadge(badgeFallback, true);
    }
  }

  // Pre-load telemetry on startup
  refreshDashboard();

  // =========================================================
  // 2. Remember Bug Form Ingestion
  // =========================================================
  const bugForm = document.getElementById("bug-ingest-form");
  const bugMsg = document.getElementById("bug-form-message");
  const btnSubmitBug = document.getElementById("btn-submit-bug");

  if (bugForm) {
    bugForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      bugMsg.textContent = "";
      bugMsg.className = "form-message";
      btnSubmitBug.disabled = true;

      const tagsRaw = document.getElementById("bug-tags").value;
      const tags = tagsRaw ? tagsRaw.split(",").map((t) => t.trim()).filter(Boolean) : [];

      const payload = {
        file_path: document.getElementById("bug-file-path").value.trim(),
        title: document.getElementById("bug-title").value.trim(),
        root_cause: document.getElementById("bug-root-cause").value.trim(),
        fix_description: document.getElementById("bug-fix-desc").value.trim(),
        severity: document.getElementById("bug-severity").value,
        tags: tags
      };

      try {
        const res = await apiCall("/api/remember-bug", "POST", payload);
        bugMsg.textContent = `✓ Bug successfully logged into Graph Memory! (Node ID: ${res.id})`;
        bugMsg.className = "form-message success";
        bugForm.reset();
        refreshDashboard();
      } catch (err) {
        bugMsg.textContent = `Error: ${err.message}`;
        bugMsg.className = "form-message error";
      } finally {
        btnSubmitBug.disabled = false;
      }
    });
  }

  // =========================================================
  // 3. Recall Search
  // =========================================================
  const recallQuery = document.getElementById("recall-query");
  const recallContext = document.getElementById("recall-context");
  const btnRunRecall = document.getElementById("btn-run-recall");
  const recallResultsList = document.getElementById("recall-results-list");

  async function performRecall() {
    const query = recallQuery.value.trim();
    const file_context = recallContext.value.trim() || null;
    if (!query) return;

    btnRunRecall.disabled = true;
    recallResultsList.innerHTML = '<p class="empty-state-text">Traversing knowledge graph and vector indices...</p>';

    try {
      const data = await apiCall("/api/recall", "POST", { query, file_context, top_k: 6 });
      recallResultsList.innerHTML = "";

      if (!data.results || data.results.length === 0) {
        recallResultsList.innerHTML = '<p class="empty-state-text">No matching memories found for this query.</p>';
        return;
      }

      data.results.forEach((rec) => {
        const card = document.createElement("div");
        card.className = "memory-result-card";
        const meta = rec.metadata || {};
        const strategy = rec.search_strategy || "GRAPH_VECTOR_HYBRID";

        card.innerHTML = `
          <div class="result-card-top">
            <span class="result-card-title">${rec.title || "Untitled Memory"}</span>
            <span class="strategy-badge">${strategy}</span>
          </div>
          <div class="result-file-path"><i class="fa-regular fa-file-code"></i> ${rec.file_path || "N/A"}</div>
          <div class="result-meta-body">
            ${meta.root_cause ? `<p><strong>Root Cause:</strong> ${meta.root_cause}</p>` : ""}
            ${meta.fix_description ? `<p style="margin-top: 4px;"><strong>Fix Applied:</strong> ${meta.fix_description}</p>` : ""}
            ${!meta.root_cause && rec.content ? `<p>${rec.content}</p>` : ""}
          </div>
        `;
        recallResultsList.appendChild(card);
      });
    } catch (err) {
      recallResultsList.innerHTML = `<div class="form-message error" style="padding: 16px;">Recall search failed: ${err.message}</div>`;
    } finally {
      btnRunRecall.disabled = false;
    }
  }

  if (btnRunRecall) btnRunRecall.addEventListener("click", performRecall);
  if (recallQuery) {
    recallQuery.addEventListener("keydown", (e) => {
      if (e.key === "Enter") performRecall();
    });
  }

  // =========================================================
  // 4. Consolidated Rules
  // =========================================================
  const rulesTableBody = document.getElementById("rules-table-body");
  const btnReflectRules = document.getElementById("btn-reflect-rules");

  async function refreshRules() {
    try {
      rulesTableBody.innerHTML = '<tr><td colspan="4" class="empty-state-text">Fetching consolidated rules...</td></tr>';
      const data = await apiCall("/api/rules");
      rulesTableBody.innerHTML = "";

      if (!data.rules || data.rules.length === 0) {
        rulesTableBody.innerHTML = `
          <tr>
            <td colspan="4" class="empty-state-text">No rules consolidated yet. Click "Reflect & Generalize Rules" to cluster bug fixes into rules.</td>
          </tr>
        `;
        return;
      }

      data.rules.forEach((rule) => {
        const tr = document.createElement("tr");
        const meta = rule.metadata || {};
        const title = meta.rule_title || rule.rule_title || rule.title || "Consolidated Pattern";
        const desc = meta.description || rule.description || rule.content || "No Description";
        const domain = meta.domain || rule.domain || "general";
        const conf = meta.confidence !== undefined ? meta.confidence : 0.95;

        tr.innerHTML = `
          <td class="rule-title-cell">${title}</td>
          <td>${desc}</td>
          <td><span class="badge active" style="font-size: 10px;">${domain.toUpperCase()}</span></td>
          <td><strong>${(conf * 100).toFixed(0)}%</strong></td>
        `;
        rulesTableBody.appendChild(tr);
      });
    } catch (e) {
      rulesTableBody.innerHTML = `<tr><td colspan="4" class="empty-state-text" style="color: var(--danger)">Failed to load coding rules: ${e.message}</td></tr>`;
    }
  }

  if (btnReflectRules) {
    btnReflectRules.addEventListener("click", async () => {
      btnReflectRules.disabled = true;
      btnReflectRules.innerHTML = '<span>⏳ Reflecting & Synthesizing...</span>';
      try {
        await apiCall("/api/reflect", "POST");
        await refreshRules();
        await refreshDashboard();
      } catch (err) {
        alert(`Rule reflection failed: ${err.message}`);
      } finally {
        btnReflectRules.disabled = false;
        btnReflectRules.innerHTML = '<span>✨ Reflect & Generalize Rules</span>';
      }
    });
  }

  // =========================================================
  // 5. Security Scanner
  // =========================================================
  const securityDiffInput = document.getElementById("security-diff-input");
  const securityFileInput = document.getElementById("security-file-input");
  const btnRunScan = document.getElementById("btn-run-scan");
  const btnPrefillDiff = document.getElementById("btn-prefill-diff");
  const securityIssuesList = document.getElementById("security-issues-list");

  if (btnPrefillDiff) {
    btnPrefillDiff.addEventListener("click", () => {
      securityDiffInput.value = `diff --git a/image_pipeline.py b/image_pipeline.py
--- a/image_pipeline.py
+++ b/image_pipeline.py
@@ -10,4 +10,6 @@ def process_file(path):
+    f = open(path, "r")
+    data = f.read()
+    # Missing with-statement and explicit close leads to descriptor leak`;
    });
  }

  if (btnRunScan) {
    btnRunScan.addEventListener("click", async () => {
      const diffText = securityDiffInput.value.trim();
      const filePath = securityFileInput.value.trim();

      if (!diffText && !filePath) {
        alert("Please paste a git diff or provide a file path to scan.");
        return;
      }

      btnRunScan.disabled = true;
      btnRunScan.textContent = "Scanning Codebase Rules...";
      securityIssuesList.innerHTML = '<p class="empty-state-text">Auditing against consolidated team anti-patterns...</p>';

      const payload = diffText ? { diff_text: diffText } : { file_path: filePath };

      try {
        const data = await apiCall("/api/scan-security", "POST", payload);
        securityIssuesList.innerHTML = "";

        if (!data.issues || data.issues.length === 0) {
          securityIssuesList.innerHTML = '<p class="empty-state-text" style="color: var(--success);">✓ Clean code! No anti-patterns or security violations detected.</p>';
          return;
        }

        data.issues.forEach((issue) => {
          const card = document.createElement("div");
          const sev = (issue.severity || "medium").toLowerCase();
          card.className = `issue-card ${sev}`;

          card.innerHTML = `
            <div class="issue-top">
              <span class="issue-title">● ${issue.vulnerability_type || "Security Issue"}</span>
              <span class="issue-severity ${sev}">${sev.toUpperCase()}</span>
            </div>
            <div class="issue-meta">
              File: <strong>${issue.file_path || "Diff Block"}</strong> ${issue.line_number ? `(Line ${issue.line_number})` : ""}<br />
              ${issue.description || ""}
            </div>
            <div class="issue-fix">
              <strong>Proposed Fix:</strong> ${issue.proposed_fix || "Apply context manager pattern."}
            </div>
          `;
          securityIssuesList.appendChild(card);
        });
      } catch (err) {
        securityIssuesList.innerHTML = `<div class="form-message error" style="padding: 14px;">Scan error: ${err.message}</div>`;
      } finally {
        btnRunScan.disabled = false;
        btnRunScan.textContent = "Run Security Scan";
      }
    });
  }

  // =========================================================
  // 6. Interactive D3 Knowledge Graph Visualizer
  // =========================================================
  let simulation = null;
  const nodeDrawer = document.getElementById("node-drawer");
  const drawerNodeTitle = document.getElementById("drawer-node-title");
  const drawerNodeContent = document.getElementById("drawer-node-content");
  const drawerCloseBtn = document.getElementById("drawer-close-btn");

  if (drawerCloseBtn) {
    drawerCloseBtn.addEventListener("click", () => {
      nodeDrawer.classList.add("hide");
    });
  }

  async function initD3Graph() {
    if (typeof d3 === "undefined") return;

    const svg = d3.select("#graph-svg");
    svg.selectAll("*").remove();

    const rect = svg.node().getBoundingClientRect();
    const width = rect.width || 800;
    const height = rect.height || 500;

    try {
      const data = await apiCall("/api/graph-data");

      if (!data.nodes || data.nodes.length === 0) {
        svg.append("text")
          .attr("x", width / 2)
          .attr("y", height / 2)
          .attr("text-anchor", "middle")
          .attr("fill", "var(--muted)")
          .text("Knowledge Graph is currently empty. Ingest some bug fixes to populate!");
        return;
      }

      // Marker for arrows
      svg.append("defs").append("marker")
        .attr("id", "arrow-marker")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 22)
        .attr("refY", 0)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .append("path")
        .attr("fill", "rgba(255, 0, 127, 0.45)")
        .attr("d", "M0,-5L10,0L0,5");

      const g = svg.append("g");

      // Zoom & Pan
      svg.call(
        d3.zoom()
          .scaleExtent([0.3, 3])
          .on("zoom", (event) => {
            g.attr("transform", event.transform);
          })
      );

      // Force Simulation
      simulation = d3.forceSimulation(data.nodes)
        .force("link", d3.forceLink(data.links).id((d) => d.id).distance(110))
        .force("charge", d3.forceManyBody().strength(-240))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(26));

      // Links
      const link = g.append("g")
        .selectAll("line")
        .data(data.links)
        .join("line")
        .attr("stroke", "rgba(255, 255, 255, 0.15)")
        .attr("stroke-width", 1.5)
        .attr("marker-end", "url(#arrow-marker)");

      // Nodes
      const node = g.append("g")
        .selectAll("g")
        .data(data.nodes)
        .join("g")
        .attr("cursor", "pointer")
        .call(
          d3.drag()
            .on("start", (event, d) => {
              if (!event.active) simulation.alphaTarget(0.3).restart();
              d.fx = d.x;
              d.fy = d.y;
            })
            .on("drag", (event, d) => {
              d.fx = event.x;
              d.fy = event.y;
            })
            .on("end", (event, d) => {
              if (!event.active) simulation.alphaTarget(0);
              d.fx = null;
              d.fy = null;
            })
        );

      node.append("circle")
        .attr("r", (d) => (d.type === "tenant" ? 15 : d.type === "file" ? 11 : 9))
        .attr("class", (d) => `node-circle ${d.type}`);

      node.append("text")
        .attr("dy", 22)
        .attr("text-anchor", "middle")
        .attr("fill", "#a1a1aa")
        .attr("font-size", "10px")
        .text((d) => {
          const l = d.label || d.id;
          return l.length > 15 ? l.substring(0, 15) + "…" : l;
        });

      // Node Click Drawer
      node.on("click", (event, d) => {
        event.stopPropagation();
        nodeDrawer.classList.remove("hide");
        drawerNodeTitle.textContent = d.label || d.id;
        drawerNodeContent.innerHTML = "";

        const details = d.details || {};
        const rows = [
          { label: "Node Type", val: d.type },
          { label: "Node ID", val: d.id },
          ...Object.entries(details).map(([k, v]) => ({ label: k, val: v }))
        ];

        rows.forEach((r) => {
          const rowEl = document.createElement("div");
          rowEl.className = "detail-row";
          rowEl.innerHTML = `
            <div class="detail-label">${r.label}</div>
            <div class="detail-value">${r.val}</div>
          `;
          drawerNodeContent.appendChild(rowEl);
        });
      });

      svg.on("click", () => nodeDrawer.classList.add("hide"));

      simulation.on("tick", () => {
        link
          .attr("x1", (d) => d.source.x)
          .attr("y1", (d) => d.source.y)
          .attr("x2", (d) => d.target.x)
          .attr("y2", (d) => d.target.y);

        node.attr("transform", (d) => `translate(${d.x},${d.y})`);
      });
    } catch (e) {
      console.error("D3 graph rendering error:", e);
    }
  }

  // =========================================================
  // 7. Landing Page Stats Count-Up Animation
  // =========================================================
  const statElements = document.querySelectorAll(".stat-value");
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  function animateStat(el, index) {
    const target = parseFloat(el.getAttribute("data-target"));
    const suffix = el.getAttribute("data-suffix") || "";
    const decimals = parseInt(el.getAttribute("data-decimals"), 10) || 0;

    if (prefersReducedMotion || isNaN(target)) {
      if (!isNaN(target)) el.textContent = target.toFixed(decimals) + suffix;
      return;
    }

    const duration = 1400 + index * 80;
    const delay = 400 + index * 80;

    setTimeout(() => {
      let startTime = null;

      function step(currentTime) {
        if (!startTime) startTime = currentTime;
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const currentEased = easeOutCubic(progress);
        const currentVal = target * currentEased;

        el.textContent = currentVal.toFixed(decimals) + suffix;

        if (progress < 1) {
          requestAnimationFrame(step);
        } else {
          el.textContent = target.toFixed(decimals) + suffix;
        }
      }

      requestAnimationFrame(step);
    }, delay);
  }

  let statsAnimated = false;
  const statsFooter = document.querySelector(".stats-footer");

  if (statsFooter && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !statsAnimated) {
            statsAnimated = true;
            statElements.forEach((el, i) => animateStat(el, i));
            observer.unobserve(statsFooter);
          }
        });
      },
      { threshold: 0.25 }
    );

    observer.observe(statsFooter);
  } else {
    statElements.forEach((el, i) => animateStat(el, i));
  }
});
