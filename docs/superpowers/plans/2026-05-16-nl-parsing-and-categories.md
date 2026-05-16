# Natural Language Parsing + Category Normalization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support Dutch + English natural language expense/income logging, add confidence-based clarification handling, and normalize dynamic AI-suggested categories to prevent duplicates.

**Architecture:** Three targeted changes — (1) `categories.py` gains `normalize_category()` with a synonym map; (2) `parser.py` gets an improved AI prompt (Dutch, confidence, clarification) and a Dutch-aware regex fallback; (3) `commands.py` checks `needs_clarification` before logging. No new files or DB tables.

**Tech Stack:** Python 3.13, OpenAI GPT-4o-mini, pytest 8.2.1, regex

**Baseline:** 230 tests passing. Never reduce this count.

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `app/categories.py` | Modify | Add `_CATEGORY_SYNONYMS` dict + `normalize_category()` function; normalize return of `get_category()` |
| `app/parser.py` | Modify | Improved AI prompt (Dutch, confidence, clarification); Dutch-aware `_regex_parse`; `parse_message` returns `needs_clarification` signal; calls `normalize_category` on AI category |
| `app/commands.py` | Modify | Check `parsed.get("needs_clarification")` before logging |
| `tests/test_categories.py` | Modify | Add tests for `normalize_category` |
| `tests/test_parser.py` | Modify | Add Dutch regex tests + AI-mocked Dutch + clarification tests |
| `tests/test_message_routing.py` | Modify | Add test for clarification reply in handle_message |

---

## Task 1: Update `app/categories.py` — `normalize_category()` + tests

**Files:**
- Modify: `app/categories.py`
- Modify: `tests/test_categories.py`

- [ ] **Step 1: Write failing tests**

Read `tests/test_categories.py` first, then append:

```python
from app.categories import normalize_category, KNOWN_CATEGORIES


def test_normalize_known_category_passthrough():
    assert normalize_category("Food") == "Food"
    assert normalize_category("Transport") == "Transport"
    assert normalize_category("Health") == "Health"


def test_normalize_synonym_maps_to_canonical():
    assert normalize_category("Eating") == "Food"
    assert normalize_category("Meals") == "Food"
    assert normalize_category("Fitness") == "Health"
    assert normalize_category("Sports") == "Health"
    assert normalize_category("Gas") == "Transport"
    assert normalize_category("Fuel") == "Transport"
    assert normalize_category("Shopping") == "Clothing"


def test_normalize_title_cases_dynamic_category():
    # New categories not in synonym map pass through title-cased
    assert normalize_category("sports gear") == "Sports Gear"
    assert normalize_category("BOXING") == "Boxing"


def test_normalize_empty_returns_other():
    assert normalize_category("") == "Other"
    assert normalize_category("   ") == "Other"


def test_normalize_case_insensitive_synonym():
    assert normalize_category("eating") == "Food"
    assert normalize_category("MEALS") == "Food"
```

- [ ] **Step 2: Run to verify FAIL**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_categories.py -v -k "normalize" 2>&1 | tail -8
```

Expected: `ImportError: cannot import name 'normalize_category'`

- [ ] **Step 3: Update `app/categories.py`**

Read the file first, then add after the `KEYWORDS` dict and before `_AI_PROMPT`:

```python
KNOWN_CATEGORIES = frozenset({
    "Food", "Transport", "Social", "Health", "Education",
    "Project", "Clothing", "Income", "Investment", "Transfer",
    "Impulse", "Other",
})

_CATEGORY_SYNONYMS: dict[str, str] = {
    "Eating": "Food", "Meals": "Food", "Restaurant": "Food",
    "Groceries": "Food", "Grocery": "Food", "Dining": "Food",
    "Car": "Transport", "Gas": "Transport", "Fuel": "Transport",
    "Travel": "Transport", "Petrol": "Transport",
    "Entertainment": "Social", "Nightlife": "Social",
    "Fitness": "Health", "Medical": "Health", "Sports": "Health",
    "Sport": "Health", "Training": "Health", "Boxing": "Health",
    "Books": "Education", "Learning": "Education", "Course": "Education",
    "Shopping": "Clothing", "Fashion": "Clothing",
    "Tech": "Project", "Software": "Project", "Tools": "Project",
    "Technology": "Project",
}


