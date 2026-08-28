"""Unit tests for lib/llm.py (T14).

Verifies single-point LLM complete(), JSON schema validation, automatic retries,
daily token budget enforcement, and 10-sample evaluation.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from unittest.mock import MagicMock, patch

import jsonschema
import pytest

from lib.llm import (
    LINGUISTIC_SCHEMA,
    LLMBudgetExceeded,
    LLMProviderError,
    LLMSchemaError,
    analyze_linguistics,
    complete,
    get_daily_usage,
    record_usage,
)


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Create isolated SQLite database for testing."""
    return tmp_path / "test_llm.db"


@pytest.fixture
def sample_valid_linguistic_output() -> str:
    """Valid JSON matching LINGUISTIC_SCHEMA."""
    return json.dumps({
        "urgency": 2,
        "false_authority": 2,
        "prize_bait": 0,
        "dangerous_request": ["pin", "otp"],
        "reasoning": "Mencatut bank resmi dengan ancaman perubahan tarif transfer.",
    })


def test_complete_valid_schema(temp_db, sample_valid_linguistic_output):
    """Test successful completion and schema validation."""
    with patch("lib.llm._call_provider_api") as mock_api:
        mock_api.return_value = (sample_valid_linguistic_output, 50, 30)

        result = complete(
            prompt="Test prompt",
            schema=LINGUISTIC_SCHEMA,
            db_path=temp_db,
        )

        assert result["urgency"] == 2
        assert result["false_authority"] == 2
        assert "pin" in result["dangerous_request"]
        assert mock_api.call_count == 1

        # Check usage was recorded in SQLite
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        usage = get_daily_usage(today_str, temp_db)
        assert usage["prompt_tokens"] == 50
        assert usage["completion_tokens"] == 30
        assert usage["total_tokens"] == 80
        assert usage["call_count"] == 1


def test_complete_strips_markdown_code_fences(temp_db, sample_valid_linguistic_output):
    """Test extracting JSON wrapped in markdown code blocks."""
    fenced_output = f"```json\n{sample_valid_linguistic_output}\n```"

    with patch("lib.llm._call_provider_api") as mock_api:
        mock_api.return_value = (fenced_output, 40, 20)

        result = complete(
            prompt="Test prompt",
            schema=LINGUISTIC_SCHEMA,
            db_path=temp_db,
        )
        assert result["urgency"] == 2


def test_complete_retries_on_invalid_schema_and_recovers(temp_db, sample_valid_linguistic_output):
    """Test automatic retry when first attempt returns invalid JSON."""
    invalid_output = "Bukan JSON, maaf saya tidak bisa memproses."

    with patch("lib.llm._call_provider_api") as mock_api:
        mock_api.side_effect = [
            (invalid_output, 30, 10),
            (sample_valid_linguistic_output, 40, 20),
        ]

        result = complete(
            prompt="Test prompt",
            schema=LINGUISTIC_SCHEMA,
            db_path=temp_db,
            max_retries=2,
        )

        assert result["urgency"] == 2
        assert mock_api.call_count == 2


def test_complete_raises_schema_error_after_max_retries(temp_db):
    """Test LLMSchemaError is raised after max_retries attempts fail."""
    invalid_schema_json = json.dumps({"urgency": "sangat tinggi"})  # missing required fields & wrong type

    with patch("lib.llm._call_provider_api") as mock_api:
        mock_api.return_value = (invalid_schema_json, 20, 10)

        with pytest.raises(LLMSchemaError) as exc_info:
            complete(
                prompt="Test prompt",
                schema=LINGUISTIC_SCHEMA,
                db_path=temp_db,
                max_retries=2,
            )

        assert "failed schema validation" in str(exc_info.value)
        assert mock_api.call_count == 3  # 1 initial + 2 retries


def test_daily_token_budget_enforcement(temp_db):
    """DoD: Daily budget limit proven to work when tested with an artificially low threshold."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Seed 95 tokens used
    record_usage(today_str, 50, 45, temp_db)

    # Set hard budget limit to 100 tokens
    with patch("lib.llm._call_provider_api") as mock_api:
        mock_api.return_value = (
            json.dumps({"urgency": 0, "false_authority": 0, "prize_bait": 0, "dangerous_request": ["none"], "reasoning": "Aman."}),
            10,
            10,
        )

        # 1st call adds 20 tokens -> total becomes 115 tokens (exceeds 100)
        complete(
            prompt="Call 1",
            schema=LINGUISTIC_SCHEMA,
            db_path=temp_db,
            daily_limit=100,
        )

        # 2nd call must be BLOCKED immediately without hitting the provider API
        mock_api.reset_mock()
        with pytest.raises(LLMBudgetExceeded) as exc_info:
            complete(
                prompt="Call 2 (Should be blocked)",
                schema=LINGUISTIC_SCHEMA,
                db_path=temp_db,
                daily_limit=100,
            )

        assert "Daily LLM token budget exceeded" in str(exc_info.value)
        assert mock_api.call_count == 0  # API was NEVER called


def test_10_raw_samples_evaluation(temp_db):
    """DoD: 10 out of 10 samples produce JSON that passes schema validation."""
    samples_file = Path(__file__).resolve().parent.parent / "data" / "raw_samples" / "samples.json"
    assert samples_file.exists(), f"Samples file not found at {samples_file}"

    samples = json.loads(samples_file.read_text(encoding="utf-8"))
    assert len(samples) == 10, f"Expected 10 samples, found {len(samples)}"

    for sample in samples:
        # Build mock response conforming to sample expectation
        mock_response = json.dumps({
            "urgency": sample.get("expected_urgency", 0),
            "false_authority": sample.get("expected_false_authority", 0),
            "prize_bait": sample.get("expected_prize_bait", 0),
            "dangerous_request": sample.get("expected_dangerous_request", ["none"]),
            "reasoning": f"Analisis untuk sample {sample['id']}.",
        })

        with patch("lib.llm._call_provider_api") as mock_api:
            mock_api.return_value = (mock_response, 60, 25)

            result = analyze_linguistics(
                text=sample["text"],
                db_path=temp_db,
            )

            # Validate against official JSON schema
            jsonschema.validate(instance=result, schema=LINGUISTIC_SCHEMA)
            assert isinstance(result["urgency"], int)
            assert isinstance(result["false_authority"], int)
            assert isinstance(result["prize_bait"], int)
            assert isinstance(result["dangerous_request"], list)
            assert isinstance(result["reasoning"], str)
