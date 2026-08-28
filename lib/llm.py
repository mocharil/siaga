"""LLM Unified Gateway and Linguistic Analysis Module (T14).

Provides complete() as the single LLM calling point across the project with
strict JSON schema validation, automatic retries, daily token budget enforcement,
and SQLite-backed usage tracking.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import ssl
import urllib.error
import urllib.request

import jsonschema

logger = logging.getLogger("siaga.llm")

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "siaga.db"
DEFAULT_TIMEOUT = 30.0
DEFAULT_DAILY_LIMIT = 100_000
DEFAULT_MAX_RETRIES = 2

# Standard JSON schema for phishing/scam linguistic analysis
LINGUISTIC_SCHEMA = {
    "type": "object",
    "properties": {
        "urgency": {"type": "integer", "minimum": 0, "maximum": 3},
        "false_authority": {"type": "integer", "minimum": 0, "maximum": 3},
        "prize_bait": {"type": "integer", "minimum": 0, "maximum": 3},
        "dangerous_request": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["otp", "pin", "apk", "transfer", "password", "none"],
            },
        },
        "reasoning": {"type": "string"},
    },
    "required": ["urgency", "false_authority", "prize_bait", "dangerous_request", "reasoning"],
}


class LLMError(Exception):
    """Base exception for LLM operations."""


class LLMSchemaError(LLMError):
    """Raised when LLM output violates JSON schema after maximum retries."""


class LLMBudgetExceeded(LLMError):
    """Raised when daily LLM token budget limit is exceeded."""


class LLMProviderError(LLMError):
    """Raised when upstream LLM provider fails."""


def _init_llm_tables(conn: sqlite3.Connection) -> None:
    """Initialize SQLite table for tracking daily token usage."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_usage (
            date TEXT PRIMARY KEY,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            call_count INTEGER DEFAULT 0
        );
        """
    )
    conn.commit()


def get_daily_usage(date_str: str, db_path: Path) -> dict[str, int]:
    """Retrieve token usage statistics for a given UTC date (YYYY-MM-DD)."""
    with sqlite3.connect(str(db_path)) as conn:
        _init_llm_tables(conn)
        cur = conn.execute(
            """
            SELECT prompt_tokens, completion_tokens, total_tokens, call_count
            FROM llm_usage WHERE date = ?
            """,
            (date_str,),
        )
        row = cur.fetchone()
        if row:
            return {
                "prompt_tokens": row[0],
                "completion_tokens": row[1],
                "total_tokens": row[2],
                "call_count": row[3],
            }
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "call_count": 0,
        }


def record_usage(
    date_str: str,
    prompt_tokens: int,
    completion_tokens: int,
    db_path: Path,
) -> None:
    """Record consumed tokens to SQLite usage table."""
    total_tokens = prompt_tokens + completion_tokens
    with sqlite3.connect(str(db_path)) as conn:
        _init_llm_tables(conn)
        conn.execute(
            """
            INSERT INTO llm_usage (date, prompt_tokens, completion_tokens, total_tokens, call_count)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(date) DO UPDATE SET
                prompt_tokens = prompt_tokens + excluded.prompt_tokens,
                completion_tokens = completion_tokens + excluded.completion_tokens,
                total_tokens = total_tokens + excluded.total_tokens,
                call_count = call_count + 1
            """,
            (date_str, prompt_tokens, completion_tokens, total_tokens),
        )
        conn.commit()


def _extract_json_from_text(raw_text: str) -> dict:
    """Extract and parse JSON object from raw LLM output text."""
    text = raw_text.strip()

    # Strip markdown code fences if present: ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    else:
        # Match outermost curly brackets
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            text = text[first_brace : last_brace + 1]

    return json.loads(text)


def _call_provider_api(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[str, int, int]:
    """Execute raw HTTP request to OpenAI-compatible LLM endpoint."""
    resolved_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not resolved_key:
        raise LLMProviderError("LLM_API_KEY is not configured in environment or parameter")

    resolved_model = model or os.getenv("LLM_MODEL") or "claude-opus-4-8-thinking"
    resolved_base = (base_url or os.getenv("LLM_BASE_URL") or "https://api.justwoker.icu/v1").rstrip("/")
    endpoint_url = f"{resolved_base}/chat/completions"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": resolved_model,
        "messages": messages,
        "temperature": 0.0,
    }

    body_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint_url,
        data=body_bytes,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {resolved_key}",
            "User-Agent": "SIAGA-FraudDetector/0.1 (+https://github.com/idwebhost-pandi/siaga)",
        },
        method="POST",
    )

    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        raise LLMProviderError(f"LLM API HTTP {e.code}: {err_msg}") from e
    except Exception as e:
        raise LLMProviderError(f"LLM API connection error: {e}") from e

    choices = data.get("choices", [])
    if not choices or "message" not in choices[0]:
        raise LLMProviderError(f"Malformed LLM API response: {data}")

    content = choices[0]["message"].get("content", "")

    usage = data.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens") or (len(prompt) // 4)
    completion_tokens = usage.get("completion_tokens") or (len(content) // 4)

    return content, prompt_tokens, completion_tokens


def complete(
    prompt: str,
    schema: dict,
    system_prompt: str | None = None,
    db_path: Path | str | None = None,
    model: str | None = None,
    daily_limit: int | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> dict:
    """Execute LLM completion with schema validation, budget enforcement, and retries.

    Args:
        prompt: User prompt text to send to the model.
        schema: Expected JSON schema dict (validated via jsonschema).
        system_prompt: Optional system instructions.
        db_path: SQLite database path for tracking token usage. Defaults to data/siaga.db.
        model: Optional model override.
        daily_limit: Optional daily token budget limit override.
        max_retries: Number of retry attempts on schema validation failures (default: 2).

    Returns:
        Validated dict conforming to the requested schema.

    Raises:
        LLMBudgetExceeded: If daily token usage has reached or exceeded daily limit.
        LLMSchemaError: If model output fails JSON schema validation after all retries.
        LLMProviderError: If upstream API call fails.
    """
    resolved_db = Path(db_path) if db_path else DEFAULT_DB_PATH
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1. Enforce daily budget limit
    limit = daily_limit
    if limit is None:
        limit_env = os.getenv("LLM_DAILY_TOKEN_LIMIT")
        limit = int(limit_env) if limit_env and limit_env.isdigit() else DEFAULT_DAILY_LIMIT

    current_usage = get_daily_usage(today_str, resolved_db)
    if current_usage["total_tokens"] >= limit:
        raise LLMBudgetExceeded(
            f"Daily LLM token budget exceeded for {today_str}: "
            f"{current_usage['total_tokens']}/{limit} tokens used"
        )

    # 2. Execution with schema validation & retry loop
    current_prompt = prompt
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        raw_text, p_tok, c_tok = _call_provider_api(
            prompt=current_prompt,
            system_prompt=system_prompt,
            model=model,
        )

        # Record token usage immediately for every call
        record_usage(today_str, p_tok, c_tok, resolved_db)

        try:
            parsed_json = _extract_json_from_text(raw_text)
            jsonschema.validate(instance=parsed_json, schema=schema)
            return parsed_json
        except (json.JSONDecodeError, jsonschema.ValidationError) as e:
            last_error = e
            logger.warning(
                "LLM output failed schema validation (attempt %d/%d): %s",
                attempt + 1,
                max_retries + 1,
                e,
            )
            # Add corrective feedback for next attempt
            current_prompt = (
                f"{prompt}\n\n[PERINGATAN]: Output sebelumnya salah ({e}). "
                f"Wajib keluarkan HANYA JSON valid sesuai skema tanpa teks lain."
            )

    raise LLMSchemaError(
        f"LLM output failed schema validation after {max_retries + 1} attempts: {last_error}"
    ) from last_error


def analyze_linguistics(
    text: str,
    db_path: Path | str | None = None,
    model: str | None = None,
) -> dict:
    """Convenience helper to analyze message linguistics using standard prompt and schema."""
    prompt_file = Path(__file__).resolve().parent.parent / "prompts" / "linguistic_analysis.txt"
    if prompt_file.exists():
        template = prompt_file.read_text(encoding="utf-8")
        prompt = template.replace("{message_text}", text)
    else:
        prompt = (
            f"Analisis indikator phishing dalam pesan ini: '{text}'. "
            f"Kembalikan JSON dengan urgency, false_authority, prize_bait, dangerous_request, reasoning."
        )

    return complete(
        prompt=prompt,
        schema=LINGUISTIC_SCHEMA,
        db_path=db_path,
        model=model,
    )
