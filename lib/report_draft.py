"""Report Draft Generator for Official Incident Reporting (T27).

Generates structured abuse / phishing notification drafts for official reporting channels
(AduanKonten Kominfo, PANDI Abuse, BSSN CSIRT, OJK 157, and Domain Registrars).

Strict compliance rules (CLAUDE.md #3 & #5):
1. Language ALWAYS uses "indikasi" (indicated), never "terbukti" (proven).
2. Contains ONLY technical infrastructure data (domain, IP/DNS, timestamps, certificates).
3. NEVER contains personal identities, phone numbers, or bank account numbers.
4. Human-in-the-loop mandatory: Drafts are prepared for human review and manual submission.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from pathlib import Path
import sqlite3
import sys
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

logger = logging.getLogger("siaga.report_draft")

DEFAULT_DB_PATH = BASE_DIR / "data" / "siaga.db"
WIB = ZoneInfo("Asia/Jakarta")


@dataclass
class ReportingChannel:
    name: str
    target_type: str
    contact: str
    submission_method: str
    notes: str


@dataclass
class ReportDraft:
    finding_id: int
    domain: str
    matched_brand: str
    risk_score: int
    risk_level: str
    first_seen_wib: str
    is_live: bool
    match_method: str
    registrar: str | None
    nameservers: str | None
    recommended_channels: list[ReportingChannel] = field(default_factory=list)
    draft_text: str = ""


def get_recommended_channels(domain: str, brand: str) -> list[ReportingChannel]:
    """Determine official escalation channels based on domain TLD and targeted brand.

    Source Verifications:
    - Kominfo AduanKonten: https://www.aduankonten.id/kontak-kami & https://aptika.kominfo.go.id/kontak/ (Aug 2026)
    - PANDI Hubungi Kami & IDADX: https://pandi.id/kontak & https://idadx.id/report (Aug 2026)
    - OJK 157 & Satgas PASTI: https://x.com/ojkindonesia/status/1704793665238077502 & https://kontak157.ojk.go.id (Aug 2026)
    - BSSN Gov-CSIRT: https://www.bssn.go.id/aduan-siber/ & https://idsirtii.or.id/halaman/tentang/rfc-2350-gov-csirt-indonesia.html (Aug 2026)
    """
    # Bilingual ID/EN pairing (demo-video-showcase branch only): the real
    # submission channel names/target types/notes stay in Indonesian first
    # since that's the language these Indonesian agencies actually operate
    # in, paired with an English gloss so an English-language dashboard
    # reader can still follow along. See lib/report_draft.py docstring --
    # the generated draft_text itself must remain submittable as-is.
    channels: list[ReportingChannel] = [
        # Verified via https://www.aduankonten.id/kontak-kami (Aug 2026)
        ReportingChannel(
            name="Aduan Konten Kominfo RI / Kominfo RI Content Complaint",
            target_type="Regulator Konten Negatif & Pemblokiran / Negative Content Regulator & Blocking Authority",
            contact="aduankonten@kominfo.go.id | WA: 08119224545",
            submission_method="Portal Resmi (https://www.aduankonten.id) / Email (aduankonten@kominfo.go.id)",
            notes="Kanal resmi pemerintah untuk pemblokiran akses internet & normalisasi DNS trust positif. / Official government channel for internet access blocking & TrustPositif DNS normalization.",
        )
    ]

    clean_dom = domain.lower().strip()
    # Check if .id domain
    # Verified via https://pandi.id/kontak (Telp: +62-21-30055777) & https://idadx.id/report (Abuse Desk) (Aug 2026)
    if clean_dom.endswith(".id"):
        channels.append(
            ReportingChannel(
                name="PANDI (Pengelola Nama Domain Internet Indonesia) / PANDI (Indonesia Internet Domain Name Registry)",
                target_type="Registry .ID",
                contact="abuse@pandi.id | helpdesk@pandi.id | Telp: +62-21-30055777",
                submission_method="Email Abuse Desk (abuse@pandi.id) / Portal IDADX https://idadx.id/report",
                notes="Permohonan penangguhan (suspend) nama domain .id yang terindikasi phishing. / Request to suspend a .id domain name indicated for phishing.",
            )
        )

    # If banking or financial institution
    brand_lower = brand.lower() if brand else ""
    if any(k in brand_lower for k in ("bank", "bca", "bni", "bri", "mandiri", "dana", "ovo", "gopay", "ojk", "bi")):
        # Verified via https://x.com/ojkindonesia/status/1704793665238077502 & https://kontak157.ojk.go.id (Aug 2026)
        channels.append(
            ReportingChannel(
                name="Kontak OJK 157 & Satgas PASTI / OJK Contact 157 & PASTI Task Force",
                target_type="Otoritas Jasa Keuangan & Satgas Pemberantasan Aktivitas Keuangan Ilegal / Financial Services Authority & Illegal Financial Activity Task Force",
                contact="konsumen@ojk.go.id | satgaspasti@ojk.go.id | Telp: 157 | WA: 081157157157",
                submission_method="Email Pengaduan (konsumen@ojk.go.id / satgaspasti@ojk.go.id) / Portal https://kontak157.ojk.go.id",
                notes="Eskalasi perlindungan konsumen dan penindakan entitas keuangan/investasi ilegal. / Escalation for consumer protection and action against illegal financial/investment entities.",
            )
        )
        # Verified via https://www.bssn.go.id/aduan-siber/ & RFC 2350 Gov-CSIRT Indonesia (Aug 2026)
        channels.append(
            ReportingChannel(
                name="Direktorat Operasi Keamanan Siber BSSN (Gov-CSIRT / CSIRT Nasional) / BSSN Cyber Security Operations Directorate (Gov-CSIRT / National CSIRT)",
                target_type="Pusat Operasi Keamanan Siber Nasional / National Cyber Security Operations Center",
                contact="bantuan70@bssn.go.id | Telp: (021) 78833610 | WA: 0812-8135-4598 (24/7)",
                submission_method="Email CSIRT BSSN (bantuan70@bssn.go.id) / Hotline Insiden Siber",
                notes="Koordinasi penanganan insiden siber sektor perbankan dan infrastruktur informasi vital. / Coordination for cyber incident handling in the banking sector and vital information infrastructure.",
            )
        )

    return channels


def format_report_text(
    finding_id: int,
    domain: str,
    brand: str,
    risk_score: int,
    risk_level: str,
    first_seen_iso: str,
    is_live: bool,
    match_method: str,
    registrar: str | None,
    nameservers: str | None,
    reasoning: str | None,
    channels: list[ReportingChannel],
) -> str:
    """Format a structured, formal incident report, in paired Indonesian/English
    lines (demo-video-showcase branch only). The Indonesian text is the real,
    submittable content -- Kominfo/BSSN/PANDI/OJK operate in Indonesian, and
    that half must never be altered from what a real submission needs. The
    English half is appended purely so an English-language dashboard reader
    can follow along; it is never a substitute for the Indonesian text.
    """
    # Convert timestamp to WIB
    try:
        dt = datetime.fromisoformat(first_seen_iso.replace("Z", "+00:00")).astimezone(WIB)
        wib_time_str = dt.strftime("%d %B %Y, pukul %H:%M:%S WIB")
    except Exception:
        wib_time_str = first_seen_iso or "-"

    status_str = "AKTIF (Merespons HTTP) / ACTIVE (Responding to HTTP)" if is_live else "TIDAK AKTIF / BELUM MERESPONS / INACTIVE / NOT RESPONDING"
    reg_str = registrar or "Tidak terdata / Private Registration / Not on record / Private Registration"
    ns_str = nameservers or "Tidak terdata / Not on record"

    lines = [
        "================================================================================",
        "DRAFT LAPORAN INDIKASI SITUS PENIPUAN / PHISHING DIGITAL",
        "DRAFT REPORT: INDICATION OF A FRAUDULENT / DIGITAL PHISHING SITE",
        "Sistem Deteksi Dini SIAGA (AI HackFest 2026) / SIAGA Early Detection System (AI HackFest 2026)",
        "================================================================================",
        "",
        "PENTING: Draft ini disusun secara otomatis berbasis data teknis publik.",
        "Pengiriman ke kanal resmi wajib ditinjau dan dilakukan secara manual oleh operator.",
        "IMPORTANT: This draft is generated automatically from public technical data.",
        "Submission to any official channel must be reviewed and sent manually by an operator.",
        "",
        "I. RINGKASAN TEMUAN / I. FINDING SUMMARY",
        "--------------------------------------------------------------------------------",
        f"1. Nama Domain Terindikasi / Indicated Domain          : {domain}",
        f"2. Institusi yang Dicatut / Impersonated Institution   : {brand}",
        f"3. Tingkat Risiko / Risk Level                         : {risk_level} (Skor/Score: {risk_score}/100)",
        f"4. Status Akses Saat Deteksi / Access Status at Detection : {status_str}",
        f"5. Waktu Deteksi Pertama / First Detected At           : {wib_time_str}",
        "",
        "II. BUKTI TEKNIS & ANALISIS INFRASTRUKTUR / II. TECHNICAL EVIDENCE & INFRASTRUCTURE ANALYSIS",
        "--------------------------------------------------------------------------------",
        f"• Metode Kemiripan Brand / Brand Similarity Method     : {match_method}",
        f"• Registrar Domain / Domain Registrar                  : {reg_str}",
        f"• Nameservers / Nameservers                            : {ns_str}",
        f"• Analisis Risiko Teknis / Technical Risk Analysis     : {reasoning or 'Terdeteksi menyerupai identitas institusi resmi. / Detected resembling the identity of an official institution.'}",
        "",
        "III. REKOMENDASI KANAL PELAPORAN / III. RECOMMENDED REPORTING CHANNELS",
        "--------------------------------------------------------------------------------",
    ]

    for i, ch in enumerate(channels, 1):
        lines.append(f"{i}. {ch.name} ({ch.target_type})")
        lines.append(f"   Kontak / Contact : {ch.contact}")
        lines.append(f"   Metode / Method  : {ch.submission_method}")
        lines.append(f"   Catatan / Notes  : {ch.notes}")
        lines.append("")

    lines.extend([
        "IV. SURAT PERMOHONAN PENANGANAN (DRAFT EMAIL / PESAN PENGADUAN)",
        "IV. REQUEST FOR ACTION LETTER (DRAFT EMAIL / COMPLAINT MESSAGE)",
        "--------------------------------------------------------------------------------",
        f"Subjek/Subject: [Laporan Dugaan Phishing / Suspected Phishing Report] Indikasi Peniruan Institusi '{brand}' pada Domain '{domain}' / Indication of Institution Impersonation of '{brand}' on Domain '{domain}'",
        "",
        "Kepada Yth. / To:",
        "Tim Penanganan Aduan / Pengelola Keamanan Siber, / Complaint Handling Team / Cyber Security Operator,",
        "",
        "Bersama ini kami menyampaikan informasi teknis mengenai indikasi situs web phishing /",
        f"penipuan digital yang mencatut nama institusi resmi '{brand}'.",
        f"We are submitting technical information regarding an indication of a phishing / digital fraud",
        f"website impersonating the official institution '{brand}'.",
        "",
        "Rincian domain yang dilaporkan / Details of the reported domain:",
        f"- Domain / Domain                : {domain}",
        f"- Dicatut / Impersonating         : {brand}",
        f"- Waktu Cek / Time Checked        : {wib_time_str}",
        f"- Status / Status                 : {status_str}",
        "",
        "Berdasarkan analisis teknis otomatis SIAGA, domain tersebut memiliki karakteristik",
        "peniruan identitas yang berpotensi membahayakan masyarakat pengguna layanan digital.",
        "Mohon kiranya dapat ditindaklanjuti sesuai prosedur penanganan dan pemblokiran yang berlaku.",
        "Based on SIAGA's automated technical analysis, this domain exhibits identity-impersonation",
        "characteristics that could endanger the public using digital services. We kindly request",
        "follow-up per the applicable handling and blocking procedure.",
        "",
        "Demikian laporan ini kami sampaikan. Atas perhatian dan kerja samanya diucapkan terima kasih.",
        "Thank you for your attention and cooperation regarding this report.",
        "",
        "--------------------------------------------------------------------------------",
        "PENAFIAN (PRIVACY & LEGAL DISCLAIMER) / DISCLAIMER (PRIVACY & LEGAL DISCLAIMER):",
        "Laporan ini disusun menggunakan data teknis publik (Certificate Transparency, DNS, RDAP)",
        "tanpa memuat nomor telepon, nomor rekening, atau data pribadi individu (UU PDP No. 27/2022).",
        "Status temuan bersifat indikasi teknis awal untuk diverifikasi oleh otoritas berwenang.",
        "This report was composed using public technical data (Certificate Transparency, DNS, RDAP)",
        "without any phone number, bank account number, or individual personal data (UU PDP No. 27/2022).",
        "The finding's status is an initial technical indication for verification by the competent authority.",
        "================================================================================",
    ])

    return "\n".join(lines)


def generate_report_draft(
    finding_id_or_domain: int | str,
    db_path: Path | str | sqlite3.Connection = DEFAULT_DB_PATH,
) -> ReportDraft:
    """Generate structured report draft from database record.

    Args:
        finding_id_or_domain: Integer finding ID or domain string to lookup.
        db_path: Path to siaga.db SQLite database or active sqlite3.Connection.

    Returns:
        ReportDraft dataclass instance.

    Raises:
        ValueError: If finding is not found in database.
    """
    def _query(conn: sqlite3.Connection) -> sqlite3.Row | None:
        conn.row_factory = sqlite3.Row
        if isinstance(finding_id_or_domain, int) or (isinstance(finding_id_or_domain, str) and str(finding_id_or_domain).isdigit()):
            target_id = int(finding_id_or_domain)
            return conn.execute("SELECT * FROM domain_findings WHERE id = ?", (target_id,)).fetchone()
        else:
            clean_dom = str(finding_id_or_domain).strip().lower()
            return conn.execute("SELECT * FROM domain_findings WHERE domain = ? ORDER BY id DESC LIMIT 1", (clean_dom,)).fetchone()

    if isinstance(db_path, sqlite3.Connection):
        row = _query(db_path)
    else:
        resolved_db = Path(db_path)
        db_uri = f"file:{resolved_db.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(db_uri, uri=True) as conn:
            row = _query(conn)

    if not row:
        raise ValueError(f"Domain finding not found in database for query: '{finding_id_or_domain}'")

    finding_id = row["id"]
    domain = row["domain"]
    brand = row["matched_brand"] or "Institusi Publik / Public Institution"
    risk_score = row["risk_score"] or 0
    risk_level = row["risk_level"] or "INDIKASI PENIPUAN"
    first_seen = row["first_seen"] or ""
    is_live = bool(row["is_live"])
    match_method = row["match_method"] or "similarity"
    registrar = row["registrar"]
    nameservers = row["nameservers"]
    reasoning = row["reasoning"]

    channels = get_recommended_channels(domain, brand)
    draft_text = format_report_text(
        finding_id=finding_id,
        domain=domain,
        brand=brand,
        risk_score=risk_score,
        risk_level=risk_level,
        first_seen_iso=first_seen,
        is_live=is_live,
        match_method=match_method,
        registrar=registrar,
        nameservers=nameservers,
        reasoning=reasoning,
        channels=channels,
    )

    return ReportDraft(
        finding_id=finding_id,
        domain=domain,
        matched_brand=brand,
        risk_score=risk_score,
        risk_level=risk_level,
        first_seen_wib=first_seen,
        is_live=is_live,
        match_method=match_method,
        registrar=registrar,
        nameservers=nameservers,
        recommended_channels=channels,
        draft_text=draft_text,
    )
