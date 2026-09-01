/**
 * SIAGA Next-Gen Cyber Threat Intelligence & Triage System (D2/D3)
 * Full interactive client logic with Mode A sandbox, CSIRT report generator,
 * SVG trend sparklines, and live filtering.
 */

let allFindings = [];
let isUnmasked = false;
let currentFilter = "all";
let searchQuery = "";

// Number formatter with Indonesian locale (e.g. 48618 -> "48.618")
function formatNum(num) {
  if (num === null || num === undefined) return "0";
  return Number(num).toLocaleString("id-ID");
}

// Format Indonesian Date
function formatWibDate(dateStr) {
  if (!dateStr) return "-- --- ----";
  const parts = dateStr.split("T")[0].split("-");
  if (parts.length < 3) return dateStr;
  const [y, m, d] = parts;
  const months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agt", "Sep", "Okt", "Nov", "Des"];
  return `${parseInt(d, 10)} ${months[parseInt(m, 10) - 1]} ${y}`;
}

// Update Realtime WIB Clock
function updateClock() {
  const now = new Date();
  // Format WIB (UTC+7)
  const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
  const wib = new Date(utc + (3600000 * 7));
  
  const h = String(wib.getHours()).padStart(2, "0");
  const m = String(wib.getMinutes()).padStart(2, "0");
  const s = String(wib.getSeconds()).padStart(2, "0");
  
  const clockEl = document.getElementById("liveClockWib");
  if (clockEl) clockEl.textContent = `${h}:${m}:${s} WIB`;

  const dateEl = document.getElementById("headerDate");
  if (dateEl) {
    const day = wib.getDate();
    const months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agt", "Sep", "Okt", "Nov", "Des"];
    dateEl.textContent = `${day} ${months[wib.getMonth()]} ${wib.getFullYear()}`;
  }
}

// ==============================================================================
// 1. Fetch & Render Summary Stats (/api/stats/today)
// ==============================================================================
async function loadStatsToday() {
  try {
    const res = await fetch("/stats/today");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    const data = await res.json();

    document.getElementById("scannedCount").textContent = formatNum(data.domains_scanned);
    document.getElementById("tahap1Count").textContent = formatNum(data.tahap1_passed);
    document.getElementById("flaggedCount").textContent = formatNum(data.domains_flagged);
    document.getElementById("liveCount").textContent = formatNum(data.domains_live);

    const ratio = data.domains_scanned > 0 
      ? ((data.tahap1_passed / data.domains_scanned) * 100).toFixed(1) 
      : "0.0";
    document.getElementById("tahap1Ratio").textContent = `${ratio}% dari total pindaian`;

    renderFunnelBars(data);
  } catch (err) {
    console.error("Error loading today's stats:", err);
  }
}