def normalize_category(category: str) -> str:
    """Normalize an AI-suggested category. Maps synonyms to canonical names.

    Unknown categories pass through title-cased (dynamic category creation).
    """
    if not category or not category.strip():
        return "Other"
    cat = category.strip().title()
    return _CATEGORY_SYNONYMS.get(cat, cat)
```

Also update `get_category` to normalize the AI result:

Find:
```python
def get_category(description: str) -> str:
    matched = _keyword_match(description)
    if matched:
        return matched
    try:
        return _ai_categorize(description)
    except Exception as exc:
        _log.warning("AI categorization failed for %r: %s", description, exc)
        return "Other"
```

Replace with:
```python
def get_category(description: str) -> str:
    matched = _keyword_match(description)
    if matched:
        return matched
    try:
        raw = _ai_categorize(description)
        return normalize_category(raw)
    except Exception as exc:
        _log.warning("AI categorization failed for %r: %s", description, exc)
        return "Other"
```

- [ ] **Step 4: Run tests to verify PASS**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_categories.py -v 2>&1 | tail -15
```

Expected: All tests PASS (existing + 5 new).

- [ ] **Step 5: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -3
```

Expected: 235 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add app/categories.py tests/test_categories.py && git commit -m "feat(parser): add normalize_category — synonym map prevents category duplication"
```

---

## Task 2: Update `app/parser.py` — Dutch AI prompt + Dutch regex + clarification

**Files:**
- Modify: `app/parser.py`
- Modify: `tests/test_parser.py`

- [ ] **Step 1: Write failing tests**

Read `tests/test_parser.py` first, then append:

```python
# --- Dutch regex fallback ---

def test_dutch_expense_with_euro_word():
    result = _regex_parse("ik heb 14 euro uitgegeven aan kebab")
    assert result["amount"] == pytest.approx(14.0)
    assert result["type"] == "Expense"
    assert "kebab" in result["description"]


def test_dutch_income_binnengekregen():
    result = _regex_parse("314 DUO binnengekregen")
    assert result["amount"] == pytest.approx(314.0)
    assert result["type"] == "Income"


def test_dutch_income_gekregen():
    result = _regex_parse("150 gekregen van mijn oom")
    assert result["amount"] == pytest.approx(150.0)
    assert result["type"] == "Income"


def test_dutch_fuel_getankt():
    result = _regex_parse("net 65 getankt")
    assert result["amount"] == pytest.approx(65.0)
    assert result["type"] == "Expense"


def test_dutch_comma_decimal():
    result = _regex_parse("vandaag 8,50 koffie gehaald")
    assert result["amount"] == pytest.approx(8.50)
    assert result["type"] == "Expense"


def test_english_natural():
    result = _regex_parse("spent 8.50 on coffee")
    assert result["amount"] == pytest.approx(8.50)
    assert result["type"] == "Expense"


# --- AI-mocked parse_message ---

def test_parse_message_dutch_ai_response():
    ai = {
        "amount": 14.0, "type": "Expense", "description": "kebab",
        "category": "Food", "is_impulse": False,
        "confidence": 0.95, "needs_clarification": False, "clarification_question": "",
    }
    with patch("app.parser._ai_parse", return_value=ai):
        result = parse_message("ik heb 14 euro uitgegeven aan kebab")
    assert result["amount"] == pytest.approx(14.0)
    assert result["type"] == "Expense"
    assert result["category"] == "Food"
    assert result.get("needs_clarification") is not True


def test_parse_message_income_duo():
    ai = {
        "amount": 314.0, "type": "Income", "description": "DUO",
        "category": "Income", "is_impulse": False,
        "confidence": 1.0, "needs_clarification": False, "clarification_question": "",
    }
    with patch("app.parser._ai_parse", return_value=ai):
        result = parse_message("314 DUO binnengekregen")
    assert result["amount"] == pytest.approx(314.0)
    assert result["type"] == "Income"


def test_parse_message_needs_clarification():
    ai = {
        "amount": None, "type": "Expense", "description": "",
        "category": "Other", "is_impulse": False,
        "confidence": 0.2, "needs_clarification": True,
        "clarification_question": "How much did you spend?",
    }
    with patch("app.parser._ai_parse", return_value=ai):
        result = parse_message("iets iets")
    assert result.get("needs_clarification") is True
    assert "How much" in result.get("clarification_question", "")


def test_parse_message_dynamic_category_normalized():
    ai = {
        "amount": 40.0, "type": "Expense", "description": "boxing gloves",
        "category": "Sports", "is_impulse": False,
        "confidence": 0.9, "needs_clarification": False, "clarification_question": "",
    }
    with patch("app.parser._ai_parse", return_value=ai):
        result = parse_message("40 boxing gloves")
    # "Sports" is a synonym for "Health"
    assert result["category"] == "Health"


def test_parse_message_synonym_category_normalized():
    ai = {
        "amount": 15.0, "type": "Expense", "description": "restaurant",
        "category": "Dining", "is_impulse": False,
        "confidence": 0.9, "needs_clarification": False, "clarification_question": "",
    }
    with patch("app.parser._ai_parse", return_value=ai):
        result = parse_message("15 dinner")
    assert result["category"] == "Food"
```

