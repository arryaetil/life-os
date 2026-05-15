from datetime import date
from app.budget import calculate_weekly_status, calculate_monthly_summary

TRANSACTIONS = [
    {
        "week_start": "2026-05-11", "month": "2026-05",
        "type": "Expense", "amount": 14.0, "category": "Food",
        "is_impulse": False, "notes": "",
    },
    {
        "week_start": "2026-05-11", "month": "2026-05",
        "type": "Expense", "amount": 20.5, "category": "Social",
        "is_impulse": False, "notes": "",
    },
    {
        "week_start": "2026-05-11", "month": "2026-05",
        "type": "Income", "amount": 314.0, "category": "Income",
        "is_impulse": False, "notes": "",
    },
    {
        "week_start": "2026-05-11", "month": "2026-05",
        "type": "Expense", "amount": 99.0, "category": "Other",
        "is_impulse": False, "notes": "[UNDONE]",
    },
]

REF = date(2026, 5, 15)

def test_weekly_spent_excludes_income_and_undone():
    result = calculate_weekly_status(TRANSACTIONS, 90.0, REF)
    assert result["weekly_spent"] == 34.5

def test_weekly_remaining():
    result = calculate_weekly_status(TRANSACTIONS, 90.0, REF)
    assert result["remaining"] == 55.5

def test_pct_used():
    result = calculate_weekly_status(TRANSACTIONS, 90.0, REF)
    assert round(result["pct_used"], 1) == 38.3

def test_remaining_never_negative():
    result = calculate_weekly_status(TRANSACTIONS, 10.0, REF)
    assert result["remaining"] == 0.0

def test_monthly_spent():
    result = calculate_monthly_summary(TRANSACTIONS, REF)
    assert result["monthly_spent"] == 34.5

def test_monthly_income():
    result = calculate_monthly_summary(TRANSACTIONS, REF)
    assert result["monthly_income"] == 314.0

def test_net_cashflow():
    result = calculate_monthly_summary(TRANSACTIONS, REF)
    assert result["net_cashflow"] == 279.5

def test_by_category_sorted_descending():
    result = calculate_monthly_summary(TRANSACTIONS, REF)
    amounts = list(result["by_category"].values())
    assert amounts == sorted(amounts, reverse=True)

def test_impulse_total():
    txns = TRANSACTIONS + [{
        "week_start": "2026-05-11", "month": "2026-05",
        "type": "Expense", "amount": 30.0, "category": "Impulse",
        "is_impulse": True, "notes": "",
    }]
    result = calculate_monthly_summary(txns, REF)
    assert result["impulse_total"] == 30.0

def test_weekly_status_empty_transactions():
    result = calculate_weekly_status([], 90.0, REF)
    assert result["weekly_spent"] == 0.0
    assert result["remaining"] == 90.0
    assert result["pct_used"] == 0.0

def test_monthly_summary_empty_transactions():
    result = calculate_monthly_summary([], REF)
    assert result["monthly_spent"] == 0.0
    assert result["monthly_income"] == 0.0
    assert result["net_cashflow"] == 0.0
    assert result["by_category"] == {}
