"""Direct Telegram Bot API Sender (T25).

Deliberately bypasses any LLM/agent text generation for the daily brief:
the message text is fully computed by lib/daily_brief.py from daily_stats
and domain_findings, then sent verbatim via a plain HTTP POST to Telegram's
Bot API. This keeps the numbers a reader sees identical to what is actually
in the database — no paraphrasing step that could drift or hallucinate a
figure.

Read-only with respect to the wider internet: this module only ever POSTs
to api.telegram.org (a channel we control, addressed to our own bot), never
to a domain under investigation.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger("siaga.telegram_notify")

TELEGRAM_API_BASE = "https://api.telegram.org"
DEFAULT_TIMEOUT = 10.0


class TelegramNotifyError(Exception):
    """Raised when a Telegram send fails after retries are exhausted."""


def send_message(
    chat_id: str,
    text: str,
    bot_token: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """Send a plain-text message to a Telegram chat.

    Args:
        chat_id: Numeric Telegram chat/user ID (as a string).
        text: Message body, sent verbatim (no Markdown/HTML parsing requested).
        bot_token: Bot token; defaults to the TELEGRAM_BOT_TOKEN env var.
        timeout: HTTP timeout in seconds.

    Returns:
        Parsed JSON response from Telegram on success.

    Raises:
        TelegramNotifyError: on missing token, HTTP error, or malformed response.
    """
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise TelegramNotifyError("TELEGRAM_BOT_TOKEN not set and no bot_token provided")

    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise TelegramNotifyError(f"Telegram API HTTP {e.code}: {error_body}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise TelegramNotifyError(f"Network error sending Telegram message: {e}") from e

    if not body.get("ok"):
        raise TelegramNotifyError(f"Telegram API returned ok=false: {body}")

    logger.info("Telegram message sent to chat_id=%s (message_id=%s)", chat_id, body.get("result", {}).get("message_id"))
    return body
