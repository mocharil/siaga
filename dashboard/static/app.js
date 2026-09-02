// SIAGA Dashboard — vanilla JS SPA shell, no build step, no framework.
// Views render into #view-root; nav buttons in the sidebar switch views.

const state = {
  view: "overview",
  masked: true,
  radar: { rows: [], sortKey: "risk_score", sortDir: "desc", search: "", brand: "all" },
  pipelineOpen: null,
};

const ICONS = {
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6L9 17l-5-5"/></svg>',
};

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function api(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

function fmtInt(n) {
  return (n ?? 0).toLocaleString("id-ID");
}

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("id-ID", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

function riskBadge(level) {
  const map = {
    "INDIKASI PENIPUAN": "badge-danger",
    "HATI-HATI": "badge-warning",
    "AMAN": "badge-success",
  };
  return `<span class="badge ${map[level] || "badge-neutral"}">${level}</span>`;
}

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------

const VIEWS = {
  overview: renderOverview,
  radar: renderRadar,
  triage: renderTriage,
  intelligence: renderIntelligence,
  architecture: renderArchitecture,
  compliance: renderCompliance,
  evaluation: renderEvaluation,
};

function setView(name) {
  state.view = name;
  document.querySelectorAll(".nav-item[data-view]").forEach((el) => {
    el.classList.toggle("active", el.dataset.view === name);
  });
  const root = document.getElementById("view-root");
  root.innerHTML = `<div class="page"><div class="empty-state"><span class="spinner"></span></div></div>`;
  VIEWS[name](root).catch((err) => {
    root.innerHTML = `<div class="page"><div class="empty-state">Gagal memuat data: ${err.message}</div></div>`;
  });
}

function pageShell({ crumb, title, desc, actions = "" }) {
  return `
    <div class="page">
      <div class="breadcrumb">${crumb}</div>
      <div class="page-header">
        <div>
          <h1 class="page-title">${title}</h1>
          <p class="page-desc">${desc}</p>
        </div>
        <div class="page-actions">${actions}</div>
      </div>
      <div id="page-body"></div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Overview
// ---------------------------------------------------------------------------

async function renderOverview(root) {
  const [metrics, today, top, health] = await Promise.all([
    api("/api/metrics"),
    api("/api/stats/today"),
    api("/api/findings/top?limit=5"),
    api("/api/health"),
  ]);

  root.innerHTML = pageShell({
    crumb: "SIAGA",
    title: "Overview",
    desc: "Ringkasan pemantauan domain phishing hari ini dan kesehatan sistem.",
  });

  const body = document.getElementById("page-body");
  body.innerHTML = `
    <div class="section">
      <div class="panel">
        <div class="metric-row">
          <div class="metric">
            <div class="metric-value">${fmtInt(today.domains_scanned)}</div>
            <div class="metric-label">Dipindai (24 jam)</div>
          </div>
          <div class="metric">
            <div class="metric-value">${fmtInt(today.domains_flagged)}</div>
            <div class="metric-label">Ditandai mencurigakan</div>
          </div>
          <div class="metric">
            <div class="metric-value">${fmtInt(today.domains_live)}</div>
            <div class="metric-label">Aktif merespons</div>
          </div>
          <div class="metric">
            <div class="metric-value">${fmtInt(metrics.total_findings_flagged)}</div>
            <div class="metric-label">Total temuan (kumulatif)</div>
          </div>
        </div>
      </div>
    </div>

    <div class="two-col">
      <div class="section">
        <div class="section-header">
          <h2 class="section-title">Temuan prioritas</h2>
          <span class="section-meta"><a href="#radar" data-nav="radar">Lihat semua →</a></span>
        </div>
        <div class="panel panel-flush" id="overview-findings"></div>
      </div>

      <div class="section">
        <div class="section-header">
          <h2 class="section-title">System Health</h2>
        </div>
        <div class="panel" id="overview-health"></div>
      </div>
    </div>
  `;

  document.getElementById("overview-findings").innerHTML = top.findings.length
    ? top.findings.map((f) => `
        <div class="health-row" style="padding: var(--sp-3) var(--sp-6);">
          <div>
            <div class="mono">${state.masked ? f.domain_masked : (f.raw_domain || f.domain_masked)}</div>
            <div class="text-tertiary" style="font-size:12px; margin-top:2px;">${f.matched_brand || "—"}</div>
          </div>
          ${riskBadge(f.risk_level)}
        </div>
      `).join("")
    : `<div class="empty-state">Belum ada temuan hari ini.</div>`;

  const healthy = health.is_healthy;
  document.getElementById("overview-health").innerHTML = `
    <div class="health-row">
      <span class="health-row-label">Status keseluruhan</span>
      <span class="health-row-value"><span class="dot ${healthy ? "ok" : "bad"}"></span>${healthy ? "Sehat" : "Ada masalah"}</span>
    </div>
    <div class="health-row">
      <span class="health-row-label">Collector</span>
      <span class="health-row-value">${health.latest_collector_status || "—"}</span>
    </div>
    <div class="health-row">
      <span class="health-row-label">Uptime collector</span>
      <span class="health-row-value">${metrics.collector_uptime_pct}%</span>
    </div>
    <div class="health-row">
      <span class="health-row-label">Memori puncak</span>
      <span class="health-row-value">${metrics.peak_ram_mb} MB</span>
    </div>
    <div class="health-row">
      <span class="health-row-label">Sinkronisasi terakhir</span>
      <span class="health-row-value">${fmtDate(health.latest_collector_time)}</span>
    </div>
  `;

  wireInternalNav(body);
}

function wireInternalNav(scope) {
  scope.querySelectorAll("[data-nav]").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      setView(el.dataset.nav);
    });
  });
}

// ---------------------------------------------------------------------------
// Radar (findings table)
// ---------------------------------------------------------------------------

async function renderRadar(root) {
  const data = await api("/api/findings/top?limit=100");
  state.radar.rows = data.findings;

  root.innerHTML = pageShell({
    crumb: "SIAGA",
    title: "Radar",
    desc: "Domain baru yang terdeteksi mencatut identitas institusi Indonesia.",
    actions: `
      <button class="btn btn-secondary" id="mask-toggle-btn">
        <span class="toggle ${state.masked ? "on" : ""}" id="mask-toggle"></span>
        Samarkan domain
      </button>
    `,
  });

  const body = document.getElementById("page-body");
  body.innerHTML = `
    <div class="panel panel-flush">
      <div class="table-toolbar">
        <input class="table-search" id="radar-search" placeholder="Cari brand atau domain...">
        <select id="radar-level">
          <option value="all">Semua level</option>
          <option value="INDIKASI PENIPUAN">Indikasi Penipuan</option>
          <option value="HATI-HATI">Hati-hati</option>
        </select>
        <span class="text-tertiary" style="margin-left:auto; font-size:12px;">${data.total_findings} total temuan</span>
      </div>
      <div id="radar-table-wrap"></div>
    </div>
  `;

  document.getElementById("mask-toggle-btn").addEventListener("click", () => {
    state.masked = !state.masked;
    renderRadarTable();
  });
  document.getElementById("radar-search").addEventListener("input", (e) => {
    state.radar.search = e.target.value.toLowerCase();
    renderRadarTable();
  });
  document.getElementById("radar-level").addEventListener("change", (e) => {
    state.radar.level = e.target.value;
    renderRadarTable();
  });

  renderRadarTable();
}

function renderRadarTable() {
  const wrap = document.getElementById("radar-table-wrap");
  if (!wrap) return;

  let rows = state.radar.rows.filter((r) => {
    if (state.radar.search) {
      const hay = `${r.matched_brand || ""} ${r.domain_masked}`.toLowerCase();
      if (!hay.includes(state.radar.search)) return false;
    }
    if (state.radar.level && state.radar.level !== "all" && r.risk_level !== state.radar.level) return false;
    return true;
  });

  rows.sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0));

  wrap.innerHTML = rows.length ? `
    <table class="data-table">
      <thead>
        <tr>
          <th>Domain</th>
          <th>Brand</th>
          <th>Risiko</th>
          <th>Metode</th>
          <th>Pertama terlihat</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        ${rows.map((r) => `
          <tr data-id="${r.id}">
            <td class="mono">${state.masked ? r.domain_masked : (r.raw_domain || r.domain_masked)}</td>
            <td>${r.matched_brand || "—"}</td>
            <td>${riskBadge(r.risk_level)} <span class="text-tertiary" style="font-size:12px;">${r.risk_score}</span></td>
            <td class="text-secondary" style="font-size:12.5px;">${r.match_method || "—"}</td>
            <td class="text-tertiary" style="font-size:12.5px;">${fmtDate(r.first_seen)}</td>
            <td>${r.is_live ? '<span class="badge badge-warning">Aktif</span>' : '<span class="badge badge-neutral">Tidak aktif</span>'}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  ` : `<div class="empty-state">Tidak ada temuan yang cocok dengan filter.</div>`;

  wrap.querySelectorAll("tbody tr").forEach((tr) => {
    tr.addEventListener("click", () => openFindingDrawer(tr.dataset.id));
  });
}

async function openFindingDrawer(id) {
  try {
    const f = await api(`/api/findings/${id}`);
    alert(
      `${state.masked ? f.domain_masked : f.domain}\n` +
      `Brand: ${f.matched_brand}\nSkor: ${f.risk_score} (${f.risk_level})\n\n${f.reasoning}`
    );
  } catch (e) {
    console.error(e);
  }
}

// ---------------------------------------------------------------------------
// Triage
// ---------------------------------------------------------------------------

async function renderTriage(root) {
  root.innerHTML = pageShell({
    crumb: "SIAGA",
    title: "Triage",
    desc: "Analisis pesan atau URL mencurigakan secara langsung — tanpa disimpan ke database.",
  });

  const body = document.getElementById("page-body");
  body.innerHTML = `
    <div class="panel">
      <textarea class="triage-input" id="triage-text" placeholder="Tempel pesan atau URL yang dicurigai di sini..."></textarea>
      <div class="mt-4">
        <button class="btn btn-primary" id="triage-submit">Analisis</button>
      </div>
      <div id="triage-result"></div>
    </div>
  `;

  document.getElementById("triage-submit").addEventListener("click", async () => {
    const text = document.getElementById("triage-text").value.trim();
    if (!text) return;
    const resultEl = document.getElementById("triage-result");
    resultEl.innerHTML = `<div class="triage-result"><span class="spinner"></span></div>`;
    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      const band = data.score >= 70 ? "fraud" : data.score >= 40 ? "caution" : "safe";
      resultEl.innerHTML = `
        <div class="triage-result">
          <span class="risk-band ${band}">Skor ${data.score}/100 — ${data.level}</span>
          <ul class="reason-list">
            ${(data.reasons || []).map((r) => `<li>${r}</li>`).join("")}
          </ul>
        </div>
      `;
    } catch (e) {
      resultEl.innerHTML = `<div class="triage-result text-secondary">Gagal menganalisis: ${e.message}</div>`;
    }
  });
}

// ---------------------------------------------------------------------------
// Intelligence
// ---------------------------------------------------------------------------

async function renderIntelligence(root) {
  const [analytics, brands] = await Promise.all([
    api("/api/stats/analytics"),
    api("/api/findings/brands"),
  ]);

  root.innerHTML = pageShell({
    crumb: "SIAGA",
    title: "Intelligence",
    desc: "Pola serangan, brand yang paling ditiru, dan distribusi TLD yang disalahgunakan.",
  });

  const body = document.getElementById("page-body");
  const maxBrand = Math.max(...brands.brands.map((b) => b.count), 1);
  const maxTld = Math.max(...analytics.tld_distribution.map((t) => t.count), 1);

  body.innerHTML = `
    <div class="two-col">
      <div class="section">
        <div class="section-header"><h2 class="section-title">Brand paling ditiru</h2></div>
        <div class="panel">
          ${brands.brands.map((b) => `
            <div class="bar-list-item">
              <div class="bar-list-top"><span class="bar-list-label">${b.brand}</span><span class="bar-list-value">${b.count}</span></div>
              <div class="bar-track"><div class="bar-fill" style="width:${(b.count / maxBrand) * 100}%"></div></div>
            </div>
          `).join("")}
        </div>
      </div>

      <div class="section">
        <div class="section-header"><h2 class="section-title">Distribusi TLD</h2></div>
        <div class="panel">
          ${analytics.tld_distribution.map((t) => `
            <div class="bar-list-item">
              <div class="bar-list-top"><span class="bar-list-label">${t.tld} <span class="badge badge-neutral" style="margin-left:6px;">${t.badge}</span></span><span class="bar-list-value">${t.pct}%</span></div>
              <div class="bar-track"><div class="bar-fill" style="width:${(t.count / maxTld) * 100}%"></div></div>
            </div>
          `).join("")}
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-header"><h2 class="section-title">Taktik penyamaran</h2></div>
      <div class="panel panel-flush">
        <table class="data-table">
          <thead><tr><th>Taktik</th><th>Jumlah</th><th>Persentase</th></tr></thead>
          <tbody>
            ${analytics.deception_tactics.map((t) => `
              <tr>
                <td><div style="font-weight:500;">${t.name}</div><div class="text-tertiary" style="font-size:12px;">${t.desc}</div></td>
                <td>${t.count}</td>
                <td>${t.pct}%</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>

    <div class="section">
      <div class="section-header">
        <h2 class="section-title">Sektor yang ditargetkan</h2>
      </div>
      <div class="panel">
        <div class="metric-row">
          ${analytics.target_sectors.map((s) => `
            <div class="metric">
              <div class="metric-value sm">${s.pct}%</div>
              <div class="metric-label">${s.sector}</div>
            </div>
          `).join("")}
        </div>
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Architecture
// ---------------------------------------------------------------------------

const PIPELINE_STAGES = [
  {
    num: "01", name: "CT Stream Ingestion",
    desc: "Mengumpulkan sertifikat domain baru dari Certificate Transparency log.",
    meta: "~10K+ domain/hari",
    detail: "Aliran A memantau TLD keluarga .id (co.id, go.id, ac.id, or.id, web.id) via ctlogs.dev. Aliran B menghasilkan kandidat typosquat dari watchlist institusi dan memverifikasinya lewat exact-domain lookup untuk TLD global murah (.xyz, .top).",
  },
  {
    num: "02", name: "Brand Filtering",
    desc: "Penyaringan string dan homoglyph tanpa memanggil LLM sama sekali.",
    meta: "0 token AI",
    detail: "Damerau-Levenshtein distance, normalisasi homoglyph (Cyrillic/Latin), deteksi punycode, dan pencocokan kata kunci brand dalam subdomain/hyphen — semua berjalan di CPU lokal.",
  },
  {
    num: "03", name: "Lightweight Verification",
    desc: "Verifikasi teknis murah sebelum kandidat sampai ke LLM.",
    meta: "RDAP + blacklist (cache)",
    detail: "HEAD-only live-check, umur domain via RDAP (cache TTL 7 hari), dan status blacklist publik (URLhaus). Domain resmi/instansi (.go.id) dikecualikan otomatis.",
  },
  {
    num: "04", name: "Risk Synthesis",
    desc: "Skoring gabungan sinyal teknis + linguistik, lalu pengelompokan kampanye.",
    meta: "Skor 0–100",
    detail: "Bobot teknis (~60%) dan linguistik (~40%) dijumlahkan jadi skor risiko. Domain dengan infrastruktur (nameserver) yang sama dikelompokkan sebagai satu kampanye. LLM hanya dipanggil untuk kandidat prioritas tinggi (skor ≥ 60).",
  },
];

async function renderArchitecture(root) {
  const metrics = await api("/api/metrics");

  root.innerHTML = pageShell({
    crumb: "Governance",
    title: "Architecture",
    desc: "Pipeline penyaringan bertingkat dari jutaan sertifikat menjadi temuan berprioritas.",
  });

  const body = document.getElementById("page-body");
  body.innerHTML = `
    <div class="section">
      <div class="panel">
        <div class="metric-row">
          <div class="metric">
            <div class="metric-value">${fmtInt(metrics.total_domains_scanned)}</div>
            <div class="metric-label">Total domain dipindai</div>
          </div>
          <div class="metric">
            <div class="metric-value">${metrics.peak_ram_mb}<span class="unit">MB</span></div>
            <div class="metric-label">Memori puncak API</div>
          </div>
          <div class="metric">
            <div class="metric-value">${metrics.collector_uptime_pct}<span class="unit">%</span></div>
            <div class="metric-label">Uptime collector</div>
          </div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-header"><h2 class="section-title">Pipeline pemrosesan</h2></div>
      <div class="pipeline" id="pipeline-stages"></div>
      <div id="pipeline-detail"></div>
    </div>
  `;

  const stagesEl = document.getElementById("pipeline-stages");
  stagesEl.innerHTML = PIPELINE_STAGES.map((s, i) => `
    <div class="pipeline-stage" data-i="${i}">
      <div class="pipeline-num">${s.num}</div>
      <div class="pipeline-name">${s.name}</div>
      <div class="pipeline-desc">${s.desc}</div>
      <div class="pipeline-meta">${s.meta}</div>
    </div>
  `).join("");

  stagesEl.querySelectorAll(".pipeline-stage").forEach((el) => {
    el.addEventListener("click", () => {
      const i = Number(el.dataset.i);
      state.pipelineOpen = state.pipelineOpen === i ? null : i;
      stagesEl.querySelectorAll(".pipeline-stage").forEach((s2, i2) => s2.classList.toggle("open", i2 === state.pipelineOpen));
      const detail = document.getElementById("pipeline-detail");
      detail.innerHTML = state.pipelineOpen !== null
        ? `<div class="pipeline-detail">${PIPELINE_STAGES[state.pipelineOpen].detail}</div>`
        : "";
    });
  });
}

// ---------------------------------------------------------------------------
// Compliance
// ---------------------------------------------------------------------------

const COMPLIANCE_ITEMS = [
  { title: "Penyimpanan hash SHA-256", desc: "Pesan pengguna yang dianalisis tidak pernah disimpan sebagai teks asli — hanya cryptographic hash." },
  { title: "Retensi otomatis 30 hari", desc: "Catatan hash pesan dihapus otomatis setelah 30 hari lewat job terjadwal, bukan janji manual." },
  { title: "Penyamaran domain default", desc: "Tampilan publik dashboard menyamarkan nama domain secara default untuk mencegah pencemaran nama tidak sengaja." },
  { title: "Isolasi laporan CSIRT", desc: "Draft laporan resmi hanya berisi indikator infrastruktur teknis — tidak pernah menyebut atau menyiratkan identitas orang." },
];

async function renderCompliance(root) {
  root.innerHTML = pageShell({
    crumb: "Governance",
    title: "Compliance",
    desc: "Kepatuhan UU PDP No. 27/2022 diterapkan di level arsitektur, bukan disclaimer.",
  });

  const body = document.getElementById("page-body");
  body.innerHTML = `
    <div class="section">
      <div class="section-header">
        <h2 class="section-title">UU PDP Compliance</h2>
        <span class="badge badge-success">${COMPLIANCE_ITEMS.length} / ${COMPLIANCE_ITEMS.length} kontrol aktif</span>
      </div>
      <div class="panel">
        ${COMPLIANCE_ITEMS.map((c) => `
          <div class="check-list-item">
            <span class="check-icon">${ICONS.check}</span>
            <div>
              <div class="check-title">${c.title}</div>
              <div class="check-desc">${c.desc}</div>
            </div>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Evaluation
// ---------------------------------------------------------------------------

async function renderEvaluation(root) {
  const metrics = await api("/api/metrics");

  root.innerHTML = pageShell({
    crumb: "Governance",
    title: "Evaluation",
    desc: "Kualitas deteksi diukur terhadap test set berlabel, dikalibrasi untuk memprioritaskan presisi.",
  });

  const body = document.getElementById("page-body");

  if (!metrics.metrics_available) {
    body.innerHTML = `<div class="panel"><div class="empty-state">Hasil evaluasi belum tersedia — jalankan scripts/run_eval.py.</div></div>`;
    return;
  }

  body.innerHTML = `
    <div class="section">
      <div class="section-header"><h2 class="section-title">Detection Quality</h2></div>
      <div class="panel">
        <div class="metric-row">
          <div class="metric">
            <div class="metric-value">${metrics.precision_pct}<span class="unit">%</span></div>
            <div class="metric-label">Precision</div>
          </div>
          <div class="metric">
            <div class="metric-value">${metrics.recall_pct}<span class="unit">%</span></div>
            <div class="metric-label">Recall</div>
          </div>
          <div class="metric">
            <div class="metric-value">${metrics.f1_score}</div>
            <div class="metric-label">F1 Score</div>
          </div>
        </div>
        <div class="mt-4 text-tertiary" style="font-size:12px;">
          Kalibrasi: ${metrics.calibration_status} · Diukur: ${fmtDate(metrics.eval_timestamp)}
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-header"><h2 class="section-title">Lead time deteksi</h2></div>
      <div class="panel">
        ${metrics.avg_lead_time_hours !== null
          ? `<div class="metric"><div class="metric-value">${metrics.avg_lead_time_hours}<span class="unit">jam</span></div><div class="metric-label">Rata-rata lebih dulu dari blacklist publik</div></div>`
          : `<div class="text-secondary" style="font-size:13px;">${metrics.lead_time_note}</div>`
        }
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

document.querySelectorAll(".nav-item[data-view]").forEach((el) => {
  el.addEventListener("click", () => setView(el.dataset.view));
});

// Refresh top bar health dot periodically
async function pollHealth() {
  try {
    const h = await api("/api/health");
    const el = document.getElementById("topbar-health");
    el.innerHTML = `<span class="dot ${h.is_healthy ? "ok" : "bad"}"></span>${h.is_healthy ? "Healthy" : "Degraded"}`;
  } catch (e) { /* silent */ }
}
pollHealth();
setInterval(pollHealth, 60000);

setView("overview");
