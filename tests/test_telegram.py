import pytest
from unittest.mock import patch, MagicMock
from app.telegram import send_telegram_message


def test_send_success(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "12345")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("httpx.post", return_value=mock_resp):
        assert send_telegram_message("hello") is True


def test_send_missing_token(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "12345")
    assert send_telegram_message("hello") is False


def test_send_missing_chat_id(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "")
    assert send_telegram_message("hello") is False


def test_send_api_error(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "12345")
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad Request"
    with patch("httpx.post", return_value=mock_resp):
        assert send_telegram_message("hello") is False


def test_send_network_failure(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "12345")
    with patch("httpx.post", side_effect=Exception("connection refused")):
        assert send_telegram_message("hello") is False
