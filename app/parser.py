import re
import json
import logging
from datetime import datetime
from app.utils import get_week_start, get_month

_log = logging.getLogger(__name__)

TRANSFER_KEYWORDS = {"savings", "portfolio", "transfer", "spaarrekening"}
INVESTMENT_KEYWORDS = {"degiro", "etf", "stock", "crypto", "invest", "investing"}

_DUTCH_INCOME_KW = frozenset({
    "gekregen", "ontvangen", "binnengekregen", "teruggekregen",
    "salary", "salaris", "loon", "inkomen", "refund",
})

_AI_PROMPT = """You are a personal finance assistant. Parse this message (Dutch or English) into a transaction.

Message: "{text}"

Return ONLY valid JSON (no markdown, no explanation):
{{
  "amount": <positive number or null>,
  "type": "<Expense|Income|Transfer|Investment>",
  "description": "<1-3 words in English, lowercase>",
  "category": "<see below>",
  "is_impulse": <true|false>,
  "confidence": <0.0-1.0>,
  "needs_clarification": <false|true>,
  "clarification_question": "<short question or empty string>"
}}

Preferred categories: Food, Transport, Social, Health, Education, Project, Clothing, Income, Investment, Transfer, Impulse, Other
If none fit, suggest a short clean name (e.g. Sports, Utilities, Personal).

Type rules:
- Expense: spending money on anything
- Income: receiving money (salary, DUO, gift, refund, "gekregen", "ontvangen", "van oom/tante")
- Transfer: moving to savings or portfolio ("gespaard", "spaarrekening", "portfolio")
- Investment: buying stocks, ETF, crypto

Dutch key phrases:
- "uitgegeven aan" / "gekocht" / "gehaald" / "getankt" = spent (Expense)
- "gekregen" / "ontvangen" / "binnengekregen" = received (Income)
- "DUO" = Dutch student finance (Income)
- "getankt" = filled up car with fuel (Expense, Transport)
- Comma is decimal separator (8,50 = 8.50)

Confidence: 1.0 if clear; <0.7 means ambiguous.
Set needs_clarification=true ONLY if amount is missing OR type cannot be determined at all.
clarification_question: a short question to ask the user (or empty string)."""


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
    """Fallback parser — handles Dutch and English, finds amount anywhere in text."""
    original = text.strip()
    lower = original.lower()

    # Determine transaction type
    if original.startswith("+"):
        msg_type = "Income"
    elif original.startswith("-"):
        msg_type = "Expense"
    elif any(kw in lower for kw in _DUTCH_INCOME_KW):
        msg_type = "Income"
    else:
        msg_type = "Expense"

    # Find amount anywhere in text (supports comma decimals)
    m = re.search(r"(\d+(?:[.,]\d+)?)", original)
    if not m:
        raise ValueError(f"Cannot parse amount from: {original!r}")
    amount = float(m.group(1).replace(",", "."))

    # Extract description: remove amount and Dutch/English filler
    desc = original
    desc = re.sub(r"[+\-]", "", desc)
    desc = re.sub(r"\d+(?:[.,]\d+)?", "", desc)
    desc = re.sub(
        r"\b(?:ik heb|vandaag|net|euro|eur|€|uitgegeven aan|gehaald|"
        r"getankt|gekocht|gekregen|ontvangen|binnengekregen|"
        r"teruggekregen|van mijn|mijn|voor|aan|spent|on|filled up|for)\b",
        " ", desc, flags=re.IGNORECASE,
    )
    desc = re.sub(r"\s+", " ", desc).strip().lower()
    desc = desc or "expense"

    # Override to Investment/Transfer if keyword found
    desc_words = set(desc.split())
    if msg_type == "Expense":
        if desc_words & INVESTMENT_KEYWORDS:
            msg_type = "Investment"
        elif desc_words & TRANSFER_KEYWORDS:
            msg_type = "Transfer"

    return {
        "amount": amount,
        "description": desc[:50],
        "type": msg_type,
        "category": None,
        "is_impulse": "impulse" in desc,
    }


def is_bulk_message(text: str) -> bool:
    """Return True if text contains 2+ lines that each have an amount."""
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    amount_lines = [l for l in lines if re.search(r"\d+(?:[.,]\d+)?", l)]
    return len(amount_lines) >= 2


def parse_bulk_message(text: str) -> list[dict]:
    """Parse each amount-bearing line as an independent transaction."""
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    results = []
    for line in lines:
        if not re.search(r"\d+(?:[.,]\d+)?", line):
            continue
        try:
            parsed = parse_message(line)
            results.append(parsed)
        except ValueError:
            pass
    return results


def parse_message(text: str) -> dict:
    """Parse a Telegram message into a transaction dict.

    Returns dict with: amount, description, type, category, is_impulse,
    timestamp, date, week_start, month.

    If AI signals needs_clarification=True, returns a special dict with
    needs_clarification=True and clarification_question instead of transaction fields.
    """
    now = datetime.now()
    today = now.date()
    time_fields = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": today.strftime("%Y-%m-%d"),
        "week_start": get_week_start(today).strftime("%Y-%m-%d"),
        "month": get_month(today),
    }

    ai_result = _ai_parse(text)

    # Handle clarification request from AI
    if ai_result and ai_result.get("needs_clarification"):
        return {
            "needs_clarification": True,
            "clarification_question": ai_result.get("clarification_question") or "Could you be more specific?",
            **time_fields,
        }

    if ai_result and ai_result.get("amount"):
        from app.categories import normalize_category
        raw_cat = ai_result.get("category") or ""
        parsed = {
            "amount": float(ai_result["amount"]),
            "description": str(ai_result.get("description", text[:30])).lower(),
            "type": ai_result.get("type", "Expense"),
            "category": normalize_category(raw_cat) if raw_cat else None,
            "is_impulse": bool(ai_result.get("is_impulse", False)),
            "confidence": float(ai_result.get("confidence", 1.0)),
        }
    else:
        parsed = _regex_parse(text)

    parsed.update(time_fields)
    return parsed
