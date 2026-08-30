/**
 * SIAGA Dashboard Application Logic (D2/D3)
 * Pure vanilla JavaScript with inline SVG trend rendering.
 * Zero external CDN / library dependencies.
 */

let isUnmasked = false;

// Format number with dots (13534 -> "13.534")
function formatNum(num) {
  if (num === null || num === undefined) return "0";
  return num.toLocaleString("id-ID");
}

// Format Indonesian Date
function formatWibDate(dateStr) {
  if (!dateStr) return "-- --- ----";
  const [y, m, d] = dateStr.split("-");
  const months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agt", "Sep", "Okt", "Nov", "Des"];
  return `${parseInt(d, 10)} ${months[parseInt(m, 10) - 1]} ${y}`;
}

// ==============================================================================
// 1. Fetch & Render Summary Stats (/api/stats/today)
// ==============================================================================
async function loadStatsToday() {
  try {
    const res = await fetch("/api/stats/today");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    document.getElementById("currentDateBadge").textContent = formatWibDate(data.date);
    document.getElementById("scannedCount").textContent = formatNum(data.domains_scanned);
    document.getElementById("tahap1Count").textContent = formatNum(data.tahap1_passed);
    document.getElementById("flaggedCount").textContent = formatNum(data.domains_flagged);
    document.getElementById("liveCount").textContent = formatNum(data.domains_live);

    const ratio = data.domains_scanned > 0 
      ? ((data.tahap1_passed / data.domains_scanned) * 100).toFixed(2) 
      : "0.00";
    document.getElementById("tahap1Ratio").textContent = `${ratio}% dari total pindaian`;

    renderFunnelBars(data);
  } catch (err) {
    console.error("Error loading today's stats:", err);
  }
}

// ==============================================================================
// 2. Render Inline SVG Trend Chart & Funnel Bars (D3)
// ==============================================================================
async function loadStatsTrend() {
  try {
    const res = await fetch("/api/stats/trend?days=14");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderTrendSvg(data.trend || []);
  } catch (err) {
    console.error("Error loading trend data:", err);
  }
}

