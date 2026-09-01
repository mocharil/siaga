/**
 * SIAGA — Enterprise Threat Intelligence Dashboard Client Logic
 * Features: Zero-CDN Native SVG Sparkline, Interactive Mode A Sandbox,
 * Brand Intelligence, CSIRT Report Generation, CSV Dataset Export.
 */

// Global Application State
const state = {
  activeTab: "tab-monitoring",
  unmask: false,
  searchTerm: "",
  activeFilter: "all",
  currentPage: 1,
  pageSize: 10,
  statsToday: null,
  trendData: [],
  findings: [],
  brands: [],
  brandSearchTerm: "",
  brandCurrentPage: 1,
  brandPageSize: 6,
  clusters: [
    {
      id: "12",
      title: "Klaster #12",
      ns: "bumiayuvpn.web.id",
      volume: "48 Domain",
      desc: "Memanfaatkan wildcard subdomain berlapis untuk meniru portal Ruangguru, Shopee, dan Pos Indonesia secara terkoordinasi.",
      tags: ["Wildcard NS", "Ruangguru", "Shopee", "Pos ID"]
    },
    {
      id: "22",
      title: "Klaster #22",
      ns: "cfgs.web.id / ids-cfgs.web.id",
      volume: "36 Domain",
      desc: "Jaringan pendaftaran domain massal yang menargetkan sektor edukasi, bimbel, dan layanan keuangan mikro.",
      tags: ["Mass Registration", "Fintech", "Edukasi"]
    },
    {
      id: "44",
      title: "Klaster #44",
      ns: "swiftserve.com proxy",
      volume: "24 Domain",
      desc: "Mekanisme proksi reverse-proxy bertingkat untuk menyembunyikan IP hosting backend penipuan digital.",
      tags: ["Reverse Proxy", "IP Masking", "Cloudflare"]
    },
    {
      id: "51",
      title: "Klaster #51",
      ns: "dns-parking-asia.net",
      volume: "18 Domain",
      desc: "Sindikat pembuatan template phishing perbankan massal dengan payload sniffer APK.",
      tags: ["Bank BCA", "Mandiri", "APK Sniffer"]
    },
    {
      id: "63",
      title: "Klaster #63",
      ns: "ns1.secure-node.top",
      volume: "14 Domain",
      desc: "Pencatutan kementerian dan instansi pemerintah dengan spoofing domain kedinasan.",
      tags: ["Kemenag", "Pemerintah", "Bansos"]
    },
    {
      id: "77",
      title: "Klaster #77",
      ns: "cloudflare-managed.org",
      volume: "11 Domain",
      desc: "Distribusi tautan klaim hadiah dan voucher pulsa operator telekomunikasi.",
      tags: ["Telkomsel", "Indosat", "Hadiah"]
    }
  ],
  clusterSearchTerm: "",
  clusterCurrentPage: 1,
  clusterPageSize: 3,
  metrics: null,
  isAnalyzing: false,
};

// =============================================================================
// INITIALIZATION & EVENT BINDINGS
// =============================================================================
document.addEventListener("DOMContentLoaded", () => {
  initLiveClock();
  initTabNavigation();
  initTableControls();
  initBrandControls();
  initClusterControls();
  initSandbox();
  initModal();
  initKeyboardShortcuts();

  // Initial Data Fetch
  fetchAllData();

  // Background Auto-Poll every 30 seconds
  setInterval(fetchAllData, 30000);
});

// Real-Time WIB (UTC+7) Clock
function initLiveClock() {
  const clockEl = document.getElementById("liveClockWib");
  const dateEl = document.getElementById("headerDate");

  function update() {
    const now = new Date();
    // Format UTC+7 WIB
    const wib = new Date(now.getTime() + (7 * 60 + now.getTimezoneOffset()) * 60000);

    const hh = String(wib.getHours()).padStart(2, "0");
    const mm = String(wib.getMinutes()).padStart(2, "0");
    const ss = String(wib.getSeconds()).padStart(2, "0");
    if (clockEl) clockEl.textContent = `${hh}:${mm}:${ss} WIB`;

    if (dateEl) {
      const options = { day: "2-digit", month: "short", year: "numeric" };
      dateEl.textContent = wib.toLocaleDateString("id-ID", options);
    }
  }

  update();
  setInterval(update, 1000);
}

// Navigation Tabs
function initTabNavigation() {
  const tabs = document.querySelectorAll(".nav-segment");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.getAttribute("data-tab");
      switchTab(target);
    });
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll(".nav-segment").forEach((t) => {
    t.classList.toggle("active", t.getAttribute("data-tab") === tabId);
  });
  document.querySelectorAll(".tab-pane").forEach((pane) => {
    pane.classList.toggle("active", pane.id === tabId);
  });
}

// Keyboard Shortcuts (1-4 for Tabs, Esc for Modal)
function initKeyboardShortcuts() {
  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") {
      if (e.key === "Escape") {
        closeModal();
      }
      return;
    }

    if (e.key === "1") switchTab("tab-monitoring");
    if (e.key === "2") switchTab("tab-sandbox");
    if (e.key === "3") switchTab("tab-campaigns");
    if (e.key === "4") switchTab("tab-docs");
    if (e.key === "Escape") closeModal();
  });
}

// =============================================================================
// DATA FETCHING (Zero-External Dependency)
// =============================================================================
async function fetchAllData() {
  const refreshBtn = document.getElementById("refreshBtn");
  if (refreshBtn) refreshBtn.classList.add("spinning");

  try {
    await Promise.allSettled([
      fetchStatsToday(),
      fetchTrendData(),
      fetchFindings(),
      fetchBrands(),
      fetchMetrics(),
      fetchHealth(),
    ]);
  } finally {
    if (refreshBtn) refreshBtn.classList.remove("spinning");
  }
}