- [ ] **Step 2: Run to verify FAIL**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_parser.py -v -k "dutch or needs_clarification or dynamic or synonym" 2>&1 | tail -15
```

Expected: Multiple FAIL — Dutch regex can't handle sentences yet, `needs_clarification` not returned.

- [ ] **Step 3: Update `app/parser.py`**

**Read the file first**, then make these changes:

**Replace `_AI_PROMPT`:**

```python
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
```

**Replace `TRANSFER_KEYWORDS` and `INVESTMENT_KEYWORDS` lines, then add Dutch income keywords:**

Keep existing:
```python
TRANSFER_KEYWORDS = {"savings", "portfolio", "transfer", "spaarrekening"}
INVESTMENT_KEYWORDS = {"degiro", "etf", "stock", "crypto", "invest", "investing"}
```

Add after them:
```python
_DUTCH_INCOME_KW = frozenset({
    "gekregen", "ontvangen", "binnengekregen", "teruggekregen",
    "salary", "salaris", "loon", "inkomen", "refund",
})
```

**Replace `_regex_parse` entirely:**

```python
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
        r"teruggekregen|van mijn|mijn|voor|aan)\b",
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
```

**Replace `parse_message` to handle clarification + normalize category:**

```python
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
        }
    else:
        parsed = _regex_parse(text)

    parsed.update(time_fields)
    return parsed
```

- [ ] **Step 4: Run parser tests to verify PASS**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_parser.py -v 2>&1 | tail -25
```

Expected: All tests PASS (existing + ~11 new). If any existing test breaks, check that `_regex_parse` behavior is unchanged for simple `"14 kebab"` format.

- [ ] **Step 5: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -3
```

Expected: ~246 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add app/parser.py tests/test_parser.py && git commit -m "feat(parser): Dutch+English AI prompt, confidence/clarification support, Dutch regex fallback"
```

---

## Task 3: Update `app/commands.py` — clarification check + test

**Files:**
- Modify: `app/commands.py`
- Modify: `tests/test_message_routing.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_message_routing.py`:

```python
async def test_ambiguous_message_sends_clarification_question():
    from app.commands import handle_message
    update = _make_update("iets vaags")
    clarification_result = {
        "needs_clarification": True,
        "clarification_question": "How much did you spend?",
        "timestamp": "2026-05-16 14:00:00",
        "date": "2026-05-16",
        "week_start": "2026-05-13",
        "month": "2026-05",
    }
    with patch("app.parser.parse_message", return_value=clarification_result), \
         patch("app.intent_classifier.classify_intent", return_value="finance_transaction"):
        await handle_message(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "How much" in reply
    # Must NOT have tried to log a transaction
```

- [ ] **Step 2: Run to verify FAIL**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_message_routing.py::test_ambiguous_message_sends_clarification_question -v 2>&1 | tail -8
```

Expected: FAIL — no clarification check in handle_message yet.

- [ ] **Step 3: Update `app/commands.py`**

**Read the file first**, then find this block (after the `try: parsed = parse_message(text)` block):

```python
    category = parsed.get("category") or get_category(parsed["description"])
    sheets.append_transaction(parsed, category)
