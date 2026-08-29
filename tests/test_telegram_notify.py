"""Unit tests for the direct Telegram sender (T25)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from lib.telegram_notify import TelegramNotifyError, send_message


def _mock_response(body: dict):
    mock = MagicMock()
    mock.read.return_value = json.dumps(body).encode("utf-8")
    mock.__enter__.return_value = mock
    return mock


def test_send_message_success():
    with patch("lib.telegram_notify.urllib.request.urlopen", return_value=_mock_response({"ok": True, "result": {"message_id": 42}})):
        result = send_message("12345", "hello", bot_token="fake-token")
    assert result["ok"] is True


def test_send_message_missing_token_raises(monkeypatch):
    # lib/llm.py calls load_dotenv() at import time for standalone-script use,
    # which leaks the real TELEGRAM_BOT_TOKEN into os.environ for the whole
    # pytest process once any module importing lib.llm runs first. Explicitly
    # clear it here rather than assuming ambient environment state.
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(TelegramNotifyError, match="TELEGRAM_BOT_TOKEN"):
        send_message("12345", "hello", bot_token=None)


def test_send_message_api_ok_false_raises():
    with patch("lib.telegram_notify.urllib.request.urlopen", return_value=_mock_response({"ok": False, "description": "chat not found"})):
        with pytest.raises(TelegramNotifyError, match="ok=false"):
            send_message("12345", "hello", bot_token="fake-token")


def test_send_message_http_error_raises():
    import urllib.error
    err = urllib.error.HTTPError(url="x", code=403, msg="Forbidden", hdrs=None, fp=None)
    err.read = lambda: b'{"ok":false,"description":"Forbidden"}'
    with patch("lib.telegram_notify.urllib.request.urlopen", side_effect=err):
        with pytest.raises(TelegramNotifyError, match="HTTP 403"):
            send_message("12345", "hello", bot_token="fake-token")
