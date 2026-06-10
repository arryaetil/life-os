# Photo Expense Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to send Bunq/banking app screenshots to the Telegram bot and have all visible transactions extracted, clarified via natural language, and logged with the correct historical dates.

**Architecture:** A new `parse_image` function in `parser.py` calls GPT-4o vision to extract transactions from the screenshot. A conversation state machine in `commands.py` handles per-transaction clarification questions and a final natural-language confirmation step (supporting selective skipping). A new `handle_photo` handler is registered in `bot.py` with `filters.PHOTO`. All existing text flows are untouched.

**Tech Stack:** python-telegram-bot (PTB), OpenAI Python SDK (gpt-4o for vision, gpt-4o-mini for clarification/confirmation text), pytest with asyncio_mode=auto, unittest.mock

---

## File Map

| File | What changes |
|------|-------------|
| `app/parser.py` | Add `parse_image`, `_resolve_clarification`, `_resolve_confirmation` |
| `app/commands.py` | Add `handle_photo`, `_send_confirmation_preview`, `_handle_image_session`; add Priority 0 check in `handle_message` |
| `app/bot.py` | Import `handle_photo`; register `filters.PHOTO` handler |
| `tests/test_image_parser.py` | New — tests for `parse_image`, `_resolve_clarification`, `_resolve_confirmation` |
| `tests/test_image_commands.py` | New — tests for `handle_photo`, `_handle_image_session`, Priority 0 routing |

---

## Task 1: `parse_image` in `parser.py`

**Files:**
- Modify: `app/parser.py`
- Test: `tests/test_image_parser.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_image_parser.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from datetime import date


def _mock_openai_response(content: str):
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


def test_parse_image_single_clear_transaction():
    resp = _mock_openai_response(
        '[{"amount": 20.40, "type": "Expense", "description": "fuel", "category": "Transport",'
        ' "is_impulse": false, "source_date": "2026-06-09", "confidence": 0.95,'
        ' "needs_clarification": false, "clarification_question": ""}]'
    )
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        mock_cfg.ANTHROPIC_API_KEY = ""
        MockOAI.return_value.chat.completions.create.return_value = resp
        from app.parser import parse_image
        result = parse_image(b"fake_bytes", today=date(2026, 6, 10))

    assert len(result) == 1
    t = result[0]
    assert t["amount"] == 20.40
    assert t["date"] == "2026-06-09"
    assert t["description"] == "fuel"
    assert t["type"] == "Expense"
    assert t["needs_clarification"] is False
    assert t["week_start"] == "2026-06-09"   # Tuesday — week starts Monday 9th
    assert t["month"] == "2026-06"


def test_parse_image_flags_clarification():
    resp = _mock_openai_response(
        '[{"amount": 351.98, "type": "Expense", "description": "ticketing payments",'
        ' "category": "Other", "is_impulse": false, "source_date": "2026-06-07",'
        ' "confidence": 0.4, "needs_clarification": true,'
        ' "clarification_question": "TicketingPayments -€351.98 — what was this for?"}]'
    )
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        mock_cfg.ANTHROPIC_API_KEY = ""
        MockOAI.return_value.chat.completions.create.return_value = resp
        from app.parser import parse_image
        result = parse_image(b"fake_bytes", today=date(2026, 6, 10))

    assert result[0]["needs_clarification"] is True
    assert "TicketingPayments" in result[0]["clarification_question"]


def test_parse_image_income_positive_sign():
    resp = _mock_openai_response(
        '[{"amount": 10.00, "type": "Income", "description": "winkens", "category": "Income",'
        ' "is_impulse": false, "source_date": "2026-06-09", "confidence": 0.9,'
        ' "needs_clarification": false, "clarification_question": ""}]'
    )
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        mock_cfg.ANTHROPIC_API_KEY = ""
        MockOAI.return_value.chat.completions.create.return_value = resp
        from app.parser import parse_image
        result = parse_image(b"fake_bytes", today=date(2026, 6, 10))

    assert result[0]["type"] == "Income"
    assert result[0]["amount"] == 10.00


def test_parse_image_returns_empty_on_api_failure():
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        mock_cfg.ANTHROPIC_API_KEY = ""
        MockOAI.return_value.chat.completions.create.side_effect = Exception("API error")
        from app.parser import parse_image
        result = parse_image(b"fake_bytes")

    assert result == []


def test_parse_image_skips_items_without_amount():
    resp = _mock_openai_response(
        '[{"amount": null, "type": "Expense", "description": "bad", "category": "Other",'
        ' "is_impulse": false, "source_date": "2026-06-10", "confidence": 0.1,'
        ' "needs_clarification": false, "clarification_question": ""}]'
    )
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        mock_cfg.ANTHROPIC_API_KEY = ""
        MockOAI.return_value.chat.completions.create.return_value = resp
        from app.parser import parse_image
        result = parse_image(b"fake_bytes", today=date(2026, 6, 10))

    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_image_parser.py -v
```