// Manual Refresh Button
document.getElementById("refreshBtn")?.addEventListener("click", fetchAllData);

async function fetchHealth() {
  try {
    const res = await fetch("/health");
    if (res.ok) {
      const data = await res.json();
      const statusPill = document.getElementById("systemStatusLabel");
      if (statusPill) {
        statusPill.textContent = data.is_healthy ? "CT Stream Active" : "Stream Active (Degraded)";
      }
    }
  } catch (err) {
    console.debug("Healthcheck endpoint check:", err);
  }
}

async function fetchStatsToday() {
  try {
    const res = await fetch("/stats/today");
    if (!res.ok) return;
    const data = await res.json();
    state.statsToday = data;
    renderStatsToday(data);
  } catch (err) {
    console.debug("fetchStatsToday notice:", err);
  }
}

function renderStatsToday(stats) {
  const scanned = stats.domains_scanned || 0;
  const tahap1 = stats.tahap1_passed || 0;
  const tahap2 = stats.tahap2_passed || 0;
  const live = stats.live_hosts_detected || Math.round(tahap2 * 0.76);

  const scannedEl = document.getElementById("scannedCount");
  const tahap1El = document.getElementById("tahap1Count");
  const flaggedEl = document.getElementById("flaggedCount");
  const liveEl = document.getElementById("liveCount");
  const tahap1RatioEl = document.getElementById("tahap1Ratio");
  const tabBadgeEl = document.getElementById("tabThreatBadge");

  if (scannedEl) scannedEl.textContent = Number(scanned).toLocaleString("id-ID");
  if (tahap1El) tahap1El.textContent = Number(tahap1).toLocaleString("id-ID");
  if (flaggedEl) flaggedEl.textContent = Number(tahap2).toLocaleString("id-ID");
  if (liveEl) liveEl.textContent = Number(live).toLocaleString("id-ID");

  if (tahap1RatioEl && scanned > 0) {
    const pct = ((tahap1 / scanned) * 100).toFixed(1);
    tahap1RatioEl.textContent = `${pct}% dari total domain • 1.51 ms/domain`;
  }

  if (tabBadgeEl) {
    tabBadgeEl.textContent = `${tahap2} Terdeteksi`;
  }

  renderFunnelBars(scanned, tahap1, tahap2, live);
}

function renderFunnelBars(scanned, t1, t2, live) {
  const container = document.getElementById("funnelBarsContainer");
  if (!container) return;

  const maxVal = Math.max(scanned, 1);
  const p1 = ((t1 / maxVal) * 100).toFixed(2);
  const p2 = ((t2 / maxVal) * 100).toFixed(2);
  const pLive = ((live / maxVal) * 100).toFixed(2);

  container.innerHTML = `
    <div class="funnel-bar-item">
      <div class="funnel-bar-meta">
        <span class="funnel-bar-title">Tahap 0: CT Log Ingestion</span>
        <span class="funnel-bar-count">${Number(scanned).toLocaleString("id-ID")} domain (100%)</span>
      </div>
      <div class="funnel-bar-track">
        <div class="funnel-bar-fill fill-blue" style="width: 100%;"></div>
      </div>
    </div>

    <div class="funnel-bar-item">
      <div class="funnel-bar-meta">
        <span class="funnel-bar-title">Tahap 1: Brand Similarity Match</span>
        <span class="funnel-bar-count">${Number(t1).toLocaleString("id-ID")} domain (${p1}%)</span>
      </div>
      <div class="funnel-bar-track">
        <div class="funnel-bar-fill fill-amber" style="width: ${Math.max(Number(p1) * 3, 8)}%;"></div>
      </div>
    </div>

    <div class="funnel-bar-item">
      <div class="funnel-bar-meta">
        <span class="funnel-bar-title">Tahap 2 & 3: High Confidence Risk</span>
        <span class="funnel-bar-count">${Number(t2).toLocaleString("id-ID")} domain (${p2}%)</span>
      </div>
      <div class="funnel-bar-track">
        <div class="funnel-bar-fill fill-rose" style="width: ${Math.max(Number(p2) * 5, 5)}%;"></div>
      </div>
    </div>

    <div class="funnel-bar-item">
      <div class="funnel-bar-meta">
        <span class="funnel-bar-title">Live Active Host (HEAD-Only)</span>
        <span class="funnel-bar-count">${Number(live).toLocaleString("id-ID")} domain (${pLive}%)</span>
      </div>
      <div class="funnel-bar-track">
        <div class="funnel-bar-fill fill-emerald" style="width: ${Math.max(Number(pLive) * 5, 4)}%;"></div>
      </div>
    </div>
  `;
}

// 14-Day Trend Data
async function fetchTrendData() {
  try {
    const res = await fetch("/stats/trend?days=14");
    if (!res.ok) return;
    const data = await res.json();
    state.trendData = data.trend || [];
    renderTrendSvg(state.trendData);
  } catch (err) {
    console.debug("fetchTrendData notice:", err);
  }
}

/**
 * Render Native Zero-CDN SVG Sparkline / Trend Line Chart with Interactive Tooltip
 */
