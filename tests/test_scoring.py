"""Unit tests for lib/scoring.py (T15).

Verifies risk scoring weight calculations, risk level mapping, concrete reasons generation,
Mode A end-to-end message analysis pipeline, and PDP-compliant privacy logging.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from lib.extract import ExtractedEntities
from lib.rdap import DomainInfo
from lib.redirect import HopInfo, RedirectTrace
from lib.scoring import (
    RISK_THRESHOLDS,
    SCORING_WEIGHTS,
    ModeAResult,
    ScoringResult,
    analyze_message,
    score_risk,
)


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Create isolated SQLite database for testing."""
    return tmp_path / "test_scoring.db"


def test_scoring_weights_constants_at_top():
    """Verify that SCORING_WEIGHTS and RISK_THRESHOLDS are exposed as constants."""
    assert isinstance(SCORING_WEIGHTS, dict)
    assert isinstance(RISK_THRESHOLDS, dict)
    assert "domain_age_under_7d" in SCORING_WEIGHTS
    assert "dangerous_request_credential" in SCORING_WEIGHTS
    assert RISK_THRESHOLDS["safe_max"] == 39
    assert RISK_THRESHOLDS["fraud_min"] == 70


def test_score_risk_high_fraud_signals():
    """Test combining multiple critical signals triggers INDIKASI PENIPUAN (score >= 70)."""
    tech_signals = {
        "domain_age_days": 2,          # +30
        "watchlist_matched": True,     # +25
        "matched_brand": "BCA",
        "is_risky_tld": True,          # +15
        "tld": "xyz",
    }
    ling_signals = {
        "dangerous_request": ["otp", "pin"],  # +30
        "urgency": 2,                         # +15
        "false_authority": 2,                 # +20
        "prize_bait": 0,
    }

    result = score_risk(tech_signals, ling_signals)
    assert result.score == 100  # Capped at 100
    assert result.level == "INDIKASI PENIPUAN"
    assert len(result.reasons) >= 3
    assert len(result.breakdown) >= 4


def test_score_risk_safe_signals():
    """Test clean message with no threat indicators produces AMAN (score <= 39)."""
    tech_signals = {
        "domain_age_days": 5000,
        "watchlist_matched": False,
        "is_risky_tld": False,
    }
    ling_signals = {
        "dangerous_request": ["none"],
        "urgency": 0,
        "false_authority": 0,
        "prize_bait": 0,
    }

    result = score_risk(tech_signals, ling_signals)
    assert result.score <= 39
    assert result.level == "AMAN"
    assert len(result.reasons) >= 3


def test_score_risk_caution_tier():
    """Test moderate suspicious indicators produce HATI-HATI (40-69)."""
    tech_signals = {
        "domain_age_days": 25,  # +20 (under 30d)
        "watchlist_matched": False,
        "is_risky_tld": True,   # +15
        "tld": "online",
    }
    ling_signals = {
        "dangerous_request": ["none"],
        "urgency": 1,           # +8
        "false_authority": 1,   # +10
        "prize_bait": 0,
    }

    result = score_risk(tech_signals, ling_signals)
    assert 40 <= result.score <= 69
    assert result.level == "HATI-HATI"
    assert len(result.reasons) >= 3


def test_mode_a_pipeline_phishing_message(temp_db):
    """DoD: End-to-end Mode A pipeline analyzing phishing message produces INDIKASI PENIPUAN with >= 3 reasons."""
    phishing_message = (
        "Pemberitahuan BCA: Tarif transfer naik Rp 150rb/bln. "
        "Batal kenaikan di hxxps://bca-tarif[.]online/batal segera malam ini atau otomatis setuju! "
        "Masukkan PIN dan OTP untuk verifikasi."
    )

    mock_llm_response = {
        "urgency": 3,
        "false_authority": 2,
        "prize_bait": 0,
        "dangerous_request": ["pin", "otp"],
        "reasoning": "Mencatut bank BCA dengan desakan perubahan tarif dan meminta PIN/OTP.",
    }

    mock_rdap_info = DomainInfo(
        domain="bca-tarif.online",
        registration_date=datetime.now(timezone.utc).isoformat(),  # 0 days old
        registrar="Hostinger",
        nameservers=["ns1.hostinger.com"],
        status=["active"],
    )

    mock_redirect_trace = RedirectTrace(
        start_url="https://bca-tarif.online/batal",
        final_url="https://bca-tarif.online/batal",
        hops=[HopInfo(url="https://bca-tarif.online/batal", status_code=200)],
        status="ok",
    )

    with (
        patch("lib.scoring.analyze_linguistics", return_value=mock_llm_response),
        patch("lib.scoring.lookup", return_value=mock_rdap_info),
        patch("lib.scoring.trace", return_value=mock_redirect_trace),
    ):
        result = analyze_message(phishing_message, db_path=temp_db)

        assert isinstance(result, ModeAResult)
        assert result.scoring.level == "INDIKASI PENIPUAN"
        assert result.scoring.score >= 70
        assert len(result.scoring.reasons) >= 3
        assert "INDIKASI PENIPUAN" in result.explanation
        assert len(result.entities.urls) >= 1
        assert result.entities.urls[0] == "https://bca-tarif.online/batal"

        # Check Privacy Audit: message_analyses table contains SHA-256 hash, NOT raw message
        with sqlite3.connect(str(temp_db)) as conn:
            cur = conn.execute("SELECT message_hash, risk_score, risk_level FROM message_analyses")
            row = cur.fetchone()
            assert row is not None
            msg_hash, stored_score, stored_level = row
            assert len(msg_hash) == 64  # valid SHA-256 hex
            assert msg_hash == result.raw_message_hash
            assert stored_score >= 70
            assert stored_level == "INDIKASI PENIPUAN"


def test_mode_a_pipeline_legitimate_message(temp_db):
    """End-to-end Mode A pipeline analyzing legitimate notification produces AMAN."""
    legit_message = (
        "m-BCA: 28/08 14:30 TRSF E-BANKING DB 50.000,00 KE 1234567890 BUDI SETIAWAN. "
        "Saldo Rp 1.250.000,00. Hubungi HaloBCA 1500888 jika tidak transaksi."
    )

    mock_llm_response = {
        "urgency": 0,
        "false_authority": 0,
        "prize_bait": 0,
        "dangerous_request": ["none"],
        "reasoning": "Pemberitahuan mutasi transaksi resmi.",
    }

    with patch("lib.scoring.analyze_linguistics", return_value=mock_llm_response):
        result = analyze_message(legit_message, db_path=temp_db)

        assert result.scoring.level == "AMAN"
        assert result.scoring.score <= 39
        assert "AMAN" in result.explanation
        assert len(result.scoring.reasons) >= 3