Expected: all fail with `ImportError: cannot import name 'parse_image'`

- [ ] **Step 3: Add `timedelta` import and `parse_image` to `parser.py`**

At the top of `app/parser.py`, the existing import line is:
```python
from datetime import datetime
```

Change it to:
```python
from datetime import datetime, timedelta, date as date_type
```

Then add this entire block **after** the existing `parse_message` function (at the end of the file):

```python
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
    from app import config

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
            from openai import OpenAI
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_image_parser.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/parser.py tests/test_image_parser.py
git commit -m "feat(image): add parse_image with GPT-4o vision"
```

---

## Task 2: `_resolve_clarification` in `parser.py`

**Files:**
- Modify: `app/parser.py`
- Test: `tests/test_image_parser.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_image_parser.py`:

```python
def test_resolve_clarification_updates_description_and_category():
    tx = {
        "description": "gelredome", "amount": 20.00, "type": "Expense",
        "date": "2026-06-08", "clarification_question": "What was Gelredome?",
        "category": "Other",
    }
    resp = _mock_openai_response('{"skip": false, "description": "concert venue", "category": "Social"}')
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        MockOAI.return_value.chat.completions.create.return_value = resp
        from app.parser import _resolve_clarification
        result = _resolve_clarification(tx, "concert with friends")

    assert result["skip"] is False
    assert result["description"] == "concert venue"
    assert result["category"] is not None


def test_resolve_clarification_marks_skip():
    tx = {
        "description": "ticketing payments", "amount": 351.98, "type": "Expense",
        "date": "2026-06-07", "clarification_question": "What was this for?",
        "category": "Other",
    }
    resp = _mock_openai_response('{"skip": true, "description": "", "category": ""}')
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        MockOAI.return_value.chat.completions.create.return_value = resp
        from app.parser import _resolve_clarification
        result = _resolve_clarification(tx, "skip that one")

    assert result["skip"] is True


def test_resolve_clarification_fallback_skip_keyword():
    tx = {
        "description": "bunq", "amount": 20.00, "type": "Expense",
        "date": "2026-06-10", "clarification_question": "What is this bunq charge?",
        "category": "Other",
    }
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        MockOAI.return_value.chat.completions.create.side_effect = Exception("fail")
        from app.parser import _resolve_clarification
        result = _resolve_clarification(tx, "leave out")

    assert result["skip"] is True


def test_resolve_clarification_fallback_non_skip():
    tx = {
        "description": "bunq", "amount": 20.00, "type": "Expense",
        "date": "2026-06-10", "clarification_question": "What is this bunq charge?",
        "category": "Other",
    }
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        MockOAI.return_value.chat.completions.create.side_effect = Exception("fail")
        from app.parser import _resolve_clarification
        result = _resolve_clarification(tx, "monthly fee")

    assert result["skip"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_image_parser.py::test_resolve_clarification_updates_description_and_category tests/test_image_parser.py::test_resolve_clarification_marks_skip tests/test_image_parser.py::test_resolve_clarification_fallback_skip_keyword tests/test_image_parser.py::test_resolve_clarification_fallback_non_skip -v
```

Expected: all fail with `ImportError: cannot import name '_resolve_clarification'`

- [ ] **Step 3: Add `_resolve_clarification` to `parser.py`**

Append to `app/parser.py` (after `parse_image`):