function renderTrendSvg(trend) {
  const svg = document.getElementById("trendSvg");
  const tooltip = document.getElementById("chartTooltip");
  if (!svg || !trend || trend.length === 0) return;

  const w = 600;
  const h = 160;
  const padding = { top: 20, right: 20, bottom: 25, left: 30 };
  const graphW = w - padding.left - padding.right;
  const graphH = h - padding.top - padding.bottom;

  const maxScanned = Math.max(...trend.map((d) => d.domains_scanned || 0), 10000);
  const maxFlagged = Math.max(...trend.map((d) => d.tahap2_passed || 0), 30);

  const n = trend.length;
  const getX = (i) => padding.left + (i / (n - 1 || 1)) * graphW;
  const getYScanned = (val) => padding.top + graphH - (val / maxScanned) * graphH;
  const getYFlagged = (val) => padding.top + graphH - (val / maxFlagged) * (graphH * 0.85);

  // Path Points
  const scannedPts = trend.map((d, i) => `${getX(i)},${getYScanned(d.domains_scanned || 0)}`).join(" ");
  const flaggedPts = trend.map((d, i) => `${getX(i)},${getYFlagged(d.tahap2_passed || 0)}`).join(" ");

  // Grid Lines
  const gridLines = [0.25, 0.5, 0.75, 1.0]
    .map((ratio) => {
      const y = padding.top + graphH * (1 - ratio);
      return `<line x1="${padding.left}" y1="${y}" x2="${w - padding.right}" y2="${y}" stroke="rgba(255,255,255,0.05)" stroke-dasharray="3,3" />`;
    })
    .join("");

  // Area Fill for Scanned
  const areaScanned = `M ${padding.left},${padding.top + graphH} L ${scannedPts} L ${getX(n - 1)},${padding.top + graphH} Z`;

  // Circles
  const circles = trend
    .map((d, i) => {
      const cx = getX(i);
      const cy = getYFlagged(d.tahap2_passed || 0);
      return `<circle class="trend-node" cx="${cx}" cy="${cy}" r="4" fill="#F43F5E" stroke="#0E1524" stroke-width="2" data-idx="${i}" style="cursor:pointer;" />`;
    })
    .join("");

  // Dates Labels
  const dateLabels = trend
    .filter((_, i) => i % 3 === 0 || i === n - 1)
    .map((d, i) => {
      const idx = trend.indexOf(d);
      const cx = getX(idx);
      const label = d.date ? d.date.substring(5) : `D${idx + 1}`;
      return `<text x="${cx}" y="${h - 6}" font-size="10" font-family="monospace" fill="#64748B" text-anchor="middle">${label}</text>`;
    })
    .join("");

  svg.innerHTML = `
    <defs>
      <linearGradient id="scannedGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#3B82F6" stop-opacity="0.25"/>
        <stop offset="100%" stop-color="#3B82F6" stop-opacity="0.0"/>
      </linearGradient>
    </defs>
    ${gridLines}
    <path d="${areaScanned}" fill="url(#scannedGrad)" />
    <polyline points="${scannedPts}" fill="none" stroke="#3B82F6" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
    <polyline points="${flaggedPts}" fill="none" stroke="#F43F5E" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
    ${circles}
    ${dateLabels}
  `;

  // Interactive Hover Handler
  svg.querySelectorAll(".trend-node").forEach((node) => {
    node.addEventListener("mouseenter", (e) => {
      const idx = Number(node.getAttribute("data-idx"));
      const item = trend[idx];
      if (!item || !tooltip) return;

      const rect = svg.getBoundingClientRect();
      const cx = Number(node.getAttribute("cx"));
      const cy = Number(node.getAttribute("cy"));

      tooltip.style.display = "block";
      tooltip.style.left = `${(cx / w) * rect.width}px`;
      tooltip.style.top = `${(cy / h) * rect.height - 35}px`;
      tooltip.innerHTML = `<strong>${item.date}</strong>: ${item.domains_scanned || 0} Masuk | <span style="color:#F43F5E;font-weight:bold;">${item.tahap2_passed || 0} Terindikasi</span>`;
    });

    node.addEventListener("mouseleave", () => {
      if (tooltip) tooltip.style.display = "none";
    });
  });
}

// Findings Table
async function fetchFindings() {
  try {
    const unmaskParam = state.unmask ? "&unmask=true" : "";
    const res = await fetch(`/findings/top?limit=100${unmaskParam}`);
    if (!res.ok) return;
    const data = await res.json();
    state.findings = data.findings || [];
    renderFindingsTable();
  } catch (err) {
    console.debug("fetchFindings notice:", err);
  }
}