function renderTrendSvg(trend) {
  const svg = document.getElementById("trendSvg");
  if (!trend || trend.length === 0) {
    svg.innerHTML = `<text x="250" y="80" fill="#64748b" font-size="12" text-anchor="middle">Belum ada data tren historis</text>`;
    return;
  }

  const width = 500;
  const height = 140;
  const padLeft = 10;
  const padRight = 10;
  const padTop = 15;
  const padBottom = 25;

  const maxVal = Math.max(...trend.map(d => Math.max(d.domains_scanned, 1)), 100);
  const n = trend.length;
  const stepX = (width - padLeft - padRight) / Math.max(n - 1, 1);

  // Generate points for Scanned line
  const ptsScanned = trend.map((d, i) => {
    const x = padLeft + i * stepX;
    const y = padTop + (1 - (d.domains_scanned / maxVal)) * (height - padTop - padBottom);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  // Generate points for Flagged line (scaled up visually for readability if small)
  const maxFlagged = Math.max(...trend.map(d => d.domains_flagged), 10);
  const ptsFlagged = trend.map((d, i) => {
    const x = padLeft + i * stepX;
    const y = padTop + (1 - (d.domains_flagged / maxFlagged)) * (height - padTop - padBottom);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  // Area polygon for Scanned
  const firstX = padLeft;
  const lastX = padLeft + (n - 1) * stepX;
  const baseY = height - padBottom;
  const areaPoints = `${firstX},${baseY} ${ptsScanned.join(" ")} ${lastX},${baseY}`;

  // Date labels
  const dateLabels = trend.map((d, i) => {
    const x = padLeft + i * stepX;
    const dayLabel = d.date.split("-").slice(1).join("/");
    return `<text x="${x.toFixed(1)}" y="${height - 5}" fill="#64748b" font-size="9" text-anchor="middle" font-family="monospace">${dayLabel}</text>`;
  }).join("");

  svg.innerHTML = `
    <defs>
      <linearGradient id="scannedGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.35"/>
        <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.0"/>
      </linearGradient>
    </defs>
    <!-- Grid line -->
    <line x1="${padLeft}" y1="${baseY}" x2="${lastX}" y2="${baseY}" stroke="#1e293b" stroke-width="1"/>
    
    <!-- Scanned Area & Line -->
    <polygon points="${areaPoints}" fill="url(#scannedGrad)"/>
    <polyline points="${ptsScanned.join(" ")}" fill="none" stroke="#38bdf8" stroke-width="2.5" stroke-linecap="round"/>
    
    <!-- Flagged Line -->
    <polyline points="${ptsFlagged.join(" ")}" fill="none" stroke="#f87171" stroke-width="2" stroke-dasharray="4 3"/>
    
    <!-- Data points -->
    ${ptsScanned.map(pt => `<circle cx="${pt.split(",")[0]}" cy="${pt.split(",")[1]}" r="3.5" fill="#38bdf8"/>`).join("")}
    
    <!-- Date labels -->
    ${dateLabels}
  `;
}

function renderFunnelBars(stats) {
  const container = document.getElementById("funnelBarsContainer");
  const scanned = stats.domains_scanned || 1;
  const t1 = stats.tahap1_passed || 0;
  const t2 = stats.tahap2_passed || t1;
  const flagged = stats.domains_flagged || 0;

  const pctT1 = ((t1 / scanned) * 100).toFixed(1);
  const pctT2 = ((t2 / scanned) * 100).toFixed(1);
  const pctFlagged = ((flagged / scanned) * 100).toFixed(2);

  container.innerHTML = `
    <div class="funnel-bar-row">
      <div class="f-bar-meta">
        <span>Tahap 0: CT Raw Ingestion</span>
        <span><b>${formatNum(scanned)}</b> (100%)</span>
      </div>
      <div class="f-bar-track">
        <div class="f-bar-fill" style="width: 100%; background: #38bdf8;"></div>
      </div>
    </div>

    <div class="funnel-bar-row">
      <div class="f-bar-meta">
        <span>Tahap 1: Brand Similarity Filter (Local CPU)</span>
        <span><b>${formatNum(t1)}</b> (${pctT1}%)</span>
      </div>
      <div class="f-bar-track">
        <div class="f-bar-fill" style="width: ${Math.max(pctT1, 3)}%; background: #fbbf24;"></div>
      </div>
    </div>

    <div class="funnel-bar-row">
      <div class="f-bar-meta">
        <span>Tahap 2: Verifikasi Teknis (RDAP &amp; Blacklist)</span>
        <span><b>${formatNum(t2)}</b> (${pctT2}%)</span>
      </div>
      <div class="f-bar-track">
        <div class="f-bar-fill" style="width: ${Math.max(pctT2, 2)}%; background: #818cf8;"></div>
      </div>
    </div>

    <div class="funnel-bar-row">
      <div class="f-bar-meta">
        <span>Tahap 3: Indikasi Ancaman (Risk Score &ge; 40)</span>
        <span><b>${formatNum(flagged)}</b> (${pctFlagged}%)</span>
      </div>
      <div class="f-bar-track">
        <div class="f-bar-fill" style="width: ${Math.max(pctFlagged, 1.5)}%; background: #f87171;"></div>
      </div>
    </div>
  `;
}

// ==============================================================================
// 3. Fetch & Render Priority Findings (/api/findings/top)
// ==============================================================================
async function loadFindingsTop() {
  const tbody = document.getElementById("findingsTableBody");
  try {
    const unmaskQuery = isUnmasked ? "&unmask=true" : "";
    const res = await fetch(`/api/findings/top?limit=10${unmaskQuery}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (!data.findings || data.findings.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted" style="padding: 24px;">Tidak ada temuan phishing berisiko tinggi hari ini.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.findings.map(f => {
      const displayDomain = isUnmasked ? (f.raw_domain || f.domain) : f.domain_masked;
      const scoreClass = f.risk_score >= 70 ? "score-high" : "score-med";
      const liveClass = f.is_live ? "live-true" : "live-false";
      const liveText = f.is_live ? "● Aktif" : "○ Mati";

      return `
        <tr>
          <td class="domain-cell">${escapeHtml(displayDomain)}</td>
          <td class="brand-cell">${escapeHtml(f.matched_brand || "-")}</td>
          <td><span class="score-badge ${scoreClass}">${f.risk_score}</span></td>
          <td><span class="live-badge ${liveClass}">${liveText}</span></td>
          <td><span class="method-tag">${escapeHtml(f.match_method || "rule")}</span></td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Error loading findings:", err);
    tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">Gagal memuat temuan.</td></tr>`;
  }
}

// ==============================================================================
// 4. Fetch & Render System Metrics & Health (/api/metrics & /api/health)
// ==============================================================================
async function loadMetricsAndHealth() {
  try {
    const [mRes, hRes] = await Promise.all([
      fetch("/api/metrics"),
      fetch("/api/health")
    ]);

    if (mRes.ok) {
      const m = await mRes.json();
      document.getElementById("metricPrecision").textContent = m.precision_pct !== null ? `${m.precision_pct}%` : "N/A";
      document.getElementById("metricRecall").textContent = m.recall_pct !== null ? `${m.recall_pct}%` : "N/A";
      document.getElementById("metricF1").textContent = m.f1_score !== null ? m.f1_score : "N/A";
      document.getElementById("metricUptime").textContent = `${m.collector_uptime_pct}%`;
      document.getElementById("metricRam").textContent = `${m.peak_ram_mb} MB`;
      document.getElementById("metricCalib").textContent = m.calibration_status || "--";
    }

    if (hRes.ok) {
      const h = await hRes.json();
      const badge = document.getElementById("healthBadge");
      const text = document.getElementById("healthText");

      if (h.is_healthy) {
        badge.className = "badge badge-health";
        text.textContent = "OPERASIONAL NORMAL";
      } else {
        badge.className = "badge badge-health degraded";
        text.textContent = "PERINGATAN OPERASIONAL";
      }
    }
  } catch (err) {
    console.error("Error loading metrics/health:", err);
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ==============================================================================
// 5. Event Listeners & Initialization
// ==============================================================================
async function refreshAll() {
  await Promise.all([
    loadStatsToday(),
    loadStatsTrend(),
    loadFindingsTop(),
    loadMetricsAndHealth(),
  ]);
}

document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("unmaskToggle");
  const toggleLabel = document.getElementById("toggleLabel");
  const refreshBtn = document.getElementById("refreshBtn");

  toggle.checked = false;
  isUnmasked = false;

  toggle.addEventListener("change", (e) => {
    isUnmasked = e.target.checked;
    toggleLabel.textContent = isUnmasked ? "Penyamaran: NONAKTIF" : "Penyamaran: AKTIF";
    toggleLabel.style.color = isUnmasked ? "var(--accent-amber)" : "var(--text-secondary)";
    loadFindingsTop();
  });

  refreshBtn.addEventListener("click", () => {
    refreshBtn.textContent = "⏳ Memuat...";
    refreshAll().finally(() => {
      refreshBtn.textContent = "🔄 Refresh";
    });
  });

  refreshAll();

  // Auto-refresh every 30 seconds
  setInterval(refreshAll, 30000);
});
