from datetime import date
from app.utils import get_week_start, get_month

def calculate_weekly_status(
    transactions: list[dict],
    budget: float,
    reference_date: date | None = None,
) -> dict:
    if reference_date is None:
        reference_date = date.today()

    week_start = get_week_start(reference_date).strftime("%Y-%m-%d")

    weekly_spent = sum(
        t["amount"]
        for t in transactions
        if t.get("week_start") == week_start
        and t.get("type") == "Expense"
        and "[UNDONE]" not in (t.get("notes") or "")
    )

    remaining = max(0.0, budget - weekly_spent)
    pct_used = min(100.0, weekly_spent / budget * 100) if budget > 0 else 0.0

    return {
        "weekly_spent": weekly_spent,
        "weekly_budget": budget,
        "remaining": remaining,
        "pct_used": pct_used,
        "week_start": week_start,
    }

def calculate_monthly_summary(
    transactions: list[dict],
    reference_date: date | None = None,
) -> dict:
    if reference_date is None:
        reference_date = date.today()

    month = get_month(reference_date)
    active = [
        t for t in transactions
        if t.get("month") == month
        and "[UNDONE]" not in (t.get("notes") or "")
    ]

    monthly_spent = sum(t["amount"] for t in active if t.get("type") == "Expense")
    monthly_income = sum(t["amount"] for t in active if t.get("type") == "Income")

    by_category: dict[str, float] = {}
    for t in active:
        if t.get("type") == "Expense":
            cat = t.get("category", "Other")
            by_category[cat] = by_category.get(cat, 0.0) + t["amount"]

    impulse_total = sum(
        t["amount"]
        for t in active
        if t.get("type") == "Expense"
        and t.get("is_impulse") in (True, "TRUE", "true", "1")
    )

    return {
        "month": month,
        "monthly_spent": monthly_spent,
        "monthly_income": monthly_income,
        "net_cashflow": monthly_income - monthly_spent,
        "by_category": dict(sorted(by_category.items(), key=lambda x: x[1], reverse=True)),
        "impulse_total": impulse_total,
    }
