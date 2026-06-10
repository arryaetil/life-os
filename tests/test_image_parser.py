import pytest
from unittest.mock import patch, MagicMock
from datetime import date


def _mock_openai_response(content: str):
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


def test_parse_image_single_clear_transaction():
    resp = _mock_openai_response(
        '[{"amount": 20.40, "type": "Expense", "description": "fuel", "category": "Transport",'
        ' "is_impulse": false, "source_date": "2026-06-09", "confidence": 0.95,'
        ' "needs_clarification": false, "clarification_question": ""}]'
    )
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        mock_cfg.ANTHROPIC_API_KEY = ""
        MockOAI.return_value.chat.completions.create.return_value = resp
        from app.parser import parse_image
        result = parse_image(b"fake_bytes", today=date(2026, 6, 10))

    assert len(result) == 1
    t = result[0]
    assert t["amount"] == 20.40
    assert t["date"] == "2026-06-09"
    assert t["description"] == "fuel"
    assert t["type"] == "Expense"
    assert t["needs_clarification"] is False
    assert t["week_start"] == "2026-06-08"   # Tuesday 2026-06-09 — week starts Monday 2026-06-08
    assert t["month"] == "2026-06"


def test_parse_image_flags_clarification():
    resp = _mock_openai_response(
        '[{"amount": 351.98, "type": "Expense", "description": "ticketing payments",'
        ' "category": "Other", "is_impulse": false, "source_date": "2026-06-07",'
        ' "confidence": 0.4, "needs_clarification": true,'
        ' "clarification_question": "TicketingPayments -€351.98 — what was this for?"}]'
    )
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        mock_cfg.ANTHROPIC_API_KEY = ""
        MockOAI.return_value.chat.completions.create.return_value = resp
        from app.parser import parse_image
        result = parse_image(b"fake_bytes", today=date(2026, 6, 10))

    assert result[0]["needs_clarification"] is True
    assert "TicketingPayments" in result[0]["clarification_question"]


def test_parse_image_income_positive_sign():
    resp = _mock_openai_response(
        '[{"amount": 10.00, "type": "Income", "description": "winkens", "category": "Income",'
        ' "is_impulse": false, "source_date": "2026-06-09", "confidence": 0.9,'
        ' "needs_clarification": false, "clarification_question": ""}]'
    )
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        mock_cfg.ANTHROPIC_API_KEY = ""
        MockOAI.return_value.chat.completions.create.return_value = resp
        from app.parser import parse_image
        result = parse_image(b"fake_bytes", today=date(2026, 6, 10))

    assert result[0]["type"] == "Income"
    assert result[0]["amount"] == 10.00


def test_parse_image_returns_empty_on_api_failure():
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        mock_cfg.ANTHROPIC_API_KEY = ""
        MockOAI.return_value.chat.completions.create.side_effect = Exception("API error")
        from app.parser import parse_image
        result = parse_image(b"fake_bytes")

    assert result == []


def test_parse_image_skips_items_without_amount():
    resp = _mock_openai_response(
        '[{"amount": null, "type": "Expense", "description": "bad", "category": "Other",'
        ' "is_impulse": false, "source_date": "2026-06-10", "confidence": 0.1,'
        ' "needs_clarification": false, "clarification_question": ""}]'
    )
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        mock_cfg.ANTHROPIC_API_KEY = ""
        MockOAI.return_value.chat.completions.create.return_value = resp
        from app.parser import parse_image
        result = parse_image(b"fake_bytes", today=date(2026, 6, 10))

    assert result == []