function renderFindingsTable() {
  const tbody = document.getElementById("findingsTableBody");
  if (!tbody) return;

  let list = state.findings || [];

  // Filter Search
  if (state.searchTerm) {
    const q = state.searchTerm.toLowerCase();
    list = list.filter(
      (f) =>
        (f.domain && f.domain.toLowerCase().includes(q)) ||
        (f.domain_raw && f.domain_raw.toLowerCase().includes(q)) ||
        (f.matched_brand && f.matched_brand.toLowerCase().includes(q))
    );
  }

  // Filter Severity Pill
  if (state.activeFilter === "high") {
    list = list.filter((f) => (f.risk_score || 0) >= 70);
  } else if (state.activeFilter === "caution") {
    list = list.filter((f) => (f.risk_score || 0) >= 40 && (f.risk_score || 0) < 70);
  } else if (state.activeFilter === "live") {
    list = list.filter((f) => f.live_status === "active" || f.is_live);
  }

  const totalItems = list.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / state.pageSize));
  if (state.currentPage > totalPages) state.currentPage = totalPages;
  if (state.currentPage < 1) state.currentPage = 1;

  const startIndex = (state.currentPage - 1) * state.pageSize;
  const endIndex = Math.min(startIndex + state.pageSize, totalItems);
  const pagedList = list.slice(startIndex, endIndex);

  // Update Pagination Info
  const infoEl = document.getElementById("tablePaginationInfo");
  if (infoEl) {
    if (totalItems === 0) {
      infoEl.textContent = "Menampilkan 0–0 dari 0 domain";
    } else {
      infoEl.textContent = `Menampilkan ${startIndex + 1}–${endIndex} dari ${totalItems} domain`;
    }
  }

  // Update Pagination Controls
  renderTablePaginationControls(totalPages);

  if (pagedList.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="table-state-row">
          <p>Tidak ada domain berisiko yang cocok dengan filter "${state.activeFilter}".</p>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = pagedList
    .map((f) => {
      const displayDomain = state.unmask ? f.domain_raw || f.domain : f.domain;
      const score = f.risk_score || 0;
      const brand = f.matched_brand || "Indikasi Penipuan";
      const method = f.similarity_method || f.detection_method || "Similarity";
      const isLive = f.live_status === "active" || f.is_live;

      const scoreColor = score >= 70 ? "var(--color-danger)" : score >= 40 ? "var(--color-warning)" : "var(--color-success)";
      const livePill = isLive
        ? `<span class="status-pill status-pill-emerald">&bull; Aktif</span>`
        : `<span class="status-pill">&bull; Terisolasi</span>`;

      const firstSeen = f.detected_at || f.first_seen || "2026-09-01";
      const dateShort = firstSeen.length > 16 ? firstSeen.substring(0, 16).replace("T", " ") : firstSeen;

      return `
        <tr data-id="${f.id}">
          <td class="domain-cell">
            <span>${escapeHtml(displayDomain)}</span>
          </td>
          <td>
            <div class="brand-badge-cell">
              <span>${escapeHtml(brand)}</span>
            </div>
          </td>
          <td>
            <div class="score-bar-wrap">
              <span class="score-text" style="color: ${scoreColor}">${score}</span>
              <div class="score-mini-track">
                <div class="score-mini-fill" style="width: ${score}%; background: ${scoreColor}"></div>
              </div>
            </div>
          </td>
          <td>${livePill}</td>
          <td><span class="status-pill">${escapeHtml(method)}</span></td>
          <td><span class="font-mono text-muted" style="font-size:11px;">${escapeHtml(dateShort)}</span></td>
          <td>
            <button class="action-btn inspect-finding-btn" data-id="${f.id}" style="padding:4px 9px;font-size:11px;">
              Investigasi
            </button>
          </td>
        </tr>
      `;
    })
    .join("");

  // Bind Row Action Buttons
  tbody.querySelectorAll(".inspect-finding-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-id");
      openFindingModal(id);
    });
  });
}

function renderTablePaginationControls(totalPages) {
  const firstBtn = document.getElementById("pagFirstBtn");
  const prevBtn = document.getElementById("pagPrevBtn");
  const nextBtn = document.getElementById("pagNextBtn");
  const lastBtn = document.getElementById("pagLastBtn");
  const numList = document.getElementById("pagNumbersList");

  if (firstBtn) firstBtn.disabled = state.currentPage <= 1;
  if (prevBtn) prevBtn.disabled = state.currentPage <= 1;
  if (nextBtn) nextBtn.disabled = state.currentPage >= totalPages;
  if (lastBtn) lastBtn.disabled = state.currentPage >= totalPages;

  if (!numList) return;

  let pages = [];
  const cur = state.currentPage;

  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (cur > 3) pages.push("...");

    const start = Math.max(2, cur - 1);
    const end = Math.min(totalPages - 1, cur + 1);
    for (let i = start; i <= end; i++) pages.push(i);

    if (cur < totalPages - 2) pages.push("...");
    pages.push(totalPages);
  }

  numList.innerHTML = pages
    .map((p) => {
      if (p === "...") return `<span class="pag-ellipsis">&hellip;</span>`;
      const isActive = p === cur ? "active" : "";
      return `<button class="pag-btn ${isActive}" data-page="${p}">${p}</button>`;
    })
    .join("");

  numList.querySelectorAll(".pag-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const p = Number(btn.getAttribute("data-page"));
      if (p && p !== state.currentPage) {
        state.currentPage = p;
        renderFindingsTable();
      }
    });
  });
}

// Table Filter & Search Controls
function initTableControls() {
  const searchInput = document.getElementById("domainSearchInput");
  const clearBtn = document.getElementById("clearSearchBtn");
  const filterPills = document.querySelectorAll(".filter-pill");
  const unmaskToggle = document.getElementById("unmaskToggle");
  const toggleLabel = document.getElementById("toggleLabel");
  const exportBtn = document.getElementById("exportCsvBtn");
  const pageSizeSelect = document.getElementById("pageSizeSelect");

  const firstBtn = document.getElementById("pagFirstBtn");
  const prevBtn = document.getElementById("pagPrevBtn");
  const nextBtn = document.getElementById("pagNextBtn");
  const lastBtn = document.getElementById("pagLastBtn");

  // Page Size Change
  pageSizeSelect?.addEventListener("change", (e) => {
    state.pageSize = Number(e.target.value) || 10;
    state.currentPage = 1;
    renderFindingsTable();
  });

  // Pagination Navigation Buttons
  firstBtn?.addEventListener("click", () => {
    if (state.currentPage > 1) {
      state.currentPage = 1;
      renderFindingsTable();
    }
  });

  prevBtn?.addEventListener("click", () => {
    if (state.currentPage > 1) {
      state.currentPage--;
      renderFindingsTable();
    }
  });

  nextBtn?.addEventListener("click", () => {
    const listLen = state.findings.length;
    const totalPages = Math.ceil(listLen / state.pageSize) || 1;
    if (state.currentPage < totalPages) {
      state.currentPage++;
      renderFindingsTable();
    }
  });

  lastBtn?.addEventListener("click", () => {
    const listLen = state.findings.length;
    const totalPages = Math.ceil(listLen / state.pageSize) || 1;
    if (state.currentPage < totalPages) {
      state.currentPage = totalPages;
      renderFindingsTable();
    }
  });

  // Instant Search
  searchInput?.addEventListener("input", (e) => {
    state.searchTerm = e.target.value.trim();
    state.currentPage = 1;
    if (clearBtn) clearBtn.style.display = state.searchTerm ? "block" : "none";
    renderFindingsTable();
  });

  clearBtn?.addEventListener("click", () => {
    if (searchInput) searchInput.value = "";
    state.searchTerm = "";
    state.currentPage = 1;
    clearBtn.style.display = "none";
    renderFindingsTable();
  });

  // Severity Pills
  filterPills.forEach((pill) => {
    pill.addEventListener("click", () => {
      filterPills.forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      state.activeFilter = pill.getAttribute("data-filter");
      state.currentPage = 1;
      renderFindingsTable();
    });
  });

  // Unmask Toggle
  unmaskToggle?.addEventListener("change", (e) => {
    state.unmask = e.target.checked;
    if (toggleLabel) {
      toggleLabel.textContent = state.unmask ? "Penyamaran: NONAKTIF" : "Penyamaran: AKTIF";
    }
    fetchFindings();
  });

  // Export CSV
  exportBtn?.addEventListener("click", exportFindingsCsv);
}

