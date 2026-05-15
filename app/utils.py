from datetime import date, timedelta

def format_currency(amount: float) -> str:
    return f"€{amount:.2f}"

def get_week_start(d: date | None = None) -> date:
    if d is None:
        d = date.today()
    return d - timedelta(days=d.weekday())

def get_month(d: date | None = None) -> str:
    if d is None:
        d = date.today()
    return d.strftime("%Y-%m")

def budget_color(pct: float) -> str:
    if pct >= 90:
        return "danger"
    if pct >= 75:
        return "warning"
    return "accent"