```python
_CLARIFICATION_PROMPT = """A user is clarifying a transaction from their bank statement.

Transaction: {description} | {sign}€{amount:.2f} on {date}
Question asked: "{question}"
User's reply: "{reply}"

If the user says to ignore/skip/leave out this transaction → set skip=true.
Otherwise extract a clean description and category.

Return ONLY valid JSON:
{{"skip": false, "description": "<1-3 English words lowercase>", "category": "<Food|Transport|Social|Health|Education|Clothing|Income|Investment|Transfer|Fee|Impulse|Other>"}}
or
{{"skip": true, "description": "", "category": ""}}"""


def _resolve_clarification(transaction: dict, reply: str) -> dict:
    """Interpret a free-text clarification reply. Returns {"skip": True} or updated fields."""
    from app import config
    from app.categories import normalize_category

    sign = "+" if transaction.get("type") == "Income" else "-"
    prompt = _CLARIFICATION_PROMPT.format(
        description=transaction.get("description", "?"),
        sign=sign,
        amount=float(transaction.get("amount", 0)),
        date=transaction.get("date", "?"),
        question=transaction.get("clarification_question", ""),
        reply=reply,
    )

    try:
        if config.OPENAI_API_KEY:
            from openai import OpenAI
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=80,
                temperature=0,
            )
            result = json.loads(response.choices[0].message.content.strip())
            if result.get("skip"):
                return {"skip": True}
            raw_cat = result.get("category", "")
            return {
                "skip": False,
                "description": result.get("description", transaction.get("description", "")),
                "category": normalize_category(raw_cat) if raw_cat else transaction.get("category"),
            }
    except Exception as exc:
        _log.warning("Clarification resolve failed: %s", exc)

    lower = reply.strip().lower()
    if any(w in lower for w in ("skip", "ignore", "leave out", "don't log", "not this", "no")):
        return {"skip": True}
    return {"skip": False, "description": reply[:30].lower(), "category": transaction.get("category")}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_image_parser.py -v
```

Expected: all 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/parser.py tests/test_image_parser.py
git commit -m "feat(image): add _resolve_clarification for natural language replies"
```

---

## Task 3: `_resolve_confirmation` in `parser.py`

**Files:**
- Modify: `app/parser.py`
- Test: `tests/test_image_parser.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_image_parser.py`:

```python
def _sample_transactions():
    return [
        {"date": "2026-06-10", "description": "bunq fee", "amount": 20.00,
         "type": "Expense", "category": "Fee"},
        {"date": "2026-06-09", "description": "fuel", "amount": 20.40,
         "type": "Expense", "category": "Transport"},
        {"date": "2026-06-09", "description": "groceries", "amount": 7.57,
         "type": "Expense", "category": "Food"},
    ]


def test_resolve_confirmation_log_all():
    resp = _mock_openai_response('{"action": "log_all", "skip_indices": []}')
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        MockOAI.return_value.chat.completions.create.return_value = resp
        from app.parser import _resolve_confirmation
        action, skip = _resolve_confirmation(_sample_transactions(), "yes")

    assert action == "log_all"
    assert skip == []


def test_resolve_confirmation_cancel():
    resp = _mock_openai_response('{"action": "cancel", "skip_indices": []}')
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        MockOAI.return_value.chat.completions.create.return_value = resp
        from app.parser import _resolve_confirmation
        action, skip = _resolve_confirmation(_sample_transactions(), "no")

    assert action == "cancel"


def test_resolve_confirmation_skip_some():
    resp = _mock_openai_response('{"action": "skip_some", "skip_indices": [0]}')
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        MockOAI.return_value.chat.completions.create.return_value = resp
        from app.parser import _resolve_confirmation
        action, skip = _resolve_confirmation(_sample_transactions(), "leave out the bunq one")

    assert action == "skip_some"
    assert 0 in skip


def test_resolve_confirmation_fallback_yes():
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        MockOAI.return_value.chat.completions.create.side_effect = Exception("fail")
        from app.parser import _resolve_confirmation
        action, skip = _resolve_confirmation(_sample_transactions(), "ja")

    assert action == "log_all"
    assert skip == []


def test_resolve_confirmation_fallback_no():
    with patch("app.parser.config") as mock_cfg, patch("app.parser.OpenAI") as MockOAI:
        mock_cfg.OPENAI_API_KEY = "test-key"
        MockOAI.return_value.chat.completions.create.side_effect = Exception("fail")
        from app.parser import _resolve_confirmation
        action, skip = _resolve_confirmation(_sample_transactions(), "nee")

    assert action == "cancel"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_image_parser.py::test_resolve_confirmation_log_all tests/test_image_parser.py::test_resolve_confirmation_cancel tests/test_image_parser.py::test_resolve_confirmation_skip_some -v
