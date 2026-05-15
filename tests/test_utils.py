from datetime import date
from app.utils import format_currency, get_week_start, get_month, budget_color

def test_format_currency_whole():
    assert format_currency(14.0) == "€14.00"

def test_format_currency_decimal():
    assert format_currency(8.5) == "€8.50"

def test_format_currency_zero():
    assert format_currency(0) == "€0.00"

def test_get_week_start_on_monday():
    monday = date(2026, 5, 11)
    assert get_week_start(monday) == monday

def test_get_week_start_on_friday():
    friday = date(2026, 5, 15)
    assert get_week_start(friday) == date(2026, 5, 11)

def test_get_week_start_on_sunday():
    sunday = date(2026, 5, 17)
    assert get_week_start(sunday) == date(2026, 5, 11)

def test_get_month():
    assert get_month(date(2026, 5, 15)) == "2026-05"

def test_budget_color_low():
    assert budget_color(38.3) == "accent"

def test_budget_color_warning():
    assert budget_color(77.8) == "warning"

def test_budget_color_danger():
    assert budget_color(95.0) == "danger"

def test_budget_color_exactly_75():
    assert budget_color(75.0) == "warning"

def test_budget_color_exactly_90():
    assert budget_color(90.0) == "danger"

def test_get_week_start_none_returns_monday():
    from datetime import date
    result = get_week_start(None)
    assert result.weekday() == 0  # Monday

def test_get_month_none_returns_current():
    from datetime import date
    result = get_month(None)
    today = date.today()
    assert result == today.strftime("%Y-%m")