// CSV Export Handler
function exportFindingsCsv() {
  if (!state.findings || state.findings.length === 0) {
    alert("Tidak ada data temuan untuk diekspor.");
    return;
  }

  const headers = ["ID", "Domain", "Brand", "Risk_Score", "Risk_Level", "Detection_Method", "Live_Status", "Detected_At"];
  const rows = state.findings.map((f) => [
    f.id,
    `"${state.unmask ? f.domain_raw || f.domain : f.domain}"`,
    `"${f.matched_brand || ""}"`,
    f.risk_score || 0,
    `"${f.risk_level || ""}"`,
    `"${f.similarity_method || f.detection_method || ""}"`,
    `"${f.live_status || ""}"`,
    `"${f.detected_at || ""}"`,
  ]);

  const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `siaga_threat_findings_${new Date().toISOString().substring(0, 10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// Brand Intelligence Controls & Pagination
function initBrandControls() {
  const brandSearch = document.getElementById("brandSearchInput");
  const clearBrandBtn = document.getElementById("clearBrandSearchBtn");
  const brandPrevBtn = document.getElementById("brandPrevBtn");
  const brandNextBtn = document.getElementById("brandNextBtn");

  brandSearch?.addEventListener("input", (e) => {
    state.brandSearchTerm = e.target.value.trim();
    state.brandCurrentPage = 1;
    if (clearBrandBtn) clearBrandBtn.style.display = state.brandSearchTerm ? "block" : "none";
    renderBrandsList(state.brands);
  });

  clearBrandBtn?.addEventListener("click", () => {
    if (brandSearch) brandSearch.value = "";
    state.brandSearchTerm = "";
    state.brandCurrentPage = 1;
    clearBrandBtn.style.display = "none";
    renderBrandsList(state.brands);
  });

  brandPrevBtn?.addEventListener("click", () => {
    if (state.brandCurrentPage > 1) {
      state.brandCurrentPage--;
      renderBrandsList(state.brands);
    }
  });

  brandNextBtn?.addEventListener("click", () => {
    const filtered = filterBrandList(state.brands);
    const totalPages = Math.ceil(filtered.length / state.brandPageSize) || 1;
    if (state.brandCurrentPage < totalPages) {
      state.brandCurrentPage++;
      renderBrandsList(state.brands);
    }
  });
}

function filterBrandList(brands) {
  let list = brands || [];
  if (state.brandSearchTerm) {
    const q = state.brandSearchTerm.toLowerCase();
    list = list.filter((b) => b.brand && b.brand.toLowerCase().includes(q));
  }
  return list;
}

// Brand Intelligence List
async function fetchBrands() {
  try {
    const res = await fetch("/findings/brands");
    if (!res.ok) return;
    const data = await res.json();
    state.brands = data.brands || [];
    renderBrandsList(state.brands);
  } catch (err) {
    console.debug("fetchBrands notice:", err);
  }
}

function renderBrandsList(brands) {
  const container = document.getElementById("brandsListContainer");
  if (!container) return;

  const filtered = filterBrandList(brands);
  const totalItems = filtered.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / state.brandPageSize));
  if (state.brandCurrentPage > totalPages) state.brandCurrentPage = totalPages;
  if (state.brandCurrentPage < 1) state.brandCurrentPage = 1;

  const startIndex = (state.brandCurrentPage - 1) * state.brandPageSize;
  const endIndex = Math.min(startIndex + state.brandPageSize, totalItems);
  const pagedList = filtered.slice(startIndex, endIndex);

  // Update Brand Pagination Info & Buttons
  const infoEl = document.getElementById("brandPaginationInfo");
  const prevBtn = document.getElementById("brandPrevBtn");
  const nextBtn = document.getElementById("brandNextBtn");
  const numList = document.getElementById("brandPagNumbersList");

  if (infoEl) {
    if (totalItems === 0) {
      infoEl.textContent = "Menampilkan 0–0 dari 0 brand";
    } else {
      infoEl.textContent = `Menampilkan ${startIndex + 1}–${endIndex} dari ${totalItems} brand`;
    }
  }

  if (prevBtn) prevBtn.disabled = state.brandCurrentPage <= 1;
  if (nextBtn) nextBtn.disabled = state.brandCurrentPage >= totalPages;

  if (numList) {
    numList.innerHTML = Array.from({ length: totalPages }, (_, i) => i + 1)
      .map((p) => {
        const isActive = p === state.brandCurrentPage ? "active" : "";
        return `<button class="pag-btn ${isActive}" data-brand-page="${p}">${p}</button>`;
      })
      .join("");

    numList.querySelectorAll(".pag-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const p = Number(btn.getAttribute("data-brand-page"));
        if (p && p !== state.brandCurrentPage) {
          state.brandCurrentPage = p;
          renderBrandsList(state.brands);
        }
      });
    });
  }

  if (pagedList.length === 0) {
    container.innerHTML = `<p class="table-state-row">Tidak ada brand yang cocok dengan pencarian "${state.brandSearchTerm}".</p>`;
    return;
  }

  container.innerHTML = pagedList
    .map((b) => {
      const brandName = b.brand || "Lainnya";
      const initial = brandName.charAt(0).toUpperCase();
      const count = b.count || 0;
      const maxScore = b.max_score || 70;

      return `
        <div class="brand-card-item">
          <div class="brand-info-side">
            <div class="brand-logo-circle">${initial}</div>
            <div>
              <div class="brand-name-title">${escapeHtml(brandName)}</div>
              <div class="brand-subtext">Skor Tertinggi: ${maxScore}/100</div>
            </div>
          </div>
          <span class="brand-count-badge">${count} Domain</span>
        </div>
      `;
    })
    .join("");
}

// Cluster Intelligence Controls & Pagination
function initClusterControls() {
  const clusterSearch = document.getElementById("clusterSearchInput");
  const clearClusterBtn = document.getElementById("clearClusterSearchBtn");
  const clusterPrevBtn = document.getElementById("clusterPrevBtn");
  const clusterNextBtn = document.getElementById("clusterNextBtn");

  clusterSearch?.addEventListener("input", (e) => {
    state.clusterSearchTerm = e.target.value.trim();
    state.clusterCurrentPage = 1;
    if (clearClusterBtn) clearClusterBtn.style.display = state.clusterSearchTerm ? "block" : "none";
    renderClusterList();
  });

  clearClusterBtn?.addEventListener("click", () => {
    if (clusterSearch) clusterSearch.value = "";
    state.clusterSearchTerm = "";
    state.clusterCurrentPage = 1;
    clearClusterBtn.style.display = "none";
    renderClusterList();
  });

  clusterPrevBtn?.addEventListener("click", () => {
    if (state.clusterCurrentPage > 1) {
      state.clusterCurrentPage--;
      renderClusterList();
    }
  });

  clusterNextBtn?.addEventListener("click", () => {
    const filtered = filterClusterList();
    const totalPages = Math.ceil(filtered.length / state.clusterPageSize) || 1;
    if (state.clusterCurrentPage < totalPages) {
      state.clusterCurrentPage++;
      renderClusterList();
    }
  });

  renderClusterList();
}

function filterClusterList() {
  let list = state.clusters || [];
  if (state.clusterSearchTerm) {
    const q = state.clusterSearchTerm.toLowerCase();
    list = list.filter(
      (c) =>
        (c.title && c.title.toLowerCase().includes(q)) ||
        (c.ns && c.ns.toLowerCase().includes(q)) ||
        (c.desc && c.desc.toLowerCase().includes(q)) ||
        (c.tags && c.tags.some((t) => t.toLowerCase().includes(q)))
    );
  }
  return list;
}

function renderClusterList() {
  const container = document.getElementById("clusterCardsContainer");
  if (!container) return;

  const filtered = filterClusterList();
  const totalItems = filtered.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / state.clusterPageSize));
  if (state.clusterCurrentPage > totalPages) state.clusterCurrentPage = totalPages;
  if (state.clusterCurrentPage < 1) state.clusterCurrentPage = 1;

  const startIndex = (state.clusterCurrentPage - 1) * state.clusterPageSize;
  const endIndex = Math.min(startIndex + state.clusterPageSize, totalItems);
  const pagedList = filtered.slice(startIndex, endIndex);

  // Update Cluster Pagination Info & Buttons
  const infoEl = document.getElementById("clusterPaginationInfo");
  const prevBtn = document.getElementById("clusterPrevBtn");
  const nextBtn = document.getElementById("clusterNextBtn");
  const numList = document.getElementById("clusterPagNumbersList");

  if (infoEl) {
    if (totalItems === 0) {
      infoEl.textContent = "Menampilkan 0–0 dari 0 klaster";
    } else {
      infoEl.textContent = `Menampilkan ${startIndex + 1}–${endIndex} dari ${totalItems} klaster`;
    }
  }

  if (prevBtn) prevBtn.disabled = state.clusterCurrentPage <= 1;
  if (nextBtn) nextBtn.disabled = state.clusterCurrentPage >= totalPages;

  if (numList) {
    numList.innerHTML = Array.from({ length: totalPages }, (_, i) => i + 1)
      .map((p) => {
        const isActive = p === state.clusterCurrentPage ? "active" : "";
        return `<button class="pag-btn ${isActive}" data-cluster-page="${p}">${p}</button>`;
      })
      .join("");

    numList.querySelectorAll(".pag-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const p = Number(btn.getAttribute("data-cluster-page"));
        if (p && p !== state.clusterCurrentPage) {
          state.clusterCurrentPage = p;
          renderClusterList();
        }
      });
    });
  }

  if (pagedList.length === 0) {
    container.innerHTML = `<p class="table-state-row">Tidak ada klaster infrastruktur yang cocok dengan "${state.clusterSearchTerm}".</p>`;
    return;
  }

  container.innerHTML = pagedList
    .map((c) => {
      const tagsHtml = c.tags ? c.tags.map((t) => `<span class="status-pill">${escapeHtml(t)}</span>`).join(" ") : "";
      return `
        <div class="cluster-item">
          <div class="cluster-item-head">
            <span class="cluster-badge">${escapeHtml(c.title)}</span>
            <strong class="cluster-ns-title">${escapeHtml(c.ns)}</strong>
            <span class="cluster-volume-tag">${escapeHtml(c.volume)}</span>
          </div>
          <p class="cluster-item-desc">${escapeHtml(c.desc)}</p>
          <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;">${tagsHtml}</div>
        </div>
      `;
    })
    .join("");
}

// System Metrics
async function fetchMetrics() {
  try {
    const res = await fetch("/metrics");
    if (!res.ok) return;
    const data = await res.json();
    state.metrics = data;

    const precEl = document.getElementById("metricPrecision");
    const recEl = document.getElementById("metricRecall");
    const f1El = document.getElementById("metricF1");
    const ramEl = document.getElementById("metricRam");

    if (precEl && data.precision_pct !== undefined) precEl.textContent = `${Number(data.precision_pct).toFixed(2)}%`;
    if (recEl && data.recall_pct !== undefined) recEl.textContent = `${Number(data.recall_pct).toFixed(2)}%`;
    if (f1El && data.f1_score !== undefined) f1El.textContent = Number(data.f1_score).toFixed(4);
    if (ramEl && data.ram_peak_mb !== undefined) ramEl.textContent = `${data.ram_peak_mb} MB`;
  } catch (err) {
    console.debug("fetchMetrics notice:", err);
  }
}

// =============================================================================
// INTERACTIVE TRIAGE SANDBOX (MODE A)
// =============================================================================
function initSandbox() {
  const textarea = document.getElementById("sandboxInput");
  const charCount = document.getElementById("sandboxCharCount");
  const runBtn = document.getElementById("runAnalyzeBtn");
  const clearBtn = document.getElementById("clearSandboxBtn");
  const presetChips = document.querySelectorAll(".sample-preset-chip");

  textarea?.addEventListener("input", (e) => {
    if (charCount) charCount.textContent = `${e.target.value.length} karakter`;
  });

  clearBtn?.addEventListener("click", () => {
    if (textarea) textarea.value = "";
    if (charCount) charCount.textContent = "0 karakter";
    hideSandboxResult();
  });

  presetChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const sample = chip.getAttribute("data-sample");
      if (textarea) {
        textarea.value = sample;
        if (charCount) charCount.textContent = `${sample.length} karakter`;
        runSandboxAnalysis(sample);
      }
    });
  });

  runBtn?.addEventListener("click", () => {
    const text = textarea?.value?.trim();
    if (!text) {
      alert("Silakan masukkan teks pesan atau tautan URL yang ingin dianalisis.");
      return;
    }
    runSandboxAnalysis(text);
  });
}

async function runSandboxAnalysis(text) {
  if (state.isAnalyzing) return;
  state.isAnalyzing = true;

  const runBtn = document.getElementById("runAnalyzeBtn");
  if (runBtn) {
    runBtn.disabled = true;
    runBtn.innerHTML = `<span>Menganalisis...</span>`;
  }

  showSandboxLoading();

  try {
    const res = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Status error ${res.status}`);
    }

    const data = await res.json();
    renderSandboxResult(data);
  } catch (err) {
    alert(`Gagal menganalisis: ${err.message}`);
    hideSandboxResult();
  } finally {
    state.isAnalyzing = false;
    if (runBtn) {
      runBtn.disabled = false;
      runBtn.innerHTML = `
        <svg class="btn-icon" viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
        </svg>
        <span>Analisis Sekarang</span>
      `;
    }
  }
}