```

Expected: all fail with `ImportError: cannot import name '_resolve_confirmation'`

- [ ] **Step 3: Add `_resolve_confirmation` to `parser.py`**

Append to `app/parser.py` (after `_resolve_clarification`):

```python
_CONFIRMATION_PROMPT = """A user is reviewing a list of transactions before logging them.

Transactions (1-based):
{transaction_list}

User's reply: "{reply}"

Determine the action:
- "yes" / "ja" / "ok" / "log all" / "sure" → log_all
- "no" / "nee" / "cancel" / "stop" → cancel
- Anything that skips specific items → skip_some with 0-based indices of the items to skip

Return ONLY valid JSON:
{{"action": "log_all" | "cancel" | "skip_some", "skip_indices": [<0-based indices to skip>]}}

Examples:
"yes" → {{"action": "log_all", "skip_indices": []}}
"no" → {{"action": "cancel", "skip_indices": []}}
"skip 1 and 3" (user says 1-based) → {{"action": "skip_some", "skip_indices": [0, 2]}}
"leave out the bunq one" (item 1 is bunq fee) → {{"action": "skip_some", "skip_indices": [0]}}
"yes but not the transfer" → {{"action": "skip_some", "skip_indices": [<transfer index>]}}"""


def _resolve_confirmation(transactions: list[dict], reply: str) -> tuple[str, list[int]]:
    """Interpret a free-text confirmation reply. Returns (action, skip_indices).

    action is one of: 'log_all', 'cancel', 'skip_some'
    skip_indices are 0-based indices into transactions to exclude.
    """
    from app import config

    tx_lines = "\n".join(
        f"{i + 1}. {t['date']} | {t['description']} | "
        f"{'+' if t['type'] == 'Income' else '-'}€{float(t['amount']):.2f} ({t.get('category', '?')})"
        for i, t in enumerate(transactions)
    )
    prompt = _CONFIRMATION_PROMPT.format(transaction_list=tx_lines, reply=reply)

    try:
        if config.OPENAI_API_KEY:
            from openai import OpenAI
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0,
            )
            result = json.loads(response.choices[0].message.content.strip())
            return result.get("action", "cancel"), result.get("skip_indices", [])
    except Exception as exc:
        _log.warning("Confirmation resolve failed: %s", exc)

    lower = reply.strip().lower()
    if lower in ("yes", "ja", "y", "ok", "yep", "sure", "log all", "ja allemaal"):
        return "log_all", []
    return "cancel", []
```

- [ ] **Step 4: Run all parser tests**

```bash
pytest tests/test_image_parser.py tests/test_parser.py -v
```

Expected: all pass (existing parser tests unchanged)

- [ ] **Step 5: Commit**

```bash
git add app/parser.py tests/test_image_parser.py
git commit -m "feat(image): add _resolve_confirmation for natural language approval"
```

---

## Task 4: `handle_photo` and `_send_confirmation_preview` in `commands.py`

**Files:**
- Modify: `app/commands.py`
- Test: `tests/test_image_commands.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_image_commands.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_photo_update():
    update = MagicMock()
    update.message.photo = [MagicMock(file_id="file_abc")]
    update.message.reply_text = AsyncMock()
    update.effective_chat.id = 123
    return update


def _make_context(user_data=None):
    context = MagicMock()
    context.bot.send_chat_action = AsyncMock()
    context.bot.get_file = AsyncMock()
    context.bot.get_file.return_value.download_as_bytearray = AsyncMock(
        return_value=bytearray(b"fake_image_bytes")
    )
    context.user_data = user_data if user_data is not None else {}
    return context


def _clear_transaction(overrides=None):
    t = {
        "amount": 7.57, "type": "Expense", "description": "groceries",
        "category": "Food", "is_impulse": False, "confidence": 0.95,
        "needs_clarification": False, "clarification_question": "",
        "date": "2026-06-08", "timestamp": "2026-06-08 10:00:00",
        "week_start": "2026-06-02", "month": "2026-06",
    }
    if overrides:
        t.update(overrides)
    return t


