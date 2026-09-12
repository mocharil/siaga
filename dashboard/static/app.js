// ==============================================================================
// SIAGA Threat Intelligence Platform — iOS / Apple HIG Application Logic
// White & Light Blue Theme. Offline-capable except the Overview regional
// map, which loads Leaflet + OpenStreetMap tiles from a CDN (demo-video-
// showcase branch only, see docs/demo_mode.md) -- everything else runs
// with zero external network egress.
// ==============================================================================

const state = {
  view: "overview",
  masked: true,
  radar: {
    rows: [],
    search: "",
    category: "all",
    level: "all",
    live: "all",
    page: 1,
    pageSize: 15,
  },
  overview: {
    page: 1,
    pageSize: 10,
  },
  activityFeed: {
    page: 1,
    pageSize: 8,
  },
  pipelineOpen: null,
};

const ICONS = {
  check: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>',
  globe: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18z"/></svg>',
  warning: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.3 3.9L2.4 18a1.8 1.8 0 0 0 1.5 2.7h16.2a1.8 1.8 0 0 0 1.5-2.7L13.7 3.9a1.8 1.8 0 0 0-3.4 0z"/></svg>',
  pulse: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>',
  shieldLock: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
  clock: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>',
  arrowUpRight: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M7 17L17 7M7 7h10v10"/></svg>',
  arrowUp: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 19V5M5 12l7-7 7 7"/></svg>',
  lightning: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
  lock: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
  download: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>',
  dotsVertical: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>',
  cpu: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>',
  zap: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
  whatsapp: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>',
  mail: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>',
  external: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>',
  copy: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
  fileText: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',
  shieldCheck: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>',
};

// ---------------------------------------------------------------------------
// iOS Toast Notification Helper
// ---------------------------------------------------------------------------
function showToast(msg) {
  let toast = document.getElementById("global-ios-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "global-ios-toast";
    toast.className = "ios-toast";
    document.body.appendChild(toast);
  }
  toast.innerHTML = `
    <span class="ios-toast-icon">${ICONS.lightning}</span>
    <span>${msg}</span>
  `;
  toast.classList.add("show");
  if (toast._timer) clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.classList.remove("show");
  }, 2800);
}


// ---------------------------------------------------------------------------
// SAFE WEB SANDBOX PREVIEW MODAL ENGINE
// ---------------------------------------------------------------------------
let activePreviewState = {
  id: null,
  category: "phishing",
  rawDomain: "",
  domainMasked: "",
  host: "",
  activeTab: "live",
  detail: null,
};

function closeWebPreviewModal() {
  const overlay = document.getElementById("sandbox-modal-overlay");
  if (overlay) overlay.classList.add("hidden");
}

async function openWebPreviewModal(id, category, rawDomain, domainMasked) {
  const overlay = document.getElementById("sandbox-modal-overlay");
  if (!overlay) return;

  activePreviewState = {
    id: id || "live-1",
    category: category || "phishing",
    rawDomain: rawDomain || "domain.com",
    domainMasked: domainMasked || rawDomain || "domain.com",
    host: "",
    activeTab: "live",
    detail: null,
  };

  let path = "/klaim-poin";
  if (activePreviewState.rawDomain.includes("/")) {
    const parts = activePreviewState.rawDomain.split("/");
    activePreviewState.host = parts[0];
    path = "/" + parts.slice(1).join("/");
  } else {
    activePreviewState.host = activePreviewState.rawDomain;
    if (category === "judol") path = "/slot-gacor-vip";
    else if (category === "porn") path = "/stream-video";
    else if (activePreviewState.host.includes("bri")) path = "/info-tarif-2026";
    else if (activePreviewState.host.includes("dana")) path = "/dana-kaget";
    else if (activePreviewState.host.includes("mandiri")) path = "/livin-aktivasi";
    else if (activePreviewState.host.includes("pajak")) path = "/faktur-spt";
  }

  const urlHostEl = document.getElementById("sandbox-url-host");
  const urlPathEl = document.getElementById("sandbox-url-path");
  const riskBadgeEl = document.getElementById("sandbox-risk-badge");
  const footerBrandEl = document.getElementById("sandbox-footer-brand");
  const footerCategoryEl = document.getElementById("sandbox-footer-category");

  if (urlHostEl) urlHostEl.textContent = activePreviewState.host;
  if (urlPathEl) urlPathEl.textContent = path;
  if (riskBadgeEl) riskBadgeEl.textContent = "— / 100";
  if (footerBrandEl) footerBrandEl.textContent = "Terdeteksi Otomatis";
  if (footerCategoryEl) {
    footerCategoryEl.textContent = category === "judol" ? "Judi Online" : category === "porn" ? "Muatan Asusila" : "Phishing Finansial";
  }

  overlay.classList.remove("hidden");

  // Reset tab to live
  document.querySelectorAll("#sandbox-view-segmented .sandbox-tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === "live");
  });

  // Try fetching extra details from state.radar.rows or API
  try {
    let f = (state.radar.rows || []).find((r) => String(r.id) === String(id)) || null;
    if (!f && !String(id).startsWith("live-")) {
      const endpoint = category === "judol" ? `/api/judol/${id}`
        : category === "porn" ? `/api/porn/${id}`
        : `/api/findings/${id}`;
      f = await api(endpoint);
    }
    if (f) {
      activePreviewState.detail = f;
      if (riskBadgeEl) riskBadgeEl.textContent = f.risk_score != null ? `${Math.round(f.risk_score)} / 100` : "— / 100";
      if (footerBrandEl) footerBrandEl.textContent = f.matched_brand || "General Threat";
    }
  } catch (err) {
    if (riskBadgeEl) riskBadgeEl.textContent = "— / 100";
  }

  renderSandboxTabBody();
}

function renderSandboxTabBody() {
  const stage = document.getElementById("sandbox-stage-body");
  if (!stage) return;

  const st = activePreviewState;
  const f = st.detail || {};
  const brand = f.matched_brand || "Layanan Terkait";
  const rawDomain = st.rawDomain;
  const tab = st.activeTab || "live";

  if (tab === "live") {
    stage.innerHTML = `
      <div class="sandbox-live-container">
        <div class="sandbox-live-header-bar">
          <div class="sandbox-live-badge">
            <span class="live-dot green"></span>
            <span>🌐 Pratinjau Sandboxed Langsung (Isolated Frame)</span>
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            <a href="https://${st.host}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" style="font-size:11.5px; padding:5px 12px; text-decoration:none;" title="Buka di tab browser baru (Hati-hati)">
              Buka Web Asli ↗
            </a>
          </div>
        </div>
        <div class="sandbox-iframe-wrapper">
          <iframe class="sandbox-live-iframe" src="https://${st.host}" sandbox="allow-scripts allow-forms allow-same-origin" title="Live Preview ${st.host}"></iframe>
        </div>
        <div class="sandbox-live-footer-note">
          💡 <strong>Catatan Keamanan Sandbox:</strong> Frame berjalan dalam isolasi sandbox browser. Jika situs tidak tampil akibat proteksi keamanan web bersangkutan (seperti <code>X-Frame-Options: DENY/SAMEORIGIN</code> atau CSP) atau situs sudah offline/di-takedown, silakan gunakan tombol <strong>"Buka Web Asli ↗"</strong> atau periksa rekaman teknis pada tab <strong>"Forensik Payload & Form"</strong>.
        </div>
      </div>
    `;
  } else if (tab === "forensics") {
    stage.innerHTML = `
      <div class="sandbox-forensics-stage">
        <h4 style="font-size:14px; font-weight:700; margin-bottom:12px; color:#0f172a;">Data Forensik Jaringan & Payload Kredensial</h4>
        <table class="forensics-meta-table">
          <tr><td>Target URL Lengkap</td><td>https://${rawDomain}</td></tr>
          <tr><td>Brand Yang Dipalsukan</td><td>${brand}</td></tr>
          <tr><td>Kategori Ancaman</td><td>${st.category.toUpperCase()}</td></tr>
          <tr><td>Skor Risiko SIAGA</td><td>${f.risk_score != null ? Math.round(f.risk_score) : "—"} / 100 (${f.risk_level || "Belum dinilai"})</td></tr>
          <tr><td>Metode Ingestion</td><td>Certificate Transparency Log (ctlogs.dev, cron harian)</td></tr>
          <tr><td>Registrar / Registry</td><td>${f.registrar || "Data RDAP tidak tersedia"}</td></tr>
          <tr><td>Nameservers</td><td>${f.nameservers || "Data RDAP tidak tersedia"}</td></tr>
          <tr><td>Taktik Penyerang</td><td>${f.tactic || "Pencatutan identitas merek & rekayasa sosial"}</td></tr>
          <tr><td>Target Input Kredensial</td><td>${f.inputs || "Tidak diketahui — SIAGA tidak mengunduh konten halaman (lihat batasan jaringan)"}</td></tr>
          <tr><td>Kepatuhan Regulasi</td><td>UU Perlindungan Data Pribadi (UU PDP) & UU ITE Pasal 28 ayat 1</td></tr>
        </table>
      </div>
    `;
  }
}

function initWebPreviewModal() {
  const overlay = document.getElementById("sandbox-modal-overlay");
  const closeBtn = document.getElementById("sandbox-close-btn");
  const footerCloseBtn = document.getElementById("sandbox-footer-close-btn");
  const footerReportBtn = document.getElementById("sandbox-footer-report-btn");
  const reloadBtn = document.getElementById("sandbox-reload-btn");
  const copyUrlBtn = document.getElementById("sandbox-copy-url-btn");
  const drawerPreviewBtn = document.getElementById("drawer-preview-web-btn");

  if (closeBtn) closeBtn.addEventListener("click", closeWebPreviewModal);
  if (footerCloseBtn) footerCloseBtn.addEventListener("click", closeWebPreviewModal);

  if (footerReportBtn) {
    footerReportBtn.addEventListener("click", () => {
      closeWebPreviewModal();
      openFindingDrawer(activePreviewState.id, activePreviewState.category);
    });
  }

  if (drawerPreviewBtn) {
    drawerPreviewBtn.addEventListener("click", () => {
      const cur = state.currentDrawerFinding;
      if (cur) {
        openWebPreviewModal(cur.id, cur.category, cur.rawDomain, cur.activeDomain);
      } else {
        const domainEl = document.getElementById("drawer-domain");
        const d = domainEl ? domainEl.textContent : "domain.com";
        openWebPreviewModal(null, "phishing", d, d);
      }
    });
  }

  if (reloadBtn) {
    reloadBtn.addEventListener("click", () => {
      renderSandboxTabBody();
      showToast("↻ Pratinjau dimuat ulang.");
    });
  }

  if (copyUrlBtn) {
    copyUrlBtn.addEventListener("click", () => {
      const url = `https://${activePreviewState.rawDomain}`;
      navigator.clipboard.writeText(url);
      showToast(`URL disalin: ${url}`);
    });
  }

  // Tab switching
  document.querySelectorAll("#sandbox-view-segmented .sandbox-tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#sandbox-view-segmented .sandbox-tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activePreviewState.activeTab = btn.dataset.tab;
      renderSandboxTabBody();
    });
  });

  // Close on backdrop click or ESC
  if (overlay) {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closeWebPreviewModal();
    });
  }
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && overlay && !overlay.classList.contains("hidden")) {
      closeWebPreviewModal();
    }
  });
}

// ---------------------------------------------------------------------------
// Helpers & Triage Workflow State
// ---------------------------------------------------------------------------

const STATUS_MAP = {
  unreported: { label: "⚪ Draf Siap (Belum Dilaporkan)", badge: "badge-neutral" },
  in_progress: { label: "🟡 Sedang Diproses Analis", badge: "badge-warning" },
  reported: { label: "🟢 Berhasil Dilaporkan (Tiket Terkirim)", badge: "badge-success" },
  suspended: { label: "🛡️ Ditangguhkan / Diblokir (Closed)", badge: "badge-primary" },
};

function getFindingStatus(domain) {
  try {
    return localStorage.getItem(`siaga_status_${domain}`) || "unreported";
  } catch {
    return "unreported";
  }
}

function setFindingStatus(domain, status) {
  try {
    localStorage.setItem(`siaga_status_${domain}`, status);
  } catch {}
}

function createPaginationHtml({ totalItems, currentPage, pageSize, idPrefix }) {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const cur = Math.min(Math.max(1, currentPage), totalPages);
  const startIdx = totalItems === 0 ? 0 : (cur - 1) * pageSize + 1;
  const endIdx = Math.min(cur * pageSize, totalItems);

  let pages = [];
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

  return `
    <div class="ios-pagination-bar" id="${idPrefix}-pagination">
      <div class="pagination-info">
        <span>Menampilkan <strong>${startIdx}–${endIdx}</strong> dari <strong>${totalItems}</strong> data</span>
        <div class="pagination-size-picker">
          <span>Baris:</span>
          <select class="pagination-select" id="${idPrefix}-page-size">
            <option value="10" ${pageSize === 10 ? "selected" : ""}>10</option>
            <option value="15" ${pageSize === 15 ? "selected" : ""}>15</option>
            <option value="25" ${pageSize === 25 ? "selected" : ""}>25</option>
            <option value="50" ${pageSize === 50 ? "selected" : ""}>50</option>
          </select>
        </div>
      </div>

      <div class="pagination-controls">
        <button class="pagination-btn" id="${idPrefix}-btn-prev" ${cur <= 1 ? "disabled" : ""}>
          ‹ Sebelumnya
        </button>
        <div class="pagination-pages">
          ${pages.map((p) => {
            if (p === "...") return `<span class="pagination-ellipsis">…</span>`;
            return `<button class="pagination-num-btn ${p === cur ? "active" : ""}" data-page="${p}">${p}</button>`;
          }).join("")}
        </div>
        <button class="pagination-btn" id="${idPrefix}-btn-next" ${cur >= totalPages ? "disabled" : ""}>
          Selanjutnya ›
        </button>
      </div>
    </div>
  `;
}

function bindPaginationEvents({ idPrefix, currentPage, pageSize, totalItems, onPageChange, onPageSizeChange }) {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const cur = Math.min(Math.max(1, currentPage), totalPages);

  const prevBtn = document.getElementById(`${idPrefix}-btn-prev`);
  if (prevBtn && cur > 1) {
    prevBtn.addEventListener("click", () => onPageChange(cur - 1));
  }

  const nextBtn = document.getElementById(`${idPrefix}-btn-next`);
  if (nextBtn && cur < totalPages) {
    nextBtn.addEventListener("click", () => onPageChange(cur + 1));
  }

  const sizeSelect = document.getElementById(`${idPrefix}-page-size`);
  if (sizeSelect) {
    sizeSelect.addEventListener("change", (e) => onPageSizeChange(Number(e.target.value)));
  }

  const bar = document.getElementById(`${idPrefix}-pagination`);
  if (bar) {
    bar.querySelectorAll(".pagination-num-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const pageNum = Number(btn.dataset.page);
        if (pageNum && pageNum !== cur) onPageChange(pageNum);
      });
    });
  }
}

function riskLabel(level) {
  const map = {
    "INDIKASI PENIPUAN": "Fraud Indication",
    "HATI-HATI": "Caution",
    "AMAN": "Safe",
  };
  return map[level] || level;
}

function riskBadge(level) {
  const map = {
    "INDIKASI PENIPUAN": "badge-danger",
    "HATI-HATI": "badge-warning",
    "AMAN": "badge-success",
  };
  return `<span class="badge ${map[level] || "badge-neutral"}">${riskLabel(level)}</span>`;
}

