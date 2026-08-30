"""Unit tests for Report Draft Generator (T27).

Tests:
1. Valid finding lookup and structured draft generation.
2. Official escalation channels routing (Kominfo, PANDI for .id, OJK & BSSN for banks).
3. Compliance rules: Always uses "indikasi", never identifies individuals, includes human-in-the-loop warning.
4. Error handling for non-existent finding IDs or domains.
"""

from datetime import datetime, timezone
import sqlite3
import pytest

from lib.db import init_db
from lib.report_draft import generate_report_draft, get_recommended_channels


@pytest.fixture
def draft_test_db(tmp_path):
    """Set up database with test findings."""
    db_file = tmp_path / "test_draft.db"
    init_db(db_file)

    now_iso = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(str(db_file)) as conn:
        conn.execute(
            """
            INSERT INTO domain_findings (id, domain, first_seen, matched_brand, match_method,
                                         risk_score, risk_level, is_live, registrar, nameservers, reasoning)
            VALUES (101, 'bankbca-update.id', ?, 'Bank Central Asia', 'keyword', 88, 'INDIKASI PENIPUAN', 1, 'PANDI Registrar', 'ns1.phish.xyz', 'Mencatut BCA'),
                   (102, 'tokopedia-promo.online', ?, 'Tokopedia', 'keyword', 75, 'INDIKASI PENIPUAN', 0, 'NameCheap', 'ns1.host.top', 'Mencatut Tokopedia')
            """,
            (now_iso, now_iso),
        )
        conn.commit()

    return db_file


def test_generate_report_draft_id_domain(draft_test_db):
    """Verify report draft for .id banking domain routes to Kominfo, PANDI, OJK, and BSSN."""
    draft = generate_report_draft(101, db_path=draft_test_db)

    assert draft.finding_id == 101
    assert draft.domain == "bankbca-update.id"
    assert draft.matched_brand == "Bank Central Asia"
    assert draft.risk_score == 88
    assert draft.is_live is True

    channel_names = [ch.name for ch in draft.recommended_channels]
    assert any("Kominfo" in name for name in channel_names)
    assert any("PANDI" in name for name in channel_names)
    assert any("OJK" in name for name in channel_names)
    assert any("BSSN" in name for name in channel_names)

    # Compliance checks
    assert "INDIKASI" in draft.draft_text
    assert "terbukti" not in draft.draft_text.lower()
    assert "Pengiriman ke kanal resmi wajib ditinjau dan dilakukan secara manual oleh operator" in draft.draft_text
    assert "UU PDP" in draft.draft_text


def test_generate_report_draft_non_id_ecommerce(draft_test_db):
    """Verify report draft for non-.id non-banking domain routes to Kominfo and registrar."""
    draft = generate_report_draft("tokopedia-promo.online", db_path=draft_test_db)

    assert draft.finding_id == 102
    assert draft.domain == "tokopedia-promo.online"
    assert draft.matched_brand == "Tokopedia"

    channel_names = [ch.name for ch in draft.recommended_channels]
    assert any("Kominfo" in name for name in channel_names)
    # Non-.id should not include PANDI
    assert not any("PANDI" in name for name in channel_names)


def test_generate_report_draft_not_found(draft_test_db):
    """Verify ValueError is raised when finding does not exist."""
    with pytest.raises(ValueError, match="not found in database"):
        generate_report_draft(9999, db_path=draft_test_db)


def test_verified_official_channel_contacts():
    """Verify exact official contact addresses, emails, phone numbers, and portals (anti-fabrication regression lock).

    Verified Sources (Aug 2026):
    1. BSSN Gov-CSIRT: bantuan70@bssn.go.id, (021) 78833610, WA 0812-8135-4598 (https://www.bssn.go.id/aduan-siber/)
    2. Kominfo AduanKonten: aduankonten@kominfo.go.id, WA 08119224545, https://www.aduankonten.id (https://www.aduankonten.id/kontak-kami)
    3. PANDI Abuse: abuse@pandi.id, helpdesk@pandi.id, (021) 80862000 (https://pandi.id/blog/peran-pandi-dalam-penanganan-penyalahgunaan-nama-domain-id)
    4. OJK 157 & Satgas PASTI: konsumen@ojk.go.id, satgaspasti@ojk.go.id, 157, WA 081157157157 (https://x.com/ojkindonesia/status/1704793665238077502)
    """
    channels = get_recommended_channels("secure-login.bankbca.id", "Bank Central Asia")

    contacts_str = " ".join([f"{ch.contact} {ch.submission_method}" for ch in channels])

    # BSSN CSIRT checks
    assert "bantuan70@bssn.go.id" in contacts_str, "BSSN CSIRT email must be bantuan70@bssn.go.id"
    assert "bantuan74@bssn.go.id" not in contacts_str, "Obsolete/incorrect bantuan74 must never appear"
    assert "(021) 78833610" in contacts_str, "BSSN CSIRT phone must be present"
    assert "0812-8135-4598" in contacts_str, "BSSN CSIRT 24/7 WhatsApp must be present"

    # Kominfo Aduan Konten checks
    assert "aduankonten@kominfo.go.id" in contacts_str, "Kominfo email must be aduankonten@kominfo.go.id"
    assert "08119224545" in contacts_str, "Kominfo WhatsApp hotline must be present"
    assert "www.aduankonten.id" in contacts_str, "Kominfo official portal must be www.aduankonten.id"

    # PANDI Abuse checks
    assert "abuse@pandi.id" in contacts_str, "PANDI abuse email must be abuse@pandi.id"
    assert "helpdesk@pandi.id" in contacts_str, "PANDI helpdesk email must be helpdesk@pandi.id"

    # OJK & Satgas PASTI checks
    assert "konsumen@ojk.go.id" in contacts_str, "OJK Consumer email must be konsumen@ojk.go.id"
    assert "satgaspasti@ojk.go.id" in contacts_str, "Satgas PASTI email must be satgaspasti@ojk.go.id"
    assert "157" in contacts_str, "OJK 157 call center must be present"
    assert "081157157157" in contacts_str, "OJK WhatsApp hotline must be present"