async def test_handle_photo_empty_result_sends_error():
    update = _make_photo_update()
    context = _make_context()

    with patch("app.commands.parse_image", return_value=[]):
        from app.commands import handle_photo
        await handle_photo(update, context)

    reply = update.message.reply_text.call_args[0][0]
    assert "Couldn't read" in reply
    assert "image_session" not in context.user_data


async def test_handle_photo_clear_transactions_skips_to_confirmation():
    update = _make_photo_update()
    context = _make_context()
    transactions = [_clear_transaction()]

    with patch("app.commands.parse_image", return_value=transactions):
        from app.commands import handle_photo
        await handle_photo(update, context)

    assert context.user_data["image_session"]["awaiting_confirmation"] is True
    reply = update.message.reply_text.call_args[0][0]
    assert "Ready to log" in reply
    assert "groceries" in reply


async def test_handle_photo_unclear_transaction_asks_first_question():
    update = _make_photo_update()
    context = _make_context()
    transactions = [
        _clear_transaction({
            "description": "ticketing", "amount": 351.98, "category": "Other",
            "confidence": 0.4, "needs_clarification": True,
            "clarification_question": "TicketingPayments -€351.98 — what was this for?",
            "date": "2026-06-07",
        })
    ]

    with patch("app.commands.parse_image", return_value=transactions):
        from app.commands import handle_photo
        await handle_photo(update, context)

    session = context.user_data["image_session"]
    assert session["awaiting_confirmation"] is False
    assert session["cursor"] == 0
    reply = update.message.reply_text.call_args[0][0]
    assert "TicketingPayments" in reply


async def test_handle_photo_mixed_transactions_asks_first_unclear_only():
    update = _make_photo_update()
    context = _make_context()
    transactions = [
        _clear_transaction(),  # clear
        _clear_transaction({
            "description": "gelredome", "needs_clarification": True,
            "clarification_question": "What was Gelredome?", "category": "Other",
        }),  # unclear
    ]

    with patch("app.commands.parse_image", return_value=transactions):
        from app.commands import handle_photo
        await handle_photo(update, context)

    session = context.user_data["image_session"]
    assert len(session["clarifications"]) == 1
    assert session["clarifications"][0][0] == 1  # index of unclear transaction
    reply = update.message.reply_text.call_args[0][0]
    assert "Gelredome" in reply
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_image_commands.py -v
```

Expected: all fail with `ImportError: cannot import name 'handle_photo'`

- [ ] **Step 3: Add imports and functions to `commands.py`**

At the top of `app/commands.py`, find the existing import:
```python
from app.parser import parse_message, is_bulk_message, parse_bulk_message
```

Replace it with:
```python
from app.parser import parse_message, is_bulk_message, parse_bulk_message, parse_image, _resolve_clarification, _resolve_confirmation
```

Then append these three functions at the **end** of `app/commands.py`:

```python
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = bytes(await file.download_as_bytearray())

    transactions = parse_image(photo_bytes)

    if not transactions:
        await update.message.reply_text(
            "Couldn't read any transactions from that screenshot. Try a clearer image."
        )
        return

    clarifications = [
        (i, t["clarification_question"])
        for i, t in enumerate(transactions)
        if t.get("needs_clarification") and t.get("clarification_question")
    ]

    context.user_data["image_session"] = {
        "transactions": transactions,
        "clarifications": clarifications,
        "cursor": 0,
        "awaiting_confirmation": len(clarifications) == 0,
    }

    if clarifications:
        _, question = clarifications[0]
        count = len(transactions)
        await update.message.reply_text(
            f"Got {count} transaction{'s' if count != 1 else ''}. A few questions first.\n\n{question}"
        )
    else:
        await _send_confirmation_preview(update, transactions)


async def _send_confirmation_preview(update: Update, transactions: list) -> None:
    lines = [f"Ready to log {len(transactions)} transaction{'s' if len(transactions) != 1 else ''}:\n"]
    for i, t in enumerate(transactions):
        sign = "+" if t["type"] == "Income" else "-"
        lines.append(
            f"{i + 1}. {t['date']}  {t['description']:<22} {sign}€{float(t['amount']):.2f}"
            f"  ({t.get('category', '?')})"
        )
    lines.append("\nReply 'yes' to log all, 'no' to cancel, or tell me which ones to leave out.")
    await update.message.reply_text("\n".join(lines))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_image_commands.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/commands.py tests/test_image_commands.py
