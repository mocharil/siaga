# SIAGA Dashboard — Feature & Data Reference

**Purpose of this document:** a complete, accurate inventory of every feature, page, and data
field currently available in the SIAGA dashboard, for handing off to an external design tool to
produce new mockups. This is a *content and data* spec, not a visual spec — it deliberately
avoids prescribing colors/layout so the redesign isn't anchored to the current build.

Source of truth: `dashboard/api.py` (backend) and `dashboard/static/app.js` (current frontend),
read directly from the codebase on 2026-09-03.

---

## 1. What SIAGA Is

SIAGA is a passive fraud/anomaly intelligence system for Indonesia. It watches Certificate
Transparency logs for newly registered domains that impersonate Indonesian institutions
(banks, e-commerce, logistics, government) and — as of this session — online gambling ("judol")
domains, including cases where a legitimate government/education domain has been hijacked with a
gambling subdomain. It also offers a manual "paste a suspicious message, get a risk score" tool.

The dashboard is a **read-only, operator-facing monitoring UI** — not the public product surface
(that's a Telegram bot). It runs locally and on a competition VPS, bound to `127.0.0.1` only.

---

## 2. Current Information Architecture (as built today)

8 flat navigation items, no grouping except a "Governance" label over the last 3:

1. Overview
2. Radar
3. Triage
4. Intelligence
5. Judol
6. *(Governance)* Architecture
7. *(Governance)* Compliance
8. *(Governance)* Evaluation

---

## 3. Feature-by-Feature Reference

### 3.1 Overview — landing/summary page

**Purpose:** at-a-glance daily snapshot + system health, with a shortcut into the detailed findings table.

**Data available** (`GET /api/stats/today`, `GET /api/metrics`, `GET /api/findings/top?limit=5`, `GET /api/health`):

| Field | Source | Type | Notes |
|---|---|---|---|
| `domains_scanned` | stats/today | int | domains scanned in the latest recorded day |
| `domains_flagged` | stats/today | int | flagged as suspicious that day |
| `domains_live` | stats/today | int | flagged domains confirmed responding (HEAD-check) |
| `total_findings_flagged` | metrics | int | cumulative all-time flagged count |
| top 5 findings | findings/top | array | see §3.2 fields — domain, brand, risk badge |
| `is_healthy` | health | bool | overall system health |
| `latest_collector_status` | health | string | `"ok" \| "partial" \| "failed"` |
| `collector_uptime_pct` | metrics | float | % of collector runs with status `ok` |
| `peak_ram_mb` | metrics | int | peak memory observed |
| `latest_collector_time` | health | ISO datetime | last collector run timestamp |

**Current interactions:** none besides a "View all →" link into Radar.

**Not currently shown but available:** `tahap1_passed`/`tahap2_passed`/`tahap3_assessed` (per-day
pipeline funnel counts — how many domains survived each filtering stage), `flagged_not_in_blacklist`
(flagged domains SIAGA caught before any public blacklist did — a strong "we're faster" claim),
`health.issues` (array of specific problem strings when unhealthy — currently only a healthy/
degraded dot is shown, the actual reasons are discarded).

---

### 3.2 Radar — phishing domain findings table

**Purpose:** the core detection table — every domain flagged as impersonating an Indonesian brand.

**Data available** (`GET /api/findings/top?limit=100&unmask=true`):

| Field | Type | Notes |
|---|---|---|
| `id` | int | primary key, used to fetch detail |
| `domain` / `domain_masked` / `raw_domain` | string | masked by default (see §7 Privacy Masking); `raw_domain` only populated when `unmask=true` |
| `first_seen` | ISO datetime (UTC) | when SIAGA's collector saw the certificate |
| `registered_at` | ISO datetime or null | domain registration date via RDAP |
| `registrar` | string or null | |
| `matched_brand` | string | e.g. "Bank Central Asia", "Ruangguru", "Pos Indonesia" |
| `match_method` | string enum | `keyword \| edit_distance \| homoglyph \| permutation` |
| `risk_score` | int 0–100 | |
| `risk_level` | string enum | `"INDIKASI PENIPUAN"` (fraud indication) / `"HATI-HATI"` (caution) / `"AMAN"` (safe) — **backend value, Indonesian; translate for display, don't rename in the API/DB** |
| `is_live` | bool | domain currently responds to a HEAD request |
| `in_public_blacklist` | bool | already listed on a public blacklist (URLhaus) at detection time |
| `campaign_id` | int or null | groups domains sharing infrastructure/brand pattern — **exists but nothing in the UI currently visualizes campaigns as groups** |
| `reasoning` | string | short human-readable explanation of the score |

**Current interactions:** search box (brand/domain substring), risk-level filter dropdown, sortable
by risk score (desc only currently), mask/unmask toggle, click a row → detail (see §3.2.1).

#### 3.2.1 Finding detail (currently a plain browser `alert()` — biggest under-built feature)

`GET /api/findings/{id}` returns far more than what's shown today:

| Field | Type | Notes |
|---|---|---|
| everything from the table row, plus: | | |
| `nameservers` | string | semicolon-joined nameserver list — **not shown anywhere today** |
| `csirt_report_draft` | string | a full auto-generated incident report draft, ready to submit — **not shown, not exportable, currently thrown away** |
| `escalation_channels` | array of `{name, target_type, contact, submission_method, notes}` | recommended organizations to report this domain to (e.g. PANDI, the impersonated bank's CSIRT, APJII) with contact info — **entirely unused in the UI today** |

**Design opportunity:** this is the single richest unused dataset in the app. A proper detail
drawer/modal with the CSIRT draft (copy-to-clipboard) and escalation channel cards would turn a
passive finding into an actionable one.

---

### 3.3 Judol — gambling domain findings table

**Purpose:** domains matching Indonesian online-gambling keywords, with a special flag for
domains that are actually hijacked government/education infrastructure (`.go.id`, `.ac.id`,
`.sch.id`, `.or.id`, `.desa.id`) — the platform's most credible, most "useful to Komdigi" signal.

**Data available** (`GET /api/judol?limit=200&unmask=true`):

| Field | Type | Notes |
|---|---|---|
| `domain` / `domain_masked` / `raw_domain` | string | same masking convention as Radar |
| `first_seen` | ISO datetime | |
| `matched_keywords` | array of strings | e.g. `["slot", "gacor"]` — which keywords matched |
| `is_hijacked_institution` | bool | true = official domain compromised, not just a new lookalike |
| `institution_suffix` | string or null | e.g. `"go.id"`, only set when hijacked |
| `detected_at` | ISO datetime | when the scan first recorded this row |
| (top-level) `total_findings` | int | |
| (top-level) `hijacked_institution_count` | int | |
| (top-level) `earliest_first_seen` | ISO datetime | oldest match in the dataset — used to prove multi-day real coverage |

**Current interactions:** mask/unmask toggle only — no search/filter yet (unlike Radar).

**Real data as of 2026-09-03:** 21 flagged domains, 2 hijacked institutions, spanning
Aug 28 – Sep 2, 2026 (real, not synthetic — see `lib/judol_detect.py`).

---

### 3.4 Intelligence — analytics / pattern breakdown

**Purpose:** aggregate patterns across all phishing findings — what's being impersonated, how,
and when.

**Data available** (`GET /api/stats/analytics`, `GET /api/findings/brands`):

**Currently rendered:**

| Field | Type | Notes |
|---|---|---|
| `brands.brands[]` = `{brand, count, max_score}` | | top 10 most-impersonated brands |
| `tld_distribution[]` = `{tld, count, pct, is_cctld, badge}` | | `badge` is `"ccTLD PANDI"` or `"gTLD Generic"` |
| `deception_tactics[]` = `{id, name, count, pct, desc}` | | 4 fixed technique categories (typosquat, keyword concatenation, homoglyph, subdomain spoofing) |
| `target_sectors[]` = `{sector, count, pct}` | | e.g. "Perbankan, Fintech & P2P", "Logistik & Ekspedisi", "E-Commerce & Travel", "EdTech & Edukasi", "BUMN & Institusi Publik", "Brand Komersial Lainnya" |

**Available but NOT currently rendered anywhere in the app** — genuinely unused data, strong
candidates for the redesign:

| Field | Type | Notes |
|---|---|---|
| `hourly_velocity.series[]` = `{hour, label, count}` × 24 | | full 24-hour registration-time distribution of attacks — a natural line/bar chart, completely absent from the current UI |
| `hourly_velocity.peak_hour` / `peak_count` | | the single busiest hour, e.g. "which hour do attackers register the most domains" |
| `dual_stream.proactive` = `{source, total_scanned, findings_flagged, infrastructure_clusters}` | | the CT-log/DNS side of detection |
| `dual_stream.reactive` = `{source, total_analyzed, fraud_detected, caution_detected, safe_verified}` | | the Telegram-bot crowdsourced side (`@siaga_ai_bot`) |
| `dual_stream.lead_time_advantage_hours` / `lead_time_status` | | "SIAGA detected this +N hours before it hit a public blacklist" — a headline competitive-advantage metric, currently only surfaced (weakly) on the Evaluation page, not here where the rest of the analytics live |

**Design opportunity:** the "dual stream" concept (passive CT scanning vs. reactive
crowdsourced Telegram reports) is a core architectural differentiator of the whole project and
currently has almost no visual presence. A side-by-side "two intelligence streams" comparison
card would tell that story much better than the current scattered treatment.

---

### 3.5 Triage — manual message/URL analyzer

**Purpose:** paste a suspicious message or URL, get an instant risk assessment. Nothing is
persisted (privacy-by-design — see §7).

**Request:** `POST /api/analyze { text: string }`

**Response fields:**

| Field | Type | Notes |
|---|---|---|
| `score` | int 0–100 | |
| `level` | string enum | same 3 Indonesian values as `risk_level` above |
| `reasons[]` | array of strings | short bullet reasons — **currently the only thing shown** |
| `explanation` | string | a longer natural-language explanation — **not shown** |
| `breakdown[]` = `{category, signal_name, points, explanation}` | | full signal-by-signal scoring ledger (e.g. "brand keyword match: +25", "risky TLD: +10") — **not shown; this is the single best way to make the tool feel transparent/trustworthy, and it's being discarded** |
| `entities.urls[]` / `entities.phone_numbers[]` / `entities.bank_accounts[]` | arrays of strings | extracted from the pasted text — **not shown** |
| `latency_ms` | int | how fast the analysis ran — **not shown, would be a nice "look how fast" touch** |

**Current interactions:** textarea + "Analyze" button → colored risk band + plain bullet list.

**Design opportunity:** the current result view is the thinnest in the app relative to how much
data the backend actually returns. A results panel with a score gauge, a collapsible signal
breakdown (like a "why" ledger), and highlighted extracted entities would use all of it.

---

### 3.6 Architecture — pipeline visualization

**Purpose:** explain the 4-stage filtering pipeline to a technical judge/reader.

**Data:** mostly static content (not from an API), plus 3 metrics from `GET /api/metrics`
(`total_domains_scanned`, `peak_ram_mb`, `collector_uptime_pct`) that duplicate numbers already
shown on Overview.

**The 4 pipeline stages** (static copy, each with a number, name, one-line description, a
"meta" tag, and a longer detail shown on click):

1. **CT Stream Ingestion** — ~10K+ domains/day. Two collection streams: Stream A watches the
   `.id` TLD family via ctlogs.dev; Stream B generates typosquat candidates from an institution
   watchlist and verifies them against cheap global TLDs (`.xyz`, `.top`).
2. **Brand Filtering** — 0 AI tokens spent. Damerau-Levenshtein distance, homoglyph
   normalization, punycode detection, brand-keyword matching — all local CPU, no LLM call.
3. **Lightweight Verification** — RDAP + blacklist, cached. HEAD-only liveness check, domain
   age via RDAP (7-day cache), public blacklist status. Official domains auto-excluded.
4. **Risk Synthesis** — score 0–100. ~60% technical weight + ~40% linguistic weight, then
   campaign clustering by shared infrastructure. LLM only called for score ≥ 60 candidates.

**Current interactions:** click a stage to expand its detail (accordion-style, one open at a time).

**Design opportunity:** since the 3 top metrics here are redundant with Overview, a redesign could
drop them from this page entirely and let it be pure pipeline storytelling.

---

### 3.7 Compliance — privacy/legal checklist

**Purpose:** demonstrate UU PDP (Indonesian data protection law) compliance is architectural, not
a disclaimer.

**Data:** fully static, 4 fixed items, each `{title, description}`:

1. **SHA-256 message hashing** — analyzed messages are never stored as raw text, only a hash.
2. **Automatic 30-day retention** — hash records are purged by a scheduled job, not a manual promise.
3. **Domain masking by default** — public dashboard view masks domain names to prevent accidental defamation.
4. **Isolated CSIRT reports** — report drafts contain only technical indicators, never a person's identity.

**Current interactions:** none, static checklist with a "4/4 active" badge.

---

### 3.8 Evaluation — detection quality metrics

**Purpose:** show real (never fabricated — hard project rule) precision/recall against a labeled test set.

**Data available** (`GET /api/metrics`):

| Field | Type | Notes |
|---|---|---|
| `metrics_available` | bool | false until `scripts/run_eval.py` has been run at least once |
| `precision_pct` / `recall_pct` | float or null | |
| `f1_score` | float or null | |
| `calibration_status` | string | e.g. `"calibrated (2026-08-29)"` or `"uncalibrated"` |
| `eval_timestamp` | ISO datetime or null | |
| `avg_lead_time_hours` | float or null | average hours SIAGA detected a domain before it hit a public blacklist |
| `lead_time_note` | string or null | honest fallback text when there isn't enough data yet — **the project has a hard rule against ever faking this number, so the empty/null state needs to look intentional, not broken** |

**Current interactions:** none, static metric display.

---

## 4. Full Endpoint Reference (quick lookup)

All are `GET` except `/api/analyze` (`POST`). All are read-only against SQLite; no endpoint
accepts a request that mutates data.

| Endpoint | Used by current UI? | One-line purpose |
|---|---|---|
| `/api/stats/today` | Overview | latest day's funnel + flag counts |
| `/api/stats/trend?days=N` (1–90) | **No — entirely unused** | historical daily series: scanned/flagged/live/ram over N days, chronological |
| `/api/stats/analytics` | Intelligence (partially) | 5-module analytics: TLD dist, tactics, hourly velocity, sectors, dual-stream |
| `/api/findings/top?limit=&unmask=` | Overview, Radar | ranked phishing findings |
| `/api/findings/brands` | Intelligence | top 10 impersonated brands |
| `/api/findings/{id}` | Radar (barely — plain alert) | full finding detail + CSIRT draft + escalation channels |
| `/api/judol?limit=&unmask=` | Judol | gambling domain findings |
| `/api/analyze` (POST) | Triage (partially) | real-time message/URL scoring |
| `/api/metrics` | Overview, Architecture, Evaluation | uptime, RAM, eval scores, lead time |
| `/api/health` | Overview, topbar | operational health + issue list |

**`/api/stats/trend` is a fully-built, fully-working endpoint with zero frontend consumer.** If
the redesign wants a real historical trend chart (line/area chart of daily scan volume, flags,
etc. over the last 2–4 weeks), the data is already there — no backend work needed.

---

## 5. Cross-Cutting Concepts to Know Before Designing

### 5.1 Privacy masking (`mask_domain`)

Domain names are masked by default everywhere (Radar, Judol, Overview's findings list) to avoid
displaying a possibly-innocent domain's full name in a screenshot/recording without cause. Rule:

- stem ≤ 3 chars → `f***.tld`
- stem ≤ 6 chars → `ab***c.tld`
- stem ≤ 10 chars → `abc***yz.tld`
- stem > 10 chars → `abcd***xyz.tld`

Every masked-domain-bearing endpoint accepts `?unmask=true` to return the real value. The
current toggle button is a client-side show/hide over data fetched unmasked once — there's no
extra network round-trip when toggling.

### 5.2 Risk level values are Indonesian at the data layer, on purpose

`"INDIKASI PENIPUAN"` / `"HATI-HATI"` / `"AMAN"` come straight from `lib/scoring.py`, which is
also what drives the public-facing Telegram bot's messages to end users (who are Indonesian).
**Do not ask to rename these in the API/database** — any English-language redesign should
translate for *display only* (e.g. a small lookup table: Fraud Indication / Caution / Safe),
leaving the backend values untouched.

### 5.3 Zero external network dependency (hard constraint if this gets rebuilt)

The current build has an automated test (`test_zero_external_cdn_dependencies`) asserting the
dashboard never loads a script/stylesheet/font from a remote CDN and never calls `fetch()` to an
external host. It must work fully offline apart from same-origin API calls. Any new implementation
that inherits this codebase should keep that property — worth telling the design tool if it likes
to suggest Google Fonts, icon CDNs, or hosted UI kits.

### 5.4 Deployment footprint

Runs identically in two places right now: the developer's laptop and a competition VPS (bound to
`127.0.0.1:8000`, reverse-tunnel access only). No public internet exposure. This is relevant if a
redesign considers any "live/shared" features (comments, multi-user cursors, etc.) — there is
currently exactly one operator viewing this at a time, no auth system exists.

---

## 6. Known Rough Edges in the Current Build (context for *why* a redesign was requested)

- Very flat/plain visual treatment — minimal color, minimal hierarchy, large unstyled areas.
- Long masked domain strings and status badges could wrap onto two lines inside table cells,
  making rows uneven (this specific bug was patched, but is a symptom of not designing table
  cells with real long-content data in mind from the start).
- 8 flat nav items with 3 awkwardly grouped under "Governance" — Radar/Judol/Intelligence all
  operate on conceptually the same "findings" data and could plausibly be one section; Architecture/
  Compliance/Evaluation are all low-interactivity reference pages and could plausibly be one section.
- Several genuinely interesting datasets (24h attack velocity, dual-stream telemetry, CSIRT
  report drafts, scoring breakdowns, extracted entities) are computed by the backend and then
  thrown away by the frontend — see §3.2.1, §3.4, §3.5 above for the specific opportunities.
- All UI copy is currently in Indonesian; the intended dashboard language going forward is English
  (the backend data values are the one exception — see §5.2).

---

## 7. Suggested Reading Order for a Mockup Tool

1. §1–2 for what the product is and its current shape.
2. §3 in full — this is the actual content inventory to design screens for.
3. §5 for the 2–3 rules that constrain any layout (masking, Indonesian data values, offline-only).
4. §4 as a lookup table once specific screens are being drafted, to confirm exact field names.
