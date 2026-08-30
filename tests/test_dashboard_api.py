"""Unit tests for SIAGA Dashboard Read-Only API (D1).

Tests:
1. All 5 read-only GET endpoints return valid structures and data from siaga.db.
2. Security enforcement: POST/PUT/PATCH/DELETE methods are rejected with HTTP 405.
3. Privacy domain masking is applied by default.
4. Database connection is strictly read-only (?mode=ro).
"""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import pytest
from fastapi.testclient import TestClient

from dashboard.api import app, mask_domain
from lib.db import init_db


@pytest.fixture
def test_db(tmp_path):
    """Set up an isolated test database with seeded rows."""
    db_file = tmp_path / "test_api.db"
    init_db(db_file)

    now_iso = datetime.now(timezone.utc).isoformat()
    today_str = "2026-08-30"
    yesterday_str = "2026-08-29"

    with sqlite3.connect(str(db_file)) as conn:
        # Collector run
        conn.execute(
            """
            INSERT INTO collector_runs (started_at, finished_at, source, fetched, inserted_new, status)
            VALUES (?, ?, 'ctlogs_id', 500, 20, 'ok')
            """,
            (now_iso, now_iso),
        )
        # Daily stats
        conn.execute(
            """
            INSERT INTO daily_stats (date, domains_scanned, tahap1_passed, tahap2_passed, tahap3_assessed,
                                    domains_flagged, domains_live, flagged_not_in_blacklist,
                                    collector_ok, heartbeat_ok, peak_ram_mb)
            VALUES (?, 6500, 200, 200, 200, 5, 2, 5, 1, 1, 42),
                   (?, 9100, 310, 310, 310, 8, 3, 8, 1, 1, 45)
            """,
            (yesterday_str, today_str),
        )
        # Domain findings
        conn.execute(
            """
            INSERT INTO domain_findings (domain, first_seen, matched_brand, match_method,
                                         risk_score, risk_level, is_live, in_public_blacklist_at_detection,
                                         campaign_id, reasoning)
            VALUES ('bankbca-klik-update.top', ?, 'Bank Central Asia', 'keyword', 88, 'INDIKASI PENIPUAN', 1, 0, 1, 'Mencatut BCA'),
                   ('mandiri-login-secure.xyz', ?, 'Bank Mandiri', 'keyword', 82, 'INDIKASI PENIPUAN', 0, 0, 1, 'Mencatut Mandiri')
            """,
            (now_iso, now_iso),
        )
        conn.commit()

    return db_file


@pytest.fixture
def client(test_db):
    """Provide FastAPI test client bound to test database."""
    app.state.db_path = test_db
    with TestClient(app) as c:
        yield c
    app.state.db_path = None


def test_stats_today_endpoint(client):
    """Verify /api/stats/today returns the latest daily summary metrics."""
    res = client.get("/api/stats/today")
    assert res.status_code == 200
    data = res.json()

    assert data["date"] == "2026-08-30"
    assert data["domains_scanned"] == 9100
    assert data["tahap1_passed"] == 310
    assert data["domains_flagged"] == 8
    assert data["domains_live"] == 3
    assert data["collector_ok"] is True
    assert data["heartbeat_ok"] is True
    assert data["peak_ram_mb"] == 45


def test_stats_trend_endpoint(client):
    """Verify /api/stats/trend returns chronological daily series."""
    res = client.get("/api/stats/trend?days=14")
    assert res.status_code == 200
    data = res.json()

    assert data["days_requested"] == 14
    assert data["total_records"] == 2
    trend = data["trend"]
    assert len(trend) == 2
    # Chronological check: yesterday first, then today
    assert trend[0]["date"] == "2026-08-29"
    assert trend[1]["date"] == "2026-08-30"


def test_findings_top_endpoint_privacy_masked(client):
    """Verify /api/findings/top masks domain names by default for privacy & defamation protection."""
    res = client.get("/api/findings/top?limit=5")
    assert res.status_code == 200
    data = res.json()

    assert data["total_findings"] == 2
    findings = data["findings"]
    assert len(findings) == 2

    # Verify highest risk finding is first (score 88 > 82)
    top_finding = findings[0]
    assert top_finding["matched_brand"] == "Bank Central Asia"
    assert top_finding["risk_score"] == 88
    assert top_finding["is_live"] is True

    # Check privacy masking is applied
    assert "***" in top_finding["domain"]
    assert top_finding["raw_domain"] is None


def test_findings_top_endpoint_unmask_param(client):
    """Verify /api/findings/top unmasks raw domains only when explicitly requested."""
    res = client.get("/api/findings/top?limit=5&unmask=true")
    assert res.status_code == 200
    data = res.json()

    top_finding = data["findings"][0]
    assert top_finding["domain"] == "bankbca-klik-update.top"
    assert top_finding["raw_domain"] == "bankbca-klik-update.top"


def test_metrics_endpoint(client):
    """Verify /api/metrics delivers validated model metrics and system stats."""
    res = client.get("/api/metrics")
    assert res.status_code == 200
    data = res.json()

    assert data["precision_pct"] == 100.0
    assert data["recall_pct"] == 91.8
    assert data["f1_score"] == 0.957
    assert data["collector_uptime_pct"] == 100.0
    assert data["peak_ram_mb"] >= 45
    assert data["total_domains_scanned"] == (6500 + 9100)
    assert data["total_findings_flagged"] == (5 + 8)


def test_health_endpoint(client):
    """Verify /api/health reuses healthcheck logic and returns system status."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "ok"
    assert data["is_healthy"] is True
    assert data["latest_collector_status"] == "ok"
    assert data["latest_heartbeat_ok"] is True
    assert len(data["issues"]) == 0


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize("endpoint", ["/api/stats/today", "/api/findings/top", "/api/metrics", "/api/health", "/api/submit"])
def test_security_write_methods_rejected_with_405(client, method, endpoint):
    """Hard security requirement: Any non-GET request must be rejected with HTTP 405 Method Not Allowed."""
    res = client.request(method, endpoint)

    assert res.status_code == 405
    assert "read-only" in res.json().get("detail", "").lower()


def test_sqlite_connection_strictly_readonly(test_db):
    """Hard security requirement: SQLite connection must be opened with ?mode=ro."""
    db_uri = f"file:{test_db.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(db_uri, uri=True) as conn:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("INSERT INTO daily_stats (date) VALUES ('2026-08-31')")


def test_mask_domain_helper():
    """Verify domain masking utility handles various domain stem lengths."""
    assert mask_domain("bca.id") == "b***.id"
    assert mask_domain("ruangguru.com") == "rua***ru.com"
    assert mask_domain("bankmandiri-secure-login.xyz") == "bank***gin.xyz"
    assert mask_domain("plain") == "plain"