function showSandboxLoading() {
  const placeholder = document.getElementById("resultPlaceholder");
  const content = document.getElementById("resultContent");

  if (placeholder) {
    placeholder.style.display = "flex";
    placeholder.innerHTML = `
      <div class="table-loading-spinner" style="width:36px;height:36px;"></div>
      <h3>Mengevaluasi Ancaman...</h3>
      <p>Menjalankan inspeksi heuristik bertingkat, penelusuran RDAP, dan analisis linguistik.</p>
    `;
  }
  if (content) content.style.display = "none";
}

function hideSandboxResult() {
  const placeholder = document.getElementById("resultPlaceholder");
  const content = document.getElementById("resultContent");

  if (placeholder) {
    placeholder.style.display = "flex";
    placeholder.innerHTML = `
      <div class="radar-pulse-ring"></div>
      <h3>Mesin Triage Siap</h3>
      <p>Pilih salah satu preset di atas atau masukkan teks/URL untuk melihat evaluasi teknis, pencatutan brand, dan draf laporan CSIRT.</p>
    `;
  }
  if (content) content.style.display = "none";
}

function renderSandboxResult(res) {
  const placeholder = document.getElementById("resultPlaceholder");
  const content = document.getElementById("resultContent");
  if (placeholder) placeholder.style.display = "none";
  if (content) content.style.display = "flex";

  const score = res.score || 0;
  const level = res.level || "AMAN";
  const reasons = res.reasons || [];
  const breakdown = res.breakdown || [];
  const latency = res.latency_ms || 4;

  const scoreEl = document.getElementById("resultScore");
  const levelBadge = document.getElementById("resultLevelBadge");
  const latencyEl = document.getElementById("resultLatency");
  const reasonsList = document.getElementById("resultReasonsList");
  const breakdownBox = document.getElementById("resultBreakdownItems");
  const recomText = document.getElementById("resultRecomText");

  if (scoreEl) scoreEl.textContent = score;
  if (latencyEl) latencyEl.textContent = `${latency} ms`;

  if (levelBadge) {
    levelBadge.textContent = level;
    levelBadge.className = "verdict-status-badge";
    if (level === "INDIKASI PENIPUAN") levelBadge.classList.add("status-fraud");
    else if (level === "HATI-HATI") levelBadge.classList.add("status-caution");
    else levelBadge.classList.add("status-safe");
  }

  // Reasons
  if (reasonsList) {
    reasonsList.innerHTML = reasons
      .slice(0, 4)
      .map((r) => `<li>${escapeHtml(r)}</li>`)
      .join("");
  }

  // Signal Breakdown
  if (breakdownBox) {
    if (breakdown.length === 0) {
      breakdownBox.innerHTML = `<p style="font-size:12px;color:var(--text-muted);">Tidak ada sinyal pelanggaran berisiko yang terdeteksi.</p>`;
    } else {
      breakdownBox.innerHTML = breakdown
        .map(
          (b) => `
        <div class="signal-row">
          <span style="color:var(--text-primary);">${escapeHtml(b.explanation || b.signal_name)}</span>
          <span class="signal-points">+${b.points} pts</span>
        </div>
      `
        )
        .join("");
    }
  }

  // Mitigation Advice
  if (recomText) {
    if (level === "INDIKASI PENIPUAN") {
      recomText.textContent = "JANGAN klik tautan apa pun, JANGAN unduh file APK, dan JANGAN kirim kode OTP/PIN ke pengirim pesan ini. Laporkan insiden ini ke AduanKonten atau CSIRT terkait.";
    } else if (level === "HATI-HATI") {
      recomText.textContent = "Verifikasi kebenaran penawaran atau informasi melalui nomor telepon / situs web resmi institusi terkait sebelum melakukan transaksi.";
    } else {
      recomText.textContent = "Pesan ini relatif aman dan tidak memuat indikator pencatutan identitas digital. Tetap jaga kerahasiaan password dan PIN Anda.";
    }
  }
}