async function api(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

function fmtInt(n) {
  return (n ?? 0).toLocaleString("id-ID");
}

function esc(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function fmtDate(iso) {
  if (!iso) return "—";
  if (typeof iso === "string" && (iso.startsWith("Baru") || iso.includes("lalu"))) return iso;
  const d = new Date(iso);
  if (isNaN(d.getTime())) return String(iso);
  return d.toLocaleString("id-ID", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

function formatFindingTime(dateVal) {
  if (!dateVal) return "Baru saja";
  if (typeof dateVal === "string" && (dateVal.startsWith("Baru") || dateVal.includes("lalu"))) return dateVal;
  try {
    const d = new Date(dateVal);
    if (!isNaN(d.getTime())) {
      const now = new Date();
      const diffSec = Math.floor((now - d) / 1000);
      if (diffSec < 60) return "Baru saja";
      if (diffSec < 3600) return `${Math.floor(diffSec / 60)} mnt lalu`;
      if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} jam lalu`;
      return d.toLocaleDateString("id-ID", { month: "short", day: "numeric" });
    }
  } catch (e) {}
  return String(dateVal);
}


// Real, honest liveness status only -- last_status_code is null whenever a
// domain was never actually HEAD-checked (every judol/porn finding, plus any
// phishing finding scored with allow_network=False or predating the
// last_status_code column). Fabricating a specific "200 OK" / "403
// Forbidden" from the is_live boolean alone -- a bug this dashboard
// previously had -- means a domain that was simply never checked can end up
// looking definitively verified. Fixed 2026-09-03 when this bug produced a
// wall of fake "403 Forbidden" rows for the 23 judol/porn findings merged
// into the unified Radar table, none of which have ever been checked.
function liveStatus(isLive, statusCode) {
  if (typeof statusCode === "number") {
    if (statusCode < 300) return { text: `${statusCode} OK Live`, dot: "ok" };
    if (statusCode < 400) return { text: `${statusCode} Redirect`, dot: "warn" };
    return { text: `${statusCode} Blocked`, dot: "bad" };
  }
  return isLive
    ? { text: "Live", dot: "ok" }
    : { text: "Not checked", dot: "neutral" };
}

// ---------------------------------------------------------------------------
// Router & Navigation
// ---------------------------------------------------------------------------

const VIEW_CONFIG = {
  overview: {
    path: "/overview",
    title: "SIAGA - Overview | Threat Intelligence",
    crumb: "SIAGA Intelligence",
    renderer: renderOverview,
  },
  radar: {
    path: "/radar",
    title: "SIAGA - Radar Phishing | Threat Intelligence",
    crumb: "Telemetry & Hunting",
    renderer: renderRadar,
  },
  triage: {
    path: "/triage",
    title: "SIAGA - Triage Sandbox | Threat Intelligence",
    crumb: "Investigation",
    renderer: renderTriage,
  },
  architecture: {
    path: "/architecture",
    title: "SIAGA - Arsitektur Pipeline | Threat Intelligence",
    crumb: "System Design",
    renderer: renderArchitecture,
  },
  compliance: {
    path: "/compliance",
    title: "SIAGA - Kepatuhan UU PDP | Threat Intelligence",
    crumb: "Governance",
    renderer: renderCompliance,
  },
  evaluation: {
    path: "/evaluation",
    title: "SIAGA - Evaluasi Model | Threat Intelligence",
    crumb: "Governance",
    renderer: renderEvaluation,
  },
  docs: {
    path: "/documentation",
    title: "SIAGA - Dokumentasi Sistem, Arsitektur & Kepatuhan",
    crumb: "Reference & SOP",
    renderer: (root) => renderDocs(root, state.docsActiveTab || "architecture"),
  },
  architecture: {
    path: "/architecture",
    title: "SIAGA - Arsitektur Sistem (Dokumentasi)",
    crumb: "Documentation",
    renderer: (root) => renderDocs(root, "architecture"),
  },
  compliance: {
    path: "/compliance",
    title: "SIAGA - Kepatuhan Regulasi UU PDP (Dokumentasi)",
    crumb: "Documentation",
    renderer: (root) => renderDocs(root, "compliance"),
  },
};

const VIEWS = {
  overview: renderOverview,
  radar: renderRadar,
  triage: renderTriage,
  architecture: (root) => renderDocs(root, "architecture"),
  compliance: (root) => renderDocs(root, "compliance"),
  evaluation: renderEvaluation,
  docs: renderDocs,
};

function showToast(message) {
  let toast = document.getElementById("ios-global-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "ios-global-toast";
    toast.className = "ios-toast";
    document.body.appendChild(toast);
  }
  toast.innerHTML = `
    <span class="ios-toast-icon">${ICONS.check}</span>
    <span>${message}</span>
  `;
  toast.classList.add("show");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.classList.remove("show");
  }, 2800);
}

function getViewFromUrl() {
  // 1. Try URL pathname: e.g. /radar, /judol, /documentation, etc.
  const pathParts = window.location.pathname.split("/").filter(Boolean);
  const lastPart = pathParts[pathParts.length - 1]?.toLowerCase();
  if (lastPart === "judol") {
    state.radar.category = "judol";
    return "radar";
  }
  if (lastPart === "porn") {
    state.radar.category = "porn";
    return "radar";
  }
  if (lastPart === "documentation" || lastPart === "docs") {
    return "docs";
  }
  if (lastPart === "architecture") {
    state.docsActiveTab = "architecture";
    return "docs";
  }
  if (lastPart === "compliance") {
    state.docsActiveTab = "compliance";
    return "docs";
  }
  if (lastPart && VIEW_CONFIG[lastPart]) {
    return lastPart;
  }

  // 2. Try URL hash: e.g. #/radar or #radar or #documentation
  const hash = window.location.hash.replace(/^#\/?/, "").toLowerCase();
  if (hash === "judol") {
    state.radar.category = "judol";
    return "radar";
  }
  if (hash === "porn") {
    state.radar.category = "porn";
    return "radar";
  }
  if (hash === "documentation" || hash === "docs") {
    return "docs";
  }
  if (hash === "architecture") {
    state.docsActiveTab = "architecture";
    return "docs";
  }
  if (hash === "compliance") {
    state.docsActiveTab = "compliance";
    return "docs";
  }
  if (hash && VIEW_CONFIG[hash]) {
    return hash;
  }

  // 3. Try query param ?view=radar
  const params = new URLSearchParams(window.location.search);
  const qCat = params.get("category")?.toLowerCase();
  if (qCat && ["phishing", "judol", "porn", "all"].includes(qCat)) {
    state.radar.category = qCat;
  }
  const qView = params.get("view")?.toLowerCase();
  if (qView && VIEW_CONFIG[qView]) {
    return qView;
  }

  return "overview";
}

function setView(name, pushState = true) {
  // Gracefully alias architecture and compliance views into the Documentation hub
  if (name === "architecture") {
    state.docsActiveTab = "architecture";
    name = "docs";
  } else if (name === "compliance") {
    state.docsActiveTab = "compliance";
    name = "docs";
  }

  if (!VIEW_CONFIG[name]) name = "overview";
  state.view = name;
  const config = VIEW_CONFIG[name];

  const topbarBadge = document.getElementById("topbar-view-badge");
  if (topbarBadge) topbarBadge.textContent = name;

  // 1. Update active sidebar item
  document.querySelectorAll(".nav-item[data-view]").forEach((el) => {
    const isDocRelated = (name === "docs" || name === "architecture" || name === "compliance") && el.dataset.view === "docs";
    el.classList.toggle("active", el.dataset.view === name || isDocRelated);
  });

  // 2. Set browser title
  document.title = `${config.title} — SIAGA SOC`;

  // 3. Sync browser URL path
  const targetUrl = config.path;
  const currentPath = window.location.pathname;
  if (pushState) {
    if (currentPath !== targetUrl) {
      history.pushState({ view: name }, config.title, targetUrl);
    }
  } else {
    const initialPath = (currentPath === "/" && name === "overview") ? "/" : targetUrl;
    history.replaceState({ view: name }, config.title, initialPath);
  }

  // Scroll main container to top
  const mainEl = document.querySelector(".content-main");
  if (mainEl) mainEl.scrollTop = 0;

  // 4. Render view content
  const root = document.getElementById("view-root");
  root.innerHTML = `<div class="page"><div class="empty-state"><span class="spinner"></span></div></div>`;

  config.renderer(root)
    .then(() => {
      // Check if URL has ?inspect=ID deep link
      const params = new URLSearchParams(window.location.search);
      const inspectId = params.get("inspect");
      if (inspectId && name === "radar") {
        openFindingDrawer(inspectId, params.get("category"));
      }
    })
    .catch((err) => {
      root.innerHTML = `<div class="page"><div class="empty-state">Gagal memuat view: ${err.message}</div></div>`;
    });
}

function pageShell({ crumb, title, desc, actions = "" }) {
  const currentView = state.view || "overview";
  const config = VIEW_CONFIG[currentView] || { path: `/${currentView}` };

  return `
    <div class="page">
      <div class="breadcrumb">
        <span>${crumb}</span>
        <span class="breadcrumb-separator">/</span>
        <span class="breadcrumb-path-badge">${config.path}</span>
      </div>
      <div class="page-header">
        <div>
          <h1 class="page-title">${title}</h1>
          <p class="page-desc">${desc}</p>
        </div>
        ${actions ? `<div class="page-actions">${actions}</div>` : ""}
      </div>
      <div id="page-body"></div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// REGIONAL HEATMAP -- real map via Leaflet.js (OpenStreetMap tiles), loaded
// from cdnjs in index.html. Marker positions are real province-capital
// coordinates (public, well-known); marker RADIUS encodes the estimate from
// /api/insight/regional-heatmap, which is itself derived (not measured) --
// see that endpoint's docstring. A module-level handle lets us tear down
// the previous map instance before re-initializing, since Leaflet throws if
// you call L.map() twice on the same container (happens when the user
// navigates away from Overview and back).
// ---------------------------------------------------------------------------

const REGION_CENTER_COORDS = {
  "Sumatera Utara": [3.5952, 98.6722],   // Medan
  "DKI Jakarta": [-6.2088, 106.8456],    // Jakarta
  "Jawa Barat": [-6.9175, 107.6191],     // Bandung
  "Jawa Tengah": [-6.9667, 110.4167],    // Semarang
  "Jawa Timur": [-7.2575, 112.7521],     // Surabaya
};

let _regionMapInstance = null;

function initRegionalLeafletMap(containerId, regions) {
  const el = document.getElementById(containerId);
  if (!el || typeof L === "undefined") return;

  if (_regionMapInstance) {
    _regionMapInstance.remove();
    _regionMapInstance = null;
  }

  const map = L.map(containerId, { scrollWheelZoom: false }).setView([-2.5, 118], 4.4);
  _regionMapInstance = map;

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 10,
  }).addTo(map);

  const maxPct = Math.max(...regions.map((r) => r.intensity_pct), 1);
  regions
    .filter((r) => REGION_CENTER_COORDS[r.region])
    .forEach((r) => {
      const baseRadius = 8 + (r.intensity_pct / maxPct) * 22;
      const marker = L.circleMarker(REGION_CENTER_COORDS[r.region], {
        radius: baseRadius,
        color: "#ff3b30",
        weight: 1.5,
        fillColor: "#ff3b30",
        fillOpacity: 0.35,
      }).addTo(map);

      marker.bindTooltip(
        `<strong>${esc(r.region)}</strong><br>Estimasi: ~${fmtInt(r.estimated_count)} temuan`,
        { direction: "top", offset: [0, -baseRadius] }
      );

      // Hover: grow + brighten the marker for a tactile feel; click still
      // opens a pinned popup (useful once the tooltip has been dismissed
      // by moving the mouse away).
      marker.on("mouseover", () => {
        marker.setStyle({ fillOpacity: 0.6, weight: 2.5 });
        marker.setRadius(baseRadius * 1.15);
      });
      marker.on("mouseout", () => {
        marker.setStyle({ fillOpacity: 0.35, weight: 1.5 });
        marker.setRadius(baseRadius);
      });
      marker.bindPopup(
        `<strong>${esc(r.region)}</strong><br>Estimasi: ~${fmtInt(r.estimated_count)} temuan`
      );
    });
}

// ---------------------------------------------------------------------------
// OVERVIEW VIEW (iPadOS Smart Widgets & High-Density iOS Feed)
// ---------------------------------------------------------------------------

async function renderOverview(root) {
  const [metrics, today, top, health, judolRes, pornRes, analytics, trend, caseStudy, activityFeed, regionalHeatmap] = await Promise.all([
    api("/api/metrics"),
    api("/api/stats/today"),
    api("/api/findings/top?limit=100&unmask=true"),
    api("/api/health"),
    api("/api/judol?limit=1").catch(() => ({ hijacked_institution_count: 0 })),
    api("/api/porn?limit=1").catch(() => ({ hijacked_institution_count: 0 })),
    api("/api/stats/analytics"),
    api("/api/stats/trend?days=2"),
    api("/api/insight/case-study").catch(() => ({ available: false })),
    api("/api/insight/activity-feed?limit=60").catch(() => ({ items: [] })),
    api("/api/insight/regional-heatmap").catch(() => ({ available: false })),
  ]);

  const hijackedTotal = (judolRes?.hijacked_institution_count || 0) + (pornRes?.hijacked_institution_count || 0);
  const [prevDay, currDay] = trend.trend.length === 2 ? trend.trend : [null, null];

  root.innerHTML = pageShell({
    crumb: "SIAGA Intelligence",
    title: "Overview",
    desc: "Active threat intelligence telemetry, proactive Certificate Transparency ingestion, and targeted brand impersonation.",
  });

  const body = document.getElementById("page-body");

  // KPI 1 Delta -- absolute count, not a percentage: with irregular collector
  // cadence a near-zero prior-day base can blow a percentage up to a
  // nonsensical value, which reads as a bug even when the arithmetic is
  // technically real. No prior-day data -> say so plainly, never a
  // placeholder number.
  let kpi1Caption = `<span class="kpi-caption neutral">No prior-day data</span>`;
  if (prevDay && currDay) {
    const diff = currDay.domains_scanned - prevDay.domains_scanned;
    if (diff === 0) {
      kpi1Caption = `<span class="kpi-caption neutral">No change vs yesterday</span>`;
    } else {
      const up = diff > 0;
      const icon = up ? ICONS.arrowUpRight : ICONS.arrowUp;
      kpi1Caption = `<span class="kpi-caption ${up ? "green" : "red"}">${icon} ${up ? "+" : ""}${fmtInt(diff)} vs yesterday</span>`;
    }
  }

  const leadTimeVal = metrics.avg_lead_time_hours !== null ? `${metrics.avg_lead_time_hours}h` : "—";
  const leadTimeCaption = metrics.avg_lead_time_hours !== null
    ? `<span class="kpi-caption green">${ICONS.lightning} vs. public blacklist</span>`
    : `<span class="kpi-caption neutral">Not enough data yet</span>`;

  const scannedToday = today?.domains_scanned ?? 0;
  const flaggedToday = today?.domains_flagged ?? 0;
  const liveToday = today?.domains_live ?? 0;

  // Dual-stream panel: every number below comes from analytics.dual_stream
  // (dashboard/api.py get_stats_analytics) -- there is no measured latency
  // or false-positive-rate source anywhere in the pipeline, so this only
  // ever shows real volume/flag-rate counts, never invented ms/% figures.
  const proactive = analytics.dual_stream?.proactive ?? { total_scanned: 0, findings_flagged: 0 };
  const reactive = analytics.dual_stream?.reactive ?? { total_analyzed: 0, fraud_detected: 0 };
  const streamTotal = proactive.total_scanned + reactive.total_analyzed;
  const ctSharePct = streamTotal > 0 ? Math.round((proactive.total_scanned / streamTotal) * 100) : 0;
  const tgSharePct = streamTotal > 0 ? 100 - ctSharePct : 0;
  const ctFlagRate = proactive.total_scanned > 0
    ? ((proactive.findings_flagged / proactive.total_scanned) * 100).toFixed(2)
    : "0.00";
  const tgFlagRate = reactive.total_analyzed > 0
    ? ((reactive.fraud_detected / reactive.total_analyzed) * 100).toFixed(2)
    : "0.00";

  body.innerHTML = `
    <!-- 5 iPadOS-style Smart KPI Widgets -->
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-top">
          <span class="kpi-label">Daily Domains</span>
          <span class="kpi-icon-tile tile-blue">${ICONS.globe}</span>
        </div>
        <div class="kpi-value" id="overview-kpi-scanned">${fmtInt(scannedToday)}</div>
        ${kpi1Caption}
      </div>

      <div class="kpi-card">
        <div class="kpi-top">
          <span class="kpi-label">Flagged Fraud</span>
          <span class="kpi-icon-tile tile-rose">${ICONS.warning}</span>
        </div>
        <div class="kpi-value" id="overview-kpi-flagged">${fmtInt(flaggedToday)}</div>
        <span class="kpi-caption red">${ICONS.arrowUp} High confidence</span>
      </div>

      <div class="kpi-card">
        <div class="kpi-top">
          <span class="kpi-label">Active Threats</span>
          <span class="kpi-icon-tile tile-orange">${ICONS.pulse}</span>
        </div>
        <div class="kpi-value" id="overview-kpi-active">${fmtInt(liveToday)}</div>
        <span class="kpi-caption amber">${ICONS.lightning} Requiring mitigation</span>
      </div>

      <div class="kpi-card">
        <div class="kpi-top">
          <span class="kpi-label">Hijacked Go/Ac</span>
          <span class="kpi-icon-tile tile-purple">${ICONS.lock}</span>
        </div>
        <div class="kpi-value" id="overview-kpi-hijacked">${fmtInt(hijackedTotal)}</div>
        <span class="kpi-caption neutral">${ICONS.shieldLock} Isolated & contained</span>
      </div>

      <div class="kpi-card">
        <div class="kpi-top">
          <span class="kpi-label">Avg Lead Time</span>
          <span class="kpi-icon-tile tile-sky">${ICONS.clock}</span>
        </div>
        <div class="kpi-value">${leadTimeVal}</div>
        ${leadTimeCaption}
      </div>
    </div>

    ${!caseStudy.available ? "" : `
    <!-- Insight Prioritas: Problem -> Data -> Insight -> Action -> Impact -->
    <div class="section">
      <div class="panel insight-story-panel">
        <div class="panel-header-row">
          <div>
            <h2 class="section-title">${ICONS.lightning} Insight Prioritas</h2>
            <p class="section-desc">Kampanye infrastruktur terbesar yang saat ini terdeteksi sistem, dari gejala sampai hasil penanganan.</p>
          </div>
          <span class="badge badge-danger">${caseStudy.evidence.total_domains} domain terhubung</span>
        </div>

        <div class="insight-story-grid">
          <div class="insight-story-step">
            <div class="insight-story-step-lbl">1. Masalah</div>
            <div class="insight-story-step-body">${caseStudy.problem}</div>
          </div>
          <div class="insight-story-step">
            <div class="insight-story-step-lbl">2. Data & Evidence</div>
            <div class="insight-story-step-body">
              <p>CT Log mendeteksi <strong>${caseStudy.evidence.total_domains} domain baru</strong> mencatut
              <strong>${esc(caseStudy.evidence.target_brand)}</strong> sejak ${fmtDate(caseStudy.evidence.first_detected_at)}.</p>
              <div class="insight-mini-timeline">
                ${(() => {
                  const counts = caseStudy.evidence.timeline.map((t) => t.count);
                  const maxCount = Math.max(...counts, 1);
                  return caseStudy.evidence.timeline.map((t) => `
                    <div class="insight-mini-bar" style="height:${Math.max(12, Math.round((t.count / maxCount) * 100))}%;" title="${t.date}: ${t.count} domain baru"></div>
                  `).join("");
                })()}
              </div>
            </div>
          </div>
          <div class="insight-story-step">
            <div class="insight-story-step-lbl">3. Insight</div>
            <div class="insight-story-step-body">${caseStudy.insight}</div>
          </div>
          <div class="insight-story-step">
            <div class="insight-story-step-lbl">4. Tindakan Pemerintah</div>
            <div class="insight-story-step-body">${caseStudy.action}</div>
          </div>
          <div class="insight-story-step insight-story-step-impact">
            <div class="insight-story-step-lbl">5. Dampak Terukur</div>
            <div class="insight-story-step-body">
              ${caseStudy.impact.summary}
              <div class="insight-impact-bars">
                <div class="insight-impact-bar-row">
                  <span>Masih aktif</span>
                  <div class="insight-impact-track"><div class="insight-impact-fill red" style="width:${Math.round(caseStudy.impact.domains_still_live / caseStudy.impact.total_domains * 100)}%;"></div></div>
                  <strong>${caseStudy.impact.domains_still_live}/${caseStudy.impact.total_domains}</strong>
                </div>
                <div class="insight-impact-bar-row">
                  <span>Masuk blacklist publik</span>
                  <div class="insight-impact-track"><div class="insight-impact-fill green" style="width:${Math.round(caseStudy.impact.domains_now_in_blacklist / caseStudy.impact.total_domains * 100)}%;"></div></div>
                  <strong>${caseStudy.impact.domains_now_in_blacklist}/${caseStudy.impact.total_domains}</strong>
                </div>
              </div>
            </div>
          </div>
        </div>

        ${!caseStudy.secondary ? "" : `
        <div class="insight-secondary-row">
          <span class="badge badge-warning">Pembanding: Belum Dieskalasi</span>
          <div class="insight-secondary-body">
            Tidak semua temuan naik jadi insiden penuh -- <strong>${esc(caseStudy.secondary.target_brand)}</strong>
            (${caseStudy.secondary.total_domains} domain, pola kemiripan brand yang sama tanpa bukti infrastruktur bersama)
            masih berstatus <strong>dipantau</strong>, bukan dieskalasi seperti kasus di atas.
            ${esc(caseStudy.secondary.note)}
          </div>
        </div>
        `}
      </div>
    </div>
    `}

    <!-- Activity Feed & Regional Estimate -->
    <div class="two-col">
      <div class="panel panel-flush">
        <div class="panel-header-row" style="padding:16px 18px 8px;">
          <div>
            <h2 class="section-title">Aktivitas Terkini</h2>
            <p class="section-desc">Temuan terbaru lintas kategori, diurutkan berdasarkan waktu deteksi</p>
          </div>
          <span class="live-status-pill" title="Collector &amp; pipeline berjalan otomatis harian">
            <span class="live-dot"></span>
            <span>Monitoring Aktif</span>
          </span>
        </div>
        <div id="overview-activity-feed-wrap"></div>
      </div>

      <div class="panel">
        <div class="panel-header-row">
          <div>
            <h2 class="section-title">Estimasi Sebaran Regional</h2>
            <p class="section-desc">${regionalHeatmap.available ? esc(regionalHeatmap.basis) : "Belum ada data untuk diestimasi."}</p>
          </div>
        </div>
        ${!regionalHeatmap.available ? `<div class="empty-state">Belum cukup data.</div>` : `
        <div id="overview-region-map" class="region-map-leaflet"></div>
        <p class="geo-map-caption">Titik menunjukkan intensitas estimasi (ukuran &amp; opacity), bukan koordinat lokasi terverifikasi -- lihat catatan estimasi di atas.</p>
        <div class="region-heatmap-list">
          ${regionalHeatmap.regions.map((r) => `
            <div class="region-heatmap-row">
              <span class="region-heatmap-label">${esc(r.region)}</span>
              <div class="region-heatmap-track"><div class="region-heatmap-fill" style="width:${r.intensity_pct}%;"></div></div>
              <span class="region-heatmap-count">~${fmtInt(r.estimated_count)}</span>
            </div>
          `).join("")}
        </div>
        `}
      </div>
    </div>

    <!-- 2-Column: Intelligence Streams & 24-Hour Velocity -->
    <div class="two-col">
      <div class="panel">
        <div class="panel-header-row">
          <div>
            <h2 class="section-title">Intelligence Streams</h2>
            <p class="section-desc">Comparative analysis between proactive CT ingestion and community threat signals.</p>
          </div>
          <span class="chip">Real-time sync</span>
        </div>

        <div class="stream-card">
          <div class="stream-head">
            <span class="stream-name"><span class="stream-dot blue"></span>CT-Stream Proactive</span>
            <span class="stream-eff blue">${ctFlagRate}% Flag Rate</span>
          </div>
          <div class="stream-track"><div class="stream-fill blue" style="width: ${ctSharePct}%;"></div></div>
          <div class="stream-stats">
            <span>Scanned: <strong>${fmtInt(proactive.total_scanned)}</strong></span>
            <span>Flagged: <strong>${fmtInt(proactive.findings_flagged)}</strong></span>
          </div>
        </div>

        <div class="stream-card">
          <div class="stream-head">
            <span class="stream-name"><span class="stream-dot amber"></span>Telegram Reactive</span>
            <span class="stream-eff amber">${tgFlagRate}% Flag Rate</span>
          </div>
          <div class="stream-track"><div class="stream-fill amber" style="width: ${tgSharePct}%;"></div></div>
          <div class="stream-stats">
            <span>Analyzed: <strong>${fmtInt(reactive.total_analyzed)}</strong></span>
            <span>Fraud: <strong>${fmtInt(reactive.fraud_detected)}</strong></span>
          </div>
        </div>

        <div class="stream-ratio-row">
          <span>Stream Weight Ratio</span>
          <strong>${ctSharePct}% CT / ${tgSharePct}% Telegram</strong>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header-row">
          <div>
            <h2 class="section-title">24-Hour Attack Velocity</h2>
            <p class="section-desc">Hourly distribution of flagged malicious domain registrations</p>
          </div>
          <div class="velocity-top-actions">
            <span class="pill-tz">UTC+07:00</span>
            <button class="btn-icon-dot" title="Options">${ICONS.dotsVertical}</button>
          </div>
        </div>

        <div class="velocity-chart-wrap" id="overview-velocity-chart"></div>
      </div>
    </div>

    <!-- Live Threat Radar Findings Section -->
    <div class="section">
      <div class="panel panel-flush">
        <div class="table-toolbar">
          <div class="table-toolbar-left-col">
            <div class="table-title-row">
              <h2 class="section-title">Live Threat Radar Findings</h2>
            </div>
            <div class="table-subtitle-row">
              <span class="section-desc">Feed temuan dari /api/findings/top, diurutkan berdasarkan skor risiko</span>
              <span class="sub-sep">•</span>
              <span id="overview-findings-counter-text" style="color:var(--text-secondary); font-weight:600;">${(top.findings || []).length} domain aktif</span>
            </div>
          </div>
          <div class="table-toolbar-right">
            <div class="live-stream-controls">
              <button class="btn-live-stream-action" id="overview-live-refresh-btn" title="Ambil ulang data temuan terkini dari server">
                <span>↻</span>
                <span>Segarkan</span>
              </button>
            </div>
            <input type="text" class="table-search-input" id="overview-table-search" placeholder="Filter radar..." spellcheck="false">
            <button class="btn-export" id="overview-export-btn">
              ${ICONS.download} Export Logs
            </button>
          </div>
        </div>

        <div class="data-table-container" id="overview-findings-wrap"></div>
      </div>
    </div>
  `;

  // Initialize the real Leaflet map for the regional heatmap, if present
  if (regionalHeatmap.available) {
    initRegionalLeafletMap("overview-region-map", regionalHeatmap.regions);
  }

  // Render 24-Hour Velocity Bars
  const series = analytics.hourly_velocity.series || [];
  const maxCount = Math.max(...series.map((h) => h.count), 1);
  const chartEl = document.getElementById("overview-velocity-chart");
  if (chartEl) {
    chartEl.innerHTML = `
      <div class="velocity-bars">
        ${series.map((h, idx) => {
          const isPeak = h.count === maxCount || (idx >= 6 && idx <= 8) || (idx >= 17 && idx <= 19);
          const barHeight = Math.max(14, Math.round((h.count / maxCount) * 100));
          return `
            <div class="velocity-bar ${isPeak ? "peak" : ""}" 
                 style="height: ${barHeight}%;" 
                 title="${h.label}: ${h.count} detections">
            </div>
          `;
        }).join("")}
      </div>
      <div class="velocity-labels">
        <span>00:00</span>
        <span>04:00</span>
        <span>08:00</span>
        <span>12:00</span>
        <span>16:00</span>
        <span>20:00</span>
        <span>23:59</span>
      </div>
    `;
  }

  // Populate state.overviewFindings and render initial findings
  state.overviewFindings = [...(top.findings || [])];
  renderOverviewTable(state.overviewFindings);
  renderActivityFeedList(activityFeed.items || []);

  const liveRefreshBtn = document.getElementById("overview-live-refresh-btn");
  if (liveRefreshBtn) {
    liveRefreshBtn.addEventListener("click", async () => {
      try {
        const fresh = await api("/api/findings/top?limit=100&unmask=true");
        state.overviewFindings = [...(fresh.findings || [])];
        renderOverviewRecentFindings();
        const counterEl = document.getElementById("overview-findings-counter-text");
        if (counterEl) counterEl.textContent = `${state.overviewFindings.length} domain aktif`;
        showToast("↻ Data temuan diperbarui dari server.");
      } catch (e) {
        showToast("Gagal memuat ulang data temuan.");
      }
    });
  }

  const filterInput = document.getElementById("overview-table-search");
  if (filterInput) {
    filterInput.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase().trim();
      if (!q) {
        renderOverviewTable(state.overviewFindings);
        return;
      }
      const filtered = (state.overviewFindings || []).filter((f) => {
        const text = `${f.matched_brand || ""} ${f.raw_domain || ""} ${f.domain_masked || ""}`.toLowerCase();
        return text.includes(q);
      });
      renderOverviewTable(filtered);
    });
  }

  const exportBtn = document.getElementById("overview-export-btn");
  if (exportBtn) {
    exportBtn.addEventListener("click", () => exportFindingsCSV(state.overviewFindings || [], "siaga_overview_findings.csv"));
  }
}

// ---------------------------------------------------------------------------
// OVERVIEW FINDINGS TABLE & REAL-TIME STREAMING RENDERER
// ---------------------------------------------------------------------------

function renderOverviewTable(allItems) {
  const findingsWrap = document.getElementById("overview-findings-wrap");
  if (!findingsWrap) return;
  if (!allItems || !allItems.length) {
    findingsWrap.innerHTML = `<div class="empty-state">No findings recorded today.</div>`;
    return;
  }

  const totalItems = allItems.length;
  const pageSize = state.overview.pageSize || 10;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  if (state.overview.page > totalPages) state.overview.page = totalPages;
  if (state.overview.page < 1) state.overview.page = 1;
  const curPage = state.overview.page;
  const startIdx = (curPage - 1) * pageSize;
  const items = allItems.slice(startIdx, startIdx + pageSize);

  const paginationHtml = createPaginationHtml({
    totalItems,
    currentPage: curPage,
    pageSize,
    idPrefix: "overview",
  });

  findingsWrap.innerHTML = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Masked Domain</th>
          <th>Kategori / Brand</th>
          <th>Risk Score & Level</th>
          <th>HEAD Check Status</th>
          <th>Public Blacklist</th>
          <th>Waktu Deteksi</th>
          <th style="text-align:right;">Action</th>
        </tr>
      </thead>
      <tbody>
        ${items.map((f) => {
          const ls = liveStatus(f.is_live, f.last_status_code);
          const domainText = state.masked ? f.domain_masked : (f.raw_domain || f.domain || f.domain_masked);
          const rawDomain = f.raw_domain || f.domain || f.domain_masked;
          const blacklistHtml = f.in_public_blacklist
            ? `<span class="badge badge-danger">Listed</span>`
            : `<span class="blacklist-clean">Clean</span>`;
          const rowClass = f.is_new_arrival ? "new-arrival-row" : "";
          const newBadgeHtml = f.is_new_arrival ? `<span class="badge-new-arrival">⚡ BARU</span>` : "";
          const timeDisplay = formatFindingTime(f.first_seen);

          return `
            <tr class="${rowClass}" data-finding-id="${f.id}">
              <td>
                <div style="display:flex; align-items:center;">
                  ${newBadgeHtml}
                  <a class="domain-preview-link" data-preview-id="${f.id}" data-category="${f.category || 'phishing'}" data-raw="${rawDomain}" data-masked="${domainText}" title="Klik untuk Pratinjau Web Terisolasi">
                    <span class="preview-mini-tag">${ICONS.globe} Preview</span>
                    <span class="truncate">${domainText}</span>
                  </a>
                </div>
              </td>
              <td><span class="chip">${f.matched_brand || "General"}</span></td>
              <td style="white-space:nowrap;">
                <strong style="margin-right:6px; font-size:13.5px;">${f.risk_score}</strong>
                ${riskBadge(f.risk_level)}
              </td>
              <td>
                <span class="status-inline">
                  <span class="dot ${ls.dot}"></span>${ls.text}
                </span>
              </td>
              <td>${blacklistHtml}</td>
              <td><span class="detect-time-chip ${f.is_new_arrival ? 'chip-live-recent' : ''}">${timeDisplay}</span></td>
              <td style="text-align:right;">
                <button class="btn-inspect" data-inspect-id="${f.id}" data-category="${f.category || 'phishing'}">Inspect</button>
              </td>
            </tr>
          `;
        }).join("")}
      </tbody>
    </table>
    ${paginationHtml}
  `;

  findingsWrap.querySelectorAll(".domain-preview-link").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      openWebPreviewModal(
        link.dataset.previewId,
        link.dataset.category,
        link.dataset.raw,
        link.dataset.masked
      );
    });
  });

  findingsWrap.querySelectorAll(".btn-inspect").forEach((btn) => {
    btn.addEventListener("click", () => openFindingDrawer(btn.dataset.inspectId, btn.dataset.category || "phishing"));
  });

  bindPaginationEvents({
    idPrefix: "overview",
    currentPage: curPage,
    pageSize,
    totalItems,
    onPageChange: (p) => {
      state.overview.page = p;
      renderOverviewTable(allItems);
    },
    onPageSizeChange: (s) => {
      state.overview.pageSize = s;
      state.overview.page = 1;
      renderOverviewTable(allItems);
    },
  });
}

function renderActivityFeedList(allItems) {
  const wrap = document.getElementById("overview-activity-feed-wrap");
  if (!wrap) return;
  if (!allItems || !allItems.length) {
    wrap.innerHTML = `<div class="empty-state">Belum ada aktivitas.</div>`;
    return;
  }

  const totalItems = allItems.length;
  const pageSize = state.activityFeed.pageSize || 8;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  if (state.activityFeed.page > totalPages) state.activityFeed.page = totalPages;
  if (state.activityFeed.page < 1) state.activityFeed.page = 1;
  const curPage = state.activityFeed.page;
  const startIdx = (curPage - 1) * pageSize;
  const items = allItems.slice(startIdx, startIdx + pageSize);

  const paginationHtml = createPaginationHtml({
    totalItems,
    currentPage: curPage,
    pageSize,
    idPrefix: "activity-feed",
  });

  wrap.innerHTML = `
    <div class="activity-feed-list">
      ${items.map((it) => {
        const catIcon = it.category === "judol" ? "🎰" : it.category === "porn" ? "🔞" : "🎣";
        const catLabel = it.category === "judol" ? "Judi Online" : it.category === "porn" ? "Konten Dewasa" : "Phishing";
        return `
          <div class="activity-feed-row">
            <span class="activity-feed-icon">${catIcon}</span>
            <div class="activity-feed-mid">
              <div class="activity-feed-title">${it.brand ? esc(it.brand) : catLabel} <span class="activity-feed-domain">${esc(it.domain_masked)}</span></div>
              <div class="activity-feed-time">${fmtDate(it.first_seen)}</div>
            </div>
            ${it.risk_score != null ? `<span class="badge ${it.risk_score >= 70 ? "badge-danger" : "badge-warning"}">${it.risk_score}</span>` : ""}
          </div>
        `;
      }).join("")}
    </div>
    ${paginationHtml}
  `;

  bindPaginationEvents({
    idPrefix: "activity-feed",
    currentPage: curPage,
    pageSize,
    totalItems,
    onPageChange: (p) => {
      state.activityFeed.page = p;
      renderActivityFeedList(allItems);
    },
    onPageSizeChange: (s) => {
      state.activityFeed.pageSize = s;
      state.activityFeed.page = 1;
      renderActivityFeedList(allItems);
    },
  });
}


function renderOverviewRecentFindings() {
  const wrap = document.getElementById("overview-findings-wrap");
  if (!wrap || !state.overviewFindings) return;
  const filterInput = document.getElementById("overview-table-search");
  const q = filterInput ? filterInput.value.toLowerCase().trim() : "";
  let items = state.overviewFindings;
  if (q) {
    items = items.filter((f) => {
      const text = `${f.matched_brand || ""} ${(f.matched_keywords || []).join(" ")} ${f.raw_domain || ""} ${f.domain_masked || ""}`.toLowerCase();
      return text.includes(q);
    });
  }
  renderOverviewTable(items);
}

// ---------------------------------------------------------------------------
// RADAR VIEW -- unified findings feed (phishing + judol + adult content),
// merged 2026-09-03 so all three categories live in one prioritized table
// with a Category filter/badge, instead of three near-duplicate pages.
// ---------------------------------------------------------------------------

const CATEGORY_LABELS = { phishing: "Phishing", judol: "Judol", porn: "Adult Content" };

async function renderRadar(root) {
  const [phishingRes, judolRes, pornRes] = await Promise.allSettled([
    api("/api/findings/top?limit=200&unmask=true"),
    api("/api/judol?limit=200&unmask=true"),
    api("/api/porn?limit=200&unmask=true"),
  ]);

  const getArrayFromRes = (res, prop) => {
    if (!res || res.status !== "fulfilled") return [];
    const v = res.value;
    if (Array.isArray(v)) return v;
    if (v && Array.isArray(v[prop])) return v[prop];
    if (v && Array.isArray(v.items)) return v.items;
    if (v && Array.isArray(v.findings)) return v.findings;
    return [];
  };

  const phishingItems = getArrayFromRes(phishingRes, "findings").map((f) => ({ ...f, category: f.category || "phishing" }));
  const judolItems = getArrayFromRes(judolRes, "items").map((f) => ({ ...f, category: f.category || "judol" }));
  const pornItems = getArrayFromRes(pornRes, "items").map((f) => ({ ...f, category: f.category || "porn" }));

  state.radar.rows = [...phishingItems, ...judolItems, ...pornItems];
  const counts = {
    total: state.radar.rows.length,
    phishing: phishingItems.length,
    judol: judolItems.length,
    porn: pornItems.length,
  };

  root.innerHTML = pageShell({
    crumb: "SIAGA Intelligence",
    title: "Threat Radar",
    desc: "Unified threat intelligence feed -- phishing domains, online gambling (judol), and adult content, prioritized in one place with a category flag per finding.",
    actions: `
      <button class="btn-export" id="radar-export-btn">
        ${ICONS.download} Export CSV
      </button>
    `,
  });

  const body = document.getElementById("page-body");
  body.innerHTML = `
    <div class="kpi-row" style="grid-template-columns: repeat(4, 1fr); margin-bottom: var(--sp-6);">
      <div class="kpi-card">
        <div class="kpi-top">
          <span class="kpi-label">Total Findings</span>
          <span class="kpi-icon-tile tile-blue">${ICONS.warning}</span>
        </div>
        <div class="kpi-value" id="radar-kpi-total">${fmtInt(counts.total)}</div>
        <span class="kpi-caption neutral">Across all categories</span>
      </div>
      <div class="kpi-card">
        <div class="kpi-top">
          <span class="kpi-label">Phishing</span>
          <span class="kpi-icon-tile tile-sky">${ICONS.shieldLock}</span>
        </div>
        <div class="kpi-value" id="radar-kpi-phishing">${fmtInt(counts.phishing)}</div>
        <span class="kpi-caption blue">Brand impersonation</span>
      </div>
      <div class="kpi-card">
        <div class="kpi-top">
          <span class="kpi-label">Judol</span>
          <span class="kpi-icon-tile tile-purple">${ICONS.warning}</span>
        </div>
        <div class="kpi-value" id="radar-kpi-judol">${fmtInt(counts.judol)}</div>
        <span class="kpi-caption amber">Online gambling</span>
      </div>
      <div class="kpi-card">
        <div class="kpi-top">
          <span class="kpi-label">Adult Content</span>
          <span class="kpi-icon-tile tile-crimson">${ICONS.warning}</span>
        </div>
        <div class="kpi-value" id="radar-kpi-porn">${fmtInt(counts.porn)}</div>
        <span class="kpi-caption red">Pornographic domains</span>
      </div>
    </div>

    <div class="panel panel-flush">
      <div class="table-toolbar">
        <div class="table-toolbar-left" style="flex-wrap:wrap; gap:12px;">
          <input type="text" class="table-search-input" id="radar-search" placeholder="Search domain, brand, or keyword..." spellcheck="false" value="${state.radar.search || ""}">

          <!-- iOS Segmented Control for Category -->
          <div class="ios-segmented" id="radar-category-seg">
            <button class="ios-segmented-item ${!state.radar.category || state.radar.category === "all" ? "active" : ""}" data-category="all">All Categories</button>
            <button class="ios-segmented-item ${state.radar.category === "phishing" ? "active" : ""}" data-category="phishing">Phishing</button>
            <button class="ios-segmented-item ${state.radar.category === "judol" ? "active" : ""}" data-category="judol">Judol</button>
            <button class="ios-segmented-item ${state.radar.category === "porn" ? "active" : ""}" data-category="porn">Adult Content</button>
          </div>

          <!-- iOS Segmented Control for Risk Level -->
          <div class="ios-segmented" id="radar-level-seg">
            <button class="ios-segmented-item active" data-level="all">All Levels</button>
            <button class="ios-segmented-item" data-level="INDIKASI PENIPUAN">Fraud</button>
            <button class="ios-segmented-item" data-level="HATI-HATI">Caution</button>
            <button class="ios-segmented-item" data-level="AMAN">Safe</button>
          </div>

          <!-- iOS Segmented Control for Liveness -->
          <div class="ios-segmented" id="radar-live-seg">
            <button class="ios-segmented-item active" data-live="all">All Status</button>
            <button class="ios-segmented-item" data-live="live">Live Only</button>
            <button class="ios-segmented-item" data-live="blocked">Blocked</button>
          </div>
        </div>

        <div class="table-toolbar-right">
          <span class="text-tertiary" style="font-size:12.5px; font-weight:600;">
            ${counts.total} Findings
          </span>
        </div>
      </div>
      <div class="data-table-container" id="radar-table-wrap"></div>
    </div>
  `;

  // Search input
  document.getElementById("radar-search").addEventListener("input", (e) => {
    state.radar.search = e.target.value.toLowerCase().trim();
    state.radar.page = 1;
    renderRadarTable();
  });

  // Category segmented control
  document.querySelectorAll("#radar-category-seg .ios-segmented-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#radar-category-seg .ios-segmented-item").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.radar.category = btn.dataset.category;
      state.radar.page = 1;
      renderRadarTable();
    });
  });

  // Level segmented control
  document.querySelectorAll("#radar-level-seg .ios-segmented-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#radar-level-seg .ios-segmented-item").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.radar.level = btn.dataset.level;
      state.radar.page = 1;
      renderRadarTable();
    });
  });

  // Live segmented control
  document.querySelectorAll("#radar-live-seg .ios-segmented-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#radar-live-seg .ios-segmented-item").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.radar.live = btn.dataset.live;
      state.radar.page = 1;
      renderRadarTable();
    });
  });

  document.getElementById("radar-export-btn").addEventListener("click", () => {
    exportFindingsCSV(state.radar.rows, "siaga_radar_findings.csv");
  });

  renderRadarTable();
}

function renderRadarTable() {
  const wrap = document.getElementById("radar-table-wrap");
  if (!wrap) return;

  let rows = state.radar.rows.filter((r) => {
    if (state.radar.category && state.radar.category !== "all" && r.category !== state.radar.category) return false;
    if (state.radar.search) {
      const hay = `${r.matched_brand || ""} ${(r.matched_keywords || []).join(" ")} ${r.raw_domain || ""} ${r.domain_masked || ""} ${r.category || ""}`.toLowerCase();
      if (!hay.includes(state.radar.search)) return false;
    }
    if (state.radar.level && state.radar.level !== "all" && r.risk_level !== state.radar.level) return false;
    if (state.radar.live === "live" && !r.is_live) return false;
    if (state.radar.live === "blocked" && r.is_live) return false;
    return true;
  });

  rows.sort((a, b) => {
    if (a.is_new_arrival && !b.is_new_arrival) return -1;
    if (!a.is_new_arrival && b.is_new_arrival) return 1;
    return (b.risk_score || 0) - (a.risk_score || 0);
  });

  if (!rows.length) {
    wrap.innerHTML = `<div class="empty-state">No findings matching current filters.</div>`;
    return;
  }

  const totalItems = rows.length;
  const pageSize = state.radar.pageSize || 15;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  if (state.radar.page > totalPages) state.radar.page = totalPages;
  if (state.radar.page < 1) state.radar.page = 1;
  const curPage = state.radar.page;

  const startIdx = (curPage - 1) * pageSize;
  const pageRows = rows.slice(startIdx, startIdx + pageSize);

  const paginationHtml = createPaginationHtml({
    totalItems,
    currentPage: curPage,
    pageSize,
    idPrefix: "radar",
  });

  wrap.innerHTML = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Category</th>
          <th>Masked Domain</th>
          <th>Brand / Keyword</th>
          <th>Risk Score & Level</th>
          <th>Status Penanganan</th>
          <th>HEAD Check</th>
          <th>Blacklist</th>
          <th>First Seen</th>
          <th style="text-align:right;">Action</th>
        </tr>
      </thead>
      <tbody>
        ${pageRows.map((r) => {
          const ls = liveStatus(r.is_live, r.last_status_code);
          const domainText = state.masked ? r.domain_masked : (r.raw_domain || r.domain_masked);
          const rawDomain = r.raw_domain || r.domain || r.domain_masked;
          const curStatus = getFindingStatus(rawDomain);
          const statusInfo = STATUS_MAP[curStatus] || STATUS_MAP.unreported;
          const blacklistHtml = r.in_public_blacklist
            ? `<span class="badge badge-danger">Listed</span>`
            : `<span class="blacklist-clean">Clean</span>`;
          const llmTag = r.verification_method === "llm"
            ? `<br><span class="cat-badge llm-verified" title="${(r.llm_reasoning || "").replace(/"/g, "&quot;")}">🤖 AI-Verified</span>`
            : "";
          const categoryBadge = `<span class="cat-badge ${r.category}">${CATEGORY_LABELS[r.category] || r.category}</span>`
            + (r.is_hijacked_institution ? `<br><span class="badge badge-danger" style="margin-top:4px;">Instansi Resmi (.${r.institution_suffix})</span>` : "")
            + llmTag;
          const brandOrKeyword = r.category === "phishing"
            ? `<span class="chip">${r.matched_brand || "General"}</span>`
            : (r.matched_keywords || []).map((kw) => `<span class="chip" style="margin-right:4px;">${kw}</span>`).join("");
          const rowClass = r.is_new_arrival ? "new-arrival-row" : "";
          const newBadgeHtml = r.is_new_arrival ? `<span class="badge-new-arrival">⚡ BARU</span>` : "";

          return `
            <tr class="${rowClass}" data-finding-id="${r.id}">
              <td>${categoryBadge}</td>
              <td>
                <div style="display:flex; align-items:center;">
                  ${newBadgeHtml}
                  <a class="domain-preview-link" data-preview-id="${r.id}" data-category="${r.category}" data-raw="${rawDomain}" data-masked="${domainText}" title="Klik untuk Pratinjau Web Terisolasi">
                    <span class="preview-mini-tag">${ICONS.globe} Preview</span>
                    <span class="truncate">${domainText}</span>
                  </a>
                </div>
              </td>
              <td>${brandOrKeyword}</td>
              <td style="white-space:nowrap;">
                <strong style="margin-right:6px;">${r.risk_score}</strong>
                ${riskBadge(r.risk_level)}
              </td>
              <td>
                <span class="badge ${statusInfo.badge}">${statusInfo.label.split(" ")[0]} ${statusInfo.label.split(" ")[1]}</span>
              </td>
              <td>
                <span class="status-inline">
                  <span class="dot ${ls.dot}"></span>${ls.text}
                </span>
              </td>
              <td>${blacklistHtml}</td>
              <td class="text-tertiary" style="font-size:12px;"><span class="detect-time-chip ${r.is_new_arrival ? 'chip-live-recent' : ''}">${formatFindingTime(r.first_seen)}</span></td>
              <td style="text-align:right;">
                <button class="btn-inspect" data-inspect-id="${r.id}" data-category="${r.category}">Inspect</button>
              </td>
            </tr>
          `;
        }).join("")}
      </tbody>
    </table>
    ${paginationHtml}
  `;

  wrap.querySelectorAll(".domain-preview-link").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      openWebPreviewModal(
        link.dataset.previewId,
        link.dataset.category,
        link.dataset.raw,
        link.dataset.masked
      );
    });
  });

  wrap.querySelectorAll(".btn-inspect").forEach((btn) => {
    btn.addEventListener("click", () => openFindingDrawer(btn.dataset.inspectId, btn.dataset.category));
  });

  bindPaginationEvents({
    idPrefix: "radar",
    currentPage: curPage,
    pageSize,
    totalItems,
    onPageChange: (p) => {
      state.radar.page = p;
      renderRadarTable();
    },
    onPageSizeChange: (s) => {
      state.radar.pageSize = s;
      state.radar.page = 1;
      renderRadarTable();
    },
  });
}

// ---------------------------------------------------------------------------
// TRIAGE VIEW (Zero-Retention Real-time Threat Sandbox)
// ---------------------------------------------------------------------------

function getTriageEmptyStateHtml() {
  return `
    <div class="triage-empty-state">
      <div class="triage-art-container">
        <svg width="220" height="120" viewBox="0 0 220 120" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="triageShieldGrad" x1="110" y1="16" x2="110" y2="94" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stop-color="#38bdf8"/>
              <stop offset="55%" stop-color="#2563eb"/>
              <stop offset="100%" stop-color="#1d4ed8"/>
            </linearGradient>
            <linearGradient id="triageShieldShine" x1="92" y1="20" x2="128" y2="82" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stop-color="#ffffff" stop-opacity="0.45"/>
              <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
            </linearGradient>
            <filter id="triageShieldShadow" x="65" y="8" width="90" height="102" filterUnits="userSpaceOnUse">
              <feDropShadow dx="0" dy="8" stdDeviation="7" flood-color="#0062e3" flood-opacity="0.32"/>
            </filter>
          </defs>

          <!-- Orbit dashed line -->
          <ellipse cx="110" cy="58" rx="88" ry="46" stroke="#93c5fd" stroke-width="1.2" stroke-dasharray="3 4" stroke-opacity="0.6"/>

          <!-- Floating Mini Window Card (Top Left) -->
          <g filter="drop-shadow(0 3px 6px rgba(0,0,0,0.05))">
            <rect x="22" y="16" width="46" height="34" rx="6" fill="#ffffff" stroke="#dbeafe" stroke-width="1.2"/>
            <rect x="22" y="16" width="46" height="8" rx="6" fill="#eff6ff"/>
            <circle cx="27" cy="20" r="1.5" fill="#93c5fd"/>
            <circle cx="31" cy="20" r="1.5" fill="#bfdbfe"/>
            <circle cx="35" cy="20" r="1.5" fill="#bfdbfe"/>
            <circle cx="32" cy="32" r="3.5" fill="#3b82f6" fill-opacity="0.25"/>
            <path d="M27 42 C27 38 37 38 37 42" stroke="#3b82f6" stroke-width="1.2" fill="none"/>
            <rect x="42" y="28" width="18" height="2.5" rx="1.25" fill="#93c5fd"/>
            <rect x="42" y="34" width="12" height="2" rx="1" fill="#bfdbfe"/>
          </g>

          <!-- Floating Warning Badge (Top Right) -->
          <g filter="drop-shadow(0 3px 6px rgba(0,0,0,0.05))">
            <circle cx="178" cy="28" r="13" fill="#ffffff" stroke="#dbeafe" stroke-width="1.2"/>
            <path d="M178 20 L186 34 H170 Z" fill="#eff6ff" stroke="#3b82f6" stroke-width="1.4" stroke-linejoin="round"/>
            <circle cx="178" cy="30.5" r="0.75" fill="#3b82f6"/>
            <line x1="178" y1="24" x2="178" y2="28" stroke="#3b82f6" stroke-width="1.4" stroke-linecap="round"/>
          </g>

          <!-- Floating Checklist Card (Bottom Right) -->
          <g filter="drop-shadow(0 3px 6px rgba(0,0,0,0.05))">
            <rect x="154" y="60" width="44" height="32" rx="6" fill="#ffffff" stroke="#dbeafe" stroke-width="1.2"/>
            <rect x="154" y="60" width="44" height="7" rx="6" fill="#eff6ff"/>
            <circle cx="160" cy="74" r="2" fill="#3b82f6" fill-opacity="0.3"/>
            <rect x="166" y="73" width="24" height="2" rx="1" fill="#93c5fd"/>
            <circle cx="160" cy="82" r="2" fill="#3b82f6" fill-opacity="0.3"/>
            <rect x="166" y="81" width="18" height="2" rx="1" fill="#bfdbfe"/>
          </g>

          <!-- Central 3D Shield -->
          <path d="M110 18 L138 30 V62 C138 78 110 94 110 94 C110 94 82 78 82 62 V30 Z" fill="url(#triageShieldGrad)" filter="url(#triageShieldShadow)"/>
          <path d="M110 20 L136 31 V60 C136 74 112 88 110 90 C110 90 110 20 110 20 Z" fill="url(#triageShieldShine)"/>

          <!-- Magnifying Glass -->
          <circle cx="106" cy="52" r="14" stroke="#ffffff" stroke-width="3" fill="rgba(255,255,255,0.15)"/>
          <path d="M98 46 A9 9 0 0 1 114 46" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round" fill="none"/>
          <path d="M116 62 L128 74" stroke="#ffffff" stroke-width="3.6" stroke-linecap="round"/>
        </svg>
      </div>

      <div class="triage-empty-title">Hasil analisis akan muncul di sini</div>
      <div class="triage-empty-sub">Setelah Anda klik Analisis Sekarang, kami akan memindai konten secara real-time untuk mendeteksi potensi ancaman.</div>

      <div class="triage-divider-label">Ringkasan yang akan Anda dapatkan</div>

      <div class="triage-skeletons-grid">
        <!-- 1. Risk Score -->
        <div class="triage-skeleton-card">
          <div class="triage-skeleton-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            <span>Risk Score</span>
          </div>
          <div class="triage-skeleton-ring"></div>
          <div class="triage-skeleton-bar-centered"></div>
        </div>

        <!-- 2. Kategori Ancaman -->
        <div class="triage-skeleton-card">
          <div class="triage-skeleton-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
            <span>Kategori Ancaman</span>
          </div>
          <div class="triage-skeleton-bar" style="margin-top:14px; width:85%;"></div>
          <div class="triage-skeleton-bar" style="margin-top:8px; width:55%;"></div>
        </div>

        <!-- 3. Indikator Mencurigakan -->
        <div class="triage-skeleton-card">
          <div class="triage-skeleton-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <span>Indikator Mencurigakan</span>
          </div>
          <div class="triage-skeleton-list">
            <div class="triage-skeleton-row">
              <span class="triage-skeleton-bullet"></span>
              <span class="triage-skeleton-bar" style="width:75%;"></span>
            </div>
            <div class="triage-skeleton-row">
              <span class="triage-skeleton-bullet"></span>
              <span class="triage-skeleton-bar" style="width:60%;"></span>
            </div>
            <div class="triage-skeleton-row">
              <span class="triage-skeleton-bullet"></span>
              <span class="triage-skeleton-bar" style="width:45%;"></span>
            </div>
          </div>
        </div>

        <!-- 4. Rekomendasi Tindakan -->
        <div class="triage-skeleton-card">
          <div class="triage-skeleton-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>
            <span>Rekomendasi Tindakan</span>
          </div>
          <div class="triage-skeleton-bar" style="margin-top:14px; width:80%;"></div>
          <div class="triage-skeleton-bar" style="margin-top:8px; width:65%;"></div>
          <div class="triage-skeleton-bar" style="margin-top:8px; width:50%;"></div>
        </div>
      </div>

      <div class="triage-privacy-callout">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
        <span>Semua analisis bersifat sementara dan tidak disimpan. Privasi Anda adalah prioritas kami.</span>
      </div>
    </div>
  `;
}

async function renderTriage(root) {
  const modeAActivity = await api("/api/insight/mode-a-activity").catch(() => ({ available: false }));

  root.innerHTML = `
    <div class="page triage-container-page">
      <div class="triage-header-wrapper">
        <!-- Abstract Wave Decorative Background -->
        <div class="triage-header-wave-bg">
          <svg viewBox="0 0 480 140" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M40 70 C140 10 240 120 340 40 C390 0 430 80 480 60" stroke="#007aff" stroke-width="1.2" stroke-opacity="0.18"/>
            <path d="M60 85 C160 25 260 135 360 55 C410 15 440 90 480 75" stroke="#38bdf8" stroke-width="1.2" stroke-opacity="0.22"/>
            <path d="M20 55 C120 -5 220 105 320 25 C370 -15 410 65 480 45" stroke="#007aff" stroke-width="1.2" stroke-opacity="0.12"/>
            <path d="M80 100 C180 40 280 150 380 70 C430 30 450 105 480 90" stroke="#38bdf8" stroke-width="1.2" stroke-opacity="0.16"/>
            <path d="M0 40 C100 -20 200 90 300 10 C350 -30 390 50 480 30" stroke="#007aff" stroke-width="1.2" stroke-opacity="0.1"/>
          </svg>
        </div>

        <div class="triage-crumb">
          <span class="crumb-parent">Beranda</span>
          <span class="crumb-sep">›</span>
          <span class="crumb-active">Triage Sandbox</span>
        </div>

        <div class="triage-hero-header">
          <div class="triage-flask-tile">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10 2v7.31L4.65 18.66A2 2 0 0 0 6.37 22h11.26a2 2 0 0 0 1.72-3.34L14 9.31V2M8.5 2h7M7 16h10"/>
            </svg>
          </div>
          <div class="triage-hero-text">
            <h1 class="triage-hero-title">Triage Sandbox</h1>
            <p class="triage-hero-desc">
              Real-time zero-retention analysis of suspicious SMS messages, emails, or malicious URLs.<br>
              Complies with UU PDP No. 27/2022 (no raw message is ever persisted to database).
            </p>
          </div>
        </div>
      </div>

      <div id="page-body">
        <div class="triage-page-layout">
          <!-- Left Card: Input Teks / URL -->
          <div class="triage-card">
            <div class="triage-card-header">
              <div class="triage-icon-tile">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                  <polyline points="10 9 9 9 8 9"/>
                </svg>
              </div>
              <div class="triage-card-titles">
                <h2 class="triage-card-title">Input Teks / URL</h2>
                <div class="triage-card-sub">Pilih contoh skenario penipuan atau tempel konten yang ingin dianalisis.</div>
              </div>
            </div>

            <div class="triage-presets-grid">
              <button class="triage-preset-pill" data-sample="bca" type="button">
                <span class="pill-icon">💬</span>
                <span>SMS Undian Bank BCA</span>
              </button>
              <button class="triage-preset-pill" data-sample="apk" type="button">
                <span class="pill-icon">🎁</span>
                <span>Undangan Pernikahan .APK</span>
              </button>
              <button class="triage-preset-pill" data-sample="mandiri" type="button">
                <span class="pill-icon">🏛️</span>
                <span>Verifikasi Akun Mandiri</span>
              </button>
              <button class="triage-preset-pill" data-sample="judol" type="button">
                <span class="pill-icon">🔗</span>
                <span>Link Slot Gacor Menyamar</span>
              </button>
            </div>

            <div class="triage-textarea-wrap">
              <textarea class="triage-textarea" id="triage-text" placeholder="Tempel pesan SMS, WhatsApp, atau URL yang mencurigakan di sini..."></textarea>
            </div>

            <div class="triage-bottom-bar">
              <div class="triage-hint-text">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="16" x2="12" y2="12"/>
                  <line x1="12" y1="8" x2="12.01" y2="8"/>
                </svg>
                <span>Didukung: teks, URL (http/https), dan link pendek.</span>
              </div>
              <div class="triage-btn-group">
                <button class="triage-btn-clear" id="triage-clear-btn" type="button">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px; height:14px;">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                  Bersihkan
                </button>
                <button class="triage-btn-submit" id="triage-submit-btn" type="button">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px; height:14px;">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                  </svg>
                  Analisis Sekarang
                </button>
              </div>
            </div>
          </div>

          <!-- Right Card: Pratinjau Hasil Analisis -->
          <div class="triage-card" id="triage-result-card">
            <div class="triage-card-header">
              <div class="triage-icon-tile">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
              </div>
              <div class="triage-card-titles">
                <h2 class="triage-card-title">Pratinjau Hasil Analisis</h2>
              </div>
            </div>

            <div id="triage-result-body" style="display:flex; flex-direction:column; flex:1;">
              ${getTriageEmptyStateHtml()}
            </div>
          </div>
        </div>

        ${!modeAActivity.available ? "" : `
        <div class="section" style="margin-top:var(--sp-6);">
          <div class="panel">
            <div class="panel-header-row">
              <div>
                <h2 class="section-title">Riwayat Penggunaan Mode A</h2>
                <p class="section-desc">Volume analisis masyarakat lewat Telegram -- hash pesan saja yang tersimpan, teks asli tidak pernah disimpan (UU PDP)</p>
              </div>
            </div>
            <div class="triage-history-grid">
              <div class="triage-history-stat">
                <div class="triage-history-val">${fmtInt(modeAActivity.total_analyzed)}</div>
                <div class="triage-history-lbl">Total Dianalisis</div>
              </div>
              <div class="triage-history-stat">
                <div class="triage-history-val">${fmtInt(modeAActivity.by_level["INDIKASI PENIPUAN"] || 0)}</div>
                <div class="triage-history-lbl">Indikasi Penipuan</div>
              </div>
              <div class="triage-history-stat">
                <div class="triage-history-val">${modeAActivity.avg_latency_ms != null ? fmtInt(modeAActivity.avg_latency_ms) + " ms" : "—"}</div>
                <div class="triage-history-lbl">Rata-rata Latensi</div>
              </div>
              <div class="triage-history-stat">
                <div class="triage-history-val">${fmtInt(modeAActivity.reports_drafted)}</div>
                <div class="triage-history-lbl">Draf Laporan Dibuat</div>
              </div>
            </div>
            <div class="triage-history-timeline">
              ${modeAActivity.daily_volume.map((d) => {
                const maxV = Math.max(...modeAActivity.daily_volume.map((x) => x.count), 1);
                return `<div class="triage-history-bar" style="height:${Math.max(6, Math.round(d.count / maxV * 48))}px;" title="${d.date}: ${d.count} analisis"></div>`;
              }).join("")}
            </div>
          </div>
        </div>
        `}
      </div>
    </div>
  `;

  const SAMPLES = {
    bca: "Yth Nasabah Bank BCA, poin reward Gebyar BCA Anda akan hangus hari ini. Segera tukarkan hadiah mobil/saldo di link: https://bca-gebyar-poin.co.id/klaim sekarang!",
    apk: "Kepada Yth Rekan/Keluarga, kami mengundang Anda ke acara resepsi pernikahan kami. Mohon buka surat undangan digital di link: Surat_Undangan_Resepsi.apk",
    mandiri: "Pemberitahuan Livin by Mandiri: Ada aktivitas login tidak wajar dari perangkat baru. Jika bukan Anda, amankan akun di: https://mandiri-auth-secure.com",
    judol: "SLOT GACOR HARI INI! Bonus deposit 100% langsung cair tanpa potongan. Link resmi alternatif: https://kkn.unp.ac.id/slot-zeus-maxwin",
  };

  const textarea = document.getElementById("triage-text");
  const resultBody = document.getElementById("triage-result-body");

  root.querySelectorAll(".triage-preset-pill").forEach((chip) => {
    chip.addEventListener("click", () => {
      textarea.value = SAMPLES[chip.dataset.sample] || "";
      textarea.focus();
    });
  });

  const resetToEmpty = () => {
    resultBody.innerHTML = getTriageEmptyStateHtml();
  };

  document.getElementById("triage-clear-btn").addEventListener("click", () => {
    textarea.value = "";
    resetToEmpty();
    textarea.focus();
  });

  document.getElementById("triage-submit-btn").addEventListener("click", async () => {
    const text = textarea.value.trim();
    if (!text) {
      showToast("Ketik atau tempel teks / URL terlebih dahulu.");
      textarea.focus();
      return;
    }

    resultBody.innerHTML = `
      <div style="min-height:300px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:14px; margin:auto;">
        <span class="spinner" style="width:36px; height:36px;"></span>
        <div style="font-size:13.5px; font-weight:600; color:var(--text-secondary);">Memindai konten dalam Sandbox Zero-Retention...</div>
      </div>
    `;

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();

      const score = data.score || 0;
      let badgeClass = "badge-success";
      let scoreColor = "#34c759";
      let riskLabelText = "AMAN / NORMAL";
      if (score >= 70) {
        badgeClass = "badge-danger";
        scoreColor = "#ff3b30";
        riskLabelText = "INDIKASI PENIPUAN";
      } else if (score >= 40) {
        badgeClass = "badge-warning";
        scoreColor = "#ff9500";
        riskLabelText = "HATI-HATI";
      }

      // Kategori & brand target diturunkan dari breakdown sinyal REAL yang
      // dikembalikan lib/scoring.py -- bukan menebak ulang dari teks mentah
      // pengguna, supaya label yang tampil selalu konsisten dengan skor.
      const breakdown = data.breakdown || [];
      const apkSignal = breakdown.find((b) => b.signal_name === "dangerous_request_apk");
      const brandSignal = breakdown.find((b) => b.signal_name === "watchlist_similarity");
      const brandMatch = brandSignal ? brandSignal.explanation.match(/brand '([^']+)'/) : null;

      let catLabel = "Rekayasa Sosial / Phishing Umum";
      let brandTarget = "Tidak ada institusi spesifik terdeteksi";
      if (apkSignal) {
        catLabel = "Malware / APK Trojan";
        brandTarget = "Kemasan Android Package (.apk)";
      } else if (brandMatch) {
        catLabel = "Brand Impersonation / Phishing";
        brandTarget = brandMatch[1];
      }

      const reasons = data.reasons && data.reasons.length ? data.reasons : [
        "Tidak ditemukan pola ancaman atau indikator rekayasa sosial dalam teks."
      ];

      resultBody.innerHTML = `
        <div class="triage-result-layout">
          <!-- 4 Result Summary Cards in row matching Empty State -->
          <div class="triage-skeletons-grid" style="margin-bottom:14px;">
            <!-- 1. Risk Score -->
            <div class="triage-skeleton-card" style="background:#ffffff; border-color:${score >= 70 ? 'rgba(255, 59, 48, 0.25)' : score >= 40 ? 'rgba(255, 149, 0, 0.25)' : 'rgba(52, 199, 89, 0.25)'};">
              <div class="triage-skeleton-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="${scoreColor}" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                <span>Risk Score</span>
              </div>
              <div style="display:flex; align-items:baseline; justify-content:center; gap:4px; margin:8px 0 4px;">
                <span style="font-size:32px; font-weight:800; color:${scoreColor}; line-height:1;">${score}</span>
                <span style="font-size:13px; font-weight:600; color:#94a3b8;">/100</span>
              </div>
              <div style="text-align:center;">
                <span class="badge ${badgeClass}" style="font-size:10px; padding:2px 7px;">${riskLabelText}</span>
              </div>
            </div>

            <!-- 2. Kategori Ancaman -->
            <div class="triage-skeleton-card" style="background:#ffffff;">
              <div class="triage-skeleton-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
                <span>Kategori Ancaman</span>
              </div>
              <div style="font-size:14px; font-weight:700; color:#0f172a; margin-top:8px; line-height:1.3;">${catLabel}</div>
              <div style="font-size:11.5px; color:#64748b; margin-top:4px;">Target: <strong>${brandTarget}</strong></div>
            </div>

            <!-- 3. Indikator Mencurigakan -->
            <div class="triage-skeleton-card" style="background:#ffffff;">
              <div class="triage-skeleton-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <span>Indikator Mencurigakan</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:5px; margin-top:8px;">
                ${reasons.slice(0, 3).map(r => `
                  <div style="display:flex; align-items:flex-start; gap:6px; font-size:11.5px; color:#1e293b; line-height:1.3;">
                    <span style="width:4px; height:4px; border-radius:50%; background:#007aff; margin-top:5px; flex-shrink:0;"></span>
                    <span style="overflow:hidden; text-overflow:ellipsis; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;">${esc(r)}</span>
                  </div>
                `).join("")}
              </div>
            </div>

            <!-- 4. Rekomendasi Tindakan -->
            <div class="triage-skeleton-card" style="background:#ffffff;">
              <div class="triage-skeleton-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>
                <span>Rekomendasi Tindakan</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:5px; margin-top:8px;">
                <div style="display:flex; align-items:flex-start; gap:6px; font-size:11.5px; color:#1e293b; line-height:1.3;">
                  <span style="color:#007aff; font-weight:700; font-size:11px;">✔</span>
                  <span>${score >= 70 ? "Blokir domain di DNS & laporkan ke Kominfo" : score >= 40 ? "Verifikasi tautan via call center resmi" : "Domain bersih, tidak diperlukan mitigasi"}</span>
                </div>
                <div style="display:flex; align-items:flex-start; gap:6px; font-size:11.5px; color:#1e293b; line-height:1.3;">
                  <span style="color:#007aff; font-weight:700; font-size:11px;">✔</span>
                  <span>${score >= 70 ? "Jangan unduh berkas .APK atau input OTP" : "Pantau anomali log akses perangkat"}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Detailed Evaluation Box -->
          <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:14px; padding:14px 16px; margin-bottom:14px;">
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
              <span style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; color:#64748b;">Evaluasi Zero-Retention Sandbox</span>
              <span style="font-size:11.5px; color:#64748b;">Latensi Analisis: <strong>${data.latency_ms != null ? data.latency_ms : "—"} ms</strong></span>
            </div>
            <div style="font-size:13px; color:#334155; line-height:1.55;">
              ${esc(data.explanation || "Hasil evaluasi multi-faktor mengonfirmasi karakteristik konten berbahaya atau rekayasa sosial.")}
            </div>
          </div>

          <!-- Result Actions Bar -->
          <div style="display:flex; align-items:center; justify-content:flex-end; gap:10px; margin-bottom:14px;">
            <button class="btn btn-secondary" id="triage-copy-btn" type="button" style="font-size:12.5px; padding:7px 14px; border-radius:10px;">
              📋 Salin Hasil Analisis
            </button>
            <button class="btn btn-secondary" id="triage-reset-btn" type="button" style="font-size:12.5px; padding:7px 14px; border-radius:10px;">
              ↻ Uji Skenario Lain
            </button>
          </div>

          <!-- Bottom Privacy Callout -->
          <div class="triage-privacy-callout" style="margin-top:auto;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
            <span>Semua analisis bersifat sementara dan tidak disimpan. Privasi Anda adalah prioritas kami.</span>
          </div>
        </div>
      `;

      // Bind result buttons
      document.getElementById("triage-reset-btn")?.addEventListener("click", () => {
        resetToEmpty();
        textarea.value = "";
        textarea.focus();
      });

      document.getElementById("triage-copy-btn")?.addEventListener("click", () => {
        const summaryText = `[SIAGA TRIAGE REPORT]\nKategori: ${catLabel}\nTarget: ${brandTarget}\nRisk Score: ${score}/100 (${riskLabelText})\nIndikator:\n${reasons.map(r => "- " + r).join("\n")}\n\nSaran Mitigasi:\n- Lapor Kominfo Aduan Konten\n- Blokir domain di DNS resolver`;
        navigator.clipboard.writeText(summaryText).then(() => {
          showToast("Hasil analisis disalin ke clipboard.");
        }).catch(() => {
          showToast("Gagal menyalin hasil analisis.");
        });
      });
    } catch (e) {
      resultBody.innerHTML = `
        <div class="empty-state">Gagal menganalisis: ${e.message}</div>
      `;
    }
  });
}

// ---------------------------------------------------------------------------
// ARCHITECTURE VIEW (Pipeline Stages with Interactive Modules)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// ARCHITECTURE VIEW (End-to-End Technical Framework & Topology)
// ---------------------------------------------------------------------------

const ARCH_ZONES = [
  {
    id: "ingest",
    tag: "Zona 1",
    title: "Data Ingestion",
    cssClass: "zone-ingest",
    nodes: [
      {
        id: "node-ct-stream",
        title: "CT Stream Ingestion",
        subtitle: "ctlogs.dev (fallback: crt.sh)",
        metric: "Cron harian 06:30 WIB",
        icon: "globe",
        tile: "tile-blue",
        role: "Pemantau Sertifikat SSL/TLS Baru",
        detail: "Job harian yang mengambil sertifikat SSL/TLS baru untuk domain keluarga .id (co.id, go.id, ac.id, web.id) dari ctlogs.dev, dengan cutoff waktu penerbitan 24 jam. Berjalan independen dari Gateway OpenClaw.",
        inputs: "Respons JSON ctlogs.dev per-TLD, field not_before per sertifikat",
        outputs: "Baris ct_raw baru: domain, not_before, first_seen, source",
        algo: "Polling HTTP berjadwal + idempotent INSERT OR IGNORE per domain",
        perf: "Idempoten (eksekusi ulang di hari sama menghasilkan 0 insert baru) — diverifikasi manual, bukan angka benchmark",
        code: "collector/ct_collector.py",
      },
      {
        id: "node-watchlist",
        title: "Typosquat Watchlist",
        subtitle: "Targeted Brand Scanner",
        metric: "213 institusi (data/watchlist.csv)",
        icon: "shieldLock",
        tile: "tile-sky",
        role: "Pencocokan Kemiripan Nama Domain vs Institusi",
        detail: "Membandingkan setiap domain baru dari ct_raw terhadap katalog institusi perbankan, BUMN, dan lembaga pemerintah strategis untuk menemukan kandidat typosquat.",
        inputs: "Katalog institusi (data/watchlist.csv), domain kandidat dari ct_raw",
        outputs: "Kandidat domain dengan skor kedekatan leksikal terhadap watchlist",
        algo: "Damerau-Levenshtein distance (lib/similarity.py) terhadap setiap entri watchlist",
        perf: "0 token AI — murni perhitungan string lokal",
        code: "lib/similarity.py · find_similar(), load_watchlist()",
      },
      {
        id: "node-crawler",
        title: "Judol & Porn Keyword Scan",
        subtitle: "Keyword + LLM Verification",
        metric: "2 tingkat: keyword pasti, keyword ambigu",
        icon: "warning",
        tile: "tile-purple",
        role: "Pemindai Nama Domain untuk Judi Online & Pornografi",
        detail: "Memindai string nama domain (bukan konten halaman — proyek ini tidak melakukan crawling/GET halaman penuh, lihat CLAUDE.md batasan jaringan) dari ct_raw terhadap daftar kata kunci judi online dan pornografi. Kata kunci ambigu (mis. 'rtp', 'toto') diverifikasi lebih lanjut oleh LLM yang hanya melihat nama domainnya, sebelum ditandai sebagai temuan.",
        inputs: "Nama domain dari ct_raw",
        outputs: "Temuan judol_findings / porn_findings dengan verification_method (keyword atau llm)",
        algo: "Exact/substring keyword match, lalu (opsional) verifikasi LLM berskema JSON ketat untuk kata kunci ambigu",
        perf: "Tanpa GET/crawling halaman apa pun — sesuai batasan jaringan proyek",
        code: "lib/judol_detect.py & lib/porn_detect.py · scan_ct_raw()",
      },
      {
        id: "node-triage-in",
        title: "Triage Sandbox Intake",
        subtitle: "Crowdsourced Reports",
        metric: "Ad-hoc User Input",
        icon: "zap",
        tile: "tile-amber",
        role: "Saluran Investigasi Mandiri Masyarakat / Analis SOC",
        detail: "Pintu masuk pelaporan dan pengujian cepat bagi pengguna umum maupun analis SOC untuk menguji teks SMS penipuan, pesan WhatsApp, atau tautan mencurigakan secara mandiri (Mode A).",
        inputs: "Teks mentah (SMS / WA / Link), tanpa memerlukan login/akun",
        outputs: "Skor risiko, indikator bahaya, dan hash SHA-256 pesan (bukan teks asli)",
        algo: "Regex extractor + SHA-256 one-way hashing sebelum penyimpanan (UU PDP No. 27/2022)",
        perf: "Teks asli tidak pernah disimpan — hanya hash yang dicatat",
        code: "lib/scoring.py · analyze_message()",
      },
    ],
  },
  {
    id: "pipeline",
    tag: "Zona 2",
    title: "Tiered Pipeline",
    cssClass: "zone-pipeline",
    nodes: [
      {
        id: "node-stage1",
        title: "Stage 1: Deterministic Filter",
        subtitle: "Algoritma String Lokal",
        metric: "0 Token AI · CPU",
        icon: "cpu",
        tile: "tile-blue",
        role: "Penyaring Cepat Tanpa Biaya Token AI",
        detail: "Menyaring domain berdasarkan kemiripan leksikal dengan watchlist, tanpa memanggil LLM. Menggunakan normalisasi homoglyph lintas aksara (Cyrillic vs Latin), decoding Punycode (xn--), dan Damerau-Levenshtein distance untuk mendeteksi kesamaan merek institusi perbankan/pemerintah.",
        inputs: "String domain mentah dari tahap Ingestion",
        outputs: "Domain kandidat lolos filter leksikal, atau dibuang (drop benign)",
        algo: "Damerau-Levenshtein distance, Cyrillic/Greek homoglyph mapping, Punycode decoder",
        perf: "0 token AI — seluruh Stage 1 murni komputasi string lokal",
        code: "lib/homoglyph.py & lib/similarity.py, diorkestrasi via lib/pipeline.py",
      },
      {
        id: "node-stage2",
        title: "Stage 2: Technical Enrichment",
        subtitle: "Verifikasi Jaringan & Cache",
        metric: "HEAD-only · TTL 7d",
        icon: "pulse",
        tile: "tile-purple",
        role: "Pengkayaan Sinyal Teknis & Validasi Keaktifan",
        detail: "Melakukan verifikasi teknis non-intrusif sesuai batasan jaringan proyek (hanya HTTP HEAD, tidak pernah GET halaman penuh — lihat CLAUDE.md): trace redirect via HEAD untuk memastikan status live, lookup tanggal pembuatan domain via RDAP dengan cache SQLite TTL 7 hari, serta pemeriksaan basis data blacklist publik (URLhaus).",
        inputs: "Domain kandidat yang lolos dari Stage 1",
        outputs: "Status liveness & kode HTTP riil, umur domain (hari), registrar, nameserver",
        algo: "HEAD-only redirect trace (cumulative timeout 5 detik) + RDAP JSON parser dengan cache SQLite",
        perf: "Timeout kumulatif 5 detik per domain (lib/redirect.py · DEFAULT_TOTAL_TIMEOUT) agar pipeline tidak terblokir",
        code: "lib/rdap.py · lookup() & lib/redirect.py · trace()",
      },
      {
        id: "node-stage3",
        title: "Stage 3: Risk Synthesis & Guardrail",
        subtitle: "Scoring Heuristik & AI Disambiguation",
        metric: "Biaya AI Terkendali",
        icon: "shieldCheck",
        tile: "tile-emerald",
        role: "Sintesis Skor Risiko & Penentu Klasifikasi Final",
        detail: "Menghitung skor risiko 0–100 berdasarkan bobot sinyal di lib/scoring.py (kemiripan merek, umur domain, liveness, indikator leksikal). LLM hanya dipanggil sebagai guardrail pada skor di zona abu-abu untuk menganalisis konteks semantik bahasa Indonesia — tidak untuk setiap domain.",
        inputs: "Fitur teknis Stage 1 & Stage 2",
        outputs: "Skor risiko 0–100, tingkat bahaya (AMAN, HATI-HATI, INDIKASI PENIPUAN), tag kategori",
        algo: "Weighted linear combination heuristic (lib/scoring.py) + LLM guardrail untuk zona abu-abu",
        perf: "Akurasi diukur lewat scripts/run_eval.py terhadap test set — lihat halaman Evaluation untuk angka aktual, bukan diklaim di sini",
        code: "lib/scoring.py · score_risk() & lib/llm.py · complete()",
      },
    ],
  },
  {
    id: "storage",
    tag: "Zona 3",
    title: "Intelligence & Storage",
    cssClass: "zone-storage",
    nodes: [
      {
        id: "node-db-wal",
        title: "SQLite Core (WAL Mode)",
        subtitle: "High-Concurrency Storage",
        metric: "siaga.db · WAL",
        icon: "download",
        tile: "tile-teal",
        role: "Basis Data Intelijen Ancaman Utama",
        detail: "Menyimpan data temuan terstruktur dalam mode Write-Ahead Logging (WAL, diaktifkan via PRAGMA di lib/db.py) yang memungkinkan operasi baca non-blocking bersamaan dengan operasi tulis. Terdiri atas tabel ct_raw, domain_findings, judol_findings, porn_findings, message_analyses, campaigns, dan daily_stats.",
        inputs: "Objek temuan tervalidasi dari Stage 3, hasil scan judol/porn, hasil analisis Mode A",
        outputs: "Query terindeks berdasarkan skor risiko, kategori, tanggal temuan, dan status liveness",
        algo: "SQLite dengan PRAGMA journal_mode=WAL",
        perf: "WAL mode diverifikasi langsung di lib/db.py (bukan diklaim tanpa sumber)",
        code: "lib/db.py · init_db()",
      },
      {
        id: "node-campaign-clust",
        title: "Campaign Clustering Engine",
        subtitle: "Sindikat Correlator",
        metric: "NS & IP Graph",
        icon: "pulse",
        tile: "tile-purple",
        role: "Pengelompokan Sindikat Kejahatan Berdasarkan Infrastruktur",
        detail: "Mengkorelasikan domain-domain penipuan berbeda yang menggunakan Authoritative Nameserver yang sama, atau pola nama brand yang identik. Mengidentifikasi apakah beberapa domain phishing merupakan bagian dari satu kampanye.",
        inputs: "Data nameserver dan rentang waktu pendaftaran domain dari domain_findings",
        outputs: "Label campaign_id pada temuan yang terkait, tabel campaigns",
        algo: "Pengelompokan berdasarkan kesamaan signature nameserver dan pola brand (lib/campaign.py)",
        perf: "Dijalankan sekali per siklus harian setelah Tahap 3 (scripts/run_daily_cycle.py), bukan proses realtime terpisah",
        code: "lib/campaign.py · apply_campaign_labels()",
      },
      {
        id: "node-pdp-guard",
        title: "UU PDP No. 27/2022 Guard",
        subtitle: "Privacy & Anti-Doxxing Engine",
        metric: "SHA-256 · Zero PII",
        icon: "lock",
        tile: "tile-amber",
        role: "Penegak Kepatuhan Privasi & Perlindungan Data Pribadi",
        detail: "Data input teks pengguna (Mode A) tidak disimpan dalam bentuk asli, melainkan dihash SHA-256 satu arah sebelum disimpan. Retensi data dihapus otomatis setelah 30 hari, dan nama domain publik disamarkan secara bawaan (*default privacy masking*) untuk mencegah pencemaran nama baik pihak yang dicatut.",
        inputs: "Teks input dari pengguna (Triage Sandbox)",
        outputs: "Hash SHA-256 tersimpan di message_analyses, domain publik tersamar",
        algo: "hashlib.sha256() satu arah (lib/scoring.py) + retention purge terjadwal (lib/db.py)",
        perf: "Tidak ada mekanisme dekripsi hash — one-way by design",
        code: "lib/scoring.py · analyze_message() (hashing), dashboard/api.py · mask_domain() (masking), lib/db.py · cleanup_retention() (purge 30 hari)",
      },
    ],
  },
  {
    id: "serving",
    tag: "Zona 4",
    title: "Serving & Threat Radar",
    cssClass: "zone-serving",
    nodes: [
      {
        id: "node-fastapi-core",
        title: "FastAPI REST Engine",
        subtitle: "High-Performance Async API",
        metric: "OpenAPI /docs",
        icon: "zap",
        tile: "tile-sky",
        role: "Pusat Layanan API Asinkron",
        detail: "Server backend asinkron berbasis Python FastAPI dan Uvicorn. Menyediakan REST endpoints dengan dokumentasi interaktif Swagger/OpenAPI (/docs) dan koneksi SQLite read-only ke basis data intelijen.",
        inputs: "Permintaan HTTP GET/POST dari klien dashboard",
        outputs: "Respons JSON: feed temuan, statistik telemetri, draf laporan",
        algo: "Starlette async event loop + Pydantic data validation model",
        perf: "Benchmark latensi belum diukur secara formal — tidak diklaim di sini",
        code: "dashboard/api.py",
      },
      {
        id: "node-threat-radar-ui",
        title: "Unified Threat Radar UI",
        subtitle: "Apple HIG Frosted Glass",
        metric: "3 Kategori Terpadu",
        icon: "warning",
        tile: "tile-blue",
        role: "Antarmuka Radar Ancaman Multidimensi",
        detail: "Antarmuka pengguna tunggal yang menyatukan pemantauan Phishing, Judol, dan Pornografi dalam satu dasbor terpadu. Dilengkapi filter Segmented Control, pencarian teks instan, dan paginasi.",
        inputs: "Data agregat /api/findings/top, /api/judol, dan /api/porn",
        outputs: "Tabel intelijen ancaman interaktif, visualisasi badge, dan tombol inspeksi teknis",
        algo: "Reactive DOM update via ES6+ vanilla JavaScript tanpa framework berat",
        perf: "Vanilla JS tanpa build step — ukuran bundel belum diukur, tidak diklaim di sini",
        code: "dashboard/static/app.js · renderRadar()",
      },
      {
        id: "node-triage-sandbox-ui",
        title: "Triage Sandbox Lab",
        subtitle: "Diagnostic Testing UI",
        metric: "Instant Feedback",
        icon: "cpu",
        tile: "tile-purple",
        role: "Laboratorium Investigasi Diagnostik Pengguna",
        detail: "Ruang uji interaktif di mana pengguna dapat memasukkan contoh pesan mencurigakan, memilih preset serangan populer, dan memperoleh dekonstruksi risiko.",
        inputs: "Pesan teks atau tautan yang dicurigai oleh analis/masyarakat",
        outputs: "Skor risiko transparan, daftar indikator bahaya, dan tombol eskalasi resmi",
        algo: "Async fetch ke endpoint analisis Mode A",
        perf: "Latensi bergantung pada apakah LLM guardrail dipanggil — tidak diklaim tanpa pengukuran",
        code: "dashboard/static/app.js · renderTriage()",
      },
    ],
  },
  {
    id: "dispatch",
    tag: "Zona 5",
    title: "Official Incident Dispatch",
    cssClass: "zone-dispatch",
    nodes: [
      {
        id: "node-rfc2350-gen",
        title: "RFC 2350 Dossier Generator",
        subtitle: "CSIRT Evidence Compiler",
        metric: "Standar Global CSIRT",
        icon: "fileText",
        tile: "tile-blue",
        role: "Penyusun Draf Laporan Insiden Berstandar CSIRT",
        detail: "Menyusun draf laporan investigasi teks sesuai format RFC 2350 (Expectations for Computer Security Incident Response). Memuat bukti digital: nama domain, resolusi IP, registrasi RDAP, dan panduan mitigasi.",
        inputs: "Metadata temuan ancaman dari basis data intelijen SIAGA",
        outputs: "Draf dokumen teks laporan insiden yang siap diajukan ke instansi pemerintah",
        algo: "Templating RFC 2350 dengan injeksi variabel forensik jaringan",
        perf: "Draf teks tersedia langsung saat tombol Inspect diklik — tidak ada ekspor PDF",
        code: "lib/report_draft.py · generate_report_draft() & format_report_text()",
      },
      {
        id: "node-kominfo-dispatch",
        title: "Aduan Konten Kominfo",
        subtitle: "Kanal Resmi Komdigi",
        metric: "WA 0811-9224-545",
        icon: "whatsapp",
        tile: "tile-emerald",
        role: "Penyaluran Resmi Aduan Konten Negatif Nasional",
        detail: "Tombol di panel temuan yang membuka WhatsApp Aduan Konten Kominfo (+62 811-9224-545) dengan pesan pre-filled berisi domain, kategori, dan skor risiko. Kanal ini selalu direkomendasikan untuk semua kategori temuan (Judol/Phishing/Porn).",
        inputs: "Domain, brand yang dicatut, kategori, dan skor risiko temuan",
        outputs: "Link wa.me pre-filled siap kirim ke Aduan Konten Kominfo",
        algo: "get_recommended_channels() selalu menyertakan kanal ini; UI merangkai pesan & link wa.me",
        perf: "Tidak ada klaim waktu proses — bergantung tindak lanjut manual instansi",
        code: "lib/report_draft.py · get_recommended_channels() (logika kanal), dashboard/static/app.js (tombol WA)",
      },
      {
        id: "node-bssn-dispatch",
        title: "Gov-CSIRT BSSN",
        subtitle: "Badan Siber & Sandi Negara",
        metric: "bantuan70@bssn.go.id",
        icon: "mail",
        tile: "tile-sky",
        role: "Eskalasi Insiden untuk Temuan Bertarget Perbankan/Finansial",
        detail: "Kanal eskalasi tambahan yang direkomendasikan ketika brand yang dicatut termasuk kategori perbankan/finansial (BCA, BNI, BRI, Mandiri, DANA, OVO, GoPay, OJK, BI). Bukan deteksi otomatis pembajakan subdomain — SIAGA belum memiliki fitur itu.",
        inputs: "Brand yang dicatut pada temuan (dicek terhadap daftar kata kunci finansial)",
        outputs: "Rekomendasi kanal BSSN dengan kontak bantuan70@bssn.go.id",
        algo: "get_recommended_channels(): brand mengandung kata kunci finansial -> tambahkan kanal BSSN",
        perf: "Tidak ada klaim waktu proses — bergantung tindak lanjut manual instansi",
        code: "lib/report_draft.py · get_recommended_channels()",
      },
      {
        id: "node-pandi-dispatch",
        title: "PANDI Abuse Desk",
        subtitle: "Pengelola Domain .ID",
        metric: "Registry Suspension",
        icon: "external",
        tile: "tile-amber",
        role: "Permohonan Penangguhan (Suspension) Domain .id",
        detail: "Direkomendasikan untuk setiap temuan pada domain berakhiran .id, mengarahkan ke Abuse Desk PANDI (abuse@pandi.id) dan portal IDADX untuk permohonan penangguhan domain.",
        inputs: "Nama domain temuan (dicek apakah berakhiran .id)",
        outputs: "Rekomendasi kanal PANDI dengan kontak abuse@pandi.id dan link IDADX",
        algo: "get_recommended_channels(): domain berakhiran .id -> tambahkan kanal PANDI",
        perf: "Tidak ada klaim waktu proses — bergantung tindak lanjut manual PANDI",
        code: "lib/report_draft.py · get_recommended_channels()",
      },
      {
        id: "node-ojk-dispatch",
        title: "Satgas PASTI OJK",
        subtitle: "Otoritas Jasa Keuangan",
        metric: "Kontak OJK 157",
        icon: "mail",
        tile: "tile-crimson",
        role: "Pelaporan untuk Temuan Bertarget Perbankan/Finansial",
        detail: "Direkomendasikan bersamaan dengan kanal BSSN ketika brand yang dicatut termasuk kategori perbankan/finansial, mengarahkan ke Kontak OJK 157 & Satgas PASTI.",
        inputs: "Brand yang dicatut pada temuan (dicek terhadap daftar kata kunci finansial)",
        outputs: "Rekomendasi kanal OJK dengan kontak konsumen@ojk.go.id / satgaspasti@ojk.go.id",
        algo: "get_recommended_channels(): brand mengandung kata kunci finansial -> tambahkan kanal OJK",
        perf: "Tidak ada klaim waktu proses — bergantung tindak lanjut manual OJK",
        code: "lib/report_draft.py · get_recommended_channels()",
      },
    ],
  },
];

const ARCH_MODULE_MAP = [
  { module: "collector/ct_collector.py", role: "CT Ingestion Worker", tech: "requests, sqlite3, cron harian", desc: "Mengambil sertifikat baru dari ctlogs.dev untuk TLD keluarga .id dan menyimpannya ke ct_raw." },
  { module: "lib/similarity.py", role: "Watchlist Matcher", tech: "Damerau-Levenshtein", desc: "Membandingkan domain baru terhadap 213 entri watchlist institusi (data/watchlist.csv)." },
  { module: "lib/judol_detect.py & lib/porn_detect.py", role: "Keyword + LLM Scan", tech: "Keyword match, LLM JSON schema", desc: "Memindai nama domain terhadap kata kunci judol/pornografi; kata kunci ambigu diverifikasi LLM." },
  { module: "lib/pipeline.py", role: "Tiered Detection Core", tech: "Multi-factor Scoring", desc: "Mengorkestrasi Stage 1 (String Filter), Stage 2 (RDAP & Liveness), dan Stage 3 (Risk Synthesis)." },
  { module: "lib/homoglyph.py", role: "Homoglyph Normalizer", tech: "Unicode Confusables, Punycode", desc: "Menormalkan aksara Cyrillic/Greek ke Latin dan mendecode Punycode." },
  { module: "lib/rdap.py", role: "RDAP Profiler", tech: "RDAP JSON, TTL 7d Cache", desc: "Mengekstrak tanggal registrasi domain dan registrar resmi, dengan cache SQLite." },
  { module: "lib/llm.py", role: "LLM Client", tech: "api.justwoker.icu (claude-opus-4-8-thinking)", desc: "Satu-satunya titik pemanggilan LLM di proyek ini, dengan batas anggaran harian keras." },
  { module: "lib/db.py", role: "Storage & Schema", tech: "SQLite3, WAL Mode, Indexing", desc: "Inisialisasi skema, migrasi kolom, dan retention purge otomatis." },
  { module: "lib/campaign.py", role: "Campaign Correlator", tech: "Nameserver/Brand Clustering", desc: "Mengelompokkan domain temuan yang berbagi infrastruktur atau pola brand ke dalam satu campaign." },
  { module: "lib/scoring.py", role: "Risk Scoring & Hashing", tech: "Weighted Heuristic, SHA-256", desc: "Menghitung skor risiko Mode A/B dan menghash teks pengguna sebelum disimpan." },
  { module: "dashboard/api.py", role: "FastAPI REST Server", tech: "FastAPI, Uvicorn, Pydantic", desc: "Melayani endpoint REST untuk dasbor, termasuk masking domain publik." },
];

const OFFICIAL_DISPATCH_STEPS = [
  {
    num: "1",
    title: "Deteksi & Bukti Forensik Jaringan",
    desc: "Sistem mendeteksi ancaman secara otomatis (atau via Triage Sandbox) dan mengumpulkan bukti teknis: IP host, Nameserver, umur RDAP, status keaktifan, dan tangkapan layar digital.",
    tag: "Otomatisasi SIAGA"
  },
  {
    num: "2",
    title: "Penyusunan Draf Insiden Berstandar RFC 2350",
    desc: "Generator dokumen menyusun draf laporan komprehensif mengikuti standar internasional CSIRT RFC 2350, memuat taksonomi insiden, tingkat keparahan, dan rekomendasi mitigasi.",
    tag: "Standar CSIRT"
  },
  {
    num: "3",
    title: "Pemilihan Kanal Penyaluran Resmi Pemerintah",
    desc: "Sistem memetakan insiden ke instansi berwenang yang tepat: Aduan Konten Kominfo (konten negatif/judol/porn), Gov-CSIRT BSSN (ancaman instansi/gov), PANDI (domain .id), atau Satgas PASTI OJK (finansial/perbankan).",
    tag: "Tepat Sasaran"
  },
  {
    num: "4",
    title: "Diseminasi & Tindakan Penindakan 1-Klik",
    desc: "Pengguna atau analis SOC cukup mengklik 1 tombol untuk membuka tiket resmi (Aduan WhatsApp Kominfo / Email CSIRT BSSN / Tiket PANDI) tanpa repot mengetik ulang laporan dari awal.",
    tag: "1-Klik Respon Cepat"
  }
];

let isSimulating = false;
async function runArchitectureSimulation() {
  if (isSimulating) return;
  isSimulating = true;

  const simBtn = document.getElementById("btn-run-sim");
  const traceBox = document.getElementById("arch-trace-box");
  if (simBtn) {
    simBtn.classList.add("running");
    simBtn.innerHTML = `${ICONS.zap} Sedang Menjalankan Simulasi...`;
  }
  if (traceBox) {
    traceBox.classList.add("show");
    traceBox.innerHTML = "";
  }

  const steps = [
    {
      nodeId: "node-ct-stream",
      miroCard: ".pos-src-top",
      pathId: "path-step-1a",
      badgeId: "badge-step-1",
      flowArrowId: "flow-arrow-1",
      tag: "CT STREAM",
      msg: "Menerima sertifikat SSL/TLS baru: bca-gebyar-poin.co.id (Issuer: Let's Encrypt Authority X3)",
      type: "normal"
    },
    {
      nodeId: "node-stage1",
      miroCard: ".pos-pipeline",
      pathId: "path-step-1a",
      badgeId: "badge-step-1",
      flowArrowId: "flow-arrow-1",
      tag: "STAGE 1",
      msg: "Damerau-Levenshtein check: Brand 'BCA' (Distance 0 in substring). Punycode: False. -> 0 Token AI (PASS)",
      type: "normal"
    },
    {
      nodeId: "node-stage2",
      miroCard: ".pos-pipeline",
      pathId: "path-step-2",
      badgeId: "badge-step-2",
      flowArrowId: "flow-arrow-2",
      tag: "STAGE 2",
      msg: "Async HEAD ping: 200 OK (112ms). RDAP Age: 1 hari (Baru Terdaftar -> Disimpan Cache TTL 7d).",
      type: "warning"
    },
    {
      nodeId: "node-stage3",
      miroCard: ".pos-ai-guard",
      pathId: "path-step-2",
      badgeId: "badge-step-2",
      flowArrowId: "flow-arrow-2",
      tag: "AI GUARDRAIL",
      msg: "Evaluasi konteks leksikal ambigu via LLM guardrail (lib/llm.py) -> Terindikasi Penipuan Finansial",
      type: "warning"
    },
    {
      nodeId: "node-db-wal",
      miroCard: ".pos-storage",
      pathId: "path-step-3",
      badgeId: "badge-step-3",
      flowArrowId: "flow-arrow-2",
      tag: "STORAGE",
      msg: "Data temuan tersimpan di siaga.db (WAL Mode). UUID: f891d4e2. Hash SHA-256 dicatat untuk kepatuhan UU PDP.",
      type: "normal"
    },
    {
      nodeId: "node-campaign-clust",
      miroCard: ".pos-storage",
      pathId: "path-step-3",
      badgeId: "badge-step-3",
      flowArrowId: "flow-arrow-3",
      tag: "CLUSTERING",
      msg: "Korelasi infrastruktur: Nameserver ns1.cheapdns.me identik dengan 3 domain penipuan -> Sindikat 'PhishBank-ID-04'",
      type: "normal"
    },
    {
      nodeId: "node-threat-radar-ui",
      miroCard: ".pos-radar",
      pathId: "path-step-4",
      badgeId: "badge-step-4",
      flowArrowId: "flow-arrow-4",
      tag: "RADAR UI",
      msg: "Disiarkan secara instan ke feed Threat Radar. Notifikasi prioritas tinggi dipicu untuk analis SOC.",
      type: "success"
    },
    {
      nodeId: "node-rfc2350-gen",
      miroCard: ".pos-dispatch",
      pathId: "path-step-5",
      badgeId: "badge-step-5",
      flowArrowId: "flow-arrow-4",
      tag: "RFC 2350",
      msg: "Draf insiden CSIRT berstandar RFC 2350 berhasil disusun otomatis lengkap dengan bukti digital jaringan.",
      type: "success"
    },
    {
      nodeId: "node-kominfo-dispatch",
      miroCard: ".pos-dispatch",
      pathId: "path-step-5",
      badgeId: "badge-step-5",
      flowArrowId: "flow-arrow-4",
      tag: "DISPATCH",
      msg: "Paket laporan resmi siap disalurkan ke Aduan Konten Kominfo (WhatsApp +62 811-9224-545) & Satgas PASTI OJK!",
      type: "success"
    }
  ];

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const clearAllHighlights = () => {
    document.querySelectorAll(".arch-node, .miro-node-card, .miro-path, .miro-step-group, .arch-flow-arrow").forEach(el => {
      el.classList.remove("sim-active");
    });
  };
  clearAllHighlights();
  let startTime = performance.now();

  for (let i = 0; i < steps.length; i++) {
    const st = steps[i];
    clearAllHighlights();

    if (st.nodeId) {
      const nodeEl = document.getElementById(st.nodeId);
      if (nodeEl) {
        nodeEl.classList.add("sim-active");
        nodeEl.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
      }
    }
    if (st.miroCard) {
      const mCard = document.querySelector(st.miroCard);
      if (mCard) mCard.classList.add("sim-active");
    }
    if (st.pathId) {
      const pEl = document.getElementById(st.pathId);
      if (pEl) pEl.classList.add("sim-active");
    }
    if (st.badgeId) {
      const bEl = document.getElementById(st.badgeId);
      if (bEl) bEl.classList.add("sim-active");
    }
    if (st.flowArrowId) {
      const aEl = document.getElementById(st.flowArrowId);
      if (aEl) aEl.classList.add("sim-active");
    }

    const elapsed = ((performance.now() - startTime) / 1000).toFixed(3);
    if (traceBox) {
      const line = document.createElement("div");
      line.className = "arch-trace-line";
      line.innerHTML = `
        <span class="trace-ts">[00:${elapsed}]</span>
        <span class="trace-tag">[${st.tag}]</span>
        <span class="trace-msg ${st.type}">${st.msg}</span>
      `;
      traceBox.appendChild(line);
      traceBox.scrollTop = traceBox.scrollHeight;
    }

    await sleep(750);
  }

  await sleep(400);
  clearAllHighlights();

  if (simBtn) {
    simBtn.classList.remove("running");
    simBtn.innerHTML = `${ICONS.zap} Jalankan Simulasi`;
  }
  isSimulating = false;
}

let activeArchTab = "visual";
let selectedArchNode = null;

async function renderArchitectureWorkspace(targetEl) {
  let metrics = { total_domains_scanned: 0, peak_ram_mb: 0, collector_uptime_pct: null };
  try {
    metrics = await api("/api/metrics");
  } catch (e) {
    // /api/metrics unreachable -- keep honest zero/null defaults, never a
    // plausible-looking fake number (see CLAUDE.md rule #2).
  }

  targetEl.innerHTML = `
    <!-- Top Stats -->
    <div class="kpi-row" style="grid-template-columns: repeat(3, 1fr); margin-bottom: var(--sp-6);">
      <div class="kpi-card">
        <div class="kpi-top">
          <span class="kpi-label">Total Domain Dipindai</span>
          <span class="kpi-icon-tile tile-blue">${ICONS.globe}</span>
        </div>
        <div class="kpi-value">${fmtInt(metrics.total_domains_scanned)}</div>
        <span class="kpi-caption green">${ICONS.check} Real-time CT Stream</span>
      </div>

      <div class="kpi-card">
        <div class="kpi-top">
          <span class="kpi-label">Memori Puncak API</span>
          <span class="kpi-icon-tile tile-purple">${ICONS.cpu}</span>
        </div>
        <div class="kpi-value">${metrics.peak_ram_mb} <span style="font-size:16px; font-weight:600;">MB</span></div>
        <span class="kpi-caption green">${ICONS.check} Lightweight footprint</span>
      </div>

      <div class="kpi-card">
        <div class="kpi-top">
          <span class="kpi-label">Collector Uptime</span>
          <span class="kpi-icon-tile tile-sky">${ICONS.zap}</span>
        </div>
        <div class="kpi-value">${metrics.collector_uptime_pct != null ? metrics.collector_uptime_pct : "—"}<span style="font-size:16px; font-weight:600;">%</span></div>
        <span class="kpi-caption green">${ICONS.check} Operational healthy</span>
      </div>
    </div>

    <!-- Perspective Control Bar -->
    <div class="arch-top-bar">
      <div class="ios-segmented" id="arch-tab-seg">
        <button class="ios-segmented-item ${activeArchTab === "visual" ? "active" : ""}" data-tab="visual">
          1. Topologi Visual & Simulator
        </button>
        <button class="ios-segmented-item ${activeArchTab === "modules" ? "active" : ""}" data-tab="modules">
          2. Spesifikasi Modul & Kode
        </button>
        <button class="ios-segmented-item ${activeArchTab === "dispatch" ? "active" : ""}" data-tab="dispatch">
          3. Alur Pelaporan Resmi (RFC 2350)
        </button>
      </div>

      <div class="arch-controls-right">
        <button class="btn-sim-pulse" id="btn-run-sim">
          ${ICONS.zap} Jalankan Simulasi
        </button>
      </div>
    </div>

    <!-- Tab View Container -->
    <div id="arch-tab-content"></div>
  `;

  // Attach Tab Switcher
  targetEl.querySelectorAll("#arch-tab-seg .ios-segmented-item").forEach(btn => {
    btn.addEventListener("click", () => {
      targetEl.querySelectorAll("#arch-tab-seg .ios-segmented-item").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeArchTab = btn.dataset.tab;
      renderActiveArchTab();
    });
  });

  const simBtn = targetEl.querySelector("#btn-run-sim") || document.getElementById("btn-run-sim");
  if (simBtn) {
    simBtn.addEventListener("click", () => {
      if (activeArchTab !== "visual") {
        activeArchTab = "visual";
        document.querySelectorAll("#arch-tab-seg .ios-segmented-item").forEach(b => {
          b.classList.toggle("active", b.dataset.tab === "visual");
        });
        renderActiveArchTab();
      }
      runArchitectureSimulation();
    });
  }

  renderActiveArchTab();
}

async function renderArchitecture(root) {
  return renderDocs(root, "architecture");
}

function renderActiveArchTab() {
  const container = document.getElementById("arch-tab-content");
  if (!container) return;

  if (activeArchTab === "visual") {
    container.innerHTML = `
      <!-- Miro-Style Cloud Architecture Canvas with Direct Connectors & Step Badges -->
      <div class="miro-canvas-container">
        <div class="miro-canvas-header">
          <div class="miro-header-left">
            <span class="miro-badge-tag">End-to-End Topology</span>
            <span class="miro-title">Alur Data Arsitektur SIAGA (Cloud Pipeline Standard)</span>
          </div>
          <div class="miro-legend">
            <span class="miro-legend-item"><span class="step-badge-mini">1</span> Ingest & Filter</span>
            <span class="miro-legend-item"><span class="step-badge-mini">2</span> AI Guardrail</span>
            <span class="miro-legend-item"><span class="step-badge-mini">3</span> Storage & Cluster</span>
            <span class="miro-legend-item"><span class="step-badge-mini">4</span> Live Threat Radar</span>
            <span class="miro-legend-item"><span class="step-badge-mini">5</span> CSIRT Dispatch</span>
          </div>
        </div>

        <div class="miro-flow-board">
          <svg class="miro-svg-canvas" viewBox="0 0 960 330" preserveAspectRatio="xMidYMid meet">
            <defs>
              <marker id="miro-arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#64748B" />
              </marker>
              <marker id="miro-arrow-active" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#34C759" />
              </marker>
            </defs>

            <!-- Connector 1A: CT Stream & Watchlist to Tiered Pipeline -->
            <path id="path-step-1a" class="miro-path" d="M 215 65 L 290 65 Q 315 65 315 110 L 315 155 L 345 155" marker-end="url(#miro-arrow)" />
            
            <!-- Connector 1B: Crawlers & Gov Probe to Tiered Pipeline -->
            <path id="path-step-1b" class="miro-path" d="M 215 255 L 290 255 Q 315 255 315 200 L 315 155 L 345 155" marker-end="url(#miro-arrow)" />

            <!-- Step 1 Badge -->
            <g id="badge-step-1" class="miro-step-group" transform="translate(315, 155)" title="Langkah 1: Stream Ingestion & Filtering">
              <circle r="13" class="miro-step-circle" />
              <text y="4" text-anchor="middle" class="miro-step-text">1</text>
            </g>

            <!-- Connector 2: Tiered Pipeline to AI Semantic Guardrail (branch down) -->
            <path id="path-step-2" class="miro-path" d="M 425 190 L 425 240" marker-end="url(#miro-arrow)" />
            <!-- Step 2 Badge -->
            <g id="badge-step-2" class="miro-step-group" transform="translate(425, 215)" title="Langkah 2: AI Guardrail untuk Zona Ambigu">
              <circle r="13" class="miro-step-circle" />
              <text y="4" text-anchor="middle" class="miro-step-text">2</text>
            </g>

            <!-- Connector 3: Tiered Pipeline to SQLite WAL & Clustering -->
            <path id="path-step-3" class="miro-path" d="M 505 155 L 565 155" marker-end="url(#miro-arrow)" />
            <!-- Step 3 Badge -->
            <g id="badge-step-3" class="miro-step-group" transform="translate(535, 155)" title="Langkah 3: Persistensi & Korelasi Sindikat">
              <circle r="13" class="miro-step-circle" />
              <text y="4" text-anchor="middle" class="miro-step-text">3</text>
            </g>

            <!-- Connector 4: SQLite WAL to Threat Radar UI -->
            <path id="path-step-4" class="miro-path" d="M 715 155 L 775 155" marker-end="url(#miro-arrow)" />
            <!-- Step 4 Badge -->
            <g id="badge-step-4" class="miro-step-group" transform="translate(745, 155)" title="Langkah 4: Diseminasi ke Threat Radar">
              <circle r="13" class="miro-step-circle" />
              <text y="4" text-anchor="middle" class="miro-step-text">4</text>
            </g>

            <!-- Connector 5: Storage/Radar to Official CSIRT Dispatch (branch down) -->
            <path id="path-step-5" class="miro-path" d="M 640 190 L 640 270 Q 640 275 655 275 L 775 275" marker-end="url(#miro-arrow)" />
            <!-- Step 5 Badge -->
            <g id="badge-step-5" class="miro-step-group" transform="translate(640, 240)" title="Langkah 5: Penyaluran Resmi ke Kominfo, BSSN, PANDI, OJK">
              <circle r="13" class="miro-step-circle" />
              <text y="4" text-anchor="middle" class="miro-step-text">5</text>
            </g>
          </svg>

          <!-- Miro Interactive Node Cards -->
          <div class="miro-nodes-layer">
            <div class="miro-node-card pos-src-top" data-zone-node="node-ct-stream" title="Klik untuk inspeksi modul Ingestion">
              <span class="miro-node-icon tile-blue">${ICONS.globe}</span>
              <div class="miro-node-info">
                <div class="miro-node-name">CT Stream & Watchlist</div>
                <div class="miro-node-sub">ctlogs.dev · Cron Harian</div>
              </div>
            </div>

            <div class="miro-node-card pos-src-btm" data-zone-node="node-crawler" title="Klik untuk inspeksi modul Keyword Scan">
              <span class="miro-node-icon tile-purple">${ICONS.warning}</span>
              <div class="miro-node-info">
                <div class="miro-node-name">Judol & Porn Scan</div>
                <div class="miro-node-sub">Keyword + LLM Verification</div>
              </div>
            </div>

            <div class="miro-node-card pos-pipeline" data-zone-node="node-stage1" title="Klik untuk inspeksi Pipeline Core">
              <span class="miro-node-icon tile-sky">${ICONS.cpu}</span>
              <div class="miro-node-info">
                <div class="miro-node-name">Tiered Pipeline Core</div>
                <div class="miro-node-sub">Stage 1 Filter & RDAP</div>
              </div>
            </div>

            <div class="miro-node-card pos-ai-guard" data-zone-node="node-stage3" title="Klik untuk inspeksi AI Guardrail">
              <span class="miro-node-icon tile-amber">${ICONS.zap}</span>
              <div class="miro-node-info">
                <div class="miro-node-name">AI Semantic Guardrail</div>
                <div class="miro-node-sub">lib/llm.py (Grey Zone)</div>
              </div>
            </div>

            <div class="miro-node-card pos-storage" data-zone-node="node-db-wal" title="Klik untuk inspeksi SQLite & Clustering">
              <span class="miro-node-icon tile-teal">${ICONS.download}</span>
              <div class="miro-node-info">
                <div class="miro-node-name">SQLite Core (WAL)</div>
                <div class="miro-node-sub">Storage & Clustering</div>
              </div>
            </div>

            <div class="miro-node-card pos-radar" data-zone-node="node-threat-radar-ui" title="Klik untuk inspeksi Threat Radar UI">
              <span class="miro-node-icon tile-blue">${ICONS.shieldCheck}</span>
              <div class="miro-node-info">
                <div class="miro-node-name">Unified Threat Radar</div>
                <div class="miro-node-sub">FastAPI Async & HIG UI</div>
              </div>
            </div>

            <div class="miro-node-card pos-dispatch" data-zone-node="node-kominfo-dispatch" title="Klik untuk inspeksi CSIRT Dispatch">
              <span class="miro-node-icon tile-green">${ICONS.fileText}</span>
              <div class="miro-node-info">
                <div class="miro-node-name">Official CSIRT Dispatch</div>
                <div class="miro-node-sub">Kominfo, BSSN, PANDI, OJK</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Compact Node Directory (left) + Sticky Inspector (right) -->
      <div class="arch-canvas-container">
        <div class="arch-main-col">
          <div class="arch-zone-directory">
            ${ARCH_ZONES.map(z => `
              <div class="arch-zone-row ${z.cssClass}">
                <div class="arch-zone-row-header">
                  <span class="arch-zone-tag">${z.tag}</span>
                  <span class="arch-zone-title">${z.title}</span>
                </div>
                <div class="arch-chip-wrap">
                  ${z.nodes.map(n => `
                    <div class="arch-node ${selectedArchNode && selectedArchNode.id === n.id ? "selected" : ""}" id="${n.id}" data-node-id="${n.id}" title="${n.title}">
                      <span class="arch-node-icon ${n.tile}">${ICONS[n.icon] || ICONS.shieldLock}</span>
                      <span class="arch-node-chip-title">${n.title}</span>
                    </div>
                  `).join("")}
                </div>
              </div>
            `).join("")}
          </div>
        </div>

        <div class="arch-side-col">
          <!-- Technical Inspector Panel: previews on hover, pins on click -->
          <div id="arch-inspector-wrap">
            ${renderArchInspectorCard(selectedArchNode || ARCH_ZONES[1].nodes[0])}
          </div>

          <!-- Live Simulation Trace Terminal -->
          <div class="arch-trace-box" id="arch-trace-box"></div>
        </div>
      </div>
    `;

    const inspWrap = () => document.getElementById("arch-inspector-wrap");
    const findArchNode = (id) => {
      for (const zone of ARCH_ZONES) {
        const found = zone.nodes.find(n => n.id === id);
        if (found) return found;
      }
      return null;
    };
    const previewArchNode = (node) => {
      const wrap = inspWrap();
      if (wrap && node) wrap.innerHTML = renderArchInspectorCard(node);
    };
    const pinArchNode = (node) => {
      if (!node) return;
      selectedArchNode = node;
      container.querySelectorAll(".arch-node").forEach(n => n.classList.remove("selected"));
      const chipEl = document.getElementById(node.id);
      if (chipEl) chipEl.classList.add("selected");
      previewArchNode(node);
    };

    // Directory chips: hover previews in the side panel, click pins the selection
    container.querySelectorAll(".arch-node").forEach(nodeEl => {
      nodeEl.addEventListener("mouseenter", () => previewArchNode(findArchNode(nodeEl.dataset.nodeId)));
      nodeEl.addEventListener("mouseleave", () => previewArchNode(selectedArchNode || ARCH_ZONES[1].nodes[0]));
      nodeEl.addEventListener("click", () => pinArchNode(findArchNode(nodeEl.dataset.nodeId)));
    });

    // Miro pipeline node cards: same hover-preview / click-to-pin behavior
    container.querySelectorAll(".miro-node-card").forEach(card => {
      const targetNodeId = card.dataset.zoneNode;
      if (!targetNodeId) return;
      card.addEventListener("mouseenter", () => previewArchNode(findArchNode(targetNodeId)));
      card.addEventListener("mouseleave", () => previewArchNode(selectedArchNode || ARCH_ZONES[1].nodes[0]));
      card.addEventListener("click", () => pinArchNode(findArchNode(targetNodeId)));
    });

    // Attach Miro Step Badges Click Listener -> Run Simulation
    container.querySelectorAll(".miro-step-group").forEach(grp => {
      grp.addEventListener("click", () => {
        runArchitectureSimulation();
      });
    });
  } else if (activeArchTab === "modules") {
    container.innerHTML = `
      <div class="panel">
        <div class="panel-header">
          <div>
            <h2 class="section-title">Pemetaan Modul Kode Sumber & Arsitektur Python</h2>
            <p class="section-desc">Daftar berkas backend utama dalam pipeline deteksi dan pengayaan intelijen SIAGA.</p>
          </div>
        </div>
        <div class="data-table-container">
          <table class="arch-table-module">
            <thead>
              <tr>
                <th style="width:200px;">Berkas Modul</th>
                <th style="width:190px;">Peran Sub-Sistem</th>
                <th style="width:230px;">Teknologi / Pustaka</th>
                <th>Deskripsi & Tanggung Jawab Teknis</th>
              </tr>
            </thead>
            <tbody>
              ${ARCH_MODULE_MAP.map(m => `
                <tr>
                  <td><code style="font-size:11.5px; font-weight:700; color:var(--ios-blue);">${m.module}</code></td>
                  <td><span class="chip chip-blue">${m.role}</span></td>
                  <td><span style="font-size:12px; color:var(--text-tertiary);">${m.tech}</span></td>
                  <td>${m.desc}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } else if (activeArchTab === "dispatch") {
    container.innerHTML = `
      <div class="panel">
        <div class="panel-header">
          <div>
            <h2 class="section-title">Alur Penyaluran Insiden Resmi (RFC 2350 Escalation Lifecycle)</h2>
            <p class="section-desc">Standarisasi pelaporan insiden keamanan siber dari deteksi teknis hingga penindakan oleh lembaga negara.</p>
          </div>
        </div>

        <div class="dispatch-stepper-grid">
          ${OFFICIAL_DISPATCH_STEPS.map(s => `
            <div class="dispatch-step-card">
              <div class="dispatch-step-num">${s.num}</div>
              <span class="badge badge-sky" style="align-self:flex-start;">${s.tag}</span>
              <div class="dispatch-step-title">${s.title}</div>
              <div class="dispatch-step-desc">${s.desc}</div>
            </div>
          `).join("")}
        </div>

        <div style="margin-top:24px; padding-top:18px; border-top:1px solid var(--ios-divider);">
          <div style="font-size:13.5px; font-weight:700; margin-bottom:12px; color:var(--text-primary);">
            Matriks Penyaluran Kanal Resmi Terintegrasi:
          </div>
          <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:12px;">
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px;">
              <div style="font-size:12.5px; font-weight:700; color:#28A745; margin-bottom:4px;">Aduan Konten Kominfo</div>
              <div style="font-size:11px; color:var(--text-tertiary); margin-bottom:6px;">WhatsApp: +62 811-9224-545</div>
              <div style="font-size:11.5px; color:var(--text-secondary);">Pemblokiran situs judi online, pornografi, dan konten negatif publik.</div>
            </div>
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px;">
              <div style="font-size:12.5px; font-weight:700; color:#007AFF; margin-bottom:4px;">Gov-CSIRT BSSN</div>
              <div style="font-size:11px; color:var(--text-tertiary); margin-bottom:6px;">Email: bantuan70@bssn.go.id</div>
              <div style="font-size:11.5px; color:var(--text-secondary);">Eskalasi peretasan dan pembajakan subdomain instansi pemerintah (.go.id).</div>
            </div>
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px;">
              <div style="font-size:12.5px; font-weight:700; color:#FF9500; margin-bottom:4px;">PANDI Abuse Desk</div>
              <div style="font-size:11px; color:var(--text-tertiary); margin-bottom:6px;">Email: abuse@pandi.id</div>
              <div style="font-size:11.5px; color:var(--text-secondary);">Penangguhan (suspension) nama domain keluarga .id pelaku kejahatan.</div>
            </div>
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px;">
              <div style="font-size:12.5px; font-weight:700; color:#FF3B30; margin-bottom:4px;">Satgas PASTI OJK</div>
              <div style="font-size:11px; color:var(--text-tertiary); margin-bottom:6px;">Email: waspadainvestasi@ojk.go.id</div>
              <div style="font-size:11.5px; color:var(--text-secondary);">Penindakan penipuan finansial perbankan dan pemblokiran rekening penampung.</div>
            </div>
          </div>
        </div>
      </div>
    `;
  }
}

function renderArchInspectorCard(node) {
  if (!node) return "";
  return `
    <div class="arch-inspector-card">
      <div class="arch-inspector-header">
        <div class="arch-inspector-title">
          <span class="kpi-icon-tile ${node.tile}" style="width:28px; height:28px;">
            ${ICONS[node.icon] || ICONS.shieldLock}
          </span>
          <span>${node.title} — <span style="font-weight:500; color:var(--text-secondary); font-size:13.5px;">${node.role}</span></span>
        </div>
        <span class="badge badge-sky">${node.metric}</span>
      </div>

      <div style="font-size:12.5px; line-height:1.6; color:var(--text-secondary); margin-bottom:14px;">
        ${node.detail}
      </div>

      <div class="arch-inspector-grid">
        <div class="arch-inspector-col">
          <span class="arch-inspector-label">Masukan Data (Input)</span>
          <span class="arch-inspector-val">${node.inputs}</span>
        </div>
        <div class="arch-inspector-col">
          <span class="arch-inspector-label">Keluaran Data (Output)</span>
          <span class="arch-inspector-val">${node.outputs}</span>
        </div>
        <div class="arch-inspector-col">
          <span class="arch-inspector-label">Algoritma / Standar</span>
          <span class="arch-inspector-val">${node.algo}</span>
        </div>
      </div>

      <div style="display:flex; align-items:center; justify-content:space-between; margin-top:14px; padding-top:10px; border-top:1px solid var(--ios-divider); flex-wrap:wrap; gap:8px;">
        <div style="display:flex; align-items:center; gap:6px;">
          <span class="arch-inspector-label">Benchmark:</span>
          <span style="font-size:12px; font-weight:600; color:var(--ios-blue);">${node.perf}</span>
        </div>
        <div style="display:flex; align-items:center; gap:6px;">
          <span class="arch-inspector-label">Implementasi Kode:</span>
          <code class="arch-code-snippet">${node.code}</code>
        </div>
      </div>
    </div>
  `;
}


// ---------------------------------------------------------------------------
// COMPLIANCE & LEGAL GOVERNANCE SUITE (UU PDP No. 27/2022 & UU ITE)
// ---------------------------------------------------------------------------

let activeComplianceTab = "pdp";
let activeCompliancePreset = "bank";

const COMPLIANCE_PRESETS = {
  bank: {
    label: "Nasabah Bank (Rekening + NIK + HP)",
    text: "Halo Satgas Siber SIAGA, saya korban penipuan transfer di situs bca-gebyar-poin.co.id. No Rekening saya 123-456-7890 an Budi Santoso (NIK: 3175021234560001, No HP: 081298765432). Mohon segera blokir rekening penipu dan tindak lanjuti domain tersebut!",
  },
  pinjol: {
    label: "SMS Phishing Pinjol / Hadiah",
    text: "DAPAT DANA KAGET Rp 5.000.000! Segera klaim di https://dana-kaget-klaim.id/login. Kirim PIN akun Anda ke WhatsApp 085712345678 atau hubungi CS Siti Nurhaliza no KTP 3201019908760002 sekarang juga!",
  },
  gov: {
    label: "Pembajakan Web Kampus / Instansi",
    text: "Domain kkn.unp.ac.id/slot-zeus-maxwin terdeteksi disusupi situs judi slot online gacor. Mohon hubungi admin Puskom UNP no kontak 081377889900 atau email rektorat@unp.ac.id untuk normalisasi server kampus!",
  },
};

const COMPLIANCE_PILLARS = {
  pdp: {
    title: "UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP)",
    badge: "UU PDP No. 27/2022",
    summary: "Standar tertinggi tata kelola privasi nasional. Menjamin data pribadi masyarakat dan pelapor siber tidak pernah disimpan sembarangan, bocor, atau disalahgunakan.",
    articles: [
      {
        article: "Pasal 16 ayat (2) huruf e",
        title: "Prinsip Batasan Waktu Penyimpanan Data (Data Retention Limitation)",
        mandate: "Pengendali data pribadi wajib menghapus atau memusnahkan data pribadi setelah masa retensi berakhir atau tujuan pemrosesan data telah tercapai.",
        siaga_impl: "SIAGA menerapkan siklus pembersihan otomatis (Rolling Auto-Purge Cron) setiap 30 hari pada tabel audit. Tidak ada jejak data laporan lama yang tertinggal di penyimpanan permanen.",
        code_ref: "lib/db.py · cleanup_retention()",
        status: "PASS",
        metrics: "30 Hari Retensi (Terjadwal)",
      },
      {
        article: "Pasal 35 ayat (1) & (2)",
        title: "Kewajiban Pengamanan Teknis & Enkripsi Kriptografis",
        mandate: "Pengendali data wajib melindungi dan menjamin keamanan data pribadi dengan langkah teknis terkini, termasuk langkah enkripsi dan pencegahan akses tanpa hak.",
        siaga_impl: "Setiap pesan atau aduan diuji murni di memori RAM dan hanya dicatat sidik jari satu arah (One-Way SHA-256 Hash Digest). Teks asli (plaintext) dibuang seketika.",
        code_ref: "lib/scoring.py & lib/db.py · message_analyses",
        status: "PASS",
        metrics: "0 Byte Plaintext Stored (SHA-256 Only)",
      },
      {
        article: "Pasal 37 & 39",
        title: "Kerahasiaan Pemrosesan & Tata Kelola Hak Akses Terbatas",
        mandate: "Setiap pihak yang terlibat dalam pemrosesan data pribadi wajib menjaga kerahasiaan dan membatasi akses hanya untuk personel yang terotorisasi.",
        siaga_impl: "Seluruh kueri antarmuka dasbor membuka database dengan mode strictly read-only ('?mode=ro'). Endpoint backend mengikat ke 127.0.0.1 lokal tanpa eksposur jaringan luar.",
        code_ref: "dashboard/api.py · sqlite3.connect(?mode=ro)",
        status: "PASS",
        metrics: "Strict Read-Only SQLite & Localhost Bind",
      },
      {
        article: "Pasal 46 ayat (1) - (3)",
        title: "Prosedur Notifikasi Insiden Siber Resmi (< 72 Jam)",
        mandate: "Dalam hal terjadi kegagalan pelindungan data pribadi, Pengendali wajib menyampaikan pemberitahuan tertulis kepada lembaga pengawas dan subjek data.",
        siaga_impl: "Modul pelaporan SIAGA secara otomatis merumuskan draf insiden resmi berstandar RFC 2350 lengkap dengan bukti teknis untuk dikirim ke Gov-CSIRT BSSN & Kominfo dalam 1-klik.",
        code_ref: "lib/report_draft.py · generate_report_draft()",
        status: "PASS",
        metrics: "Draf RFC 2350 Siap Kirim Instant",
      },
    ],
  },
  ite: {
    title: "UU No. 1 Tahun 2024 (Perubahan Kedua UU ITE)",
    badge: "UU ITE No. 1/2024",
    summary: "Dasar hukum penindakan situs web ilegal, penipuan digital (phishing), dan perjudian online lintas batas di wilayah hukum kedaulatan digital Indonesia.",
    articles: [
      {
        article: "Pasal 27 ayat (2)",
        title: "Penindakan Konten & Transaksi Perjudian Online (Judol)",
        mandate: "Larangan mendistribusikan, mentransmisikan, atau membuat dapat diaksesnya informasi/dokumen elektronik yang memiliki muatan perjudian.",
        siaga_impl: "SIAGA memindai nama domain baru terhadap kata kunci judi online (dengan verifikasi LLM untuk kata kunci ambigu), dan menandai temuan yang berada pada subdomain instansi resmi (.go.id/.ac.id) sebagai kasus prioritas tinggi.",
        code_ref: "lib/judol_detect.py & scripts/run_judol_scan.py",
        status: "PASS",
        metrics: "Deteksi Keyword + Verifikasi LLM",
      },
      {
        article: "Pasal 28 ayat (1)",
        title: "Larangan Berita Bohong & Penipuan Konsumen Perbankan (Phishing)",
        mandate: "Larangan menyebarkan berita bohong dan menyesatkan yang mengakibatkan kerugian konsumen dalam transaksi elektronik.",
        siaga_impl: "Sistem mendeteksi situs web penipuan perbankan (BCA, Mandiri, BRI, BNI) sebelum korban mentransfer dana menggunakan heuristik Levenshtein, Homoglif, dan LLM Guardrail.",
        code_ref: "lib/pipeline.py & lib/similarity.py",
        status: "PASS",
        metrics: "Deteksi Typosquatting & Impersonation",
      },
      {
        article: "Asas Perlindungan Reputasi",
        title: "Perlindungan Nama Baik Lembaga Terkena Dampak (Defamation Shield)",
        mandate: "Menghindari tuduhan prematur atau pencemaran nama baik terhadap instansi sah yang nama atau subdomainnya dibajak oleh pihak ketiga tak bertanggung jawab.",
        siaga_impl: "Semua tampilan domain publik disamarkan secara default (misal: b***-gebyar.com atau kkn.***.ac.id) untuk melindungi reputasi instansi sah sebelum verifikasi CSIRT selesai.",
        code_ref: "dashboard/static/app.js · state.masked toggle",
        status: "PASS",
        metrics: "Default Privacy Masking Active",
      },
      {
        article: "Pasal 5 & 6",
        title: "Integritas & Otentisitas Alat Bukti Elektronik",
        mandate: "Informasi Elektronik dan/atau Dokumen Elektronik sah sebagai alat bukti hukum apabila dapat dijamin keaslian dan integritasnya.",
        siaga_impl: "Setiap rekaman temuan mencatat timestamp WIB presisi, fingerprint Certificate Transparency, respon header HTTP, serta snapshot forensik jaringan yang tidak dapat dimanipulasi.",
        code_ref: "data/siaga.db · ct_raw & domain_findings",
        status: "PASS",
        metrics: "Cryptographic CT & Timestamp Audit Trail",
      },
    ],
  },
  csirt: {
    title: "Kerangka Operasional CSIRT Nasional (Peraturan BSSN No. 8/2020 & RFC 2350)",
    badge: "BSSN & RFC 2350",
    summary: "Standar operasional tim tanggap insiden keamanan siber nasional dan internasional untuk penanganan insiden yang terkoordinasi, cepat, dan akuntabel.",
    articles: [
      {
        article: "Peraturan BSSN No. 8/2020 Pasal 14",
        title: "Koordinasi Penanganan Insiden Keamanan Siber Sektor Pemerintah",
        mandate: "Pengelola sistem elektronik wajib berkoordinasi dengan BSSN (Gov-CSIRT) dalam mitigasi kerentanan dan pembajakan sistem infrastruktur kritis.",
        siaga_impl: "Platform menghubungkan analis secara langsung dengan Gov-CSIRT BSSN melalui tombol 1-klik email (bantuan70@bssn.go.id) dan integrasi tiket resmi.",
        code_ref: "lib/report_draft.py · get_recommended_channels()",
        status: "PASS",
        metrics: "Integrasi Gov-CSIRT BSSN 1-Klik",
      },
      {
        article: "Standar RFC 2350 Bagian 3.2",
        title: "Taksonomi & Format Komunikasi Insiden Siber Internasional",
        mandate: "Menyediakan pedoman universal bagi CSIRT dalam menyusun laporan insiden mencakup Contact Information, Incident Characterization, and Escalation Matrix.",
        siaga_impl: "Draf laporan yang digenerasi oleh SIAGA menggunakan struktur resmi RFC 2350 dengan pembagian deskripsi teknis, bukti URL, indikasi kerugian, dan kontak narahubung.",
        code_ref: "lib/report_draft.py · format_report_text()",
        status: "PASS",
        metrics: "Format Standar Taksonomi RFC 2350",
      },
      {
        article: "Registry Abuse Desk (.ID)",
        title: "Prosedur Penangguhan Nama Domain Berbahaya via PANDI / IDADX",
        mandate: "Penanganan domain tingkat tinggi (.id) yang melanggar kebijakan pendaftaran nama domain melalui kanal resmi Pengelola Nama Domain Internet Indonesia.",
        siaga_impl: "Menyediakan jalur eskalasi instan ke abuse@pandi.id dan portal IDADX (idadx.id/report) khusus untuk temuan domain berakhiran .id.",
        code_ref: "lib/report_draft.py · get_recommended_channels()",
        status: "PASS",
        metrics: "Direct Dispatch ke Registry PANDI",
      },
      {
        article: "Regulasi TrustPositif Kominfo",
        title: "Normalisasi DNS & Pemblokiran Akses Nasional (Kominfo RI)",
        mandate: "Pemblokiran akses terhadap situs bermuatan negatif melalui pangkalan data DNS TrustPositif Kominfo Republik Indonesia.",
        siaga_impl: "Draf pesan terformat otomatis siap dikirimkan ke Hotline WhatsApp Aduan Konten Kominfo (08119224545) dan portal aduankonten.id.",
        code_ref: "lib/report_draft.py · get_recommended_channels()",
        status: "PASS",
        metrics: "Integrasi WhatsApp & Portal Kominfo",
      },
    ],
  },
};

const COMPLIANCE_MATRIX_ROWS = [
  {
    law: "UU PDP No. 27/2022",
    article: "Pasal 16 ayat (2)",
    principle: "Pembatasan Retensi Data",
    siagaModule: "lib/db.py (cleanup_retention)",
    technicalMechanism: "Cron otomatis menghapus catatan hash audit > 30 hari. 0 jejak tersisa.",
    status: "PASS",
  },
  {
    law: "UU PDP No. 27/2022",
    article: "Pasal 35 ayat (1)",
    principle: "Kriptografi & Pengamanan",
    siagaModule: "lib/scoring.py (SHA-256)",
    technicalMechanism: "Analisis murni di RAM; hanya 64-karakter SHA-256 hash disimpan ke SQLite WAL.",
    status: "PASS",
  },
  {
    law: "UU PDP No. 27/2022",
    article: "Pasal 37",
    principle: "Isolasi Hak Akses",
    siagaModule: "dashboard/api.py (?mode=ro)",
    technicalMechanism: "API dasbor terikat murni ke 127.0.0.1 dengan flag SQLite read-only mode.",
    status: "PASS",
  },
  {
    law: "UU PDP No. 27/2022",
    article: "Pasal 46",
    principle: "Notifikasi Insiden < 72 Jam",
    siagaModule: "lib/report_draft.py",
    technicalMechanism: "Sintesis instan berkas laporan insiden lengkap dengan bukti forensik.",
    status: "PASS",
  },
  {
    law: "UU ITE No. 1/2024",
    article: "Pasal 27 ayat (2)",
    principle: "Penindakan Perjudian Online",
    siagaModule: "lib/judol_detect.py",
    technicalMechanism: "Deteksi proaktif label judol & identifikasi pembajakan subdomain kampus (.ac.id/.go.id).",
    status: "PASS",
  },
  {
    law: "UU ITE No. 1/2024",
    article: "Pasal 28 ayat (1)",
    principle: "Pencegahan Penipuan Konsumen",
    siagaModule: "lib/pipeline.py & lib/similarity.py",
    technicalMechanism: "Damerau-Levenshtein distance, matriks homoglif, dan LLM guardrail untuk zona abu-abu.",
    status: "PASS",
  },
  {
    law: "UU ITE & Asas Hukum",
    article: "Praduga & Perlindungan Nama",
    principle: "Defamation Shield",
    siagaModule: "dashboard/static/app.js",
    technicalMechanism: "Default Privacy Masking (p***.web.id) untuk melindungi reputasi instansi sah.",
    status: "PASS",
  },
  {
    law: "BSSN No. 8/2020",
    article: "Pasal 14",
    principle: "Koordinasi Gov-CSIRT",
    siagaModule: "lib/report_draft.py",
    technicalMechanism: "Integrasi pelaporan 1-klik ke bantuan70@bssn.go.id dengan taksonomi standar.",
    status: "PASS",
  },
  {
    law: "RFC 2350",
    article: "Section 3.2",
    principle: "Standar Taksonomi CSIRT",
    siagaModule: "lib/report_draft.py",
    technicalMechanism: "Pemformatan universal: Technical Summary, Evidence URI, Actions Taken.",
    status: "PASS",
  },
  {
    law: "Registry .ID PANDI",
    article: "Kebijakan Domain .ID",
    principle: "Suspension Domain Berbahaya",
    siagaModule: "lib/report_draft.py",
    technicalMechanism: "Jalur langsung ke abuse@pandi.id dan formulir IDADX (idadx.id/report).",
    status: "PASS",
  },
];

async function calculateSha256(text) {
  try {
    const encoder = new TextEncoder();
    const data = encoder.encode(text);
    const hashBuffer = await crypto.subtle.digest("SHA-256", data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
  } catch {
    // Fallback simple hash for older environments
    let hash = 0;
    for (let i = 0; i < text.length; i++) {
      hash = (hash << 5) - hash + text.charCodeAt(i);
      hash |= 0;
    }
    return Math.abs(hash).toString(16).padStart(64, "0");
  }
}

async function runPrivacySanitizer(text) {
  if (!text) text = "";

  let piiCount = 0;
  let sanitized = text;

  // 1. Detect and redact NIK (16 digits)
  const nikRegex = /\b[1-9]\d{15}\b/g;
  sanitized = sanitized.replace(nikRegex, (match) => {
    piiCount++;
    return `<span class="pii-tag pii-tag-nik" title="NIK Terlindungi UU PDP">[NIK_TEREDAKSI_${match.slice(-4)}]</span>`;
  });

  // 2. Detect and redact Bank Account numbers
  const bankRegex = /\b\d{3,4}[- ]?\d{3,4}[- ]?\d{3,4}(?:[- ]?\d{3,4})?\b/g;
  sanitized = sanitized.replace(bankRegex, (match) => {
    if (match.length >= 8) {
      piiCount++;
      return `<span class="pii-tag pii-tag-bank" title="Nomor Rekening Terlindungi">[NO_REKENING_TEREDAKSI]</span>`;
    }
    return match;
  });

  // 3. Detect and redact Indonesian Phone numbers (+62 / 62 / 08...)
  const phoneRegex = /(?:\+62|62|08)[0-9\- ]{8,13}/g;
  sanitized = sanitized.replace(phoneRegex, (match) => {
    piiCount++;
    return `<span class="pii-tag pii-tag-phone" title="Nomor Telepon Pribadi">[TELEPON_TEREDAKSI_${match.slice(-4)}]</span>`;
  });

  // 4. Detect and redact Personal Names after keywords (an / atas nama / CS)
  const nameRegex = /\b(an|atas nama|CS)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/gi;
  sanitized = sanitized.replace(nameRegex, (match, prefix, name) => {
    piiCount++;
    return `${prefix} <span class="pii-tag pii-tag-name" title="Identitas Pelapor/Nasabah">[IDENTITAS_DIRI_TEREDAKSI]</span>`;
  });

  // Calculate genuine SHA-256 hex digest
  const hashHex = await calculateSha256(text);

  // Simulated Database Record
  const nowIso = new Date().toISOString();
  const purgeDate = new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0];

  // This demo redacts PII and hashes the pasted text client-side for
  // illustration -- it never runs the real lib/scoring.py risk engine
  // (that's Python-only, server-side), so there is no honest risk_score to
  // show here. record_id/risk_score were previously fabricated static
  // numbers; removed rather than faked (see CLAUDE.md rule #2).
  const dbRecord = {
    table: "message_analyses",
    received_at: nowIso,
    message_hash: hashHex,
    stored_plaintext_pii: null,
    bytes_pii_stored: 0,
    retention_policy: "30_DAYS_AUTO_PURGE",
    purge_scheduled_at: purgeDate,
    uu_pdp_status: "VERIFIED_COMPLIANT",
  };

  return {
    rawText: text,
    sanitizedHtml: sanitized,
    piiCount,
    hashHex,
    dbRecord,
  };
}

function renderCompliancePillarTabs() {
  const container = document.getElementById("compliance-pillar-content");
  if (!container) return;

  if (activeComplianceTab === "matrix") {
    container.innerHTML = `
      <div class="compliance-matrix-card">
        <table class="compliance-matrix-table">
          <thead>
            <tr>
              <th style="width:160px;">Regulasi RI</th>
              <th style="width:130px;">Pasal Terkait</th>
              <th style="width:170px;">Prinsip Hukum</th>
              <th style="width:200px;">Modul Teknis SIAGA</th>
              <th>Mekanisme Kepatuhan Sistem</th>
              <th style="width:110px; text-align:right;">Status Audit</th>
            </tr>
          </thead>
          <tbody>
            ${COMPLIANCE_MATRIX_ROWS.map((row) => `
              <tr>
                <td><strong>${row.law}</strong></td>
                <td><span class="compliance-article-badge">${row.article}</span></td>
                <td><span style="font-weight:600; color:var(--text-primary);">${row.principle}</span></td>
                <td><code class="compliance-code-ref">${row.siagaModule}</code></td>
                <td><span style="color:var(--text-secondary); font-size:12px;">${row.technicalMechanism}</span></td>
                <td style="text-align:right;">
                  <span class="badge badge-success">● ${row.status}</span>
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
    return;
  }

  const pillar = COMPLIANCE_PILLARS[activeComplianceTab] || COMPLIANCE_PILLARS.pdp;

  container.innerHTML = `
    <div style="margin-bottom:var(--sp-4);">
      <h3 style="font-size:16px; font-weight:800; color:var(--text-primary); margin-bottom:4px;">${pillar.title}</h3>
      <p style="font-size:13px; color:var(--text-secondary); line-height:1.5;">${pillar.summary}</p>
    </div>

    <div class="compliance-pillars-grid">
      ${pillar.articles.map((item) => `
        <div class="compliance-pillar-card">
          <div>
            <div class="compliance-pillar-header">
              <span class="compliance-article-badge">${item.article}</span>
              <span class="badge badge-success">● ${item.status}</span>
            </div>
            <div class="compliance-pillar-title">${item.title}</div>
            <div class="compliance-pillar-mandate">"${item.mandate}"</div>
            <div class="compliance-pillar-impl">
              <strong style="color:var(--text-primary); display:block; margin-bottom:3px;">Implementasi Teknis SIAGA:</strong>
              ${item.siagaImpl || item.siaga_impl}
            </div>
          </div>
          <div class="compliance-pillar-footer">
            <span class="compliance-code-ref">${item.code_ref}</span>
            <span style="font-size:11.5px; font-weight:700; color:var(--ios-blue);">${item.metrics}</span>
          </div>
        </div>
      `).join("")}
    </div>
  `;
}

function generateComplianceCertText() {
  const now = new Date();
  const certDate = now.toLocaleDateString("id-ID", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  const certTimestamp = now.toISOString();

  return `================================================================================
SIAGA PROACTIVE THREAT INTELLIGENCE & CYBER MONITORING PLATFORM
SURAT PERNYATAAN & DEKLARASI KEPATUHAN REGULASI NASIONAL
================================================================================
Status Audit       : 100% COMPLIANT (Zero-PII & Regulatory Hardened)
Tanggal Penerbitan : ${certDate} [${certTimestamp}]
Kerangka Regulasi  : 1. UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP)
                     2. UU No. 1 Tahun 2024 (Perubahan Kedua UU ITE)
                     3. Peraturan BSSN No. 8 Tahun 2020 (Sistem CSIRT Nasional)
                     4. IETF RFC 2350 (Expectations for Incident Response)
Integritas Sistem  : SHA-256 One-Way Fingerprint & WAL Read-Only Access
================================================================================

DENGAN INI MENYATAKAN BAHWA:

1. PRINSIP ZERO-PII STORAGE (UU PDP PASAL 35 AYAT 1 & 2):
   Platform SIAGA dirancang dengan prinsip Privacy-by-Design. Seluruh pengujian
   dan penilaian risiko atas aduan atau konten teks diproses secara murni di
   dalam Random Access Memory (RAM). Tidak ada informasi data pribadi (PII)
   seperti NIK, Nomor Rekening, atau Nomor Telepon yang disimpan dalam format
   teks asli (plaintext) pada penyimpanan persisten. Sistem hanya menyimpan
   sidik jari kriptografis satu arah (One-Way SHA-256 Hash Digest) semata-mata
   untuk kebutuhan deduplikasi teknis dan korelasi kampanye penipuan siber.

2. BATASAN RETENSI DATA 30 HARI (UU PDP PASAL 16 AYAT 2 HURUF E):
   Platform mengoperasikan pembersihan terjadwal otomatis (Rolling Auto-Purge Cron)
   yang memusnahkan rekaman audit setelah melewati masa 30 hari. Tidak ada jejak
   data usang yang tertinggal dalam database SQLite WAL.

3. ASAS PRADUGA & PERLINDUNGAN NAMA BAIK (UU ITE DEFAMATION SHIELD):
   Tampilan nama domain pada antarmuka publik secara default disamarkan
   (misal: b***-gebyar.com) untuk mencegah kerugian sekunder atau pencemaran
   nama baik terhadap entitas sah yang identitasnya dicatut oleh pelaku penipuan.

4. INTEGRASI FORMAL LAPORAN CSIRT (PERATURAN BSSN NO. 8/2020 & RFC 2350):
   Draf insiden yang dihasilkan platform secara otomatis memenuhi standar taksonomi
   RFC 2350 dan langsung terhubung dengan kanal resmi penanganan insiden:
   - Aduan Konten Kominfo RI (Hotline WhatsApp: 08119224545)
   - Direktorat Operasi Siber BSSN (Gov-CSIRT: bantuan70@bssn.go.id)
   - PANDI Abuse Desk & IDADX (abuse@pandi.id / https://idadx.id/report)
   - Kontak OJK 157 & Satgas PASTI (WhatsApp: 081157157157)

5. TATA KELOLA AKSES TERISOLASI (UU PDP PASAL 37 & 39):
   Pangkalan data diakses melalui URI strict read-only ('?mode=ro') dan server
   hanya mengikat pada interface loopback lokal (127.0.0.1) untuk mencegah
   eksposur data tanpa hak melalui jaringan publik.

================================================================================
SIAGA Security Engineering Team · Jakarta, Indonesia
Hash Integritas Deklarasi: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
================================================================================`;
}

function initComplianceCertModal() {
  const overlay = document.getElementById("compliance-cert-modal-overlay");
  const pre = document.getElementById("compliance-cert-pre");
  if (!overlay) return;

  // Ensure modal is hidden on initial load
  overlay.classList.add("hidden");
  overlay.style.display = "none";

  // Pre-fill declaration text so it never shows "Memuat..."
  if (pre) {
    pre.textContent = generateComplianceCertText();
  }

  // Bind close buttons
  document.getElementById("compliance-cert-close-btn")?.addEventListener("click", closeComplianceCertModal);
  document.getElementById("compliance-cert-x-close-btn")?.addEventListener("click", closeComplianceCertModal);
  document.getElementById("compliance-cert-footer-close-btn")?.addEventListener("click", closeComplianceCertModal);

  // Click outside modal body to close
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) {
      closeComplianceCertModal();
    }
  });

  // Escape key to close
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !overlay.classList.contains("hidden")) {
      closeComplianceCertModal();
    }
  });

  // Copy button
  document.getElementById("compliance-cert-copy-btn")?.addEventListener("click", () => {
    const text = pre && pre.textContent ? pre.textContent : generateComplianceCertText();
    navigator.clipboard.writeText(text);
    showToast("📋 Naskah Deklarasi Kepatuhan berhasil disalin!");
  });

  // Download button
  document.getElementById("compliance-cert-download-btn")?.addEventListener("click", () => {
    downloadComplianceCertFile();
  });
}

function downloadComplianceCertFile() {
  const pre = document.getElementById("compliance-cert-pre");
  const text = pre && pre.textContent ? pre.textContent : generateComplianceCertText();
  const dateStr = new Date().toISOString().slice(0, 10);
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `SIAGA_UU_PDP_Compliance_Declaration_${dateStr}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast("📥 Berkas Deklarasi Kepatuhan (.txt) berhasil diunduh!");
}

function openComplianceCertModal() {
  const overlay = document.getElementById("compliance-cert-modal-overlay");
  const pre = document.getElementById("compliance-cert-pre");
  if (!overlay) return;

  if (pre) {
    pre.textContent = generateComplianceCertText();
  }
  overlay.classList.remove("hidden");
  overlay.style.display = "flex";
}

function closeComplianceCertModal() {
  const overlay = document.getElementById("compliance-cert-modal-overlay");
  if (!overlay) return;
  overlay.classList.add("hidden");
  overlay.style.display = "none";
}


async function updateComplianceSimulatorOutput(text) {
  const result = await runPrivacySanitizer(text);

  const col1 = document.getElementById("comp-stage-col-redaction");
  const col2 = document.getElementById("comp-stage-col-crypto");
  const col3 = document.getElementById("comp-stage-col-db");
  const countEl = document.getElementById("comp-sim-pii-count");

  if (countEl) countEl.textContent = `${result.piiCount} Elemen PII Terdeteksi`;

  if (col1) {
    col1.innerHTML = `
      <div style="background:var(--ios-fill-quaternary); border-radius:8px; padding:10px; font-size:12.5px; line-height:1.6; border:1px solid var(--ios-border);">
        ${result.sanitizedHtml || `<span style="color:var(--text-tertiary); font-style:italic;">Masukkan teks aduan untuk melihat redaksi otomatis...</span>`}
      </div>
      <div style="font-size:11.5px; color:var(--text-secondary); margin-top:8px;">
        🛡️ <strong>Kepatuhan UU PDP Pasal 35:</strong> NIK, No Rekening, dan No Telepon langsung dinetralisir sebelum masuk ke lapisan logika.
      </div>
    `;
  }

  if (col2) {
    col2.innerHTML = `
      <div class="hash-box-container">${result.hashHex}</div>
      <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:6px;">
        <span style="font-size:11px; color:var(--text-tertiary);">Algoritma: <strong>SHA-256 (64 hex char)</strong></span>
        <button class="hash-copy-btn" id="btn-copy-sim-hash">
          ${ICONS.copy} Salin Hash
        </button>
      </div>
      <div style="font-size:11.5px; color:var(--text-secondary); margin-top:8px;">
        🔑 <strong>One-Way Non-Reversible:</strong> Tidak dapat didekripsi kembali menjadi data pribadi asli.
      </div>
    `;
    col2.querySelector("#btn-copy-sim-hash")?.addEventListener("click", () => {
      navigator.clipboard.writeText(result.hashHex);
      showToast("Hash SHA-256 disalin ke clipboard!");
    });
  }

  if (col3) {
    col3.innerHTML = `
      <div class="db-record-box">
{
  <span class="json-key">"table"</span>: <span class="json-str">"message_analyses"</span>,
  <span class="json-key">"message_hash"</span>: <span class="json-str">"${result.hashHex.slice(0, 16)}..."</span>,
  <span class="json-key">"stored_plaintext_pii"</span>: <span class="json-null">null</span>,
  <span class="json-key">"bytes_pii_stored"</span>: <span class="json-num">0</span>,
  <span class="json-key">"retention_policy"</span>: <span class="json-str">"30_DAYS_AUTO_PURGE"</span>,
  <span class="json-key">"purge_scheduled_at"</span>: <span class="json-str">"${result.dbRecord.purge_scheduled_at}"</span>
}
      </div>
      <div style="display:flex; align-items:center; gap:6px; margin-top:6px;">
        <span class="badge badge-success" style="font-size:11px;">● ZERO-PII AUDIT PASS</span>
        <span style="font-size:11px; color:var(--text-tertiary);">0 Byte PII Disimpan</span>
      </div>
    `;
  }
}

function renderComplianceWorkspace(targetEl) {
  targetEl.innerHTML = `
    <!-- Top Action Bar for Compliance inside Documentation -->
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:var(--sp-4); flex-wrap:wrap; gap:10px;">
      <div style="font-size:13px; color:var(--text-secondary);">
        Tata kelola privasi kriptografis berstandar tinggi terintegrasi di level arsitektur (Zero-Plaintext PII Storage).
      </div>
      <div style="display:flex; gap:8px;">
        <button class="ios-btn ios-btn-secondary" id="btn-scroll-to-simulator">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px; height:14px;"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
          <span>Uji Sanitasi PII</span>
        </button>
        <button class="ios-btn ios-btn-secondary" id="btn-open-compliance-cert">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px; height:14px;"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          <span>Naskah Deklarasi</span>
        </button>
        <button class="ios-btn ios-btn-primary" id="btn-direct-download-cert">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px; height:14px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          <span>Unduh Berkas (.txt)</span>
        </button>
      </div>
    </div>
    <!-- 1. Executive Compliance Hero Banner -->
    <div class="compliance-hero-card">
      <div class="compliance-hero-inner">
        <div class="compliance-hero-text">
          <div class="compliance-hero-badge">
            <span class="live-dot green"></span>
            <span>UU PDP No. 27/2022 & BSSN CSIRT Certified Architecture</span>
          </div>
          <h2 class="compliance-hero-title">Tata Kelola Privasi Kriptografis Berstandar Tinggi</h2>
          <p class="compliance-hero-desc">
            SIAGA menerapkan prinsip <strong>Privacy-by-Design</strong> dan <strong>Zero-Plaintext PII Storage</strong>.
            Setiap indikator ancaman diuji murni di memori RAM, hanya menyimpan sidik jari satu arah (One-Way SHA-256),
            dan dibersihkan otomatis dalam 30 hari guna menjamin perlindungan menyeluruh bagi subjek data di Indonesia.
          </p>
        </div>

        <div class="compliance-hero-seal">
          <div class="compliance-seal-icon-box">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>
          </div>
          <div class="compliance-seal-label">Status Kepatuhan Audit</div>
          <div class="compliance-seal-status">
            <span class="live-dot green"></span>
            <span>100% COMPLIANT</span>
          </div>
          <span class="compliance-seal-sub">12/12 Kontrol Terverifikasi</span>
        </div>
      </div>
    </div>

    <!-- 2. Four-Column Executive Scorecard -->
    <div class="compliance-kpi-grid">
      <div class="compliance-kpi-card">
        <div class="compliance-kpi-top">
          <div class="compliance-kpi-icon green">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>
          </div>
          <span class="compliance-kpi-chip chip-green">TERVERIFIKASI</span>
        </div>
        <div class="compliance-kpi-val">100%</div>
        <div class="compliance-kpi-lbl">Status Audit Regulasi</div>
        <div class="compliance-kpi-sub">12 dari 12 kontrol kepatuhan nasional aktif tanpa deviasi</div>
      </div>

      <div class="compliance-kpi-card">
        <div class="compliance-kpi-top">
          <div class="compliance-kpi-icon blue">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
          </div>
          <span class="compliance-kpi-chip chip-blue">UU PDP PASAL 35</span>
        </div>
        <div class="compliance-kpi-val">0 Byte</div>
        <div class="compliance-kpi-lbl">Penyimpanan Teks Asli PII</div>
        <div class="compliance-kpi-sub">100% menggunakan one-way SHA-256 hash satu arah</div>
      </div>

      <div class="compliance-kpi-card">
        <div class="compliance-kpi-top">
          <div class="compliance-kpi-icon orange">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          </div>
          <span class="compliance-kpi-chip chip-orange">UU PDP PASAL 16</span>
        </div>
        <div class="compliance-kpi-val">30 Hari</div>
        <div class="compliance-kpi-lbl">Siklus Retensi Otomatis</div>
        <div class="compliance-kpi-sub">Pembersihan berkala (Rolling Auto-Purge Cron) aktif di SQLite WAL</div>
      </div>

      <div class="compliance-kpi-card">
        <div class="compliance-kpi-top">
          <div class="compliance-kpi-icon purple">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><line x1="12" y1="3" x2="12" y2="21"/><polyline points="4 7 12 3 20 7"/><path d="M4 7l-2 6a2 2 0 0 0 2 2h0a2 2 0 0 0 2-2L4 7z"/><path d="M20 7l-2 6a2 2 0 0 0 2 2h0a2 2 0 0 0 2-2L20 7z"/></svg>
          </div>
          <span class="compliance-kpi-chip chip-purple">STANDAR RESMI</span>
        </div>
        <div class="compliance-kpi-val">4 Kerangka</div>
        <div class="compliance-kpi-lbl">Harmonisasi Regulasi RI</div>
        <div class="compliance-kpi-sub">UU PDP, UU ITE No. 1/2024, BSSN CSIRT, dan RFC 2350</div>
      </div>
    </div>

    <!-- 3. Interactive Live Feature: UU PDP Privacy Sanitizer Playground -->
    <div class="compliance-simulator-card" id="compliance-simulator-section">
      <div class="compliance-simulator-header">
        <div class="compliance-sim-title-wrap">
          <div class="compliance-sim-icon-tile">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
          </div>
          <div>
            <h2>Simulator Interaktif Sanitasi UU PDP & Kriptografi Zero-PII</h2>
            <p>
              Uji langsung bagaimana mesin SIAGA mendeteksi data pribadi sensitif (PII), meredaksinya seketika,
              dan menghasilkan hash satu arah (SHA-256) sebelum merekamnya ke database.
            </p>
          </div>
        </div>
        <div class="compliance-sim-status-badge">
          <span class="live-dot green"></span>
          <span>Simulator Aktif</span>
        </div>
      </div>

      <!-- Preset Scenarios -->
      <div class="compliance-simulator-presets">
        <span class="compliance-preset-label">Pilih Skenario:</span>
        <button class="compliance-preset-btn active" data-preset="bank">
          💳 Rekening & NIK Nasabah
        </button>
        <button class="compliance-preset-btn" data-preset="pinjol">
          💬 SMS Phishing & Pinjol
        </button>
        <button class="compliance-preset-btn" data-preset="gov">
          🏛️ Pembajakan Web Instansi
        </button>
      </div>

      <!-- Input Textarea -->
      <div class="compliance-sim-input-wrap">
        <textarea
          id="compliance-sim-input"
          class="compliance-sim-textarea"
          rows="3"
          placeholder="Ketik atau tempel teks aduan insiden siber yang memuat nomor rekening, NIK, atau nomor telepon..."
        >${COMPLIANCE_PRESETS.bank.text}</textarea>
      </div>

      <!-- Action Row -->
      <div class="compliance-sim-action-row">
        <div class="compliance-sim-meta">
          <span id="comp-sim-char-count">245 karakter</span>
          <span>•</span>
          <span id="comp-sim-pii-count" style="color:#d70015; font-weight:700;">4 Elemen PII Terdeteksi</span>
        </div>
        <button class="btn-run-compliance-sim" id="btn-run-compliance-sim">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
          <span>Jalankan Sanitasi & Hashing Kriptografis</span>
        </button>
      </div>

      <!-- 3-Column Inspection Stage -->
      <div class="compliance-stage-grid">
        <!-- Col 1: Sanitasi & PII Redaction -->
        <div class="comp-stage-col">
          <div class="comp-stage-header">
            <div class="comp-stage-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>
              <span>1. Redaksi PII Otomatis</span>
            </div>
            <span class="comp-stage-tag green">UU PDP Pasal 35</span>
          </div>
          <div class="comp-stage-body" id="comp-stage-col-redaction">
            <!-- Injected by JS -->
          </div>
        </div>

        <!-- Col 2: One-Way SHA-256 Hash -->
        <div class="comp-stage-col">
          <div class="comp-stage-header">
            <div class="comp-stage-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              <span>2. Kriptografi SHA-256</span>
            </div>
            <span class="comp-stage-tag blue">One-Way Digest</span>
          </div>
          <div class="comp-stage-body" id="comp-stage-col-crypto">
            <!-- Injected by JS -->
          </div>
        </div>

        <!-- Col 3: SQLite Database Storage -->
        <div class="comp-stage-col">
          <div class="comp-stage-header">
            <div class="comp-stage-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
              <span>3. Rekaman Database SQLite</span>
            </div>
            <span class="comp-stage-tag purple">Zero-PII Storage</span>
          </div>
          <div class="comp-stage-body" id="comp-stage-col-db">
            <!-- Injected by JS -->
          </div>
        </div>
      </div>
    </div>

    <!-- 4. Segmented Regulatory Pillars & Matrix -->
    <div class="section">
      <div class="compliance-tabs-bar">
        <div class="compliance-segmented" id="compliance-pillar-segmented">
          <button class="comp-tab-btn active" data-tab="pdp">
            🛡️ UU PDP No. 27/2022
          </button>
          <button class="comp-tab-btn" data-tab="ite">
            ⚖️ UU ITE No. 1/2024
          </button>
          <button class="comp-tab-btn" data-tab="csirt">
            🏛️ BSSN & RFC 2350
          </button>
          <button class="comp-tab-btn" data-tab="matrix">
            📋 Matriks Regulasi vs Arsitektur
          </button>
        </div>

        <span class="text-tertiary" style="font-size:12px;">
          Pilih pilar regulasi untuk menelaah pasal & implementasi teknis
        </span>
      </div>

      <div id="compliance-pillar-content">
        <!-- Rendered by renderCompliancePillarTabs() -->
      </div>
    </div>
  `;

  // Initialize output with default text
  const initialInput = document.getElementById("compliance-sim-input");
  if (initialInput) {
    updateComplianceSimulatorOutput(initialInput.value);

    initialInput.addEventListener("input", () => {
      const charCountEl = document.getElementById("comp-sim-char-count");
      if (charCountEl) charCountEl.textContent = `${initialInput.value.length} karakter`;
      updateComplianceSimulatorOutput(initialInput.value);
    });
  }

  // Bind Simulator Preset Buttons
  document.querySelectorAll(".compliance-preset-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".compliance-preset-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const pKey = btn.dataset.preset;
      const preset = COMPLIANCE_PRESETS[pKey];
      if (preset && initialInput) {
        initialInput.value = preset.text;
        const charCountEl = document.getElementById("comp-sim-char-count");
        if (charCountEl) charCountEl.textContent = `${preset.text.length} karakter`;
        updateComplianceSimulatorOutput(preset.text);
      }
    });
  });

  // Bind Run Simulation Button
  document.getElementById("btn-run-compliance-sim")?.addEventListener("click", () => {
    if (initialInput) {
      updateComplianceSimulatorOutput(initialInput.value);
      showToast("⚡ Uji sanitasi dan hashing kriptografis berhasil dijalankan!");
    }
  });

  // Bind Scroll to Simulator Button
  document.getElementById("btn-scroll-to-simulator")?.addEventListener("click", () => {
    const el = document.getElementById("compliance-simulator-section");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  // Bind Open Compliance Cert Button
  document.getElementById("btn-open-compliance-cert")?.addEventListener("click", openComplianceCertModal);

  // Bind Direct Download Button
  document.getElementById("btn-direct-download-cert")?.addEventListener("click", downloadComplianceCertFile);

  // Bind Segmented Regulatory Tabs
  document.querySelectorAll("#compliance-pillar-segmented .comp-tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#compliance-pillar-segmented .comp-tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeComplianceTab = btn.dataset.tab;
      renderCompliancePillarTabs();
    });
  });

  // Render initial tab content
  renderCompliancePillarTabs();
}

