import pytest
from app.parser import parse_message

def test_basic_expense():
    result = parse_message("14 kebab")
    assert result["type"] == "Expense"
    assert result["amount"] == 14.0
    assert result["description"] == "kebab"

def test_minus_prefix_is_expense():
    result = parse_message("-50 dinner")
    assert result["type"] == "Expense"
    assert result["amount"] == 50.0

def test_plus_prefix_is_income():
    result = parse_message("+314 DUO income")
    assert result["type"] == "Income"
    assert result["amount"] == 314.0
    assert result["description"] == "duo income"

def test_decimal_dot():
    result = parse_message("8.50 coffee")
    assert result["amount"] == 8.50

def test_decimal_comma():
    result = parse_message("8,50 coffee")
    assert result["amount"] == 8.50

def test_investment_keyword_overrides_type():
    result = parse_message("100 degiro etf")
    assert result["type"] == "Investment"

def test_transfer_keyword_overrides_type():
    result = parse_message("200 savings")
    assert result["type"] == "Transfer"

def test_income_prefix_not_overridden_by_keyword():
    result = parse_message("+200 savings refund")
    assert result["type"] == "Income"

def test_is_impulse_true():
    result = parse_message("25 impulse buy")
    assert result["is_impulse"] is True

def test_is_impulse_false():
    result = parse_message("14 kebab")
    assert result["is_impulse"] is False

def test_invalid_message_raises():
    with pytest.raises(ValueError):
        parse_message("no amount here")

def test_week_start_is_monday():
    result = parse_message("5 coffee")
    from datetime import date
    from app.utils import get_week_start
    week_start = get_week_start(date.today()).strftime("%Y-%m-%d")
    assert result["week_start"] == week_start