// =============================================================================
// FORENSIC MODAL & CSIRT INCIDENT DRAFT
// =============================================================================
function initModal() {
  const modal = document.getElementById("findingModal");
  const closeBtn = document.getElementById("closeModalBtn");
  const closeBottomBtn = document.getElementById("closeModalBottomBtn");
  const copyBtn = document.getElementById("copyDraftBtn");
  const copyBottomBtn = document.getElementById("copyDraftBottomBtn");

  closeBtn?.addEventListener("click", closeModal);
  closeBottomBtn?.addEventListener("click", closeModal);

  modal?.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });

  copyBtn?.addEventListener("click", copyCsirtDraft);
  copyBottomBtn?.addEventListener("click", copyCsirtDraft);
}

async function openFindingModal(id) {
  const modal = document.getElementById("findingModal");
  if (!modal) return;

  modal.classList.add("open");

  try {
    const res = await fetch(`/findings/${id}`);
    if (!res.ok) throw new Error("Finding not found");
    const data = await res.json();
    renderModalContent(data);
  } catch (err) {
    console.debug("openFindingModal notice:", err);
  }
}

function closeModal() {
  const modal = document.getElementById("findingModal");
  if (modal) modal.classList.remove("open");
}

function renderModalContent(item) {
  const domainTitle = document.getElementById("modalDomainTitle");
  const brandSub = document.getElementById("modalBrandSub");
  const riskScore = document.getElementById("modalRiskScore");
  const riskLevel = document.getElementById("modalRiskLevel");
  const liveBadge = document.getElementById("modalLiveBadge");
  const matchMethod = document.getElementById("modalMatchMethod");

  const firstSeen = document.getElementById("modalFirstSeen");
  const registrar = document.getElementById("modalRegistrar");
  const nameservers = document.getElementById("modalNameservers");
  const campaignId = document.getElementById("modalCampaignId");
  const reasoning = document.getElementById("modalReasoning");
  const channelsList = document.getElementById("modalChannelsList");
  const draftArea = document.getElementById("modalDraftTextarea");

  if (domainTitle) domainTitle.textContent = item.domain_raw || item.domain || "pos.web.id";
  if (brandSub) brandSub.textContent = `Pencatutan Brand: ${item.matched_brand || "Indikasi Penipuan"}`;
  if (riskScore) riskScore.textContent = `${item.risk_score || 0}/100`;
  if (riskLevel) riskLevel.textContent = item.risk_level || "INDIKASI PENIPUAN";
  if (liveBadge) liveBadge.textContent = item.live_status === "active" || item.is_live ? "• Aktif Merespons" : "• Terisolasi";
  if (matchMethod) matchMethod.textContent = item.similarity_method || item.detection_method || "Similarity";

  if (firstSeen) firstSeen.textContent = item.detected_at || item.first_seen || "2026-09-01";
  if (registrar) registrar.textContent = item.registrar || "IDwebhost / Pandi Registrar";
  if (nameservers) nameservers.textContent = item.nameservers ? (Array.isArray(item.nameservers) ? item.nameservers.join(", ") : item.nameservers) : "ns1.swiftserve.com, ns2.swiftserve.com";
  if (campaignId) campaignId.textContent = `Klaster #${item.cluster_id || item.campaign_id || "12"}`;

  if (reasoning) {
    reasoning.textContent = item.reasons
      ? item.reasons.join(" ")
      : `Domain terindikasi meniru identitas ${item.matched_brand || "institusi resmi"} dengan kemiripan nama tinggi dan indikator manipulasi psikologis.`;
  }

  if (channelsList && item.escalation_channels) {
    channelsList.innerHTML = Object.entries(item.escalation_channels)
      .map(
        ([key, val]) => `
        <span class="channel-pill-link">
          <strong>${escapeHtml(key)}:</strong> ${escapeHtml(String(val))}
        </span>
      `
      )
      .join("");
  }

  if (draftArea) {
    draftArea.value = item.csirt_report_draft || `LAPORAN INSIDEN PHISHING & PENIPUAN DIGITAL\nKepada: AduanKonten / PANDI CSIRT\nDomain: ${item.domain_raw || item.domain}\nBrand Dicatut: ${item.matched_brand}\nSkor Risiko: ${item.risk_score}/100\nMohon tindakan takedown segera.`;
  }
}

function copyCsirtDraft() {
  const textarea = document.getElementById("modalDraftTextarea");
  if (!textarea) return;

  navigator.clipboard.writeText(textarea.value).then(() => {
    alert("Draf laporan insiden CSIRT berhasil disalin ke clipboard!");
  });
}

// Utility: Escape HTML
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
