"""Unit tests for Campaign Clustering (T23)."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

import pytest

from lib.campaign import (
    apply_campaign_labels,
    nameserver_signature,
    _registrable_domain,
)
from lib.db import init_db


def test_registrable_domain_generic_tld():
    assert _registrable_domain("ns1.badhost.xyz") == "badhost.xyz"
    assert _registrable_domain("ns2.badhost.xyz") == "badhost.xyz"


def test_registrable_domain_id_second_level():
    assert _registrable_domain("ns1.provider.co.id") == "provider.co.id"
    assert _registrable_domain("ns2.provider.co.id") == "provider.co.id"


def test_registrable_domain_bare_tld_no_crash():
    assert _registrable_domain("localhost") is None
    assert _registrable_domain("") is None


def test_nameserver_signature_stable_across_hostnames():
    """ns1/ns2 differ but resolve to the same parent — signature must match."""
    sig_a = nameserver_signature("ns1.badhost.xyz;ns2.badhost.xyz")
    sig_b = nameserver_signature("ns3.badhost.xyz;ns4.badhost.xyz")
    assert sig_a == sig_b
    assert sig_a is not None


def test_nameserver_signature_different_operators_differ():
    sig_a = nameserver_signature("ns1.badhost.xyz")
    sig_b = nameserver_signature("ns1.otherhost.top")
    assert sig_a != sig_b


def test_nameserver_signature_empty_returns_none():
    assert nameserver_signature(None) is None
    assert nameserver_signature("") is None
    assert nameserver_signature("   ") is None


@pytest.fixture
def db_with_findings(tmp_path):
    db_file = tmp_path / "campaign_test.db"
    init_db(db_file)
    return db_file


def _insert_finding(conn, domain, nameservers, matched_brand, method, first_seen):
    conn.execute(
        """
        INSERT INTO domain_findings (domain, first_seen, nameservers, matched_brand, match_method, risk_score, risk_level)
        VALUES (?, ?, ?, ?, ?, 70, 'INDIKASI PENIPUAN')
        """,
        (domain, first_seen, nameservers, matched_brand, method),
    )


def test_nameserver_clustering_groups_shared_infrastructure(db_with_findings):
    """Three domains on the same DNS provider must share one campaign_id;
    a fourth on unrelated infrastructure must not join that cluster."""
    with sqlite3.connect(str(db_with_findings)) as conn:
        _insert_finding(conn, "bca-verify1.xyz", "ns1.evilhost.top;ns2.evilhost.top", "Bank Central Asia", "edit_distance", "2026-08-28T01:00:00+00:00")
        _insert_finding(conn, "bca-verify2.online", "ns3.evilhost.top;ns4.evilhost.top", "Bank Central Asia", "edit_distance", "2026-08-28T02:00:00+00:00")
        _insert_finding(conn, "mandiri-login.xyz", "ns1.evilhost.top", "Bank Mandiri", "keyword", "2026-08-28T03:00:00+00:00")
        _insert_finding(conn, "unrelated-legit.id", "ns1.pandi.id;ns2.pandi.id", "PLN", "keyword", "2026-08-28T04:00:00+00:00")
        conn.commit()

    summary = apply_campaign_labels(db_path=db_with_findings)

    assert summary.nameserver_clusters_found == 1
    assert summary.nameserver_domains_labeled == 3

    with sqlite3.connect(str(db_with_findings)) as conn:
        rows = dict(conn.execute("SELECT domain, campaign_id FROM domain_findings").fetchall())

    assert rows["bca-verify1.xyz"] is not None
    assert rows["bca-verify1.xyz"] == rows["bca-verify2.online"] == rows["mandiri-login.xyz"]
    assert rows["unrelated-legit.id"] is None


def test_nameserver_clustering_singleton_not_a_campaign(db_with_findings):
    """A domain with unique infrastructure must not be forced into a cluster."""
    with sqlite3.connect(str(db_with_findings)) as conn:
        _insert_finding(conn, "lone-domain.xyz", "ns1.onlyme.com", "Bank BRI", "edit_distance", "2026-08-28T01:00:00+00:00")
        conn.commit()

    summary = apply_campaign_labels(db_path=db_with_findings)
    assert summary.nameserver_clusters_found == 0

    with sqlite3.connect(str(db_with_findings)) as conn:
        row = conn.execute("SELECT campaign_id FROM domain_findings WHERE domain = 'lone-domain.xyz'").fetchone()
    assert row[0] is None


def test_brand_pattern_clustering_within_window(db_with_findings):
    """Three domains targeting the same brand within 7 days, with no shared
    nameserver, should still cluster as a weaker brand_pattern campaign."""
    base = datetime(2026, 8, 28, tzinfo=timezone.utc)
    with sqlite3.connect(str(db_with_findings)) as conn:
        for i, days_offset in enumerate([0, 2, 5]):
            ts = (base + timedelta(days=days_offset)).isoformat()
            _insert_finding(conn, f"bri-fake-{i}.xyz", None, "Bank Rakyat Indonesia", "edit_distance", ts)
        conn.commit()

    summary = apply_campaign_labels(db_path=db_with_findings)

    assert summary.nameserver_clusters_found == 0
    assert summary.brand_pattern_clusters_found == 1
    assert summary.brand_pattern_domains_labeled == 3


def test_brand_pattern_clustering_outside_window_not_grouped(db_with_findings):
    """Same brand, but spread across 30 days — outside the 7-day window,
    should not be treated as one coordinated campaign."""
    base = datetime(2026, 8, 1, tzinfo=timezone.utc)
    with sqlite3.connect(str(db_with_findings)) as conn:
        for i, days_offset in enumerate([0, 15, 30]):
            ts = (base + timedelta(days=days_offset)).isoformat()
            _insert_finding(conn, f"bri-fake-{i}.xyz", None, "Bank Rakyat Indonesia", "edit_distance", ts)
        conn.commit()

    summary = apply_campaign_labels(db_path=db_with_findings)
    assert summary.brand_pattern_clusters_found == 0


def test_nameserver_signal_takes_priority_over_brand_pattern(db_with_findings):
    """A finding already labeled via nameserver clustering must not be
    re-labeled (downgraded) by the weaker brand_pattern pass."""
    with sqlite3.connect(str(db_with_findings)) as conn:
        _insert_finding(conn, "bri-fake-1.xyz", "ns1.evilhost.top", "Bank Rakyat Indonesia", "edit_distance", "2026-08-28T01:00:00+00:00")
        _insert_finding(conn, "bri-fake-2.xyz", "ns1.evilhost.top", "Bank Rakyat Indonesia", "edit_distance", "2026-08-28T02:00:00+00:00")
        _insert_finding(conn, "bri-fake-3.xyz", None, "Bank Rakyat Indonesia", "edit_distance", "2026-08-28T03:00:00+00:00")
        conn.commit()

    summary = apply_campaign_labels(db_path=db_with_findings)

    with sqlite3.connect(str(db_with_findings)) as conn:
        rows = dict(conn.execute("SELECT domain, campaign_id FROM domain_findings").fetchall())

    # bri-fake-1 and bri-fake-2 share nameserver infra -> one campaign.
    assert rows["bri-fake-1.xyz"] == rows["bri-fake-2.xyz"]
    # bri-fake-3 has no nameserver info; only 1 other unlabeled peer exists
    # for the brand_pattern pass (min size 3), so it stays unlabeled.
    assert rows["bri-fake-3.xyz"] is None


def test_apply_campaign_labels_idempotent(db_with_findings):
    """Running clustering twice must not create duplicate campaign rows
    or change existing labels."""
    with sqlite3.connect(str(db_with_findings)) as conn:
        _insert_finding(conn, "bca-verify1.xyz", "ns1.evilhost.top", "Bank Central Asia", "edit_distance", "2026-08-28T01:00:00+00:00")
        _insert_finding(conn, "bca-verify2.xyz", "ns2.evilhost.top", "Bank Central Asia", "edit_distance", "2026-08-28T02:00:00+00:00")
        conn.commit()

    apply_campaign_labels(db_path=db_with_findings)
    with sqlite3.connect(str(db_with_findings)) as conn:
        first_pass = dict(conn.execute("SELECT domain, campaign_id FROM domain_findings").fetchall())
        campaign_count_1 = conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]

    apply_campaign_labels(db_path=db_with_findings)
    with sqlite3.connect(str(db_with_findings)) as conn:
        second_pass = dict(conn.execute("SELECT domain, campaign_id FROM domain_findings").fetchall())
        campaign_count_2 = conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]

    assert first_pass == second_pass
    assert campaign_count_1 == campaign_count_2 == 1