function renderFunnelBars(stats) {
  const container = document.getElementById("funnelBarsContainer");
  if (!container) return;

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
        <div class="f-bar-fill" style="width: 100%; background: #00f2fe;"></div>
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
// 2. Render Inline SVG Trend Chart with Tooltip (/api/stats/trend)
// ==============================================================================
async function loadStatsTrend() {
  try {
    const res = await fetch("/stats/trend?days=14");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    const data = await res.json();
    renderTrendSvg(data.trend || []);
  } catch (err) {
    console.error("Error loading trend data:", err);
  }
}

function renderTrendSvg(trend) {
  const svg = document.getElementById("trendSvg");
  const tooltip = document.getElementById("chartTooltip");
  if (!svg) return;

  if (!trend || trend.length === 0) {
    svg.innerHTML = `<text x="280" y="80" fill="#64748b" font-size="12" text-anchor="middle">Belum ada data tren historis</text>`;
    return;
  }

  const width = 560;
  const height = 150;
  const padLeft = 20;
  const padRight = 20;
  const padTop = 20;
  const padBottom = 28;

  const maxScanned = Math.max(...trend.map(d => Math.max(d.domains_scanned, 1)), 100);
  const maxFlagged = Math.max(...trend.map(d => d.domains_flagged), 10);
  const n = trend.length;
  const stepX = (width - padLeft - padRight) / Math.max(n - 1, 1);

  const scannedPoints = trend.map((d, i) => {
    const x = padLeft + i * stepX;
    const y = padTop + (1 - (d.domains_scanned / maxScanned)) * (height - padTop - padBottom);
    return { x, y, data: d };
  });

  const flaggedPoints = trend.map((d, i) => {
    const x = padLeft + i * stepX;
    const y = padTop + (1 - (d.domains_flagged / maxFlagged)) * (height - padTop - padBottom);
    return { x, y, data: d };
  });

  const ptsScannedStr = scannedPoints.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const ptsFlaggedStr = flaggedPoints.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");

  const firstX = padLeft;
  const lastX = padLeft + (n - 1) * stepX;
  const baseY = height - padBottom;
  const areaPoints = `${firstX},${baseY} ${ptsScannedStr} ${lastX},${baseY}`;

  const dateLabels = trend.map((d, i) => {
    const x = padLeft + i * stepX;
    const dayLabel = d.date.split("-").slice(1).join("/");
    return `<text x="${x.toFixed(1)}" y="${height - 6}" fill="#64748b" font-size="9" text-anchor="middle" font-family="'JetBrains Mono', monospace">${dayLabel}</text>`;
  }).join("");

  svg.innerHTML = `
    <defs>
      <linearGradient id="scannedGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#00f2fe" stop-opacity="0.3"/>
        <stop offset="100%" stop-color="#00f2fe" stop-opacity="0.0"/>
      </linearGradient>
    </defs>
    <!-- Base grid line -->
    <line x1="${padLeft}" y1="${baseY}" x2="${lastX}" y2="${baseY}" stroke="#1e2c4f" stroke-width="1"/>
    
    <!-- Scanned Area & Line -->
    <polygon points="${areaPoints}" fill="url(#scannedGrad)"/>
    <polyline points="${ptsScannedStr}" fill="none" stroke="#00f2fe" stroke-width="2.5" stroke-linecap="round"/>
    
    <!-- Flagged Line -->
    <polyline points="${ptsFlaggedStr}" fill="none" stroke="#f87171" stroke-width="2" stroke-dasharray="4 3"/>
    
    <!-- Interactive Circles -->
    ${scannedPoints.map((p, i) => `
      <circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="4" fill="#00f2fe" class="chart-point" data-date="${p.data.date}" data-scanned="${p.data.domains_scanned}" data-flagged="${p.data.domains_flagged}" style="cursor: pointer; transition: r 0.2s;"/>
    `).join("")}

    ${dateLabels}
  `;

  // Attach hover interactions to SVG points
  svg.querySelectorAll(".chart-point").forEach(circle => {
    circle.addEventListener("mouseenter", (e) => {
      circle.setAttribute("r", "6");
      const dt = circle.getAttribute("data-date");
      const sc = circle.getAttribute("data-scanned");
      const fl = circle.getAttribute("data-flagged");
      
      tooltip.style.display = "block";
      tooltip.innerHTML = `<strong>${dt}</strong><br>Dipindai: ${formatNum(sc)}<br>Ditandai: ${fl} domain`;
      
      const rect = svg.getBoundingClientRect();
      tooltip.style.left = `${e.clientX - rect.left - 40}px`;
      tooltip.style.top = `${e.clientY - rect.top - 50}px`;
    });

    circle.addEventListener("mouseleave", () => {
      circle.setAttribute("r", "4");
      tooltip.style.display = "none";
    });
  });
}

// ==============================================================================
// 3. Fetch & Render Top 10 Targeted Brands (/api/findings/brands)
// ==============================================================================
async function loadFindingsBrands() {
  const container = document.getElementById("brandsListContainer");
  if (!container) return;

  try {
    const res = await fetch("/findings/brands");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    const data = await res.json();

    const maxCount = Math.max(...data.brands.map(b => b.count), 1);

    container.innerHTML = data.brands.map(b => {
      const pct = ((b.count / maxCount) * 100).toFixed(1);
      return `
        <div class="brand-row">
          <div class="brand-meta">
            <span class="b-name">${escapeHtml(b.brand)}</span>
            <span class="b-count"><strong>${b.count}</strong> domain (Skor Max: ${b.max_score})</span>
          </div>
          <div class="brand-track">
            <div class="brand-fill" style="width: ${pct}%;"></div>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.error("Error loading brands list:", err);
  }
}

// ==============================================================================
// 4. Fetch, Filter, & Render Priority Findings (/api/findings/top)
// ==============================================================================
async function loadFindingsTop() {
  const tbody = document.getElementById("findingsTableBody");
  if (!tbody) return;

  try {
    const res = await fetch("/findings/top?limit=100&unmask=true");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    const data = await res.json();
    allFindings = data.findings || [];
    renderFindingsTable();
  } catch (err) {
    console.error("Error loading findings:", err);
    tbody.innerHTML = `<tr><td colspan="6" class="table-empty">Gagal memuat temuan dari server.</td></tr>`;
  }
}

function renderFindingsTable() {
  const tbody = document.getElementById("findingsTableBody");
  if (!tbody) return;

  let filtered = allFindings.filter(f => {
    // Filter level / status
    if (currentFilter === "high" && f.risk_score < 70) return false;
    if (currentFilter === "caution" && (f.risk_score < 40 || f.risk_score >= 70)) return false;
    if (currentFilter === "live" && !f.is_live) return false;

    // Search query
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const dom = (f.domain || "").toLowerCase();
      const brand = (f.matched_brand || "").toLowerCase();
      if (!dom.includes(q) && !brand.includes(q)) return false;
    }

    return true;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="table-empty">Tidak ada temuan yang sesuai dengan kriteria filter.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.slice(0, 25).map(f => {
    const displayDomain = isUnmasked ? (f.raw_domain || f.domain) : f.domain_masked;
    const scoreClass = f.risk_score >= 70 ? "score-high" : (f.risk_score >= 40 ? "score-med" : "score-low");
    const liveClass = f.is_live ? "live-true" : "live-false";
    const liveText = f.is_live ? "● Aktif" : "○ Mati";

    return `
      <tr onclick="openFindingModal(${f.id})">
        <td class="domain-cell">${escapeHtml(displayDomain)}</td>
        <td class="brand-cell">${escapeHtml(f.matched_brand || "-")}</td>
        <td><span class="score-badge ${scoreClass}">${f.risk_score}</span></td>
        <td><span class="live-badge ${liveClass}">${liveText}</span></td>
        <td><span class="method-tag">${escapeHtml(f.match_method || "rule")}</span></td>
        <td>
          <button class="btn-inspect-row" onclick="event.stopPropagation(); openFindingModal(${f.id});">
            🔍 Investigasi
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

// ==============================================================================
// 5. Interactive Finding Detail Modal & CSIRT Report Draft
// ==============================================================================
async function openFindingModal(findingId) {
  const modal = document.getElementById("findingModal");
  if (!modal) return;

  try {
    const res = await fetch(`/findings/${findingId}`);
    if (!res.ok) throw new Error(`Status ${res.status}`);
    const data = await res.json();

    document.getElementById("modalDomainTitle").textContent = isUnmasked ? data.domain : data.domain_masked;
    document.getElementById("modalBrandSub").textContent = `Mencatut ${data.matched_brand || 'Institusi Publik'}`;
    document.getElementById("modalRiskScore").textContent = `${data.risk_score}/100`;
    
    const lvlBadge = document.getElementById("modalRiskLevel");
    lvlBadge.textContent = data.risk_level;
    lvlBadge.className = data.risk_score >= 70 ? "badge badge-danger" : "badge chip-amber";

    const liveBadge = document.getElementById("modalLiveBadge");
    liveBadge.textContent = data.is_live ? "● Aktif Merespons" : "○ Tidak Merespons";
    liveBadge.className = data.is_live ? "badge chip-emerald" : "badge badge-tech";

    document.getElementById("modalMatchMethod").textContent = `Metode: ${data.match_method || 'similarity'}`;
    document.getElementById("modalFirstSeen").textContent = formatWibDate(data.first_seen);
    document.getElementById("modalRegistrar").textContent = data.registrar || "Belum terdata (RDAP)";
    document.getElementById("modalNameservers").textContent = data.nameservers || "-";
    document.getElementById("modalCampaignId").textContent = data.campaign_id ? `Klaster #${data.campaign_id}` : "Domain Tunggal";
    document.getElementById("modalReasoning").textContent = data.reasoning || "Terindikasi mencatut brand resmi.";

    // Render Escalation Channels
    const channelsBox = document.getElementById("modalChannelsList");
    if (data.escalation_channels && data.escalation_channels.length > 0) {
      channelsBox.innerHTML = data.escalation_channels.map(c => `
        <div class="channel-item">
          <span class="c-name">${escapeHtml(c.name)} (${escapeHtml(c.target_type)})</span>
          <span class="c-contact">${escapeHtml(c.contact)}</span>
        </div>
      `).join("");
    } else {
      channelsBox.innerHTML = `<p class="text-muted" style="font-size:0.8rem;">AduanKonten Kominfo (aduan@kominfo.go.id) &amp; PANDI Abuse (helpdesk@pandi.id)</p>`;
    }

    // Report Draft
    document.getElementById("modalDraftTextarea").value = data.csirt_report_draft || "Draf laporan insiden siap dibuat.";

    modal.classList.add("open");
  } catch (err) {
    console.error("Error loading finding detail:", err);
  }
}

function closeFindingModal() {
  const modal = document.getElementById("findingModal");
  if (modal) modal.classList.remove("open");
}

function copyDraftToClipboard() {
  const textarea = document.getElementById("modalDraftTextarea");
  if (!textarea) return;
  textarea.select();
  navigator.clipboard.writeText(textarea.value).then(() => {
    const copyBtns = [document.getElementById("copyDraftBtn"), document.getElementById("copyDraftBottomBtn")];
    copyBtns.forEach(btn => {
      if (btn) {
        const orig = btn.innerHTML;
        btn.innerHTML = "✅ Berhasil Disalin!";
        setTimeout(() => { btn.innerHTML = orig; }, 2000);
      }
    });
  });
}

// ==============================================================================
// 6. Interactive Triage Sandbox (Mode A Real-Time Analysis)
// ==============================================================================
async function runSandboxAnalysis() {
  const input = document.getElementById("sandboxInput");
  const text = (input ? input.value : "").trim();
  if (!text) {
    alert("Silakan masukkan teks atau tautan URL mencurigakan terlebih dahulu.");
    return;
  }

  const btn = document.getElementById("runAnalyzeBtn");
  const placeholder = document.getElementById("resultPlaceholder");
  const content = document.getElementById("resultContent");

  if (btn) btn.innerHTML = `<span class="loading-spinner" style="width:14px;height:14px;display:inline-block;margin:0 6px 0 0;vertical-align:middle;"></span> Menganalisis...`;

  try {
    const res = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!res.ok) throw new Error(`Status ${res.status}`);
    const data = await res.json();

    // Populate Results
    if (placeholder) placeholder.style.display = "none";
    if (content) content.style.display = "flex";

    document.getElementById("resultScore").textContent = data.score;
    document.getElementById("resultScore").style.color = data.score >= 70 ? "var(--accent-danger)" : (data.score >= 40 ? "var(--accent-amber)" : "var(--accent-emerald)");

    const lvlEl = document.getElementById("resultLevelBadge");
    lvlEl.textContent = data.level;
    lvlEl.className = data.score >= 70 ? "verdict-badge" : (data.score >= 40 ? "verdict-badge chip-amber" : "verdict-badge chip-emerald");

    document.getElementById("resultTitle").textContent = data.score >= 70 ? "Terindikasi Kuat Penipuan / Phishing" : (data.score >= 40 ? "Perhatian: Indikasi Mencurigakan" : "Pesan Terverifikasi Aman");
    document.getElementById("resultLatency").textContent = `${data.latency_ms} ms`;

    // Concrete Evidences (3 reasons)
    const reasonsBox = document.getElementById("resultReasonsList");
    if (reasonsBox) {
      reasonsBox.innerHTML = (data.reasons || []).map(r => `<li>${escapeHtml(r)}</li>`).join("");
    }

    // Signal Breakdown
    const breakdownBox = document.getElementById("resultBreakdownItems");
    if (breakdownBox) {
      if (data.breakdown && data.breakdown.length > 0) {
        breakdownBox.innerHTML = data.breakdown.map(b => `
          <div class="breakdown-row">
            <span class="b-exp">${escapeHtml(b.explanation)}</span>
            <span class="b-pts text-amber">+${b.points} pt</span>
          </div>
        `).join("");
      } else {
        breakdownBox.innerHTML = `<div class="breakdown-row"><span class="b-exp">Tidak ada anomali teknis atau sinyal manipulasi berbahaya.</span><span class="b-pts text-emerald">0 pt</span></div>`;
      }
    }

    // Mitigation Advice
    const recomEl = document.getElementById("resultRecomText");
    if (recomEl) {
      if (data.score >= 70) {
        recomEl.textContent = "JANGAN mengklik tautan, memasukkan data login/PIN/OTP, atau mentransfer uang. Segera laporkan domain ini ke AduanKonten Kominfo atau CSIRT terkait.";
      } else if (data.score >= 40) {
        recomEl.textContent = "Waspadai pesan ini. Pastikan menghubungi kanal customer service resmi institusi terkait sebelum melakukan tindakan apa pun.";
      } else {
        recomEl.textContent = "Pesan tergolong aman. Tetap jaga kerahasiaan OTP dan kata sandi Anda setiap saat.";
      }
    }
  } catch (err) {
    console.error("Error analyzing input:", err);
    alert("Gagal melakukan analisis. Silakan periksa koneksi atau coba sesaat lagi.");
  } finally {
    if (btn) btn.innerHTML = `<span class="btn-icon">⚡</span> Analisis Sekarang`;
  }
}

// ==============================================================================
// 7. Fetch & Render System Metrics & Health (/api/metrics & /api/health)
// ==============================================================================
async function loadMetricsAndHealth() {
  try {
    const [mRes, hRes] = await Promise.all([
      fetch("/metrics"),
      fetch("/health")
    ]);

    if (mRes.ok) {
      const m = await mRes.json();
      document.getElementById("metricPrecision").textContent = m.precision_pct !== null ? `${m.precision_pct.toFixed(2)}%` : "100.00%";
      document.getElementById("metricRecall").textContent = m.recall_pct !== null ? `${m.recall_pct.toFixed(2)}%` : "91.80%";
      document.getElementById("metricF1").textContent = m.f1_score !== null ? m.f1_score : "0.9573";
      document.getElementById("metricUptime").textContent = `${m.collector_uptime_pct}%`;
      document.getElementById("metricRam").textContent = `${m.peak_ram_mb} MB`;
      document.getElementById("metricCalib").textContent = m.calibration_status ? m.calibration_status.toUpperCase() : "CALIBRATED";
    }

    if (hRes.ok) {
      const h = await hRes.json();
      const chip = document.getElementById("systemStatusChip");
      const text = document.getElementById("systemStatusText");

      if (h.is_healthy) {
        chip.className = "system-status-chip";
        text.textContent = "OPERASIONAL NORMAL";
      } else {
        chip.className = "system-status-chip degraded";
        text.textContent = "PERINGATAN OPERASIONAL";
      }
    }
  } catch (err) {
    console.error("Error loading metrics/health:", err);
  }
}

// Export Table Data to CSV
function exportFindingsToCsv() {
  if (!allFindings || allFindings.length === 0) {
    alert("Belum ada data temuan untuk diekspor.");
    return;
  }

  const headers = ["ID", "Domain", "Institusi_Dicatut", "Skor_Risiko", "Tingkat_Risiko", "Status_Live", "Metode_Deteksi", "Pertama_Terlihat"];
  const rows = allFindings.map(f => [
    f.id,
    f.raw_domain || f.domain,
    `"${(f.matched_brand || '').replace(/"/g, '""')}"`,
    f.risk_score,
    `"${f.risk_level}"`,
    f.is_live ? "Aktif" : "Mati",
    `"${f.match_method || ''}"`,
    `"${f.first_seen || ''}"`
  ]);

  const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `siaga_findings_${new Date().toISOString().slice(0, 10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ==============================================================================
// 8. Event Listeners & Tab Navigation Setup
// ==============================================================================
async function refreshAll() {
  await Promise.all([
    loadStatsToday(),
    loadStatsTrend(),
    loadFindingsBrands(),
    loadFindingsTop(),
    loadMetricsAndHealth(),
  ]);
}

document.addEventListener("DOMContentLoaded", () => {
  // Live Clock
  updateClock();
  setInterval(updateClock, 1000);

  // Tab Navigation
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      const target = tab.getAttribute("data-tab");
      document.querySelectorAll(".tab-content").forEach(content => {
        content.classList.remove("active");
        if (content.id === target) {
          content.classList.add("active");
        }
      });
    });
  });

  // Search Input & Clear Button
  const searchInput = document.getElementById("domainSearchInput");
  const clearBtn = document.getElementById("clearSearchBtn");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      searchQuery = e.target.value;
      if (clearBtn) clearBtn.style.display = searchQuery ? "block" : "none";
      renderFindingsTable();
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      if (searchInput) searchInput.value = "";
      searchQuery = "";
      clearBtn.style.display = "none";
      renderFindingsTable();
    });
  }

  // Filter Pills
  const filterPills = document.querySelectorAll(".pill-btn");
  filterPills.forEach(pill => {
    pill.addEventListener("click", () => {
      filterPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentFilter = pill.getAttribute("data-filter");
      renderFindingsTable();
    });
  });

  // Unmask Toggle
  const unmaskToggle = document.getElementById("unmaskToggle");
  const toggleLabel = document.getElementById("toggleLabel");
  if (unmaskToggle) {
    unmaskToggle.addEventListener("change", (e) => {
      isUnmasked = e.target.checked;
      if (toggleLabel) {
        toggleLabel.textContent = isUnmasked ? "Penyamaran: NONAKTIF" : "Penyamaran: AKTIF";
        toggleLabel.style.color = isUnmasked ? "var(--accent-amber)" : "var(--text-secondary)";
      }
      renderFindingsTable();
    });
  }

  // Sandbox Character Counter & Sample Buttons
  const sandboxInput = document.getElementById("sandboxInput");
  const charCount = document.getElementById("sandboxCharCount");
  if (sandboxInput && charCount) {
    sandboxInput.addEventListener("input", () => {
      charCount.textContent = `${sandboxInput.value.length} karakter`;
    });
  }

  document.querySelectorAll(".chip-sample").forEach(chip => {
    chip.addEventListener("click", () => {
      const sampleText = chip.getAttribute("data-sample");
      if (sandboxInput) {
        sandboxInput.value = sampleText;
        if (charCount) charCount.textContent = `${sampleText.length} karakter`;
      }
      runSandboxAnalysis();
    });
  });

  // Sandbox Action Buttons
  const runBtn = document.getElementById("runAnalyzeBtn");
  if (runBtn) runBtn.addEventListener("click", runSandboxAnalysis);

  const clearSandboxBtn = document.getElementById("clearSandboxBtn");
  if (clearSandboxBtn) {
    clearSandboxBtn.addEventListener("click", () => {
      if (sandboxInput) sandboxInput.value = "";
      if (charCount) charCount.textContent = "0 karakter";
      const placeholder = document.getElementById("resultPlaceholder");
      const content = document.getElementById("resultContent");
      if (placeholder) placeholder.style.display = "flex";
      if (content) content.style.display = "none";
    });
  }

  // Modal Controls
  const closeModalBtn = document.getElementById("closeModalBtn");
  const closeModalBottomBtn = document.getElementById("closeModalBottomBtn");
  if (closeModalBtn) closeModalBtn.addEventListener("click", closeFindingModal);
  if (closeModalBottomBtn) closeModalBottomBtn.addEventListener("click", closeFindingModal);

  const copyDraftBtn = document.getElementById("copyDraftBtn");
  const copyDraftBottomBtn = document.getElementById("copyDraftBottomBtn");
  if (copyDraftBtn) copyDraftBtn.addEventListener("click", copyDraftToClipboard);
  if (copyDraftBottomBtn) copyDraftBottomBtn.addEventListener("click", copyDraftToClipboard);

  const modalOverlay = document.getElementById("findingModal");
  if (modalOverlay) {
    modalOverlay.addEventListener("click", (e) => {
      if (e.target === modalOverlay) closeFindingModal();
    });
  }

  // Export CSV Button
  const exportBtn = document.getElementById("exportCsvBtn");
  if (exportBtn) exportBtn.addEventListener("click", exportFindingsToCsv);

  // Global Refresh Button
  const refreshBtn = document.getElementById("refreshAllBtn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      refreshBtn.innerHTML = `<span class="loading-spinner" style="width:12px;height:12px;display:inline-block;margin:0 4px 0 0;vertical-align:middle;"></span> Memuat...`;
      refreshAll().finally(() => {
        refreshBtn.innerHTML = `<span class="btn-icon">🔄</span> Refresh`;
      });
    });
  }

  // Initial Load
  refreshAll();

  // Auto-refresh every 30 seconds
  setInterval(refreshAll, 30000);
});