git commit -m "feat(image): add handle_photo entry point and confirmation preview"
```

---

## Task 5: `_handle_image_session` in `commands.py`

**Files:**
- Modify: `app/commands.py`
- Test: `tests/test_image_commands.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_image_commands.py`:

```python
def _session_with_one_clarification():
    tx = _clear_transaction({
        "description": "gelredome", "needs_clarification": True,
        "clarification_question": "What was Gelredome?", "category": "Other",
    })
    return {
        "transactions": [tx],
        "clarifications": [(0, "What was Gelredome?")],
        "cursor": 0,
        "awaiting_confirmation": False,
    }


def _session_awaiting_confirmation(n=2):
    txns = [_clear_transaction({"description": f"item{i}", "amount": float(i + 1)}) for i in range(n)]
    return {
        "transactions": txns,
        "clarifications": [],
        "cursor": 0,
        "awaiting_confirmation": True,
    }


async def test_image_session_clarification_updates_transaction_and_shows_preview():
    update = MagicMock()
    update.message.text = "concert with friends"
    update.message.reply_text = AsyncMock()
    context = _make_context({"image_session": _session_with_one_clarification()})

    clarification_result = {"skip": False, "description": "concert", "category": "Social"}

    with patch("app.commands._resolve_clarification", return_value=clarification_result):
        from app.commands import _handle_image_session
        await _handle_image_session(update, context)

    session = context.user_data["image_session"]
    assert session["awaiting_confirmation"] is True
    assert session["transactions"][0]["description"] == "concert"
    reply = update.message.reply_text.call_args[0][0]
    assert "Ready to log" in reply


async def test_image_session_clarification_skip_excludes_from_preview():
    update = MagicMock()
    update.message.text = "skip that"
    update.message.reply_text = AsyncMock()
    context = _make_context({"image_session": _session_with_one_clarification()})

    with patch("app.commands._resolve_clarification", return_value={"skip": True}):
        from app.commands import _handle_image_session
        await _handle_image_session(update, context)

    session = context.user_data["image_session"]
    assert session["transactions"][0].get("_skip") is True
    assert session["awaiting_confirmation"] is True


async def test_image_session_confirmation_log_all_logs_and_clears_session():
    update = MagicMock()
    update.message.text = "yes"
    update.message.reply_text = AsyncMock()
    context = _make_context({"image_session": _session_awaiting_confirmation(2)})

    with patch("app.commands._resolve_confirmation", return_value=("log_all", [])), \
         patch("app.commands.sheets.append_transaction") as mock_append, \
         patch("app.commands.sheets.get_all_transactions", return_value=[]), \
         patch("app.commands.budget_module.calculate_weekly_status",
               return_value={"weekly_spent": 10.0, "weekly_budget": 90.0,
                             "pct_used": 11.0, "remaining": 80.0}):
        from app.commands import _handle_image_session
        await _handle_image_session(update, context)

    assert mock_append.call_count == 2
    assert "image_session" not in context.user_data
    reply = update.message.reply_text.call_args[0][0]
    assert "Logged 2" in reply


async def test_image_session_confirmation_cancel_clears_session():
    update = MagicMock()
    update.message.text = "no"
    update.message.reply_text = AsyncMock()
    context = _make_context({"image_session": _session_awaiting_confirmation(2)})

    with patch("app.commands._resolve_confirmation", return_value=("cancel", [])):
        from app.commands import _handle_image_session
        await _handle_image_session(update, context)

    assert "image_session" not in context.user_data
    reply = update.message.reply_text.call_args[0][0]
    assert "Cancelled" in reply


