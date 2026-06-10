import re
import json
import logging
from datetime import datetime, timedelta, date as date_type
from app.utils import get_week_start, get_month
from app import config

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

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


_IMAGE_PROMPT = """You are a personal finance assistant parsing a Dutch banking app screenshot.

Today's date is {today}. Yesterday was {yesterday}.

Extract ALL visible transactions. Resolve relative date headers to real dates:
- "Today" → {today}
- "Yesterday" → {yesterday}
- Any explicit date like "Monday 8 June 2026" → use that exact date in YYYY-MM-DD format

For each transaction return exactly these fields:
- amount: positive number (always positive, sign is captured in type)
- type: "Expense" | "Income" | "Transfer" | "Investment"
  Negative sign or plain debit = Expense; positive/green = Income;
  "transfer", "savings", "spaarrekening" = Transfer; ETF/crypto/DeGiro = Investment
- description: 1-3 clean English words, lowercase (e.g. "groceries", "fuel", "concert ticket")
- category: one of Food | Transport | Social | Health | Education | Clothing | Income | Investment | Transfer | Fee | Impulse | Other
- is_impulse: true if clearly an impulse buy, else false
- source_date: YYYY-MM-DD resolved from the date section header above this transaction
- confidence: 0.0-1.0 (lower when merchant is cryptic or category is unclear)
- needs_clarification: true if merchant is cryptic/unrecognisable OR amount sign is ambiguous
- clarification_question: a short natural-language question (empty string if needs_clarification=false)

Known Dutch merchants (never need clarification):
- AH / Albert Heijn / Jan Linders = groceries (Food)
- Shell / Esso / BP / Texaco / getankt = fuel (Transport)
- NS / GVB / RET / OV-chipkaart = public transport (Transport)
- Tikkie = check sign for Expense or Income

Always needs clarification (confidence < 0.7):
- All-caps merchant codes, BCK* prefix, PAS124 suffix alone
- "Exploitatie ..." venue names
- "TicketingPayments", "bunq" internal transactions without clear context

Return ONLY a valid JSON array, no markdown, no explanation:
[{{"amount": ..., "type": ..., "description": ..., "category": ..., "is_impulse": ...,
  "source_date": ..., "confidence": ..., "needs_clarification": ..., "clarification_question": ...}}]"""


def parse_image(photo_bytes: bytes, today: date_type | None = None) -> list[dict]:
    """Parse a banking screenshot into a list of transaction dicts using GPT-4o vision."""
    import base64

    if today is None:
        today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    prompt = _IMAGE_PROMPT.format(
        today=today.strftime("%Y-%m-%d"),
        yesterday=yesterday.strftime("%Y-%m-%d"),
    )
    image_b64 = base64.b64encode(photo_bytes).decode()

    raw_transactions = []
    try:
        if config.OPENAI_API_KEY:
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                    ],
                }],
                max_tokens=1000,
                temperature=0,
            )
            raw_transactions = json.loads(response.choices[0].message.content.strip())
    except Exception as exc:
        _log.warning("Image parse failed: %s", exc)
        return []

    results = []
    for tx in raw_transactions:
        if not tx.get("amount"):
            continue
        source_date_str = tx.get("source_date") or today.strftime("%Y-%m-%d")
        try:
            source_date = datetime.strptime(source_date_str, "%Y-%m-%d").date()
        except ValueError:
            source_date = today

        from app.categories import normalize_category
        raw_cat = tx.get("category") or ""

        results.append({
            "amount": float(tx["amount"]),
            "type": tx.get("type", "Expense"),
            "description": str(tx.get("description", "")).lower()[:50],
            "category": normalize_category(raw_cat) if raw_cat else None,
            "is_impulse": bool(tx.get("is_impulse", False)),
            "confidence": float(tx.get("confidence", 1.0)),
            "needs_clarification": bool(tx.get("needs_clarification", False)),
            "clarification_question": str(tx.get("clarification_question", "")),
            "timestamp": datetime.combine(source_date, datetime.now().time()).strftime("%Y-%m-%d %H:%M:%S"),
            "date": source_date.strftime("%Y-%m-%d"),
            "week_start": get_week_start(source_date).strftime("%Y-%m-%d"),
            "month": get_month(source_date),
        })

    return results
