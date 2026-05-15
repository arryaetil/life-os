import re
import json
import logging

_log = logging.getLogger(__name__)

_NW_TRIGGERS = {"net worth", "networth", "nw"}
_NW_KEYWORDS = {
    "cash", "investments", "investment", "invest",
    "crypto", "savings", "saving",
    "liabilities", "liability", "debt", "other",
}

_AMOUNT_PAT = r"(\d+(?:[.,]\d+)?k?)"

_FIELD_PATTERNS = [
    ("cash",         re.compile(r"cash\s+" + _AMOUNT_PAT, re.IGNORECASE)),
    ("investments",  re.compile(r"invest(?:ments?)?\s+" + _AMOUNT_PAT, re.IGNORECASE)),
    ("crypto",       re.compile(r"crypto\s+" + _AMOUNT_PAT, re.IGNORECASE)),
    ("savings",      re.compile(r"savings?\s+" + _AMOUNT_PAT, re.IGNORECASE)),
    ("other_assets", re.compile(r"other(?:_assets?)?\s+" + _AMOUNT_PAT, re.IGNORECASE)),
    ("liabilities",  re.compile(r"(?:liabilities|liability|debt)\s+" + _AMOUNT_PAT, re.IGNORECASE)),
]

_TOTAL_ONLY_PAT = re.compile(r"(?:net\s*worth|nw)\s+" + _AMOUNT_PAT, re.IGNORECASE)

_AI_PROMPT = (
    'Parse this net worth message and return ONLY valid JSON:\n'
    '{{"cash":0,"investments":0,"crypto":0,"savings":0,"other_assets":0,"liabilities":0}}\n'
    'Rules: missing fields = 0, "k" suffix = x1000, liabilities/debt are positive numbers.\n'
    'Message: "{text}"'
)


def _parse_amount(raw: str) -> float:
    """Convert amount string to float. Handles 'k' suffix (2k → 2000) and comma decimals."""
    raw = raw.strip().lower()
    if raw.endswith("k"):
        return float(raw[:-1].replace(",", ".")) * 1000.0
    return float(raw.replace(",", "."))


def is_net_worth_message(text: str) -> bool:
    lower = text.lower()
    for trigger in _NW_TRIGGERS:
        if trigger in lower:
            return True
    found = sum(1 for kw in _NW_KEYWORDS if re.search(r"\b" + kw + r"\b", lower))
    return found >= 2


def _regex_parse(text: str) -> dict:
    result = {field: 0.0 for field, _ in _FIELD_PATTERNS}
    for field, pattern in _FIELD_PATTERNS:
        m = pattern.search(text)
        if m:
            result[field] = _parse_amount(m.group(1))
    if all(v == 0.0 for v in result.values()):
        m = _TOTAL_ONLY_PAT.search(text)
        if m:
            result["other_assets"] = _parse_amount(m.group(1))
    return result


def _ai_parse(text: str) -> dict | None:
    from app import config
    prompt = _AI_PROMPT.format(text=text)
    try:
        if config.OPENAI_API_KEY:
            from openai import OpenAI
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0,
            )
            return json.loads(resp.choices[0].message.content.strip())
        if config.ANTHROPIC_API_KEY:
            from anthropic import Anthropic
            client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )
            return json.loads(msg.content[0].text.strip())
    except Exception as exc:
        _log.warning("AI net worth parse failed: %s", exc)
    return None


def parse_net_worth_message(text: str) -> dict:
    """Parse natural language net worth message into asset field dict.

    Returns: {cash, investments, crypto, savings, other_assets, liabilities}
    All values are floats. Missing fields default to 0.0.
    """
    _fields = [f for f, _ in _FIELD_PATTERNS]
    ai = _ai_parse(text)
    if ai and any(float(ai.get(f, 0)) > 0 for f in _fields):
        return {f: float(ai.get(f, 0.0)) for f in _fields}
    return _regex_parse(text)
