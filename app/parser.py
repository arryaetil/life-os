import re
from datetime import datetime
from app.utils import get_week_start, get_month

TRANSFER_KEYWORDS = {"savings", "portfolio", "transfer", "spaarrekening"}
INVESTMENT_KEYWORDS = {"degiro", "etf", "stock", "crypto", "invest", "investing"}

def parse_message(text: str) -> dict:
    text = text.strip()

    if text.startswith("+"):
        msg_type = "Income"
        text = text[1:].strip()
    elif text.startswith("-"):
        msg_type = "Expense"
        text = text[1:].strip()
    else:
        msg_type = "Expense"

    match = re.match(r"^(\d+(?:[.,]\d+)?)\s*(.*)", text)
    if not match:
        raise ValueError(f"Cannot parse amount from: {text!r}")

    amount = float(match.group(1).replace(",", "."))
    description = match.group(2).strip().lower()
    desc_words = set(description.split())

    if msg_type == "Expense":
        if desc_words & INVESTMENT_KEYWORDS:
            msg_type = "Investment"
        elif desc_words & TRANSFER_KEYWORDS:
            msg_type = "Transfer"

    now = datetime.now()
    today = now.date()

    return {
        "amount": amount,
        "description": description,
        "type": msg_type,
        "is_impulse": "impulse" in description,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": today.strftime("%Y-%m-%d"),
        "week_start": get_week_start(today).strftime("%Y-%m-%d"),
        "month": get_month(today),
    }