```

Insert a check BEFORE those two lines:

```python
    # AI requested clarification (low confidence or missing amount)
    if parsed.get("needs_clarification"):
        await update.message.reply_text(
            parsed.get("clarification_question") or "Could you be more specific?\n\n"
            "• Log an expense: `14 kebab` or `8,50 koffie`\n"
            "• Income: `+314 DUO` or `150 gekregen van oom`"
        )
        return

    category = parsed.get("category") or get_category(parsed["description"])
    sheets.append_transaction(parsed, category)
```

- [ ] **Step 4: Run all routing tests**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_message_routing.py -v 2>&1 | tail -15
```

Expected: All 11 tests PASS (10 existing + 1 new).

- [ ] **Step 5: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -3
```

Expected: ~247 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add app/commands.py tests/test_message_routing.py && git commit -m "feat(parser): ask clarification when AI signals low confidence instead of logging"
```

---

## Task 4: Final verification + Telegram completion + push

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -5
```

Expected: 245+ passed, 0 failed.

- [ ] **Step 2: Quick smoke test of Dutch parsing chain**

```bash
python -c "
from unittest.mock import patch
ai = {'amount': 14.0, 'type': 'Expense', 'description': 'kebab', 'category': 'Food',
      'is_impulse': False, 'confidence': 0.95, 'needs_clarification': False, 'clarification_question': ''}
with patch('app.parser._ai_parse', return_value=ai):
    from app.parser import parse_message
    r = parse_message('ik heb 14 euro uitgegeven aan kebab')
    print(f'amount={r[\"amount\"]} type={r[\"type\"]} category={r[\"category\"]}')
    assert r['amount'] == 14.0 and r['type'] == 'Expense' and r['category'] == 'Food'
    print('✅ Dutch parsing smoke test PASS')
"
```

Expected: `amount=14.0 type=Expense category=Food` + PASS.

- [ ] **Step 3: Send Telegram completion notification**

```bash
cd /Users/arryawillems/finance-lifeos && python scripts/notify_me.py complete "Dutch+English parsing live. AI prompt updated for Dutch, regex handles NL sentences, clarification when ambiguous, category normalization prevents duplicates. All tests passing."
```

- [ ] **Step 4: Update handoff silently + push**

```bash
cd /Users/arryawillems/finance-lifeos && python scripts/create_handoff.py --silent && git add handoff/ && git diff --cached --quiet || git commit -m "docs: handoff after NL parsing improvements" && git push origin master
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task |
|---|---|
| Dutch: "ik heb 14 euro uitgegeven aan kebab" | Task 2 (AI prompt + regex) |
| Dutch: "vandaag 8,50 koffie gehaald" | Task 2 (regex comma decimal) |
| Dutch: "net 65 getankt" → Transport Expense | Task 2 (regex) |
| Dutch: "314 DUO binnengekregen" → Income | Task 2 (regex income detection) |
| Dutch: "150 gekregen van mijn oom" → Income | Task 2 (regex) |
| English: "spent 8.50 on coffee" | Task 2 (existing regex, still works) |
| AI categorization with type/amount/description | Task 2 (improved prompt) |
| Category list (Food/Transport/Social/etc.) | Task 1 + Task 2 prompt |
| AI fallback if no key → regex | Existing, unchanged |
| Clarification if ambiguous | Task 2 (needs_clarification return) + Task 3 (check) |
| Net worth coupling | Already working (previous fix) |
| Tests Dutch + English | Task 2 |
| Dynamic category creation | Task 1 (normalize_category allows new names) |
| Prefer existing categories | Task 1 (synonym map normalizes "Sports" → "Health") |
| Only new category when clearly useful | Task 2 (AI prompt instruction) |
| Normalize consistently | Task 1 (normalize_category) |
| No duplicates (Food/Eating/Meals) | Task 1 (synonym map) |
| Low confidence → clarification | Task 2 + Task 3 |
| Full tests, preserve existing | Every task runs full suite |

**Placeholder scan:** None. All code complete.

**Type consistency:**
- `normalize_category(category: str) -> str` — defined Task 1, called in `parser.py` Task 2, called in `get_category` Task 1 ✓
- `parse_message` return: either full transaction dict OR `{"needs_clarification": True, "clarification_question": str, ...time_fields}` — Task 2 defines both cases, Task 3 checks `parsed.get("needs_clarification")` ✓
- `_regex_parse` signature unchanged — existing tests continue to work ✓
