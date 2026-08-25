from datetime import date
from app.utils import get_week_start, get_month

REIMBURSEMENT_MARKER = "[REIMBURSEMENT]"


def is_reimbursement(transaction: dict) -> bool:
    return (
        transaction.get("type") == "Income"
        and REIMBURSEMENT_MARKER in (transaction.get("notes") or "")
    )


def calculate_weekly_status(
    transactions: list[dict],
    budget: float,
    reference_date: date | None = None,
) -> dict:
    if reference_date is None:
        reference_date = date.today()

    week_start = get_week_start(reference_date).strftime("%Y-%m-%d")

    active = [
        t for t in transactions
        if t.get("week_start") == week_start
        and "[UNDONE]" not in (t.get("notes") or "")
    ]
    gross_spent = sum(
        t["amount"]
        for t in active
        if t.get("type") == "Expense"
    )
    reimbursements = sum(t["amount"] for t in active if is_reimbursement(t))
    weekly_spent = max(0.0, gross_spent - reimbursements)

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

    gross_spent = sum(t["amount"] for t in active if t.get("type") == "Expense")
    reimbursements = sum(t["amount"] for t in active if is_reimbursement(t))
    monthly_spent = max(0.0, gross_spent - reimbursements)
    monthly_income = sum(
        t["amount"]
        for t in active
        if t.get("type") == "Income" and not is_reimbursement(t)
    )

    by_category: dict[str, float] = {}
    for t in active:
        if t.get("type") == "Expense":
            cat = t.get("category", "Other")
            by_category[cat] = by_category.get(cat, 0.0) + t["amount"]
        elif is_reimbursement(t):
            cat = t.get("category", "Other")
            by_category[cat] = by_category.get(cat, 0.0) - t["amount"]
    by_category = {cat: amount for cat, amount in by_category.items() if amount > 0}

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
        "monthly_reimbursements": reimbursements,
        "net_cashflow": monthly_income - monthly_spent,
        "by_category": dict(sorted(by_category.items(), key=lambda x: x[1], reverse=True)),
        "impulse_total": impulse_total,
    }
