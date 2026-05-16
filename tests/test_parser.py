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


# --- Dutch regex fallback ---

def test_dutch_expense_with_euro_word():
    result = _regex_parse("ik heb 14 euro uitgegeven aan kebab")
    assert result["amount"] == pytest.approx(14.0)
    assert result["type"] == "Expense"
    assert "kebab" in result["description"]


def test_dutch_income_binnengekregen():
    result = _regex_parse("314 DUO binnengekregen")
    assert result["amount"] == pytest.approx(314.0)
    assert result["type"] == "Income"


def test_dutch_income_gekregen():
    result = _regex_parse("150 gekregen van mijn oom")
    assert result["amount"] == pytest.approx(150.0)
    assert result["type"] == "Income"


def test_dutch_fuel_getankt():
    result = _regex_parse("net 65 getankt")
    assert result["amount"] == pytest.approx(65.0)
    assert result["type"] == "Expense"


def test_dutch_comma_decimal():
    result = _regex_parse("vandaag 8,50 koffie gehaald")
    assert result["amount"] == pytest.approx(8.50)
    assert result["type"] == "Expense"


def test_english_natural():
    result = _regex_parse("spent 8.50 on coffee")
    assert result["amount"] == pytest.approx(8.50)
    assert result["type"] == "Expense"


# --- AI-mocked parse_message ---

def test_parse_message_dutch_ai_response():
    ai = {
        "amount": 14.0, "type": "Expense", "description": "kebab",
        "category": "Food", "is_impulse": False,
        "confidence": 0.95, "needs_clarification": False, "clarification_question": "",
    }
    with patch("app.parser._ai_parse", return_value=ai):
        result = parse_message("ik heb 14 euro uitgegeven aan kebab")
    assert result["amount"] == pytest.approx(14.0)
    assert result["type"] == "Expense"
    assert result["category"] == "Food"
    assert result.get("needs_clarification") is not True


def test_parse_message_income_duo():
    ai = {
        "amount": 314.0, "type": "Income", "description": "DUO",
        "category": "Income", "is_impulse": False,
        "confidence": 1.0, "needs_clarification": False, "clarification_question": "",
    }
    with patch("app.parser._ai_parse", return_value=ai):
        result = parse_message("314 DUO binnengekregen")
    assert result["amount"] == pytest.approx(314.0)
    assert result["type"] == "Income"


def test_parse_message_needs_clarification():
    ai = {
        "amount": None, "type": "Expense", "description": "",
        "category": "Other", "is_impulse": False,
        "confidence": 0.2, "needs_clarification": True,
        "clarification_question": "How much did you spend?",
    }
    with patch("app.parser._ai_parse", return_value=ai):
        result = parse_message("iets iets")
    assert result.get("needs_clarification") is True
    assert "How much" in result.get("clarification_question", "")


def test_parse_message_dynamic_category_normalized():
    ai = {
        "amount": 40.0, "type": "Expense", "description": "boxing gloves",
        "category": "Sports", "is_impulse": False,
        "confidence": 0.9, "needs_clarification": False, "clarification_question": "",
    }
    with patch("app.parser._ai_parse", return_value=ai):
        result = parse_message("40 boxing gloves")
    # "Sports" is a synonym for "Health"
    assert result["category"] == "Health"


def test_parse_message_synonym_category_normalized():
    ai = {
        "amount": 15.0, "type": "Expense", "description": "restaurant",
        "category": "Dining", "is_impulse": False,
        "confidence": 0.9, "needs_clarification": False, "clarification_question": "",
    }
    with patch("app.parser._ai_parse", return_value=ai):
        result = parse_message("15 dinner")
    assert result["category"] == "Food"
