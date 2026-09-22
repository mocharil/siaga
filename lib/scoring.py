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

    # Linguistic Signals (~40% group weight - calibrated in T21)
    "dangerous_request_credential": 35,  # otp, pin, password
    "dangerous_request_apk": 50,         # apk download/install (Sniffer APK)
    "dangerous_request_transfer": 30,    # money transfer / deposit / advance fee
    "urgency_high": 20,                  # urgency >= 2
    "urgency_medium": 8,                 # urgency == 1
    "false_authority_high": 25,          # false_authority >= 2
    "false_authority_medium": 10,        # false_authority == 1
    "prize_bait_high": 25,               # prize_bait >= 2
    "prize_bait_medium": 10,             # prize_bait == 1
    "unofficial_chat_channel": 15,       # t.me / wa.me link for sensitive transaction
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
    try:
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
    except Exception as e:
        logger.debug("Failed to init scoring tables (read-only filesystem): %s", e)


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
            breakdown.append(SignalBreakdown("technical", "domain_age_under_7d", pts, f"Domain sangat baru ({domain_age_days} hari) / Very new domain ({domain_age_days} days)"))
            reasons.append(f"Domain baru didaftarkan {domain_age_days} hari yang lalu (indikator kuat situs penipuan sementara). / Domain was registered {domain_age_days} days ago (a strong indicator of a temporary fraud site).")
            breakdown.append(SignalBreakdown("technical", "domain_age_under_7d", pts, f"Very new domain ({domain_age_days} days)"))
            reasons.append(f"Domain was registered {domain_age_days} days ago (strong indicator of temporary fraud infrastructure).")
        elif domain_age_days < 30:
            pts = SCORING_WEIGHTS["domain_age_under_30d"]
            tech_points += pts
            breakdown.append(SignalBreakdown("technical", "domain_age_under_30d", pts, f"Domain berumur {domain_age_days} hari (< 30 hari) / Domain age {domain_age_days} days (< 30 days)"))
            reasons.append(f"Domain berumur kurang dari satu bulan ({domain_age_days} hari). / Domain is less than one month old ({domain_age_days} days).")
            breakdown.append(SignalBreakdown("technical", "domain_age_under_30d", pts, f"Domain age {domain_age_days} days (< 30 days)"))
            reasons.append(f"Domain is less than one month old ({domain_age_days} days).")
        elif domain_age_days < 90:
            pts = SCORING_WEIGHTS["domain_age_under_90d"]
            tech_points += pts
            breakdown.append(SignalBreakdown("technical", "domain_age_under_90d", pts, f"Domain berumur {domain_age_days} hari (< 90 hari) / Domain age {domain_age_days} days (< 90 days)"))
            breakdown.append(SignalBreakdown("technical", "domain_age_under_90d", pts, f"Domain age {domain_age_days} days (< 90 days)"))

    if technical_signals.get("watchlist_matched"):
        matched_brand = technical_signals.get("matched_brand", "institusi resmi / official institution")
        matched_brand = technical_signals.get("matched_brand", "official institution")
        pts = SCORING_WEIGHTS["watchlist_similarity"]
        tech_points += pts
        breakdown.append(SignalBreakdown("technical", "watchlist_similarity", pts, f"Mencatut nama/brand '{matched_brand}' pada domain bukan resmi / Impersonates name/brand '{matched_brand}' on a non-official domain"))
        reasons.append(f"Alamat domain mencatut nama '{matched_brand}' tetapi bukan domain resmi institusi tersebut. / Domain address impersonates the name '{matched_brand}' but is not that institution's official domain.")
        breakdown.append(SignalBreakdown("technical", "watchlist_similarity", pts, f"Impersonates name/brand '{matched_brand}' on a non-official domain"))
        reasons.append(f"Domain address impersonates the name '{matched_brand}' but is not that institution's official domain.")

    if technical_signals.get("is_risky_tld"):
        tld = technical_signals.get("tld", "")
        pts = SCORING_WEIGHTS["risky_tld"]
        tech_points += pts
        breakdown.append(SignalBreakdown("technical", "risky_tld", pts, f"Menggunakan TLD berisiko tinggi (.{tld}) / Uses a high-risk TLD (.{tld})"))
        reasons.append(f"Menggunakan ekstensi domain berisiko tinggi (.{tld}) yang lazim dipakai phishing murah. / Uses a high-risk domain extension (.{tld}) commonly used for cheap phishing.")
        breakdown.append(SignalBreakdown("technical", "risky_tld", pts, f"Uses a high-risk TLD (.{tld})"))
        reasons.append(f"Uses a high-risk domain extension (.{tld}) commonly associated with disposable phishing campaigns.")

    if technical_signals.get("redirect_hops_count", 0) > 1:
        hops = technical_signals["redirect_hops_count"]
        pts = SCORING_WEIGHTS["multi_hop_redirect"]
        tech_points += pts
        breakdown.append(SignalBreakdown("technical", "multi_hop_redirect", pts, f"Melewati {hops} lompatan redirect / Passes through {hops} redirect hops"))
        reasons.append(f"URL disamarkan melalui {hops} tahapan pengalihan (redirect). / URL is disguised through {hops} redirect hops.")
        breakdown.append(SignalBreakdown("technical", "multi_hop_redirect", pts, f"Passes through {hops} redirect hops"))
        reasons.append(f"URL is disguised through {hops} redirect hops.")

    # 2. Evaluate Linguistic Signals (~40%)
    dangerous_requests = linguistic_signals.get("dangerous_request", [])
    if any(req in dangerous_requests for req in ["otp", "pin", "password"]):
        pts = SCORING_WEIGHTS["dangerous_request_credential"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "dangerous_request_credential", pts, "Meminta data rahasia (OTP / PIN / Password) / Requests secret data (OTP / PIN / Password)"))
        reasons.append("Pesan meminta data rahasia sensitif (OTP/PIN/Kata Sandi) yang tidak pernah diminta oleh bank resmi. / Message requests sensitive secret data (OTP/PIN/Password) that an official bank would never ask for.")
        breakdown.append(SignalBreakdown("linguistic", "dangerous_request_credential", pts, "Requests confidential credentials (OTP / PIN / Password)"))
        reasons.append("Message requests sensitive credentials (OTP/PIN/Password) never requested by genuine financial institutions.")

    if "apk" in dangerous_requests:
        pts = SCORING_WEIGHTS["dangerous_request_apk"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "dangerous_request_apk", pts, "Mengarahkan pengunduhan aplikasi APK berbahaya / Directs download of a dangerous APK app"))
        reasons.append("Pesan mengarahkan korban menginstal file aplikasi (.APK) di luar toko aplikasi resmi (potensi malware pencuri SMS/rekening). / Message directs the victim to install an app file (.APK) outside the official app store (potential SMS/account-stealing malware).")
        breakdown.append(SignalBreakdown("linguistic", "dangerous_request_apk", pts, "Directs download of untrusted APK application"))
        reasons.append("Message directs the recipient to install an app file (.APK) outside official app stores (potential SMS/account-stealing malware).")

    if "transfer" in dangerous_requests:
        pts = SCORING_WEIGHTS["dangerous_request_transfer"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "dangerous_request_transfer", pts, "Meminta transfer dana / biaya aktivasi / Requests a fund transfer / activation fee"))
        reasons.append("Pesan menuntut transfer uang atau biaya administrasi awal. / Message demands a money transfer or an upfront administrative fee.")
        breakdown.append(SignalBreakdown("linguistic", "dangerous_request_transfer", pts, "Demands fund transfer or activation fee"))
        reasons.append("Message demands an immediate fund transfer or upfront administrative activation fee.")

    urgency = linguistic_signals.get("urgency", 0)
    if urgency >= 2:
        pts = SCORING_WEIGHTS["urgency_high"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "urgency_high", pts, f"Desakan waktu tinggi / ancaman (level {urgency}) / High time pressure / threat (level {urgency})"))
        reasons.append("Menggunakan taktik manipulasi psikologis berupa desakan waktu dan ancaman agar korban panik. / Uses psychological manipulation via time pressure and threats to panic the victim.")
        breakdown.append(SignalBreakdown("linguistic", "urgency_high", pts, f"High time pressure / threat (level {urgency})"))
        reasons.append("Employs psychological manipulation via strict time limits and threats to panic the recipient.")
    elif urgency == 1:
        pts = SCORING_WEIGHTS["urgency_medium"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "urgency_medium", pts, "Desakan waktu sedang / Moderate time pressure"))
        reasons.append("Terdapat indikasi desakan waktu untuk segera merespons. / There is an indication of pressure to respond immediately.")
        breakdown.append(SignalBreakdown("linguistic", "urgency_medium", pts, "Moderate time pressure"))
        reasons.append("Presents artificial urgency demanding an immediate response.")

    false_authority = linguistic_signals.get("false_authority", 0)
    if false_authority >= 2:
        pts = SCORING_WEIGHTS["false_authority_high"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "false_authority_high", pts, f"Pencatutan otoritas / instansi resmi (level {false_authority}) / Impersonation of an authority / official institution (level {false_authority})"))
        reasons.append("Mencatut nama institusi atau otoritas resmi dengan format pesan yang meniru pengumuman asli. / Impersonates the name of an institution or official authority using a message format mimicking a genuine announcement.")
        breakdown.append(SignalBreakdown("linguistic", "false_authority_high", pts, f"Impersonation of authority or official institution (level {false_authority})"))
        reasons.append("Impersonates the name of an institution or official authority using a format mimicking genuine announcements.")
    elif false_authority == 1:
        pts = SCORING_WEIGHTS["false_authority_medium"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "false_authority_medium", pts, "Penyebutan institusi / Mentions an institution"))
        reasons.append("Pesan mengatasnamakan institusi tertentu yang perlu diverifikasi keabsahannya. / Message claims to be from a specific institution whose authenticity needs verification.")
        breakdown.append(SignalBreakdown("linguistic", "false_authority_medium", pts, "Mentions an official institution"))
        reasons.append("Claims to originate from an institution whose authenticity requires independent verification.")

    prize_bait = linguistic_signals.get("prize_bait", 0)
    if prize_bait >= 2:
        pts = SCORING_WEIGHTS["prize_bait_high"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "prize_bait_high", pts, f"Iming-iming hadiah / uang tanpa dasar (level {prize_bait}) / Baseless prize/cash bait (level {prize_bait})"))
        reasons.append("Menjanjikan hadiah uang tunai atau saldo gratis yang tidak masuk akal. / Promises an implausible cash prize or free balance.")
        breakdown.append(SignalBreakdown("linguistic", "prize_bait_high", pts, f"Unsubstantiated prize or cash bait (level {prize_bait})"))
        reasons.append("Promises implausible cash prizes or complimentary account balances.")
    elif prize_bait == 1:
        pts = SCORING_WEIGHTS["prize_bait_medium"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "prize_bait_medium", pts, "Iming-iming promo / Promo bait"))
        reasons.append("Menyebutkan penawaran hadiah atau promo yang menarik perhatian. / Mentions an eye-catching prize or promo offer.")
        breakdown.append(SignalBreakdown("linguistic", "prize_bait_medium", pts, "Promotional or bonus incentive"))
        reasons.append("Mentions an eye-catching promotional offer or reward incentive.")

    if linguistic_signals.get("unofficial_chat_channel"):
        pts = SCORING_WEIGHTS["unofficial_chat_channel"]
        ling_points += pts
        breakdown.append(SignalBreakdown("linguistic", "unofficial_chat_channel", pts, "Mengarahkan transaksi ke saluran chat pribadi non-resmi / Directs the transaction to an unofficial private chat channel"))
        reasons.append("Mengarahkan transaksi finansial/verifikasi ke kontak chat pribadi (WhatsApp/Telegram). / Directs financial transactions/verification to a private chat contact (WhatsApp/Telegram).")
        breakdown.append(SignalBreakdown("linguistic", "unofficial_chat_channel", pts, "Directs transaction to unofficial private chat channel"))
        reasons.append("Directs financial transactions or verification to private messaging contacts (WhatsApp/Telegram).")

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
                "Tidak ditemukan permintaan data rahasia seperti OTP, PIN, atau kata sandi. / No request for secret data such as OTP, PIN, or password was found.",
                "Struktur pesan wajar tanpa indikasi manipulasi psikologis atau desakan mendesak. / The message structure is normal, with no sign of psychological manipulation or urgent pressure.",
                "Tidak ditemukan tautan berbahaya atau pengunduhan file tidak dikenal. / No malicious link or unknown file download was found.",
                "No requests for confidential credentials such as OTP, PIN, or password were found.",
                "Message phrasing is consistent with normal notices without coercive urgency or threats.",
                "No malicious links or unauthorized file downloads detected.",
            ]
        else:
            reasons = [
                "Karakteristik pesan menunjukkan pola penipuan digital. / The message's characteristics show a digital fraud pattern.",
                "Terdapat ketidakwajaran pada instruksi atau tautan yang diberikan. / There is something irregular about the given instructions or link.",
                "Disarankan memverifikasi langsung melalui saluran resmi. / Direct verification through an official channel is recommended.",
                "Message characteristics match digital fraud behavioral patterns.",
                "Irregularities identified in the provided instructions or destination link.",
                "Direct verification through official institutional channels is strongly recommended.",
            ]

    return ScoringResult(
        score=score,
        level=level,
        breakdown=breakdown,
        reasons=reasons,
    )


