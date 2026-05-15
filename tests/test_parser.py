import pytest
from unittest.mock import patch
from app.parser import parse_message, _regex_parse

# Test the regex fallback directly — no AI involved
def test_basic_expense():
    result = _regex_parse("14 kebab")
    assert result["type"] == "Expense"
    assert result["amount"] == 14.0
    assert result["description"] == "kebab"

def test_minus_prefix_is_expense():
    result = _regex_parse("-50 dinner")
    assert result["type"] == "Expense"
    assert result["amount"] == 50.0

def test_plus_prefix_is_income():
    result = _regex_parse("+314 DUO income")
    assert result["type"] == "Income"
    assert result["amount"] == 314.0

def test_decimal_dot():
    result = _regex_parse("8.50 coffee")
    assert result["amount"] == 8.50

def test_decimal_comma():
    result = _regex_parse("8,50 coffee")
    assert result["amount"] == 8.50

def test_investment_keyword():
    result = _regex_parse("100 degiro etf")
    assert result["type"] == "Investment"

def test_transfer_keyword():
    result = _regex_parse("200 savings")
    assert result["type"] == "Transfer"

def test_income_not_overridden():
    result = _regex_parse("+200 savings refund")
    assert result["type"] == "Income"

def test_is_impulse_true():
    result = _regex_parse("25 impulse buy")
    assert result["is_impulse"] is True

def test_is_impulse_false():
    result = _regex_parse("14 kebab")
    assert result["is_impulse"] is False

def test_invalid_raises():
    with pytest.raises(ValueError):
        _regex_parse("no amount here")

# Test parse_message with AI mocked to fail → falls back to regex
def test_parse_message_fallback_to_regex(monkeypatch):
    monkeypatch.setattr("app.config.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.config.ANTHROPIC_API_KEY", "")
    result = parse_message("14 kebab")
    assert result["amount"] == 14.0
    assert result["type"] == "Expense"
    assert "timestamp" in result
    assert "week_start" in result

# Test parse_message uses AI result when available
def test_parse_message_uses_ai_result(monkeypatch):
    monkeypatch.setattr("app.config.OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr("app.config.ANTHROPIC_API_KEY", "")

    ai_response = '{"amount": 3.5, "type": "Expense", "description": "coffee", "category": "Food", "is_impulse": false}'

    from unittest.mock import MagicMock
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=ai_response))]
    )
    with patch("openai.OpenAI", return_value=mock_client):
        result = parse_message("coffee was 3.50 this morning")

    assert result["amount"] == 3.5
    assert result["description"] == "coffee"
    assert result["category"] == "Food"
    assert result["type"] == "Expense"

def test_parse_message_week_start_is_monday(monkeypatch):
    monkeypatch.setattr("app.config.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.config.ANTHROPIC_API_KEY", "")
    result = parse_message("5 coffee")
    from datetime import date
    from app.utils import get_week_start
    assert result["week_start"] == get_week_start(date.today()).strftime("%Y-%m-%d")