async def test_image_session_confirmation_skip_some_logs_remaining():
    update = MagicMock()
    update.message.text = "leave out item0"
    update.message.reply_text = AsyncMock()
    context = _make_context({"image_session": _session_awaiting_confirmation(2)})

    with patch("app.commands._resolve_confirmation", return_value=("skip_some", [0])), \
         patch("app.commands.sheets.append_transaction") as mock_append, \
         patch("app.commands.sheets.get_all_transactions", return_value=[]), \
         patch("app.commands.budget_module.calculate_weekly_status",
               return_value={"weekly_spent": 10.0, "weekly_budget": 90.0,
                             "pct_used": 11.0, "remaining": 80.0}):
        from app.commands import _handle_image_session
        await _handle_image_session(update, context)

    assert mock_append.call_count == 1
    reply = update.message.reply_text.call_args[0][0]
    assert "Logged 1" in reply
    assert "Skipped" in reply
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_image_commands.py::test_image_session_clarification_updates_transaction_and_shows_preview tests/test_image_commands.py::test_image_session_confirmation_log_all_logs_and_clears_session -v
```

Expected: fail with `ImportError: cannot import name '_handle_image_session'`

- [ ] **Step 3: Add `_handle_image_session` to `commands.py`**

Append to the end of `app/commands.py`:

```python
async def _handle_image_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = context.user_data["image_session"]
    text = update.message.text.strip()

    if not session["awaiting_confirmation"]:
        cursor = session["cursor"]
        idx, _ = session["clarifications"][cursor]
        tx = session["transactions"][idx]

        result = _resolve_clarification(tx, text)
        if result.get("skip"):
            session["transactions"][idx]["_skip"] = True
        else:
            session["transactions"][idx]["description"] = result["description"]
            session["transactions"][idx]["category"] = result["category"]

        session["cursor"] += 1

        if session["cursor"] < len(session["clarifications"]):
            _, next_question = session["clarifications"][session["cursor"]]
            await update.message.reply_text(next_question)
        else:
            session["awaiting_confirmation"] = True
            active = [t for t in session["transactions"] if not t.get("_skip")]
            await _send_confirmation_preview(update, active)
        return

    # Awaiting confirmation
    active = [t for t in session["transactions"] if not t.get("_skip")]
    action, skip_indices = _resolve_confirmation(active, text)

    if action == "cancel":
        del context.user_data["image_session"]
        await update.message.reply_text("Cancelled.")
        return

    final_skip = set(skip_indices) if action == "skip_some" else set()
    logged = []
    skipped = []

    for i, tx in enumerate(active):
        if i in final_skip:
            skipped.append(tx)
            continue
        category = tx.get("category") or get_category(tx["description"])
        sheets.append_transaction(tx, category)
        logged.append(tx)

    del context.user_data["image_session"]

    all_txns = sheets.get_all_transactions()
    status = budget_module.calculate_weekly_status(all_txns, config.WEEKLY_BUDGET)
    pct_left = 100 - status["pct_used"]

    lines = [f"Logged {len(logged)} transaction{'s' if len(logged) != 1 else ''}."]
    if skipped:
        skipped_str = ", ".join(
            f"{t['description']} (-€{float(t['amount']):.2f})" for t in skipped
        )
        lines.append(f"Skipped: {skipped_str}")
    lines.append(
        f"Weekly: {format_currency(status['weekly_spent'])} / "
        f"{format_currency(status['weekly_budget'])}. {pct_left:.0f}% left."
    )
    await update.message.reply_text("\n".join(lines))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_image_commands.py -v
```

Expected: all 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/commands.py tests/test_image_commands.py
git commit -m "feat(image): add _handle_image_session state machine"
```

---

## Task 6: Priority 0 routing in `handle_message`

**Files:**
- Modify: `app/commands.py`
- Test: `tests/test_image_commands.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_image_commands.py`:

```python
async def test_handle_message_routes_to_image_session_when_active():
    update = MagicMock()
    update.message.text = "yes"
    update.message.reply_text = AsyncMock()
    session = _session_awaiting_confirmation(1)
    context = _make_context({"image_session": session})

    with patch("app.commands._handle_image_session", new_callable=AsyncMock) as mock_sess, \
         patch("app.commands.is_agent_reply", return_value=False):
        from app.commands import handle_message
        await handle_message(update, context)

    mock_sess.assert_called_once_with(update, context, "yes")


async def test_handle_message_no_session_uses_normal_flow():
    update = MagicMock()
    update.message.text = "14 kebab"
    update.message.reply_text = AsyncMock()
    context = _make_context({})  # no image_session

    with patch("app.commands._handle_transaction", new_callable=AsyncMock) as mock_txn, \
         patch("app.commands.is_agent_reply", return_value=False), \
         patch("app.commands.is_net_worth_message", return_value=False), \
         patch("app.commands.is_bulk_message", return_value=False), \
         patch("app.commands.classify_intent", return_value="finance_transaction"):
        from app.commands import handle_message
        await handle_message(update, context)

    mock_txn.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_image_commands.py::test_handle_message_routes_to_image_session_when_active tests/test_image_commands.py::test_handle_message_no_session_uses_normal_flow -v
```

