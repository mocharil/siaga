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
    - PANDI Abuse Desk: https://pandi.id/blog/peran-pandi-dalam-penanganan-penyalahgunaan-nama-domain-id (Aug 2026)
    - OJK 157 & Satgas PASTI: https://x.com/ojkindonesia/status/1704793665238077502 & https://kontak157.ojk.go.id (Aug 2026)
    - BSSN Gov-CSIRT: https://www.bssn.go.id/aduan-siber/ & https://idsirtii.or.id/halaman/tentang/rfc-2350-gov-csirt-indonesia.html (Aug 2026)
    """
    channels: list[ReportingChannel] = [
        # Verified via https://www.aduankonten.id/kontak-kami (Aug 2026)
        ReportingChannel(
            name="Aduan Konten Kominfo RI",
            target_type="Regulator Konten Negatif & Pemblokiran",
            contact="aduankonten@kominfo.go.id | WA: 08119224545",
            submission_method="Portal Resmi (https://www.aduankonten.id) / Email (aduankonten@kominfo.go.id)",
            notes="Kanal resmi pemerintah untuk pemblokiran akses internet & normalisasi DNS trust positif.",
        )
    ]

    clean_dom = domain.lower().strip()
    # Check if .id domain
    # Verified via https://pandi.id/blog/peran-pandi-dalam-penanganan-penyalahgunaan-nama-domain-id (Aug 2026)
    if clean_dom.endswith(".id"):
        channels.append(
            ReportingChannel(
                name="PANDI (Pengelola Nama Domain Internet Indonesia)",
                target_type="Registry .ID",
                contact="abuse@pandi.id | helpdesk@pandi.id | Telp: (021) 80862000",
                submission_method="Email Abuse Desk (abuse@pandi.id) / Portal https://pandi.id",
                notes="Permohonan penangguhan (suspend) nama domain .id yang terindikasi phishing.",
            )
        )

    # If banking or financial institution
    brand_lower = brand.lower() if brand else ""
    if any(k in brand_lower for k in ("bank", "bca", "bni", "bri", "mandiri", "dana", "ovo", "gopay", "ojk", "bi")):
        # Verified via https://x.com/ojkindonesia/status/1704793665238077502 (Aug 2026)
        channels.append(
            ReportingChannel(
                name="Kontak OJK 157 & Satgas PASTI",
                target_type="Otoritas Jasa Keuangan & Satgas Pemberantasan Aktivitas Keuangan Ilegal",
                contact="konsumen@ojk.go.id | satgaspasti@ojk.go.id | Telp: 157 | WA: 081157157157",
                submission_method="Email Pengaduan (konsumen@ojk.go.id / satgaspasti@ojk.go.id) / Portal https://kontak157.ojk.go.id",
                notes="Eskalasi perlindungan konsumen dan penindakan entitas keuangan/investasi ilegal.",
            )
        )
        # Verified via https://www.bssn.go.id/aduan-siber/ & RFC 2350 Gov-CSIRT Indonesia (Aug 2026)
        channels.append(
            ReportingChannel(
                name="Direktorat Operasi Keamanan Siber BSSN (Gov-CSIRT / CSIRT Nasional)",
                target_type="Pusat Operasi Keamanan Siber Nasional",
                contact="bantuan70@bssn.go.id | Telp: (021) 78833610 | WA: 0812-8135-4598 (24/7)",
                submission_method="Email CSIRT BSSN (bantuan70@bssn.go.id) / Hotline Insiden Siber",
                notes="Koordinasi penanganan insiden siber sektor perbankan dan infrastruktur informasi vital.",
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
    """Format structured, formal Indonesian incident report text."""
    # Convert timestamp to WIB
    try:
        dt = datetime.fromisoformat(first_seen_iso.replace("Z", "+00:00")).astimezone(WIB)
        wib_time_str = dt.strftime("%d %B %Y, pukul %H:%M:%S WIB")
    except Exception:
        wib_time_str = first_seen_iso or "-"

    status_str = "AKTIF (Merespons HTTP)" if is_live else "TIDAK AKTIF / BELUM MERESPONS"
    reg_str = registrar or "Tidak terdata / Private Registration"
    ns_str = nameservers or "Tidak terdata"

    lines = [
        "================================================================================",
        "DRAFT LAPORAN INDIKASI SITUS PENIPUAN / PHISHING DIGITAL",
        "Sistem Deteksi Dini SIAGA (AI HackFest 2026)",
        "================================================================================",
        "",
        "PENTING: Draft ini disusun secara otomatis berbasis data teknis publik.",
        "Pengiriman ke kanal resmi wajib ditinjau dan dilakukan secara manual oleh operator.",
        "",
        "I. RINGKASAN TEMUAN",
        "--------------------------------------------------------------------------------",
        f"1. Nama Domain Terindikasi   : {domain}",
        f"2. Institusi yang Dicatut    : {brand}",
        f"3. Tingkat Risiko            : {risk_level} (Skor: {risk_score}/100)",
        f"4. Status Akses Saat Deteksi : {status_str}",
        f"5. Waktu Deteksi Pertama     : {wib_time_str}",
        "",
        "II. BUKTI TEKNIS & ANALISIS INFRASTRUKTUR",
        "--------------------------------------------------------------------------------",
        f"• Metode Kemiripan Brand     : {match_method}",
        f"• Registrar Domain           : {reg_str}",
        f"• Nameservers                : {ns_str}",
        f"• Analisis Risiko Teknis     : {reasoning or 'Terdeteksi menyerupai identitas institusi resmi.'}",
        "",
        "III. REKOMENDASI KANAL PELAPORAN",
        "--------------------------------------------------------------------------------",
    ]

    for i, ch in enumerate(channels, 1):
        lines.append(f"{i}. {ch.name} ({ch.target_type})")
        lines.append(f"   Kontak : {ch.contact}")
        lines.append(f"   Metode : {ch.submission_method}")
        lines.append(f"   Catatan: {ch.notes}")
        lines.append("")

    lines.extend([
        "IV. SURAT PERMOHONAN PENANGANAN (DRAFT EMAIL / PESAN PENGADUAN)",
        "--------------------------------------------------------------------------------",
        f"Subjek: [Laporan Dugaan Phishing] Indikasi Peniruan Institusi '{brand}' pada Domain '{domain}'",
        "",
        "Kepada Yth.",
        "Tim Penanganan Aduan / Pengelola Keamanan Siber,",
        "",
        "Bersama ini kami menyampaikan informasi teknis mengenai indikasi situs web phishing /",
        f"penipuan digital yang mencatut nama institusi resmi '{brand}'.",
        "",
        f"Rincian domain yang dilaporkan:",
        f"- Domain    : {domain}",
        f"- Dicatut   : {brand}",
        f"- Waktu Cek : {wib_time_str}",
        f"- Status    : {status_str}",
        "",
        "Berdasarkan analisis teknis otomatis SIAGA, domain tersebut memiliki karakteristik",
        "peniruan identitas yang berpotensi membahayakan masyarakat pengguna layanan digital.",
        "Mohon kiranya dapat ditindaklanjuti sesuai prosedur penanganan dan pemblokiran yang berlaku.",
        "",
        "Demikian laporan ini kami sampaikan. Atas perhatian dan kerja samanya diucapkan terima kasih.",
        "",
        "--------------------------------------------------------------------------------",
        "PENAFIAN (PRIVACY & LEGAL DISCLAIMER):",
        "Laporan ini disusun menggunakan data teknis publik (Certificate Transparency, DNS, RDAP)",
        "tanpa memuat nomor telepon, nomor rekening, atau data pribadi individu (UU PDP No. 27/2022).",
        "Status temuan bersifat indikasi teknis awal untuk diverifikasi oleh otoritas berwenang.",
        "================================================================================",
    ])

    return "\n".join(lines)


def generate_report_draft(
    finding_id_or_domain: int | str,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> ReportDraft:
    """Generate structured report draft from database record.

    Args:
        finding_id_or_domain: Integer finding ID or domain string to lookup.
        db_path: Path to siaga.db SQLite database.

    Returns:
        ReportDraft dataclass instance.

    Raises:
        ValueError: If finding is not found in database.
    """
    resolved_db = Path(db_path)
    db_uri = f"file:{resolved_db.resolve().as_posix()}?mode=ro"

    with sqlite3.connect(db_uri, uri=True) as conn:
        conn.row_factory = sqlite3.Row

        if isinstance(finding_id_or_domain, int) or (isinstance(finding_id_or_domain, str) and finding_id_or_domain.isdigit()):
            target_id = int(finding_id_or_domain)
            row = conn.execute("SELECT * FROM domain_findings WHERE id = ?", (target_id,)).fetchone()
        else:
            clean_dom = str(finding_id_or_domain).strip().lower()
            row = conn.execute("SELECT * FROM domain_findings WHERE domain = ? ORDER BY id DESC LIMIT 1", (clean_dom,)).fetchone()

        if not row:
            raise ValueError(f"Domain finding not found in database for query: '{finding_id_or_domain}'")

        finding_id = row["id"]
        domain = row["domain"]
        brand = row["matched_brand"] or "Institusi Publik"
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
