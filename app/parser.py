import re
import json
import logging
from datetime import datetime
from app.utils import get_week_start, get_month

_log = logging.getLogger(__name__)

TRANSFER_KEYWORDS = {"savings", "portfolio", "transfer", "spaarrekening"}
INVESTMENT_KEYWORDS = {"degiro", "etf", "stock", "crypto", "invest", "investing"}

_AI_PROMPT = """You are a personal finance assistant parsing a Telegram message into a transaction.

Message: "{text}"

Return ONLY a valid JSON object, no explanation, no markdown:
{{
  "amount": <number or null if no amount found>,
  "type": "<Expense|Income|Transfer|Investment>",
  "description": "<1-3 word description in English>",
  "category": "<Food|Social|Transport|Project|Health|Clothing|Education|Impulse|Income|Investment|Transfer|Other>",
  "is_impulse": <true|false>
}}

Rules:
- type is Income if receiving money (salary, gift, refund, freelance, DUO, from someone)
- type is Transfer if moving money to savings or portfolio
- type is Investment if buying stocks, ETF, crypto
- type is Expense for everything else
- is_impulse is true only if the purchase seems unplanned or unnecessary
- description should be 1-3 words maximum, lowercase
- amount must be a positive number"""


def _ai_parse(text: str) -> dict | None:
    """Try to parse using AI. Returns parsed dict or None on failure."""
    from app import config

    prompt = _AI_PROMPT.format(text=text)

    try:
        if config.OPENAI_API_KEY:
            from openai import OpenAI
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0,
            )
            raw = response.choices[0].message.content.strip()
            return json.loads(raw)

        if config.ANTHROPIC_API_KEY:
            from anthropic import Anthropic
            client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            return json.loads(raw)

    except Exception as exc:
        _log.warning("AI parse failed for %r: %s", text, exc)

    return None


def _regex_parse(text: str) -> dict:
    """Fallback: original rigid format parser."""
    original = text.strip()

    if original.startswith("+"):
        msg_type = "Income"
        text = original[1:].strip()
    elif original.startswith("-"):
        msg_type = "Expense"
        text = original[1:].strip()
    else:
        msg_type = "Expense"
        text = original

    match = re.match(r"^(\d+(?:[.,]\d+)?)\s*(.*)", text)
    if not match:
        raise ValueError(f"Cannot parse amount from: {original!r}")

    amount = float(match.group(1).replace(",", "."))
    description = match.group(2).strip().lower()
    desc_words = set(description.split())

    if msg_type == "Expense":
        if desc_words & INVESTMENT_KEYWORDS:
            msg_type = "Investment"
        elif desc_words & TRANSFER_KEYWORDS:
            msg_type = "Transfer"

    return {
        "amount": amount,
        "description": description or "expense",
        "type": msg_type,
        "category": None,
        "is_impulse": "impulse" in description,
    }


def parse_message(text: str) -> dict:
    """Parse a Telegram message into a transaction dict.

    Tries AI parsing first (understands natural language), falls back to
    rigid regex parsing if AI is unavailable or fails.

    Returns dict with: amount, description, type, category, is_impulse,
    timestamp, date, week_start, month.
    """
    now = datetime.now()
    today = now.date()

    # Try AI first
    ai_result = _ai_parse(text)

    if ai_result and ai_result.get("amount"):
        parsed = {
            "amount": float(ai_result["amount"]),
            "description": str(ai_result.get("description", text[:30])).lower(),
            "type": ai_result.get("type", "Expense"),
            "category": ai_result.get("category"),
            "is_impulse": bool(ai_result.get("is_impulse", False)),
        }
    else:
        # Fallback to regex
        parsed = _regex_parse(text)

    # Add time fields
    parsed.update({
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": today.strftime("%Y-%m-%d"),
        "week_start": get_week_start(today).strftime("%Y-%m-%d"),
        "month": get_month(today),
    })

    return parsed