Expected: `test_handle_message_routes_to_image_session_when_active` fails — `_handle_image_session` is NOT called (no Priority 0 check yet)

- [ ] **Step 3: Add Priority 0 check to `handle_message`**

In `app/commands.py`, find `handle_message`. The current first line after the function signature is:
```python
    text = update.message.text.strip()

    # Priority 1: agent-control replies (A/B/C/DONE/yes/no/etc.)
    if is_agent_reply(text):
```

Insert **before** Priority 1:
```python
    text = update.message.text.strip()

    # Priority 0: active image session waiting for clarification or confirmation reply
    if context.user_data.get("image_session"):
        await _handle_image_session(update, context, text)
        return

    # Priority 1: agent-control replies (A/B/C/DONE/yes/no/etc.)
    if is_agent_reply(text):
```

Also update `_handle_image_session` signature to accept `text` as a parameter (it currently reads `update.message.text` internally). Change the signature from:
```python
async def _handle_image_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = context.user_data["image_session"]
    text = update.message.text.strip()
```
to:
```python
async def _handle_image_session(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    session = context.user_data["image_session"]
```

Then update the five Task 5 tests in `tests/test_image_commands.py` to pass `text` explicitly. Replace every call of the form:
```python
await _handle_image_session(update, context)
```
with:
```python
await _handle_image_session(update, context, update.message.text)
```

- [ ] **Step 4: Run all image tests and existing message routing tests**

```bash
pytest tests/test_image_commands.py tests/test_message_routing.py -v
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add app/commands.py tests/test_image_commands.py
git commit -m "feat(image): add Priority 0 routing for active image sessions"
```

---

## Task 7: Register photo handler in `bot.py`

**Files:**
- Modify: `app/bot.py`

No new tests needed — `bot.py` is pure wiring and already tested via integration.

- [ ] **Step 1: Add import and handler to `bot.py`**

In `app/bot.py`, find:
```python
from app.commands import (
    handle_message,
    cmd_start, cmd_help, cmd_today, cmd_week,
    cmd_month, cmd_income, cmd_undo, cmd_summary, cmd_budget,
    cmd_status, cmd_next, cmd_git, cmd_handoff,
    cmd_networth, cmd_networth_history, cmd_goal, cmd_nw,
)
```

Replace with:
```python
from app.commands import (
    handle_message, handle_photo,
    cmd_start, cmd_help, cmd_today, cmd_week,
    cmd_month, cmd_income, cmd_undo, cmd_summary, cmd_budget,
    cmd_status, cmd_next, cmd_git, cmd_handoff,
    cmd_networth, cmd_networth_history, cmd_goal, cmd_nw,
)
```

Then find:
```python
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, owner_only(handle_message))
    )
```

Add after it:
```python
    application.add_handler(
        MessageHandler(filters.PHOTO, owner_only(handle_photo))
    )
```

- [ ] **Step 2: Run the full test suite**

```bash
pytest -v
```

Expected: all 179+ existing tests pass, plus all new image tests pass. Total count increases by the new tests.

- [ ] **Step 3: Commit**

```bash
git add app/bot.py
git commit -m "feat(image): register photo handler in bot"
```

---

## Final Verification

- [ ] **Run full test suite one last time**

```bash
pytest -v --tb=short 2>&1 | tail -20
```

Expected: all tests pass, no regressions.

- [ ] **Manual smoke test checklist** (requires running bot locally)

```bash
LOCAL_POLLING=true python run_polling.py
```

1. Send a Bunq screenshot with mixed clear/unclear transactions → bot asks clarification questions one at a time
2. Answer each question in natural Dutch/English → bot updates the transaction
3. Confirm with "yes but skip the bunq one" → bot logs the rest, shows correct dates and budget line
4. Send "14 kebab" as text → logs immediately as before (no regression)
5. Send a regular coaching question → goes to coach as before (no regression)
6. Send a screenshot with all clear transactions → skips straight to confirmation preview
7. Reply "nee" → session cancelled cleanly
