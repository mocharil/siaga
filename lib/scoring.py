"""Risk Scoring and Mode A Pipeline Module (T15).

Combines technical (~60%) and linguistic (~40%) signals into a calibrated 0-100 risk score,
maps them to risk levels (AMAN, HATI-HATI, INDIKASI PENIPUAN), and provides the full
end-to-end Mode A pipeline for analyzing user-submitted messages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import sqlite3
import time
import urllib.parse

from lib.extract import ExtractedEntities, extract_entities
from lib.llm import analyze_linguistics
from lib.rdap import DomainInfo, lookup
from lib.redirect import RedirectTrace, trace
from lib.similarity import find_similar

logger = logging.getLogger("siaga.scoring")

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "siaga.db"

# ------------------------------------------------------------------------------
# CALIBRATABLE CONSTANTS & WEIGHTS (Edit here for calibration in T21)
# ------------------------------------------------------------------------------

SCORING_WEIGHTS = {
    # Technical Signals (~60% group weight)
    "domain_age_under_7d": 30,
    "domain_age_under_30d": 20,
    "domain_age_under_90d": 10,
    "watchlist_similarity": 25,
    "punycode_or_homoglyph": 20,
    "risky_tld": 15,
    "multi_hop_redirect": 15,
    "unreachable_domain": 10,

    # Linguistic Signals (~40% group weight)
    "dangerous_request_credential": 30,  # otp, pin, password
    "dangerous_request_apk": 30,         # apk download/install
    "dangerous_request_transfer": 20,    # money transfer
    "urgency_high": 15,                  # urgency >= 2
    "urgency_medium": 8,                 # urgency == 1
    "false_authority_high": 20,          # false_authority >= 2
    "false_authority_medium": 10,        # false_authority == 1
    "prize_bait_high": 20,               # prize_bait >= 2
    "prize_bait_medium": 10,             # prize_bait == 1
}

RISK_THRESHOLDS = {
    "safe_max": 39,        # 0–39: AMAN
    "caution_max": 69,     # 40–69: HATI-HATI
    "fraud_min": 70,       # 70–100: INDIKASI PENIPUAN
}

RISKY_TLDS = {
    "xyz", "top", "online", "site", "vip", "live", "club", "store",
    "shop", "fun", "icu", "click", "rest", "surf", "fit", "work",
}

KNOWN_OFFICIAL_KEYWORDS = {
    "bca", "bri", "mandiri", "bni", "bsi", "btn", "cimb", "danamon",
    "permata", "mega", "ocbc", "panin", "btpn", "jenius", "jago",
    "dana", "ovo", "gopay", "shopee", "tokopedia", "pln", "pajak", "polri",
}


@dataclass
class SignalBreakdown:
    category: str       # "technical" | "linguistic"
    signal_name: str
    points: int
    explanation: str


@dataclass
class ScoringResult:
    score: int
    level: str          # "AMAN" | "HATI-HATI" | "INDIKASI PENIPUAN"
    breakdown: list[SignalBreakdown] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


@dataclass
class ModeAResult:
    raw_message_hash: str
    entities: ExtractedEntities
    rdap_info: DomainInfo | None
    redirect_trace: RedirectTrace | None
    linguistic_analysis: dict
    scoring: ScoringResult
    explanation: str
    latency_ms: int


def _init_scoring_tables(conn: sqlite3.Connection) -> None:
    """Initialize table for message analyses adhering to PDP privacy (storing hash, not text)."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS message_analyses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            received_at     TIMESTAMP NOT NULL,
            channel         TEXT DEFAULT 'telegram',
            message_hash    TEXT NOT NULL,
            urls_found      INTEGER DEFAULT 0,
            risk_score      INTEGER NOT NULL,
            risk_level      TEXT NOT NULL,
            latency_ms      INTEGER NOT NULL,
            report_drafted  BOOLEAN DEFAULT 0
        );
        """
    )
    conn.commit()


def _calculate_domain_age_days(registration_date_str: str | None) -> int | None:
    """Calculate domain age in days from registration ISO date string."""
    if not registration_date_str:
        return None
    try:
        clean_str = registration_date_str.replace("Z", "+00:00")
        reg_dt = datetime.fromisoformat(clean_str)
        now_dt = datetime.now(timezone.utc)
        return max(0, (now_dt - reg_dt).days)
    except Exception:
        return None


def score_risk(
    technical_signals: dict,
    linguistic_signals: dict,
) -> ScoringResult:
    """Combine technical and linguistic signals into calibrated 0-100 score and reasons."""
    breakdown: list[SignalBreakdown] = []
    reasons: list[str] = []

    tech_points = 0
    ling_points = 0

    # 1. Evaluate Technical Signals (~60%)
    domain_age_days = technical_signals.get("domain_age_days")
    if domain_age_days is not None:
        if domain_age_days < 7:
            pts = SCORING_WEIGHTS["domain_age_under_7d"]
            tech_points += pts
            breakdown.append(SignalBreakdown("technical", "domain_age_under_7d", pts, f"Domain sangat baru ({domain_age_days} hari)"))
            reasons.append(f"Domain baru didaftarkan {domain_age_days} hari yang lalu (indikator kuat situs penipuan sementara).")
        elif domain_age_days < 30:
            pts = SCORING_WEIGHTS["domain_age_under_30d"]
            tech_points += pts
            breakdown.append(SignalBreakdown("technical", "domain_age_under_30d", pts, f"Domain berumur {domain_age_days} hari (< 30 hari)"))
            reasons.append(f"Domain berumur kurang dari satu bulan ({domain_age_days} hari).")
        elif domain_age_days < 90:
            pts = SCORING_WEIGHTS["domain_age_under_90d"]
            tech_points += pts
            breakdown.append(SignalBreakdown("technical", "domain_age_under_90d", pts, f"Domain berumur {domain_age_days} hari (< 90 hari)"))

    if technical_signals.get("watchlist_matched"):
        matched_brand = technical_signals.get("matched_brand", "institusi resmi")
        pts = SCORING_WEIGHTS["watchlist_similarity"]
        tech_points += pts
        breakdown.append(SignalBreakdown("technical", "watchlist_similarity", pts, f"Mencatut nama/brand '{matched_brand}' pada domain bukan resmi"))
        reasons.append(f"Alamat domain mencatut nama '{matched_brand}' tetapi bukan domain resmi institusi tersebut.")

    if technical_signals.get("is_risky_tld"):
        tld = technical_signals.get("tld", "")
        pts = SCORING_WEIGHTS["risky_tld"]
        tech_points += pts
        breakdown.append(SignalBreakdown("technical", "risky_tld", pts, f"Menggunakan TLD berisiko tinggi (.{tld})"))
        reasons.append(f"Menggunakan ekstensi domain berisiko tinggi (.{tld}) yang lazim dipakai phishing murah.")

    if technical_signals.get("redirect_hops_count", 0) > 1:
        hops = technical_signals["redirect_hops_count"]
        pts = SCORING_WEIGHTS["multi_hop_redirect"]
        tech_points += pts
        breakdown.append(SignalBreakdown("technical", "multi_hop_redirect", pts, f"Melewati {hops} lompatan redirect"))
        reasons.append(f"URL disamarkan melalui {hops} tahapan pengalihan (redirect).")

    # 2. Evaluate Linguistic Signals (~40%)
    dangerous_requests = linguistic_signals.get("dangerous_request", [])
    if any(req in dangerous_requests for req in ["otp", "pin", "password"]):
        pts = SCORING_WEIGHTS["dangerous_request_credential"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "dangerous_request_credential", pts, "Meminta data rahasia (OTP / PIN / Password)"))
        reasons.append("Pesan meminta data rahasia sensitif (OTP/PIN/Kata Sandi) yang tidak pernah diminta oleh bank resmi.")

    if "apk" in dangerous_requests:
        pts = SCORING_WEIGHTS["dangerous_request_apk"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "dangerous_request_apk", pts, "Mengarahkan pengunduhan aplikasi APK berbahaya"))
        reasons.append("Pesan mengarahkan korban menginstal file aplikasi (.APK) di luar toko aplikasi resmi (potensi malware pencuri SMS/rekening).")

    if "transfer" in dangerous_requests:
        pts = SCORING_WEIGHTS["dangerous_request_transfer"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "dangerous_request_transfer", pts, "Meminta transfer dana / biaya aktivasi"))
        reasons.append("Pesan menuntut transfer uang atau biaya administrasi awal.")

    urgency = linguistic_signals.get("urgency", 0)
    if urgency >= 2:
        pts = SCORING_WEIGHTS["urgency_high"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "urgency_high", pts, f"Desakan waktu tinggi / ancaman (level {urgency})"))
        reasons.append("Menggunakan taktik manipulasi psikologis berupa desakan waktu dan ancaman agar korban panik.")
    elif urgency == 1:
        pts = SCORING_WEIGHTS["urgency_medium"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "urgency_medium", pts, "Desakan waktu sedang"))
        reasons.append("Terdapat indikasi desakan waktu untuk segera merespons.")

    false_authority = linguistic_signals.get("false_authority", 0)
    if false_authority >= 2:
        pts = SCORING_WEIGHTS["false_authority_high"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "false_authority_high", pts, f"Pencatutan otoritas / instansi resmi (level {false_authority})"))
        reasons.append("Mencatut nama institusi atau otoritas resmi dengan format pesan yang meniru pengumuman asli.")
    elif false_authority == 1:
        pts = SCORING_WEIGHTS["false_authority_medium"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "false_authority_medium", pts, "Penyebutan institusi"))
        reasons.append("Pesan mengatasnamakan institusi tertentu yang perlu diverifikasi keabsahannya.")

    prize_bait = linguistic_signals.get("prize_bait", 0)
    if prize_bait >= 2:
        pts = SCORING_WEIGHTS["prize_bait_high"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "prize_bait_high", pts, f"Iming-iming hadiah / uang tanpa dasar (level {prize_bait})"))
        reasons.append("Menjanjikan hadiah uang tunai atau saldo gratis yang tidak masuk akal.")
    elif prize_bait == 1:
        pts = SCORING_WEIGHTS["prize_bait_medium"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "prize_bait_medium", pts, "Iming-iming promo"))
        reasons.append("Menyebutkan penawaran hadiah atau promo yang menarik perhatian.")

    # 3. Combine and Cap Score
    raw_total = tech_points + ling_points
    score = min(100, max(0, raw_total))

    # 4. Map to Level
    if score >= RISK_THRESHOLDS["fraud_min"]:
        level = "INDIKASI PENIPUAN"
    elif score > RISK_THRESHOLDS["safe_max"]:
        level = "HATI-HATI"
    else:
        level = "AMAN"

    # Ensure at least 3 concrete reasons if flagged
    if not reasons:
        if level == "AMAN":
            reasons = [
                "Tidak ditemukan permintaan data rahasia seperti OTP, PIN, atau kata sandi.",
                "Struktur pesan wajar tanpa indikasi manipulasi psikologis atau desakan mendesak.",
                "Tidak ditemukan tautan berbahaya atau pengunduhan file tidak dikenal.",
            ]
        else:
            reasons = [
                "Karakteristik pesan menunjukkan pola penipuan digital.",
                "Terdapat ketidakwajaran pada instruksi atau tautan yang diberikan.",
                "Disarankan memverifikasi langsung melalui saluran resmi.",
            ]

    return ScoringResult(
        score=score,
        level=level,
        breakdown=breakdown,
        reasons=reasons,
    )


def _generate_user_explanation(result: ScoringResult) -> str:
    """Generate concise, layman-friendly explanation in Indonesian (max 5 sentences)."""
    if result.level == "INDIKASI PENIPUAN":
        header = f"🚨 *HASIL ANALISIS: INDIKASI PENIPUAN* (Skor Risiko: {result.score}/100)\n\n"
        body = "Pesan ini memiliki indikasi kuat penipuan digital karena:\n"
        for idx, reason in enumerate(result.reasons[:4], 1):
            body += f"{idx}. {reason}\n"
        body += "\n⚠️ *Saran:* JANGAN klik tautan, JANGAN kirim data apa pun, dan abaikan pesan ini."
        return header + body
    elif result.level == "HATI-HATI":
        header = f"⚠️ *HASIL ANALISIS: PERLU HATI-HATI* (Skor Risiko: {result.score}/100)\n\n"
        body = "Pesan ini memiliki beberapa hal mencurigakan:\n"
        for idx, reason in enumerate(result.reasons[:3], 1):
            body += f"{idx}. {reason}\n"
        body += "\n🔍 *Saran:* Verifikasi kebenaran informasi ini ke call center atau situs resmi sebelum merespons."
        return header + body
    else:
        header = f"✅ *HASIL ANALISIS: RELATIF AMAN* (Skor Risiko: {result.score}/100)\n\n"
        body = "Pesan ini tidak menunjukkan indikator penipuan atau permintaan data sensitif.\n"
        for idx, reason in enumerate(result.reasons[:3], 1):
            body += f"• {reason}\n"
        body += "\n🛡️ Tetap jaga kerahasiaan OTP dan PIN Anda di semua transaksi."
        return header + body


def analyze_message(
    message: str,
    db_path: Path | str | None = None,
    channel: str = "telegram",
) -> ModeAResult:
    """Execute complete end-to-end Mode A pipeline for a single user message.

    Workflow:
    1. Extract entities (URLs, phone numbers, bank accounts) via lib/extract.py
    2. Trace redirects (HEAD-only) via lib/redirect.py & check RDAP via lib/rdap.py
    3. Perform linguistic analysis via lib/llm.py
    4. Compute technical + linguistic risk score via score_risk()
    5. Formulate layman-friendly explanation (max 5 sentences)
    6. Record hashed message audit row in SQLite (UU PDP privacy compliant)
    """
    start_time = time.monotonic()
    resolved_db = Path(db_path) if db_path else DEFAULT_DB_PATH

    # PDP Privacy: compute message hash, NEVER store raw text in persistent log
    msg_hash = hashlib.sha256(message.strip().encode("utf-8")).hexdigest()

    # Step 1: Entity extraction
    entities = extract_entities(message)

    # Step 2: Technical investigation
    rdap_info: DomainInfo | None = None
    redirect_trace: RedirectTrace | None = None
    tech_signals: dict = {}

    if entities.urls:
        target_url = entities.urls[0]

        # Trace redirects HEAD-only
        redirect_trace = trace(target_url, max_hops=5, timeout=5.0)
        final_url = redirect_trace.final_url
        tech_signals["redirect_hops_count"] = len(redirect_trace.hops)

        # Parse domain
        parsed = urllib.parse.urlparse(final_url)
        domain = parsed.netloc.lower()
        if ":" in domain:
            domain = domain.split(":")[0]

        # Check risky TLD
        tld = domain.split(".")[-1]
        tech_signals["tld"] = tld
        tech_signals["is_risky_tld"] = tld in RISKY_TLDS

        # Check brand similarity against 200+ institution watchlist
        sim_matches = find_similar(domain)
        if sim_matches:
            tech_signals["watchlist_matched"] = True
            tech_signals["matched_brand"] = sim_matches[0].brand_name
            tech_signals["similarity_method"] = sim_matches[0].method

        # Query RDAP
        rdap_info = lookup(domain, db_path=resolved_db)
        if rdap_info and rdap_info.registration_date:
            tech_signals["domain_age_days"] = _calculate_domain_age_days(rdap_info.registration_date)

    # Step 3: Linguistic Analysis
    ling_signals = analyze_linguistics(message, db_path=resolved_db)

    # Step 4: Scoring
    scoring_result = score_risk(
        technical_signals=tech_signals,
        linguistic_signals=ling_signals,
    )

    # Step 5: Format explanation
    explanation = _generate_user_explanation(scoring_result)

    # Step 6: Log privacy-safe audit record in SQLite
    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        with sqlite3.connect(str(resolved_db)) as conn:
            _init_scoring_tables(conn)
            conn.execute(
                """
                INSERT INTO message_analyses (
                    received_at, channel, message_hash, urls_found, risk_score, risk_level, latency_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now_iso,
                    channel,
                    msg_hash,
                    len(entities.urls),
                    scoring_result.score,
                    scoring_result.level,
                    elapsed_ms,
                ),
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.warning("Failed to record message_analyses: %s", e)

    return ModeAResult(
        raw_message_hash=msg_hash,
        entities=entities,
        rdap_info=rdap_info,
        redirect_trace=redirect_trace,
        linguistic_analysis=ling_signals,
        scoring=scoring_result,
        explanation=explanation,
        latency_ms=elapsed_ms,
    )