def _generate_user_explanation(result: ScoringResult) -> str:
    """Generate a concise, layman-friendly explanation, in paired Indonesian/
    English lines (demo-video-showcase branch only; max 5 sentences per
    language). The Indonesian text is the real message a Telegram user
    would read -- it must never be altered from what a real Mode A reply
    needs. The English half is appended purely so an English-language
    reader can follow along.
    """
    """Generate a concise, layman-friendly explanation in English."""
    if result.level == "INDIKASI PENIPUAN":
        header = f"🚨 *HASIL ANALISIS: INDIKASI PENIPUAN* (Skor Risiko: {result.score}/100)\n🚨 *ANALYSIS RESULT: FRAUD INDICATION* (Risk Score: {result.score}/100)\n\n"
        body = "Pesan ini memiliki indikasi kuat penipuan digital karena: / This message shows a strong indication of digital fraud because:\n"
        header = f"🚨 *ANALYSIS RESULT: INDIKASI PENIPUAN / FRAUD INDICATION* (Risk Score: {result.score}/100)\n\n"
        header = f"🚨 *ANALYSIS RESULT: FRAUD INDICATION / INDIKASI PENIPUAN* (Risk Score: {result.score}/100)\n\n"
        body = "This message shows strong indicators of digital fraud:\n"
        for idx, reason in enumerate(result.reasons[:4], 1):
            body += f"{idx}. {reason}\n"
        body += "\n⚠️ *Saran:* JANGAN klik tautan, JANGAN kirim data apa pun, dan abaikan pesan ini.\n⚠️ *Advice:* Do NOT click the link, do NOT send any data, and ignore this message."
        body += "\n⚠️ *Advice:* Do NOT click any links, do NOT provide sensitive credentials, and ignore this message."
        return header + body
    elif result.level == "HATI-HATI":
        header = f"⚠️ *HASIL ANALISIS: PERLU HATI-HATI* (Skor Risiko: {result.score}/100)\n⚠️ *ANALYSIS RESULT: CAUTION NEEDED* (Risk Score: {result.score}/100)\n\n"
        body = "Pesan ini memiliki beberapa hal mencurigakan: / This message has a few suspicious elements:\n"
        header = f"⚠️ *ANALYSIS RESULT: HATI-HATI / CAUTION NEEDED* (Risk Score: {result.score}/100)\n\n"
        header = f"⚠️ *ANALYSIS RESULT: CAUTION NEEDED / HATI-HATI* (Risk Score: {result.score}/100)\n\n"
        body = "This message contains suspicious indicators:\n"
        for idx, reason in enumerate(result.reasons[:3], 1):
            body += f"{idx}. {reason}\n"
        body += "\n🔍 *Saran:* Verifikasi kebenaran informasi ini ke call center atau situs resmi sebelum merespons.\n🔍 *Advice:* Verify this information via an official call center or website before responding."
        body += "\n🔍 *Advice:* Verify this communication through official institutional channels before responding."
        return header + body
    else:
        header = f"✅ *HASIL ANALISIS: RELATIF AMAN* (Skor Risiko: {result.score}/100)\n✅ *ANALYSIS RESULT: RELATIVELY SAFE* (Risk Score: {result.score}/100)\n\n"
        body = "Pesan ini tidak menunjukkan indikator penipuan atau permintaan data sensitif. / This message shows no fraud indicators or sensitive-data requests.\n"
        header = f"✅ *ANALYSIS RESULT: AMAN / RELATIVELY SAFE* (Risk Score: {result.score}/100)\n\n"
        body = "This message shows no active fraud indicators or unauthorized credential requests.\n"
        header = f"✅ *ANALYSIS RESULT: RELATIVELY SAFE / AMAN* (Risk Score: {result.score}/100)\n\n"
        body = "This message shows no active fraud indicators or unauthorized credential requests:\n"
        for idx, reason in enumerate(result.reasons[:3], 1):
            body += f"• {reason}\n"
        body += "\n🛡️ Tetap jaga kerahasiaan OTP dan PIN Anda di semua transaksi.\n🛡️ Always keep your OTP and PIN confidential in every transaction."
        body += "\n🛡️ *Security Reminder:* Always keep your OTP, PIN, and passwords confidential."
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

    # Check for sensitive transaction redirect to unofficial chat channel (wa.me / t.me)
    if any(u in message.lower() for u in ["wa.me/", "t.me/", "chat.whatsapp.com/"]):
        if ling_signals.get("false_authority", 0) > 0 or ling_signals.get("urgency", 0) > 0 or "transfer" in ling_signals.get("dangerous_request", []):
            ling_signals["unofficial_chat_channel"] = True

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
    except Exception as e:
        logger.debug("Failed to record message_analyses (likely read-only DB): %s", e)

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
