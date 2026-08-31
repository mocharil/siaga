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

    from datetime import timedelta
    from zoneinfo import ZoneInfo

    WIB = ZoneInfo("Asia/Jakarta")
    now_dt = datetime.now(WIB)
    today_str = now_dt.strftime("%Y-%m-%d")
    yesterday_str = (now_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).isoformat()

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
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    today_str = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y-%m-%d")

    res = client.get("/api/stats/today")
    assert res.status_code == 200
    data = res.json()

    assert data["date"] == today_str
    assert data["domains_scanned"] == 9100
    assert data["tahap1_passed"] == 310
    assert data["domains_flagged"] == 8
    assert data["domains_live"] == 3
    assert data["collector_ok"] is True
    assert data["heartbeat_ok"] is True
    assert data["peak_ram_mb"] == 45


def test_stats_trend_endpoint(client):
    """Verify /api/stats/trend returns chronological daily series."""
    from datetime import datetime, timedelta, timezone
    from zoneinfo import ZoneInfo
    now_wib = datetime.now(ZoneInfo("Asia/Jakarta"))
    today_str = now_wib.strftime("%Y-%m-%d")
    yesterday_str = (now_wib - timedelta(days=1)).strftime("%Y-%m-%d")

    res = client.get("/api/stats/trend?days=14")
    assert res.status_code == 200
    data = res.json()

    assert data["days_requested"] == 14
    assert data["total_records"] == 2
    trend = data["trend"]
    assert len(trend) == 2
    # Chronological check: yesterday first, then today
    assert trend[0]["date"] == yesterday_str
    assert trend[1]["date"] == today_str


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


def test_metrics_endpoint_live_eval_data(client):
    """Verify /api/metrics delivers dynamic model metrics from data/eval_results.json."""
    res = client.get("/api/metrics")
    assert res.status_code == 200
    data = res.json()

    assert data["precision_pct"] == 100.0
    assert data["recall_pct"] == 91.8
    assert data["f1_score"] == 0.9573
    assert data["metrics_available"] is True
    assert data["collector_uptime_pct"] == 100.0
    assert data["peak_ram_mb"] >= 45
    assert data["total_domains_scanned"] == (6500 + 9100)
    assert data["total_findings_flagged"] == (5 + 8)
    assert "calibrated" in data["calibration_status"]


def test_metrics_dynamic_file_change(client, tmp_path):
    """Verify that modifying eval_results.json dynamically changes the /api/metrics response.

    Why this test is crucial (Lessons from T06/CLAUDE.md Rule #2):
    Hardcoded metrics disguise stale calibrations. This test injects custom eval numbers
    (precision 87.5%, recall 76.2%) and proves the API returns these exact numbers.
    """
    import json
    mock_eval = tmp_path / "mock_eval.json"
    mock_eval.write_text(json.dumps({
        "summary": {
            "timestamp": "2026-09-01T12:00:00Z",
            "metrics": {
                "precision": 0.875,
                "recall": 0.762,
                "f1_score": 0.8145
            }
        }
    }), encoding="utf-8")

    app.state.eval_results_path = mock_eval
    try:
        res = client.get("/api/metrics")
        assert res.status_code == 200
        data = res.json()

        assert data["precision_pct"] == 87.5
        assert data["recall_pct"] == 76.2
        assert data["f1_score"] == 0.8145
        assert data["metrics_available"] is True
        assert data["eval_timestamp"] == "2026-09-01T12:00:00Z"
        assert data["calibration_status"] == "calibrated (2026-09-01)"
    finally:
        app.state.eval_results_path = None


def test_metrics_missing_eval_file(client, tmp_path):
    """Verify that when eval_results.json does not exist, /api/metrics returns nulls with metrics_available=False."""
    non_existent = tmp_path / "does_not_exist_eval.json"
    app.state.eval_results_path = non_existent
    try:
        res = client.get("/api/metrics")
        assert res.status_code == 200
        data = res.json()

        assert data["metrics_available"] is False
        assert data["precision_pct"] is None
        assert data["recall_pct"] is None
        assert data["f1_score"] is None
        assert data["calibration_status"] == "uncalibrated"
    finally:
        app.state.eval_results_path = None


def test_metrics_lead_time_calculation(client, test_db):
    """Verify that avg_lead_time_hours calculates real duration when blacklist_listed_at is populated."""
    with sqlite3.connect(str(test_db)) as conn:
        conn.execute(
            """
            INSERT INTO domain_findings (domain, first_seen, blacklist_listed_at, risk_score)
            VALUES ('phish1.xyz', '2026-08-28T00:00:00Z', '2026-08-29T06:00:00Z', 90),
                   ('phish2.top', '2026-08-28T00:00:00Z', '2026-08-29T12:00:00Z', 90)
            """
        )
        conn.commit()

    res = client.get("/api/metrics")
    assert res.status_code == 200
    data = res.json()

    # phish1: 30 hours, phish2: 36 hours -> average = 33.0 hours
    assert data["avg_lead_time_hours"] == 33.0


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


def test_serve_dashboard_ui_and_static_files(client):
    """Verify that root endpoint serves index.html and /static serves css/js."""
    r_index = client.get("/")
    assert r_index.status_code == 200
    assert "SIAGA" in r_index.text
    assert "<title>" in r_index.text

    r_css = client.get("/static/style.css")
    assert r_css.status_code == 200
    assert "--bg-main" in r_css.text

    r_js = client.get("/static/app.js")
    assert r_js.status_code == 200
    assert "renderTrendSvg" in r_js.text


def test_zero_external_cdn_dependencies():
    """Verify that all dashboard assets are 100% local with zero external CDN/font/script links (D3)."""
    static_path = Path(__file__).resolve().parent.parent / "dashboard" / "static"
    for asset in static_path.glob("*"):
        text = asset.read_text(encoding="utf-8")
        assert "http://" not in text and "https://" not in text, f"Found external reference in {asset.name}"