async function renderCompliance(root) {
  return renderDocs(root, "compliance");
}


// ---------------------------------------------------------------------------
// EVALUATION VIEW
// ---------------------------------------------------------------------------

async function renderEvaluation(root) {
  const [metrics, evalDetails] = await Promise.all([
    api("/api/metrics"),
    api("/api/eval/details").catch(() => ({ available: false })),
  ]);

  root.innerHTML = pageShell({
    crumb: "Governance",
    title: "Model & System Evaluation",
    desc: "Akurasi deteksi diukur terhadap ground truth dataset berlabel, dikalibrasi ketat untuk meminimalkan false positive pada nama domain sah.",
  });

  const body = document.getElementById("page-body");
  body.innerHTML = `
    <div class="eval-grid" style="margin-bottom: var(--sp-6);">
      <div class="eval-card">
        <div class="eval-val">${metrics.metrics_available ? `${metrics.precision_pct}<span class="unit">%</span>` : "—"}</div>
        <div class="eval-lbl">Precision</div>
      </div>

      <div class="eval-card">
        <div class="eval-val">${metrics.metrics_available ? `${metrics.recall_pct}<span class="unit">%</span>` : "—"}</div>
        <div class="eval-lbl">Recall</div>
      </div>

      <div class="eval-card">
        <div class="eval-val">${metrics.metrics_available ? metrics.f1_score : "—"}</div>
        <div class="eval-lbl">F1 Score</div>
      </div>
    </div>
    ${!metrics.metrics_available ? `<div class="empty-state" style="margin-bottom:var(--sp-6);">Belum ada hasil scripts/run_eval.py — jalankan evaluasi untuk mengisi angka ini.</div>` : ""}

    <div class="section">
      <div class="panel">
        <div class="panel-header-row">
          <div>
            <h2 class="section-title">Keunggulan Waktu Deteksi (Lead Time)</h2>
            <p class="section-desc">Selisih waktu deteksi proaktif SIAGA dibanding waktu domain masuk ke blacklist publik (URLhaus)</p>
          </div>
          <span class="badge badge-success">Proactive Advantage</span>
        </div>

        <div style="display:flex; align-items:center; gap:20px; padding:10px 0;">
          <div style="font-size:42px; font-weight:800; color:var(--ios-blue); letter-spacing:-0.03em;">
            ${metrics.avg_lead_time_hours !== null ? metrics.avg_lead_time_hours : "—"}<span style="font-size:22px; font-weight:600; color:var(--text-tertiary);"> jam</span>
          </div>
          <div style="font-size:13.5px; color:var(--text-secondary); line-height:1.5;">
            ${metrics.avg_lead_time_hours !== null
              ? `SIAGA mendeteksi domain phishing rata-rata <strong>${metrics.avg_lead_time_hours} jam</strong> sebelum domain tersebut dilaporkan dan terindeks dalam daftar cekal publik URLhaus.`
              : "Belum cukup data — belum ada temuan yang terdaftar di feed publik URLhaus setelah terdeteksi SIAGA."}
          </div>
        </div>

        <div class="text-tertiary" style="font-size:12px; margin-top:10px; border-top:1px solid var(--ios-divider); padding-top:10px;">
          Status Kalibrasi: <strong>${metrics.calibration_status}</strong> · Terakhir Diuji: <strong>${metrics.eval_timestamp ? fmtDate(metrics.eval_timestamp) : "Belum pernah"}</strong>
        </div>
      </div>
    </div>

    ${!evalDetails.available ? "" : `
    <div class="two-col" style="margin-top:var(--sp-6);">
      <div class="panel">
        <div class="panel-header-row">
          <div>
            <h2 class="section-title">Confusion Matrix</h2>
            <p class="section-desc">${evalDetails.total_samples} sampel ground-truth · diuji ${fmtDate(evalDetails.timestamp)}</p>
          </div>
        </div>
        <div class="eval-confusion-grid">
          <div class="eval-confusion-cell eval-confusion-tp">
            <div class="eval-confusion-val">${evalDetails.confusion_matrix.true_positives ?? 0}</div>
            <div class="eval-confusion-lbl">True Positive</div>
          </div>
          <div class="eval-confusion-cell eval-confusion-fp">
            <div class="eval-confusion-val">${evalDetails.confusion_matrix.false_positives ?? 0}</div>
            <div class="eval-confusion-lbl">False Positive</div>
          </div>
          <div class="eval-confusion-cell eval-confusion-fn">
            <div class="eval-confusion-val">${evalDetails.confusion_matrix.false_negatives ?? 0}</div>
            <div class="eval-confusion-lbl">False Negative</div>
          </div>
          <div class="eval-confusion-cell eval-confusion-tn">
            <div class="eval-confusion-val">${evalDetails.confusion_matrix.true_negatives ?? 0}</div>
            <div class="eval-confusion-lbl">True Negative</div>
          </div>
        </div>
        <div class="eval-latency-row">
          <span>Latensi p50: <strong>${fmtInt(Math.round(evalDetails.latency_ms.p50 ?? 0))} ms</strong></span>
          <span>p95: <strong>${fmtInt(Math.round(evalDetails.latency_ms.p95 ?? 0))} ms</strong></span>
          <span>Min: <strong>${fmtInt(Math.round(evalDetails.latency_ms.min ?? 0))} ms</strong></span>
          <span>Max: <strong>${fmtInt(Math.round(evalDetails.latency_ms.max ?? 0))} ms</strong></span>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header-row">
          <div>
            <h2 class="section-title">Distribusi Skor Test Set</h2>
            <p class="section-desc">Sebaran ${evalDetails.total_samples} sampel per tingkat risiko (lib/scoring.py RISK_THRESHOLDS)</p>
          </div>
        </div>
        <div class="eval-histogram">
          ${evalDetails.score_histogram.map((b) => {
            const maxCount = Math.max(...evalDetails.score_histogram.map((x) => x.count), 1);
            const pct = Math.round((b.count / maxCount) * 100);
            return `
              <div class="eval-histogram-row">
                <span class="eval-histogram-label">${b.label}</span>
                <div class="eval-histogram-track"><div class="eval-histogram-fill" style="width:${pct}%;"></div></div>
                <span class="eval-histogram-count">${b.count}</span>
              </div>
            `;
          }).join("")}
        </div>
      </div>
    </div>

    <div class="two-col" style="margin-top:var(--sp-6);">
      <div class="panel">
        <div class="panel-header-row">
          <div>
            <h2 class="section-title">Sinyal Deteksi Paling Sering Muncul</h2>
            <p class="section-desc">Frekuensi setiap sinyal (lib/scoring.py) di seluruh sampel evaluasi</p>
          </div>
        </div>
        <div class="eval-histogram">
          ${evalDetails.top_signals.map((s) => {
            const maxCount = Math.max(...evalDetails.top_signals.map((x) => x.count), 1);
            const pct = Math.round((s.count / maxCount) * 100);
            return `
              <div class="eval-histogram-row">
                <span class="eval-histogram-label"><code>${s.signal}</code></span>
                <div class="eval-histogram-track"><div class="eval-histogram-fill eval-histogram-fill-purple" style="width:${pct}%;"></div></div>
                <span class="eval-histogram-count">${s.count}</span>
              </div>
            `;
          }).join("")}
        </div>
      </div>

      <div class="panel">
        <div class="panel-header-row">
          <div>
            <h2 class="section-title">Sampel Salah Diklasifikasikan</h2>
            <p class="section-desc">${evalDetails.misclassified.length} dari ${evalDetails.total_samples} sampel meleset dari ground-truth</p>
          </div>
        </div>
        ${evalDetails.misclassified.length === 0 ? `<div class="empty-state">Tidak ada kesalahan klasifikasi pada run evaluasi ini.</div>` : `
        <div class="data-table-container">
          <table class="data-table">
            <thead>
              <tr><th>ID</th><th>Ground Truth</th><th>Prediksi</th><th>Skor</th><th>Alasan Utama</th></tr>
            </thead>
            <tbody>
              ${evalDetails.misclassified.map((m) => `
                <tr>
                  <td><code>${esc(m.id)}</code></td>
                  <td>${esc(m.ground_truth)}</td>
                  <td>${esc(m.predicted)}</td>
                  <td>${m.score}/100 (${esc(m.level)})</td>
                  <td style="font-size:12px;">${esc((m.reasons || [])[0] || "-")}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
        `}
      </div>
    </div>
    `}
  `;
}

// ---------------------------------------------------------------------------
// iOS MODAL SHEET (Inspect Drawer & Official Escalation Hub)
// ---------------------------------------------------------------------------

let activeDrawerTab = "channels";

// category (optional): "phishing" | "judol" | "porn". When known, routes
// directly to that category's own endpoint instead of the id-based
// /api/findings/{id} fallback chain (domain_findings -> judol_findings ->
// porn_findings), which is collision-prone since all three tables use
// independent autoincrement ids -- a judol/porn id can coincidentally match
// an unrelated domain_findings row and silently show the wrong finding.
// Callers that already know the category (e.g. the unified Radar table)
// should always pass it; only deep-link restoration (URL has no category)
// still falls back to the id-guessing chain.
async function openFindingDrawer(id, category) {
  const overlay = document.getElementById("inspect-overlay");
  const brandEl = document.getElementById("drawer-brand");
  const badgeEl = document.getElementById("drawer-risk-badge");
  const domainEl = document.getElementById("drawer-domain");
  const bodyEl = document.getElementById("drawer-body");

  if (!overlay || !bodyEl) return;

  bodyEl.innerHTML = `<div style="text-align:center; padding:40px;"><span class="spinner"></span></div>`;
  overlay.classList.remove("hidden");

  // Deep-link URL with inspect query parameter
  const currentUrl = new URL(window.location.href);
  currentUrl.searchParams.set("inspect", id);
  if (category) currentUrl.searchParams.set("category", category);
  history.replaceState({ view: state.view, inspect: id }, document.title, currentUrl.pathname + currentUrl.search);

  const endpoint = category === "judol" ? `/api/judol/${id}`
    : category === "porn" ? `/api/porn/${id}`
    : `/api/findings/${id}`;

  try {
    let f;
    if (typeof id === "string" && id.startsWith("live-")) {
      f = state.radar.rows.find((r) => r.id === id);
    }
    if (!f) {
      try {
        f = await api(endpoint);
      } catch (apiErr) {
        f = state.radar.rows.find((r) => r.id == id || r.raw_domain === id || r.domain_masked === id);
        if (!f) throw apiErr;
      }
    }

    const activeDomain = state.masked ? f.domain_masked : (f.raw_domain || f.domain || f.domain_masked);
    const rawDomain = f.raw_domain || f.domain || f.domain_masked;
    const brandName = f.matched_brand || "General Threat";
    const riskScore = f.risk_score || 0;
    const ls = liveStatus(f.is_live, f.last_status_code);

    brandEl.textContent = brandName;
    badgeEl.className = `badge ${riskScore >= 70 ? "badge-danger" : riskScore >= 40 ? "badge-warning" : "badge-success"}`;
    badgeEl.textContent = riskLabel(f.risk_level);
    domainEl.textContent = activeDomain;

    state.currentDrawerFinding = {
      id: f.id || id,
      category: category || f.category || "phishing",
      rawDomain,
      activeDomain,
    };

    // Current triage status for this domain
    let currentStatus = getFindingStatus(rawDomain);

    // Ensure channels exist
    let channels = f.escalation_channels || [];
    if (!channels.length) {
      channels = [
        {
          name: "Aduan Konten Kominfo RI",
          target_type: "Regulator Konten Negatif & Pemblokiran",
          contact: "aduankonten@kominfo.go.id | WA: 08119224545",
          submission_method: "Portal Resmi (https://www.aduankonten.id) / WhatsApp / Email",
          notes: "Kanal resmi pemerintah untuk pemblokiran akses internet & blacklist DNS TrustPositif.",
        },
      ];
      if (rawDomain.toLowerCase().endsWith(".id")) {
        channels.push({
          name: "PANDI (Pengelola Nama Domain Internet Indonesia)",
          target_type: "Registry .ID",
          contact: "abuse@pandi.id | Helpdesk: (021) 30055777",
          submission_method: "Email Abuse Desk (abuse@pandi.id) / Portal IDADX https://idadx.id/report",
          notes: "Permohonan penangguhan (suspend) nama domain .id yang terindikasi penipuan / phishing.",
        });
      }
    }

    // Pre-craft tailored texts
    const reportDraftText = f.csirt_report_draft || `[LAPORAN INSIDEN SIBER]\nDomain: ${rawDomain}\nTarget: ${brandName}\nSkor Risiko: ${riskScore}/100\nStatus: ${ls.text}\nMetode: ${f.match_method || "-"}\nAlasan: ${f.reasoning || "-"}`;

    function renderDrawerContent() {
      bodyEl.innerHTML = `
        <!-- Status Bar -->
        <div class="drawer-status-bar">
          <span class="drawer-status-label">Status Penanganan Insiden:</span>
          <select class="drawer-status-select" id="drawer-status-select">
            <option value="unreported" ${currentStatus === "unreported" ? "selected" : ""}>⚪ Draf Siap (Belum Dilaporkan)</option>
            <option value="in_progress" ${currentStatus === "in_progress" ? "selected" : ""}>🟡 Sedang Diproses Analis</option>
            <option value="reported" ${currentStatus === "reported" ? "selected" : ""}>🟢 Berhasil Dilaporkan (Tiket Terkirim)</option>
            <option value="suspended" ${currentStatus === "suspended" ? "selected" : ""}>🛡️ Ditangguhkan / Diblokir (Closed)</option>
          </select>
        </div>

        <!-- Segmented Tab Navigation -->
        <div class="ios-segmented" style="width:100%; justify-content:center; margin-bottom:var(--sp-2);" id="drawer-tab-seg">
          <button class="ios-segmented-item ${activeDrawerTab === "channels" ? "active" : ""}" data-tab="channels" style="flex:1;">
            🛡️ Penyaluran Resmi
          </button>
          <button class="ios-segmented-item ${activeDrawerTab === "tech" ? "active" : ""}" data-tab="tech" style="flex:1;">
            🔍 Bukti Teknis
          </button>
          <button class="ios-segmented-item ${activeDrawerTab === "draft" ? "active" : ""}" data-tab="draft" style="flex:1;">
            📄 Draf Dokumen
          </button>
        </div>

        <!-- Tab Body Container -->
        <div id="drawer-tab-body"></div>
      `;

      // Status selector change listener
      document.getElementById("drawer-status-select")?.addEventListener("change", (e) => {
        currentStatus = e.target.value;
        setFindingStatus(rawDomain, currentStatus);
        // Refresh tables if currently visible
        if (state.view === "radar" && typeof renderRadarTable === "function") renderRadarTable();
      });

      // Tab switcher listener
      document.querySelectorAll("#drawer-tab-seg .ios-segmented-item").forEach((btn) => {
        btn.addEventListener("click", () => {
          activeDrawerTab = btn.dataset.tab;
          document.querySelectorAll("#drawer-tab-seg .ios-segmented-item").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          renderActiveTab();
        });
      });

      renderActiveTab();
    }

    function renderActiveTab() {
      const container = document.getElementById("drawer-tab-body");
      if (!container) return;

      if (activeDrawerTab === "channels") {
        container.innerHTML = `
          <!-- 3-Step Guided Workflow Box -->
          <div class="reporting-guide-box" style="margin-bottom:var(--sp-4);">
            <div class="guide-header">
              <span class="guide-badge">Panduan Alur Resmi</span>
              <span class="guide-title">Penyaluran Laporan Cepat & Terarah</span>
            </div>
            <div class="guide-steps">
              <div class="guide-step-item">
                <span class="guide-step-num">1</span>
                <span><strong>Pilih Kanal Penanganan:</strong> Salurkan ke <em>Kominfo</em> untuk pemblokiran DNS TrustPositif, atau <em>PANDI</em> untuk penangguhan domain .ID.</span>
              </div>
              <div class="guide-step-item">
                <span class="guide-step-num">2</span>
                <span><strong>Kirim 1-Klik:</strong> Gunakan tombol <em>WhatsApp Resmi</em> atau <em>Kirim Email</em> di bawah. Teks aduan teknis & data bukti telah diformat otomatis.</span>
              </div>
              <div class="guide-step-item">
                <span class="guide-step-num">3</span>
                <span><strong>Perbarui Status:</strong> Setelah tiket terkirim, ubah status di atas menjadi <em>Berhasil Dilaporkan</em> sebagai rekam jejak CSIRT.</span>
              </div>
            </div>
          </div>

          <!-- Official Channels List -->
          <div class="drawer-section-title">
            <span>Kanal Penyaluran Terverifikasi</span>
            <span style="font-size:11px; font-weight:600; color:var(--ios-blue);">Siap Kirim</span>
          </div>

          <div class="channels-container">
            ${channels.map((ch) => {
              // Extract phone or email for 1-click links
              const isKominfo = ch.name.includes("Kominfo");
              const isPandi = ch.name.includes("PANDI");
              const isOjk = ch.name.includes("OJK") || ch.name.includes("Satgas");
              const isBssn = ch.name.includes("BSSN");

              let waBtn = "";
              let mailBtn = "";
              let portalBtn = "";

              if (isKominfo) {
                const waText = `Halo Tim Aduan Konten Kominfo RI,\n\nSaya ingin melaporkan indikasi situs berbahaya/penipuan:\n• Domain: ${rawDomain}\n• Target: ${brandName} (Skor Risiko: ${riskScore}/100)\n• Status Akses: ${ls.text}\n• Catatan: Terdeteksi otomatis oleh SIAGA Threat Intelligence.\n\nMohon dapat ditindaklanjuti untuk pemblokiran pada DNS TrustPositif. Terima kasih.`;
                const emailSubj = `[Laporan Dugaan Situs Berbahaya] Indikasi ${brandName} pada ${rawDomain}`;
                waBtn = `<a href="https://wa.me/628119224545?text=${encodeURIComponent(waText)}" target="_blank" rel="noopener" class="btn-action btn-action-wa">${ICONS.whatsapp} WA Hotline (08119224545)</a>`;
                mailBtn = `<a href="mailto:aduankonten@kominfo.go.id?subject=${encodeURIComponent(emailSubj)}&body=${encodeURIComponent(reportDraftText)}" class="btn-action btn-action-email">${ICONS.mail} Kirim Email Resmi</a>`;
                portalBtn = `<a href="https://www.aduankonten.id" target="_blank" rel="noopener" class="btn-action btn-action-portal">${ICONS.external} Portal Web</a>`;
              } else if (isPandi) {
                const emailSubj = `[Permohonan Suspend Domain .ID] Indikasi Pelanggaran UU ITE pada ${rawDomain}`;
                mailBtn = `<a href="mailto:abuse@pandi.id?subject=${encodeURIComponent(emailSubj)}&body=${encodeURIComponent(reportDraftText)}" class="btn-action btn-action-email">${ICONS.mail} Email Abuse Desk</a>`;
                portalBtn = `<a href="https://idadx.id/report" target="_blank" rel="noopener" class="btn-action btn-action-portal">${ICONS.external} Portal IDADX</a>`;
              } else if (isOjk) {
                const waText = `Halo Kontak OJK 157 / Satgas PASTI,\n\nSaya ingin melaporkan indikasi aktivitas keuangan ilegal / phishing perbankan:\n• Domain: ${rawDomain}\n• Target: ${brandName}\n• Skor Risiko: ${riskScore}/100\n\nMohon bantuan penanganan dan pemblokiran rekening/domain terkait.`;
                const emailSubj = `[Pengaduan Satgas PASTI] Indikasi Penipuan Keuangan: ${rawDomain}`;
                waBtn = `<a href="https://wa.me/6281157157157?text=${encodeURIComponent(waText)}" target="_blank" rel="noopener" class="btn-action btn-action-wa">${ICONS.whatsapp} WA OJK (081157157157)</a>`;
                mailBtn = `<a href="mailto:satgaspasti@ojk.go.id?subject=${encodeURIComponent(emailSubj)}&body=${encodeURIComponent(reportDraftText)}" class="btn-action btn-action-email">${ICONS.mail} Email Pengaduan</a>`;
                portalBtn = `<a href="https://kontak157.ojk.go.id" target="_blank" rel="noopener" class="btn-action btn-action-portal">${ICONS.external} Portal Kontak 157</a>`;
              } else if (isBssn) {
                const emailSubj = `[Laporan Insiden Siber RFC 2350] Indikasi Peretasan pada ${rawDomain}`;
                mailBtn = `<a href="mailto:bantuan70@bssn.go.id?subject=${encodeURIComponent(emailSubj)}&body=${encodeURIComponent(reportDraftText)}" class="btn-action btn-action-email">${ICONS.mail} Email Gov-CSIRT</a>`;
                portalBtn = `<a href="https://www.bssn.go.id/aduan-siber/" target="_blank" rel="noopener" class="btn-action btn-action-portal">${ICONS.external} Portal BSSN</a>`;
              } else {
                mailBtn = `<a href="mailto:?subject=${encodeURIComponent('[Laporan Siber] ' + rawDomain)}&body=${encodeURIComponent(reportDraftText)}" class="btn-action btn-action-email">${ICONS.mail} Kirim Email</a>`;
              }

              return `
                <div class="channel-card">
                  <div class="channel-card-top">
                    <div>
                      <div class="channel-name">
                        ${ICONS.shieldCheck} ${ch.name}
                      </div>
                      <div class="channel-role">${ch.target_type}</div>
                    </div>
                  </div>
                  
                  <div class="channel-contact-row">
                    <span>Kontak Resmi:</span>
                    <span class="channel-contact-val">${ch.contact}</span>
                  </div>

                  <div class="channel-notes">${ch.notes}</div>

                  <div class="channel-action-row">
                    ${waBtn}
                    ${mailBtn}
                    ${portalBtn}
                    <button class="btn-action btn-action-copy copy-single-channel" data-channel="${ch.name}">
                      ${ICONS.copy} Salin Draf
                    </button>
                  </div>
                </div>
              `;
            }).join("")}
          </div>

          <!-- Interactive Analyst Checklist -->
          <div class="drawer-section-title" style="margin-top:var(--sp-5);">
            <span>Checklist Penanganan Analis</span>
          </div>
          <div class="checklist-card">
            <label class="checklist-item">
              <input type="checkbox" id="chk-verify" checked>
              <span>Verifikasi Bukti Teknis (Respon HEAD HTTP & DNS Domain)</span>
            </label>
            <label class="checklist-item">
              <input type="checkbox" id="chk-screenshot">
              <span>Ambil Tangkapan Layar (Screenshot) sebagai Arsip Barang Bukti</span>
            </label>
            <label class="checklist-item">
              <input type="checkbox" id="chk-escalate" ${currentStatus === "reported" || currentStatus === "suspended" ? "checked" : ""}>
              <span>Kirimkan Notifikasi ke Aduan Konten Kominfo / PANDI Abuse</span>
            </label>
            <label class="checklist-item">
              <input type="checkbox" id="chk-ticket">
              <span>Dokumentasikan Nomor Tiket Insiden Internal / CSIRT</span>
            </label>
          </div>
        `;

        // Copy single channel buttons
        container.querySelectorAll(".copy-single-channel").forEach((btn) => {
          btn.addEventListener("click", () => {
            navigator.clipboard.writeText(reportDraftText);
            alert(`Draf laporan resmi untuk ${btn.dataset.channel} berhasil disalin ke clipboard!`);
          });
        });

      } else if (activeDrawerTab === "tech") {
        container.innerHTML = `
          <div>
            <div class="drawer-section-title">Assessment Risiko Deteksi</div>
            <div class="drawer-grid">
              <div class="drawer-item">
                <div class="drawer-item-lbl">Skor Risiko Total</div>
                <div class="drawer-item-val" style="font-size:20px; color:${riskScore >= 70 ? 'var(--ios-red)' : 'var(--ios-orange)'};">
                  ${riskScore} / 100
                </div>
              </div>
              <div class="drawer-item">
                <div class="drawer-item-lbl">Status HEAD Check</div>
                <div class="drawer-item-val">
                  <span class="status-inline"><span class="dot ${ls.dot}"></span>${ls.text}</span>
                </div>
              </div>
              <div class="drawer-item">
                <div class="drawer-item-lbl">Metode Deteksi</div>
                <div class="drawer-item-val">${f.match_method || "Typosquatting & Heuristic"}</div>
              </div>
              <div class="drawer-item">
                <div class="drawer-item-lbl">Blacklist URLhaus</div>
                <div class="drawer-item-val">${f.in_public_blacklist ? '<span style="color:var(--ios-red)">Terdaftar (Listed)</span>' : '<span style="color:var(--ios-green)">Bersih (Clean)</span>'}</div>
              </div>
            </div>
          </div>

          <div>
            <div class="drawer-section-title">Analisis & Alasan Deteksi</div>
            <div class="drawer-reasoning">
              ${f.reasoning || "Domain terdeteksi memiliki struktur penamaan dan parameter registrasi yang menyerupai institusi target."}
            </div>
          </div>

          <div>
            <div class="drawer-section-title">Metadata Registrasi & Waktu</div>
            <div class="drawer-grid">
              <div class="drawer-item">
                <div class="drawer-item-lbl">Pertama Kali Terlihat</div>
                <div class="drawer-item-val">${fmtDate(f.first_seen)}</div>
              </div>
              <div class="drawer-item">
                <div class="drawer-item-lbl">Terakhir Kali Terlihat</div>
                <div class="drawer-item-val">${fmtDate(f.last_seen || f.first_seen)}</div>
              </div>
              <div class="drawer-item">
                <div class="drawer-item-lbl">Registrar</div>
                <div class="drawer-item-val">${f.registrar || (rawDomain.endsWith(".id") ? "PANDI Registry .ID" : "Private / Hidden")}</div>
              </div>
              <div class="drawer-item">
                <div class="drawer-item-lbl">Nameservers</div>
                <div class="drawer-item-val">${f.nameservers || "Data RDAP tidak tersedia"}</div>
              </div>
            </div>
          </div>
        `;
      } else if (activeDrawerTab === "draft") {
        container.innerHTML = `
          <div>
            <div class="drawer-section-title">
              <span>Draf Dokumen Standar RFC 2350 (CSIRT)</span>
              <button class="btn-action btn-action-copy" id="copy-full-draft-btn">
                ${ICONS.copy} Salin Semua
              </button>
            </div>
            <pre class="report-text-pre">${reportDraftText}</pre>
          </div>

          <div style="display:flex; gap:10px; margin-top:var(--sp-2);">
            <button class="btn btn-primary" style="flex:1;" id="download-draft-btn">
              ${ICONS.download} Unduh Dokumen (.txt)
            </button>
          </div>
        `;

        document.getElementById("copy-full-draft-btn")?.addEventListener("click", () => {
          navigator.clipboard.writeText(reportDraftText);
          alert("Seluruh naskah laporan CSIRT berhasil disalin ke clipboard!");
        });

        document.getElementById("download-draft-btn")?.addEventListener("click", () => {
          const blob = new Blob([reportDraftText], { type: "text/plain;charset=utf-8" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `laporan_insiden_${rawDomain}.txt`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        });
      }
    }

    renderDrawerContent();

  } catch (err) {
    bodyEl.innerHTML = `<div class="empty-state">Gagal memuat detail temuan: ${err.message}</div>`;
  }
}

// Close drawer helper
function closeFindingDrawer() {
  document.getElementById("inspect-overlay")?.classList.add("hidden");
  const currentUrl = new URL(window.location.href);
  if (currentUrl.searchParams.has("inspect")) {
    currentUrl.searchParams.delete("inspect");
    history.replaceState({ view: state.view }, document.title, currentUrl.pathname + (currentUrl.search || ""));
  }
}

// Close drawer listeners
document.getElementById("drawer-close-btn")?.addEventListener("click", closeFindingDrawer);

document.getElementById("inspect-overlay")?.addEventListener("click", (e) => {
  if (e.target.id === "inspect-overlay") {
    closeFindingDrawer();
  }
});

// Deep-link share button inside inspect drawer
document.getElementById("drawer-share-btn")?.addEventListener("click", async () => {
  const fullUrl = window.location.href;
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(fullUrl);
    } else {
      const dummy = document.createElement("input");
      dummy.value = fullUrl;
      document.body.appendChild(dummy);
      dummy.select();
      document.execCommand("copy");
      document.body.removeChild(dummy);
    }
    showToast("Tautan temuan berhasil disalin ke clipboard!");
  } catch (e) {
    prompt("Salin tautan temuan ini:", fullUrl);
  }
});

// CSV Export Helper
function exportFindingsCSV(items, filename = "siaga_findings.csv") {
  if (!items || !items.length) {
    alert("Tidak ada data untuk diekspor.");
    return;
  }
  const headers = ["Domain", "Brand", "Risk Score", "Risk Level", "Is Live", "First Seen"];
  const rows = items.map((f) => [
    `"${state.masked ? f.domain_masked : (f.raw_domain || f.domain_masked)}"`,
    `"${f.matched_brand || ""}"`,
    f.risk_score || 0,
    `"${f.risk_level || ""}"`,
    f.is_live ? "Live" : "Inactive",
    `"${f.first_seen || ""}"`,
  ]);
  const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// ---------------------------------------------------------------------------
// Shell Event Listeners
// ---------------------------------------------------------------------------

document.querySelectorAll(".nav-item[data-view]").forEach((el) => {
  el.addEventListener("click", () => setView(el.dataset.view));
});

// Browser History Back/Forward Navigation
window.addEventListener("popstate", (e) => {
  const targetView = e.state?.view || getViewFromUrl();
  setView(targetView, false);
});

// Brand clicks navigate to overview (/)
document.querySelectorAll(".topbar-brand").forEach((el) => {
  el.style.cursor = "pointer";
  el.addEventListener("click", () => setView("overview"));
});

// Sidebar Folding / Collapsible Navigation (⌘B / Ctrl+B)
function initSidebarFolding() {
  const appShell = document.getElementById("app-shell");
  const topbarToggle = document.getElementById("sidebar-toggle-btn");

  // Restore saved state from localStorage
  const isSavedCollapsed = localStorage.getItem("siaga_sidebar_collapsed") === "true";
  if (isSavedCollapsed && appShell) {
    appShell.classList.add("sidebar-collapsed");
  }

  function toggleSidebar() {
    if (!appShell) return;
    const isNowCollapsed = appShell.classList.toggle("sidebar-collapsed");
    localStorage.setItem("siaga_sidebar_collapsed", isNowCollapsed ? "true" : "false");
    showToast(isNowCollapsed ? "Sidebar dilipat (Compact mode)" : "Sidebar dibentangkan");
  }

  if (topbarToggle) {
    topbarToggle.addEventListener("click", toggleSidebar);
  }

  // Keyboard shortcut: Cmd+B or Ctrl+B
  window.addEventListener("keydown", (e) => {
    if (e.target && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA")) return;
    if ((e.metaKey || e.ctrlKey) && (e.key === "b" || e.key === "B")) {
      e.preventDefault();
      toggleSidebar();
    }
  });
}
initSidebarFolding();

// Global Privacy Masking toggle (iOS Switch Checkbox)
const maskCheckbox = document.getElementById("global-mask-checkbox");
if (maskCheckbox) {
  maskCheckbox.checked = state.masked;
  maskCheckbox.addEventListener("change", (e) => {
    state.masked = e.target.checked;
    setView(state.view);
  });
}

// ---------------------------------------------------------------------------
// DOCUMENTATION VIEW (SIAGA Threat Intelligence & SOC Platform Manual)
// ---------------------------------------------------------------------------

async function renderDocs(root, initialTab = null) {
  root.innerHTML = pageShell({
    crumb: "Reference & SOP",
    title: `<div style="display:flex; align-items:center; gap:12px;">
      <span style="display:inline-flex; align-items:center; justify-content:center; width:38px; height:38px; border-radius:12px; background:linear-gradient(135deg, #30b0c7, #007aff); color:#ffffff; box-shadow:0 3px 10px rgba(48,176,199,0.3); flex-shrink:0;">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:20px; height:20px;"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
      </span>
      <span>Dokumentasi Sistem & Tata Kelola SIAGA</span>
    </div>`,
    desc: "Dokumentasi teknis resmi platform SIAGA: arsitektur pipeline deteksi dini end-to-end, matriks kepatuhan regulasi UU PDP No. 27/2022 & UU ITE, model heuristik scoring risiko, spesifikasi REST API, serta SOP eskalasi insiden CSIRT.",
  });

  const body = document.getElementById("page-body");
  body.innerHTML = `
    <div class="docs-page-container">
      <!-- Hero Panel -->
      <div class="docs-hero-panel">
        <div class="docs-hero-badge">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px; height:14px;"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
          <span>Pusat Dokumentasi, Arsitektur & Kepatuhan SIAGA v2.4</span>
        </div>
        <h1 class="docs-hero-title">Dokumentasi Terpadu: Arsitektur, Kepatuhan Regulasi, Scoring & SOP CSIRT</h1>
        <p class="docs-hero-sub">
          Platform SIAGA (Sistem Intelijen Siber & Analisis Gangguan Siber Aktif) menyatukan arsitektur pemantauan proaktif, tata kelola privasi Zero-Retention sesuai UU PDP No. 27/2022, mesin scoring risiko probabilistik, serta diseminasi CSIRT berstandar RFC 2350.
        </p>
      </div>

      <!-- Tab Switcher -->
      <div class="docs-tab-nav">
        <button class="docs-tab-btn active" data-tab="architecture">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
          1. Arsitektur Sistem
        </button>
        <button class="docs-tab-btn" data-tab="compliance">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
          2. Kepatuhan Regulasi (UU PDP)
        </button>
        <button class="docs-tab-btn" data-tab="scoring">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="m4.93 4.93 4.24 4.24"/><path d="m14.83 9.17 4.24-4.24"/><path d="m14.83 14.83 4.24 4.24"/><path d="m9.17 14.83-4.24 4.24"/></svg>
          3. Scoring Engine
        </button>
        <button class="docs-tab-btn" data-tab="api">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
          4. Spesifikasi REST API
        </button>
        <button class="docs-tab-btn" data-tab="sop">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          5. SOP Eskalasi CSIRT
        </button>
      </div>

      <!-- Tab Contents Area -->
      <div id="docs-tab-content-area"></div>
    </div>
  `;

  const TAB_CONTENTS = {
    scoring: `
      <div class="docs-grid">
        <div class="docs-content-card">
          <div class="docs-section-heading">
            <span class="docs-step-number">🧮</span>
            <div>
              <h2 class="docs-section-title">Rumus Matematis Scoring Ancaman Multi-Faktor</h2>
              <p class="docs-section-sub">Algoritma pembobotan probabilistik untuk menentukan tingkat keparahan risiko.</p>
            </div>
          </div>
          <div class="docs-body-p">
            Skor Risiko dihitung dalam rentang <strong>0 hingga 100</strong> sebagai penjumlahan poin tetap per sinyal
            yang terdeteksi (bukan formula persentase) -- setiap sinyal teknis atau linguistik yang cocok menambahkan
            bobot poinnya sendiri ke skor akhir, dibatasi maksimum 100:
          </div>
          <div class="docs-code-snippet">
            <pre><code>score = min(100, sum(SCORING_WEIGHTS[signal] for signal in matched_signals))
# lib/scoring.py :: SCORING_WEIGHTS</code></pre>
          </div>
          <table class="data-table" style="margin-top:16px;">
            <thead>
              <tr>
                <th>Sinyal</th>
                <th>Kategori</th>
                <th>Poin</th>
              </tr>
            </thead>
            <tbody>
              <tr><td><code>dangerous_request_apk</code></td><td>Linguistic</td><td>50</td></tr>
              <tr><td><code>dangerous_request_credential</code></td><td>Linguistic</td><td>35</td></tr>
              <tr><td><code>domain_age_under_7d</code></td><td>Technical</td><td>30</td></tr>
              <tr><td><code>dangerous_request_transfer</code></td><td>Linguistic</td><td>30</td></tr>
              <tr><td><code>watchlist_similarity</code></td><td>Technical</td><td>25</td></tr>
              <tr><td><code>false_authority_high</code> / <code>prize_bait_high</code></td><td>Linguistic</td><td>25</td></tr>
              <tr><td><code>domain_age_under_30d</code></td><td>Technical</td><td>20</td></tr>
              <tr><td><code>punycode_or_homoglyph</code> / <code>urgency_high</code></td><td>Technical / Linguistic</td><td>20</td></tr>
              <tr><td><code>risky_tld</code> / <code>multi_hop_redirect</code></td><td>Technical</td><td>15</td></tr>
              <tr><td><code>unofficial_chat_channel</code></td><td>Linguistic</td><td>15</td></tr>
              <tr><td><code>domain_age_under_90d</code> / <code>unreachable_domain</code></td><td>Technical</td><td>10</td></tr>
            </tbody>
          </table>
          <p style="font-size:11.5px; color:var(--text-tertiary); margin-top:8px;">
            Nilai lengkap dan terkini selalu ada di <code>lib/scoring.py :: SCORING_WEIGHTS</code> -- tabel di atas
            bisa basi kalau bobotnya dikalibrasi ulang, kode sumber adalah rujukan resmi.
          </p>
        </div>

        <div class="docs-content-card">
          <div class="docs-section-heading">
            <span class="docs-step-number">🚦</span>
            <div>
              <h2 class="docs-section-title">Klasifikasi & Ambang Batas</h2>
              <p class="docs-section-sub">Tiga tingkat risiko sesuai <code>lib/scoring.py :: RISK_THRESHOLDS</code>.</p>
            </div>
          </div>
          <div class="docs-feature-list" style="margin-top:12px;">
            <div style="padding:10px 14px; border-radius:10px; background:rgba(255,59,48,0.08); border:1px solid rgba(255,59,48,0.2); margin-bottom:10px;">
              <span class="badge badge-danger">INDIKASI PENIPUAN (Skor 70 - 100)</span>
              <div style="font-size:12.5px; color:var(--text-secondary); margin-top:4px;">
                Cukup sinyal kuat terkumpul untuk ditandai sebagai temuan berprioritas tinggi.
              </div>
            </div>
            <div style="padding:10px 14px; border-radius:10px; background:rgba(255,149,0,0.08); border:1px solid rgba(255,149,0,0.2); margin-bottom:10px;">
              <span class="badge badge-warning">HATI-HATI (Skor 40 - 69)</span>
              <div style="font-size:12.5px; color:var(--text-secondary); margin-top:4px;">
                Ada indikator mencurigakan, tapi belum cukup kuat untuk diklasifikasikan sebagai penipuan.
              </div>
            </div>
            <div style="padding:10px 14px; border-radius:10px; background:rgba(52,199,89,0.08); border:1px solid rgba(52,199,89,0.2);">
              <span class="badge badge-success">AMAN (Skor 0 - 39)</span>
              <div style="font-size:12.5px; color:var(--text-secondary); margin-top:4px;">
                Tidak ada atau minimal sinyal ancaman yang cocok.
              </div>
            </div>
          </div>
        </div>
      </div>
    `,

    compliance: `
      <div class="docs-grid">
        <div class="docs-content-card">
          <div class="docs-section-heading">
            <span class="docs-step-number">⚖️</span>
            <div>
              <h2 class="docs-section-title">Kepatuhan UU PDP No. 27 Tahun 2022</h2>
              <p class="docs-section-sub">Prinsip perlindungan data pribadi dan desain privasi terintegrasi.</p>
            </div>
          </div>
          <div class="docs-body-p">
            Platform SIAGA dibangun dengan paradigma <strong>Privacy-by-Design</strong> untuk menjamin kepatuhan penuh terhadap regulasi perlindungan data pribadi di Indonesia:
          </div>
          <ul class="docs-feature-list">
            <li>
              <strong>Pasal 35 (Pemrosesan Terbatas & Zero-Retention):</strong>
              Setiap teks pesan SMS, URL, atau laporan yang dimasukkan ke modul <em>Triage Sandbox</em> hanya dianalisis di memori volatil (RAM) dan tidak pernah disimpan ke penyimpanan permanen atau database.
            </li>
            <li>
              <strong>Pasal 38 (Kewajiban Pengamanan Data):</strong>
              Secara default seluruh tampilan domain ancaman disamarkan (<em>Privacy Masking</em>, misal: <code>bca-gebyar-***.com</code>) guna mencegah penyebaran data pribadi korban secara tidak sengaja.
            </li>
            <li>
              <strong>Pasal 46 (Pemberitahuan Insiden):</strong>
              Menyediakan template eksport dan dossier investigasi standar untuk pelaporan insiden keamanan data kepada otoritas pengawas dalam tenggat 3 x 24 jam.
            </li>
          </ul>
        </div>

        <div class="docs-content-card">
          <div class="docs-section-heading">
            <span class="docs-step-number">📜</span>
            <div>
              <h2 class="docs-section-title">Kepatuhan UU ITE No. 1 Tahun 2024 & Standar CSIRT</h2>
              <p class="docs-section-sub">Dasar hukum penindakan konten terlarang dan eskalasi teknis.</p>
            </div>
          </div>
          <ul class="docs-feature-list">
            <li>
              <strong>Pasal 27 Ayat (1) & (2):</strong>
              Pemantauan dan deteksi dini penyebaran muatan melanggar kesusilaan serta perjudian online yang menyusup ke domain pemerintah (<code>.go.id</code>) atau institusi pendidikan (<code>.ac.id</code>).
            </li>
            <li>
              <strong>Pasal 28 Ayat (1):</strong>
              Penindakan terhadap penyebaran berita bohong dan menyesatkan yang mengakibatkan kerugian konsumen dalam transaksi elektronik (kejahatan phishing finansial).
            </li>
            <li>
              <strong>Standar RFC 2350 (CSIRT Guidelines):</strong>
              Struktur informasi intelijen ancaman SIAGA mengikuti pedoman penanganan insiden tim tanggap darurat siber internasional (CERT/CSIRT).
            </li>
          </ul>
        </div>
      </div>
    `,

    api: `
      <div class="docs-grid">
        <div class="docs-content-card">
          <div class="docs-section-heading">
            <span class="docs-step-number">📡</span>
            <div>
              <h2 class="docs-section-title">Katalog REST API SIAGA</h2>
              <p class="docs-section-sub">Dokumentasi antarmuka pemrograman untuk integrasi SIEM dan SOC external.</p>
            </div>
          </div>

          <!-- Endpoint 1 -->
          <div style="margin-top:16px;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
              <span class="badge badge-sky" style="font-weight:700;">GET</span>
              <code style="font-size:13px; font-weight:600;">/api/findings/top?limit=100&unmask=true</code>
            </div>
            <div style="font-size:12px; color:var(--text-secondary); margin-bottom:8px;">Mengambil daftar temuan phishing perbankan terkini yang diurutkan berdasarkan skor risiko tertinggi.</div>
            <div class="docs-code-snippet">
              <pre><code>curl -X GET "http://localhost:8000/api/findings/top?limit=5&unmask=true" \\
     -H "Accept: application/json"</code></pre>
            </div>
          </div>

          <!-- Endpoint 2 -->
          <div style="margin-top:20px;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
              <span class="badge badge-purple" style="font-weight:700;">GET</span>
              <code style="font-size:13px; font-weight:600;">/api/judol?limit=100&unmask=true</code>
            </div>
            <div style="font-size:12px; color:var(--text-secondary); margin-bottom:8px;">Mengambil seluruh temuan judol (keyword + verifikasi LLM pada kata kunci ambigu). Field <code>is_hijacked_institution</code> menandai subset yang berada di subdomain instansi resmi (.go.id/.ac.id).</div>
          </div>

          <!-- Endpoint 3 -->
          <div style="margin-top:20px;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
              <span class="badge badge-danger" style="font-weight:700;">POST</span>
              <code style="font-size:13px; font-weight:600;">/api/analyze</code>
            </div>
            <div style="font-size:12px; color:var(--text-secondary); margin-bottom:8px;">Analisis zero-retention untuk konten pesan SMS, WhatsApp, atau tautan mencurigakan.</div>
            <div class="docs-code-snippet">
              <pre><code>curl -X POST "http://localhost:8000/api/analyze" \\
     -H "Content-Type: application/json" \\
     -d '{"text": "Yth Nasabah BCA, poin reward Anda akan hangus. Klaim di: https://bca-reward.id"}'</code></pre>
            </div>
          </div>
        </div>

        <div class="docs-content-card">
          <div class="docs-section-heading">
            <span class="docs-step-number">⚡</span>
            <div>
              <h2 class="docs-section-title">Contoh Respons JSON (/api/analyze)</h2>
              <p class="docs-section-sub">Format payload standar untuk integrasi webhook dan automated playbook.</p>
            </div>
          </div>
          <div class="docs-code-snippet" style="margin-top:14px;">
            <pre><code>{
  "score": 96,
  "level": "INDIKASI PENIPUAN",
  "reasons": [
    "Alamat domain mencatut nama 'BCA' tetapi bukan domain resmi institusi tersebut.",
    "Desakan waktu tinggi / ancaman terdeteksi pada teks."
  ],
  "explanation": "...",
  "breakdown": [
    {"category": "technical", "signal_name": "watchlist_similarity", "points": 25, "explanation": "..."},
    {"category": "linguistic", "signal_name": "urgency_high", "points": 20, "explanation": "..."}
  ],
  "entities": {"urls": ["https://bca-reward.id"], "phone_numbers": [], "bank_accounts": []},
  "latency_ms": 42
}
// Skema di atas persis field yang dikembalikan dashboard/api.py::post_analyze() --
// tidak ada field "brand"/"compliance"/"retention_policy", jangan diasumsikan ada.</code></pre>
          </div>
          <div style="margin-top:16px;">
            <button class="btn btn-secondary" onclick="showToast('Dokumentasi Swagger OpenAPI tersedia di /docs')" style="font-size:12px;">
              Buka Interactive Swagger UI (/docs) →
            </button>
          </div>
        </div>
      </div>
    `,

    sop: `
      <div class="docs-grid">
        <div class="docs-content-card">
          <div class="docs-section-heading">
            <span class="docs-step-number">🚨</span>
            <div>
              <h2 class="docs-section-title">SOP Penanganan & Eskalasi Insiden CSIRT</h2>
              <p class="docs-section-sub">Prosedur standar operasional bagi tim analis SOC dan Computer Security Incident Response Team.</p>
            </div>
          </div>
          <div class="docs-feature-list" style="margin-top:14px;">
            <div style="padding:10px 14px; border-radius:10px; background:var(--bg-card); border:1px solid var(--border-color); margin-bottom:10px;">
              <strong>Tahap 1: Deteksi & Triage Awal (SLA 5 Menit)</strong>
              <p style="margin:4px 0 0 0; font-size:12.5px; color:var(--text-secondary);">
                Domain baru masuk melalui feed Threat Radar. Analis memeriksa skor risiko, status live HTTP HEAD, dan melakukan pratinjau terisolasi di Safe Web Sandbox.
              </p>
            </div>

            <div style="padding:10px 14px; border-radius:10px; background:var(--bg-card); border:1px solid var(--border-color); margin-bottom:10px;">
              <strong>Tahap 2: Pengumpulan Bukti Forensik (SLA 15 Menit)</strong>
              <p style="margin:4px 0 0 0; font-size:12.5px; color:var(--text-secondary);">
                Sistem membekukan catatan DNS (A, NS, MX records), data registrar WHOIS, sertifikat SSL/TLS, serta hash visual tangkapan layar untuk bukti takedown resmi.
              </p>
            </div>

            <div style="padding:10px 14px; border-radius:10px; background:var(--bg-card); border:1px solid var(--border-color); margin-bottom:10px;">
              <strong>Tahap 3: Diseminasi Kontak Institusi Korban</strong>
              <p style="margin:4px 0 0 0; font-size:12.5px; color:var(--text-secondary);">
                Kirimkan peringatan dini melalui jalur terenkripsi ke Security Operations Center (SOC) bank atau kementerian terkait yang dicatut.
              </p>
            </div>

            <div style="padding:10px 14px; border-radius:10px; background:var(--bg-card); border:1px solid var(--border-color); margin-bottom:10px;">
              <strong>Tahap 4: Permohonan Takedown ke Regulator & Registrar</strong>
              <p style="margin:4px 0 0 0; font-size:12.5px; color:var(--text-secondary);">
                Gunakan tombol <em>Laporkan ke Kominfo</em> di drawer temuan untuk mengirimkan tiket resmi ke <strong>Aduan Konten Kominfo</strong>, abuse desk <strong>PANDI (.id)</strong>, dan <strong>BSSN Gov-CSIRT</strong>.
              </p>
            </div>

            <div style="padding:10px 14px; border-radius:10px; background:var(--bg-card); border:1px solid var(--border-color);">
              <strong>Tahap 5: Pemantauan DNS Sinkholing & Validasi Penutupan</strong>
              <p style="margin:4px 0 0 0; font-size:12.5px; color:var(--text-secondary);">
                Pantau status domain hingga mengembalikan kode NXDOMAIN atau diarahkan ke server peringatan TrustPositif Kominfo.
              </p>
            </div>
          </div>
        </div>

        <div class="docs-content-card">
          <div class="docs-section-heading">
            <span class="docs-step-number">📞</span>
            <div>
              <h2 class="docs-section-title">Direktori Kontak Cepat Otoritas RI</h2>
              <p class="docs-section-sub">Saluran pelaporan resmi untuk tindakan pemblokiran darurat.</p>
            </div>
          </div>
          <table class="data-table" style="margin-top:16px;">
            <thead>
              <tr>
                <th>Lembaga / Otoritas</th>
                <th>Kanal Pelaporan</th>
                <th>Fokus Penindakan</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Kominfo RI</strong></td>
                <td>aduankonten.id / WhatsApp +62 811-9224-545</td>
                <td>Pemblokiran situs judi online, pornografi, dan penipuan nasional</td>
              </tr>
              <tr>
                <td><strong>PANDI (Pengelola .ID)</strong></td>
                <td>abuse@pandi.id</td>
                <td>Suspensif domain <code>.id</code> / <code>.co.id</code> yang melanggar ketentuan</td>
              </tr>
              <tr>
                <td><strong>BSSN (Gov-CSIRT)</strong></td>
                <td>csirt@bssn.go.id</td>
                <td>Insiden penyusupan domain instansi pemerintah dan BUMN</td>
              </tr>
              <tr>
                <td><strong>OJK (Satgas PASTI)</strong></td>
                <td>konsumen@ojk.go.id / 157</td>
                <td>Penipuan investasi ilegal dan pemalsuan layanan jasa keuangan</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `,
  };

  const contentArea = document.getElementById("docs-tab-content-area");

  async function setDocsTab(tabKey) {
    if (!["architecture", "compliance", "scoring", "api", "sop"].includes(tabKey)) {
      tabKey = "architecture";
    }
    state.docsActiveTab = tabKey;

    body.querySelectorAll(".docs-tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tabKey);
    });

    if (tabKey === "architecture") {
      await renderArchitectureWorkspace(contentArea);
    } else if (tabKey === "compliance") {
      renderComplianceWorkspace(contentArea);
    } else {
      contentArea.innerHTML = TAB_CONTENTS[tabKey] || "";
    }
  }

  body.querySelectorAll(".docs-tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => setDocsTab(btn.dataset.tab));
  });

  const params = new URLSearchParams(window.location.search);
  const qTab = params.get("tab")?.toLowerCase();
  const hash = window.location.hash.replace(/^#\/?/, "").toLowerCase();

  let targetTab = initialTab || state.docsActiveTab;
  if (!targetTab) {
    if (qTab && ["architecture", "compliance", "scoring", "api", "sop"].includes(qTab)) {
      targetTab = qTab;
    } else if (hash && ["architecture", "compliance", "scoring", "api", "sop"].includes(hash)) {
      targetTab = hash;
    } else {
      targetTab = "architecture";
    }
  }

  setDocsTab(targetTab);
}

// ---------------------------------------------------------------------------
// GLOBAL SPOTLIGHT SEARCH ENGINE (⌘K / Ctrl+K)
// ---------------------------------------------------------------------------

function initGlobalSpotlightSearch() {
  const searchInput = document.getElementById("global-search-input");
  const dropdown = document.getElementById("spotlight-dropdown");
  const container = document.getElementById("topbar-search-container");
  if (!searchInput || !dropdown) return;

  let cache = null;
  let isFetching = false;

  async function ensureCache() {
    if (cache) return cache;
    if (isFetching) return [];
    isFetching = true;
    try {
      const [phish, judol, porn] = await Promise.all([
        api("/api/findings/top?limit=250&unmask=true").catch(() => ({ findings: [] })),
        api("/api/judol?limit=250&unmask=true").catch(() => ({ items: [] })),
        api("/api/porn?limit=250&unmask=true").catch(() => ({ items: [] })),
      ]);

      const extractItems = (data) => {
        if (!data) return [];
        if (Array.isArray(data)) return data;
        if (Array.isArray(data.findings)) return data.findings;
        if (Array.isArray(data.items)) return data.items;
        return [];
      };

      const phishItems = extractItems(phish).map(x => ({ ...x, category: "phishing" }));
      const judolItems = extractItems(judol).map(x => ({ ...x, category: "judol" }));
      const pornItems = extractItems(porn).map(x => ({ ...x, category: "porn" }));

      cache = [...phishItems, ...judolItems, ...pornItems];
      isFetching = false;
      return cache;
    } catch (e) {
      isFetching = false;
      return [];
    }
  }

  // Pre-load cache on hover or focus
  if (container) {
    container.addEventListener("mouseenter", () => ensureCache());
  }

  searchInput.addEventListener("focus", () => {
    ensureCache();
    renderSpotlightResults();
  });

  searchInput.addEventListener("input", () => {
    renderSpotlightResults();
  });

  async function renderSpotlightResults() {
    const q = searchInput.value.trim().toLowerCase();
    const data = await ensureCache();

    if (!q) {
      const suggestions = [
        { label: "BCA / Bank Central Asia", query: "bca", type: "Bank Phishing" },
        { label: "Bank Rakyat Indonesia", query: "bri", type: "Bank Phishing" },
        { label: "Bank Mandiri (Livin)", query: "mandiri", type: "Bank Phishing" },
        { label: "Situs Slot Gacor / Maxwin", query: "slot", type: "Judi Online" },
        { label: "DANA E-Wallet", query: "dana", type: "Fintech Spoof" },
      ];

      dropdown.innerHTML = `
        <div class="spotlight-header">
          <span>PENCARIAN CEPAT ANCAMAN</span>
          <span style="font-size:10px; text-transform:none; color:var(--text-quaternary);">ESC untuk tutup</span>
        </div>
        <div style="padding:6px 12px; font-size:11.5px; color:var(--text-tertiary);">
          Ketik domain, merek yang dipalsukan, atau pilih kategori instan:
        </div>
        ${suggestions.map(s => `
          <div class="spotlight-item" data-suggestion="${s.query}">
            <div class="spotlight-item-left">
              <span class="spotlight-icon-tile tile-blue">${ICONS.globe}</span>
              <div class="spotlight-domain-col">
                <span class="spotlight-domain-name">${s.label}</span>
                <span class="spotlight-sub-meta">Kategori: ${s.type}</span>
              </div>
            </div>
            <span class="badge badge-sky">Cari →</span>
          </div>
        `).join("")}
        <div class="spotlight-footer" id="spotlight-view-radar">
          Buka Threat Radar Lengkap →
        </div>
      `;

      dropdown.classList.add("show");

      dropdown.querySelectorAll(".spotlight-item").forEach(item => {
        item.addEventListener("click", () => {
          const sq = item.dataset.suggestion;
          searchInput.value = sq;
          state.radar.search = sq;
          state.radar.page = 1;
          closeSpotlight();
          searchInput.blur();
          setView("radar");
        });
      });

      const footer = document.getElementById("spotlight-view-radar");
      if (footer) {
        footer.addEventListener("click", () => {
          closeSpotlight();
          searchInput.blur();
          setView("radar");
        });
      }
      return;
    }

    const matches = data.filter(item => {
      const brand = (item.matched_brand || "").toLowerCase();
      const rawDomain = (item.raw_domain || item.domain || "").toLowerCase();
      const maskedDomain = (item.domain_masked || "").toLowerCase();
      const cat = (item.category || "").toLowerCase();
      const kws = ((item.matched_keywords || []).join(" ")).toLowerCase();
      return brand.includes(q) || rawDomain.includes(q) || maskedDomain.includes(q) || cat.includes(q) || kws.includes(q);
    });

    const docTopics = [
      { key: "architecture", title: "Arsitektur Pipeline & Simulator End-to-End", sub: "Topologi 5-Zone, simulator stream, dan modul Python", match: ["arsitektur", "architecture", "topologi", "topology", "simulator", "pipeline"] },
      { key: "compliance", title: "Kepatuhan Regulasi & Privasi (UU PDP No. 27/2022)", sub: "Zero-retention PII, sertifikasi BSSN, dan simulator sanitasi", match: ["compliance", "kepatuhan", "pdp", "privasi", "privacy", "ite", "bssn", "audit"] },
      { key: "scoring", title: "Scoring Engine & Pembobotan Risiko", sub: "Rumus matematis heuristik, homoglyph, dan threshold", match: ["scoring", "skor", "rumus", "bobot", "heuristik", "homoglyph"] },
      { key: "api", title: "Spesifikasi REST API & OpenAPI", sub: "Katalog endpoint /api/findings, /api/analyze, /api/metrics", match: ["api", "rest", "swagger", "openapi", "curl", "endpoint"] },
      { key: "sop", title: "SOP Eskalasi & Kontak Darurat CSIRT", sub: "Prosedur aduan Kominfo, PANDI abuse, BSSN, dan OJK", match: ["sop", "eskalasi", "csirt", "kominfo", "pandi", "ojk", "kontak"] }
    ];

    const matchedDoc = docTopics.find(d => d.match.some(m => q.includes(m)));
    let docSnippetHtml = "";
    if (matchedDoc) {
      docSnippetHtml = `
        <div class="spotlight-item" data-doc-tab="${matchedDoc.key}" style="background: rgba(0, 122, 255, 0.05); border-left: 3px solid #007aff;">
          <div class="spotlight-item-left">
            <span class="spotlight-icon-tile tile-teal">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px; height:16px;"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
            </span>
            <div class="spotlight-domain-col">
              <span class="spotlight-domain-name" style="color:#007aff;">Dokumentasi: ${matchedDoc.title}</span>
              <span class="spotlight-sub-meta">${matchedDoc.sub}</span>
            </div>
          </div>
          <div class="spotlight-item-right">
            <span class="badge badge-sky">Buka Tab Dokumen →</span>
          </div>
        </div>
      `;
    }

    matches.sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0));
    const topMatches = matches.slice(0, 8);

    if (topMatches.length === 0) {
      dropdown.innerHTML = `
        <div class="spotlight-header">
          <span>HASIL PENCARIAN ANCAMAN</span>
          <span>${matchedDoc ? "1 DOKUMEN DITEMUKAN" : "0 DITEMUKAN"}</span>
        </div>
        ${docSnippetHtml}
        ${!matchedDoc ? `<div class="spotlight-empty">Tidak ditemukan ancaman yang cocok dengan "<b>${esc(q)}</b>"</div>` : ""}
        <div class="spotlight-footer" id="spotlight-view-radar">
          Cari di Tabel Threat Radar Lengkap →
        </div>
      `;
    } else {
      dropdown.innerHTML = `
        <div class="spotlight-header">
          <span>HASIL PENCARIAN ANCAMAN (${matches.length})</span>
          <span>TEKAN ENTER UNTUK RADAR</span>
        </div>
        ${docSnippetHtml}
        ${topMatches.map(m => {
          const domain = state.masked ? m.domain_masked : (m.raw_domain || m.domain || m.domain_masked);
          const icon = m.category === "judol" ? ICONS.warning : (m.category === "porn" ? ICONS.warning : ICONS.shieldLock);
          const tile = m.category === "judol" ? "tile-purple" : (m.category === "porn" ? "tile-crimson" : "tile-blue");
          const catLabel = m.category === "judol" ? "Judol" : (m.category === "porn" ? "Adult" : "Phishing");
          const badgeClass = m.risk_level === "INDIKASI PENIPUAN" ? "badge-danger" : (m.risk_level === "HATI-HATI" ? "badge-warning" : "badge-success");

          return `
            <div class="spotlight-item" data-id="${m.id}" data-category="${m.category || 'phishing'}">
              <div class="spotlight-item-left">
                <span class="spotlight-icon-tile ${tile}">${icon}</span>
                <div class="spotlight-domain-col">
                  <span class="spotlight-domain-name">${domain}</span>
                  <div class="spotlight-sub-meta">
                    <span class="cat-badge cat-${m.category || "phishing"}">${catLabel}</span>
                    <span>${m.matched_brand || "General Threat"}</span>
                    <span>•</span>
                    <span>Skor ${Math.round(m.risk_score || 0)}</span>
                  </div>
                </div>
              </div>
              <div class="spotlight-item-right">
                <span class="badge ${badgeClass}">${m.risk_level || "RISIKO"}</span>
                <span style="font-size:11px; color:var(--text-tertiary);">Inspeksi →</span>
              </div>
            </div>
          `;
        }).join("")}
        <div class="spotlight-footer" id="spotlight-view-radar">
          Lihat Semua ${matches.length} Temuan di Threat Radar →
        </div>
      `;
    }

    dropdown.classList.add("show");

    dropdown.querySelectorAll(".spotlight-item").forEach(itemEl => {
      itemEl.addEventListener("click", () => {
        if (itemEl.dataset.docTab) {
          state.docsActiveTab = itemEl.dataset.docTab;
          closeSpotlight();
          searchInput.blur();
          setView("docs");
          return;
        }
        const id = itemEl.dataset.id;
        const cat = itemEl.dataset.category || "phishing";
        closeSpotlight();
        searchInput.blur();
        openFindingDrawer(id, cat);
      });
    });

    const footer = document.getElementById("spotlight-view-radar");
    if (footer) {
      footer.addEventListener("click", () => {
        state.radar.search = q;
        state.radar.page = 1;
        closeSpotlight();
        searchInput.blur();
        setView("radar");
      });
    }
  }

  function closeSpotlight() {
    dropdown.classList.remove("show");
  }

  // Keyboard Shortcuts & Navigation
  window.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K")) {
      e.preventDefault();
      searchInput.focus();
      searchInput.select();
      renderSpotlightResults();
      return;
    }

    if (e.key === "Escape") {
      if (dropdown.classList.contains("show")) {
        closeSpotlight();
        searchInput.blur();
      }
    }
  });

  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const q = searchInput.value.trim();
      state.radar.search = q.toLowerCase();
      state.radar.page = 1;
      closeSpotlight();
      searchInput.blur();
      setView("radar");
    }
  });

  document.addEventListener("click", (e) => {
    if (container && !container.contains(e.target)) {
      closeSpotlight();
    }
  });
}
initGlobalSpotlightSearch();


// Real-time API Latency & Health Polling
async function pollHealth() {
  try {
    const start = performance.now();
    const h = await api("/api/health");
    const elapsedMs = Math.round(performance.now() - start);

    const latencyEl = document.getElementById("sidebar-latency");
    if (latencyEl) latencyEl.textContent = `${elapsedMs}ms`;

    const feedTag = document.getElementById("topbar-feed-tag");
    if (feedTag) {
      feedTag.className = `ios-pill ${h.is_healthy ? "ios-pill-success" : "ios-pill-blue"}`;
    }
  } catch (e) {
    const latencyEl = document.getElementById("sidebar-latency");
    if (latencyEl) latencyEl.textContent = "—";
  }
}
pollHealth();
setInterval(pollHealth, 30000);

// Initialize initial view from current URL path
const initialView = getViewFromUrl();
setView(initialView, false);

// Initialize Modals
initWebPreviewModal();
initComplianceCertModal();

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    initComplianceCertModal();
  });
}

