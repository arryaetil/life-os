# Finance Life OS — Module 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Telegram bot that logs expenses/income to Google Sheets and a FastAPI dashboard that visualises the data, deployed as a single always-on Railway service.

**Architecture:** Single Railway web service — FastAPI serves the dashboard and receives Telegram webhook calls at `/webhook`. On startup, FastAPI registers the Railway HTTPS URL with Telegram. Google Sheets is the only data store (no database). PTB v20 runs inside FastAPI's lifespan context.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, python-telegram-bot v20, gspread, openai/anthropic (optional AI fallback), Jinja2, python-dotenv, pytest, httpx

**Spec:** `docs/superpowers/specs/2026-05-15-finance-lifeos-design.md`

---

## File Map

| File | Responsibility |
|---|---|
| `app/__init__.py` | Makes app a Python package |
| `app/config.py` | Reads env vars, exposes as typed constants |
| `app/utils.py` | Pure helpers: format_currency, get_week_start, get_month |
| `app/parser.py` | Parses raw Telegram message text → structured dict |
| `app/categories.py` | Keyword match + AI fallback → category string |
| `app/budget.py` | Pure math: weekly status, monthly summary from transaction list |
| `app/sheets.py` | All Google Sheets I/O: append row, read all rows, undo |
| `app/commands.py` | All Telegram handlers (commands + expense message handler) |
| `app/bot.py` | create_ptb_app() — builds and wires the PTB Application |
| `app/dashboard.py` | FastAPI app, lifespan, webhook route, 3 dashboard routes |
| `app/templates/base.html` | Shared nav, CSS imports, layout shell |
| `app/templates/dashboard.html` | Home page — KPI cards + recent transactions |
| `app/templates/categories.html` | Category breakdown + progress bars |
| `app/templates/transactions.html` | Full transactions table |
| `app/static/style.css` | Complete liquid glass design system |
| `tests/__init__.py` | Makes tests a package |
| `tests/test_utils.py` | Tests for utils.py |
| `tests/test_parser.py` | Tests for parser.py |
| `tests/test_categories.py` | Tests for categories.py |
| `tests/test_budget.py` | Tests for budget.py |
| `tests/test_sheets.py` | Tests for sheets.py (mocked gspread) |
| `tests/test_dashboard.py` | Tests for FastAPI routes (mocked sheets) |
| `requirements.txt` | All dependencies pinned |
| `.env.example` | Template for env vars |
| `.gitignore` | Excludes .env, __pycache__, etc. |
| `Procfile` | Railway start command |
| `run_polling.py` | Local dev script — runs bot in polling mode |

---

## Task 1: Project Scaffolding

**Files:**
- Create: entire directory structure + git init + requirements.txt + .env.example + .gitignore + Procfile

- [ ] **Step 1: Create the directory structure**

```bash
mkdir -p finance-lifeos/app/templates finance-lifeos/app/static finance-lifeos/tests
cd finance-lifeos
git init
```

- [ ] **Step 2: Create `requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-telegram-bot==20.7
gspread==6.1.2
google-auth==2.29.0
Jinja2==3.1.4
python-dotenv==1.0.1
openai==1.30.1
anthropic==0.26.1
httpx==0.27.0
pytest==8.2.1
pytest-asyncio==0.23.6
```

- [ ] **Step 3: Create `.env.example`**

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=change-me-to-a-random-string
GOOGLE_SHEET_ID=
GOOGLE_SERVICE_ACCOUNT_JSON=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
WEEKLY_BUDGET=90
WEBHOOK_BASE_URL=https://your-app.railway.app
LOCAL_POLLING=false
```

- [ ] **Step 4: Create `.gitignore`**

```
.env
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.venv/
venv/
*.egg-info/
dist/
build/
.DS_Store
```

- [ ] **Step 5: Create `Procfile`**

```
web: uvicorn app.dashboard:app --host 0.0.0.0 --port $PORT
```

- [ ] **Step 6: Create empty `__init__.py` files**

```bash
touch app/__init__.py tests/__init__.py
```

- [ ] **Step 7: Install dependencies**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 8: Copy `.env.example` to `.env` and fill in values**

```bash
cp .env.example .env
# Edit .env with your actual values — see setup guide below
```

- [ ] **Step 9: Initial commit**

```bash
git add .
git commit -m "feat: project scaffolding and dependencies"
```

---

## Task 2: config.py

**Files:**
- Create: `app/config.py`

- [ ] **Step 1: Create `app/config.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_WEBHOOK_SECRET: str = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
GOOGLE_SHEET_ID: str = os.environ["GOOGLE_SHEET_ID"]
GOOGLE_SERVICE_ACCOUNT_JSON: str = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
WEEKLY_BUDGET: float = float(os.environ.get("WEEKLY_BUDGET", "90"))
WEBHOOK_BASE_URL: str = os.environ.get("WEBHOOK_BASE_URL", "")
LOCAL_POLLING: bool = os.environ.get("LOCAL_POLLING", "false").lower() == "true"
```

- [ ] **Step 2: Verify it imports without error**

```bash
python -c "from app import config; print('WEEKLY_BUDGET:', config.WEEKLY_BUDGET)"
```

Expected output: `WEEKLY_BUDGET: 90.0`

- [ ] **Step 3: Commit**

```bash
git add app/config.py
git commit -m "feat: config module — reads env vars"
```

---

## Task 3: utils.py + tests

**Files:**
- Create: `app/utils.py`
- Create: `tests/test_utils.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_utils.py
from datetime import date
from app.utils import format_currency, get_week_start, get_month, budget_color

def test_format_currency_whole():
    assert format_currency(14.0) == "€14.00"

def test_format_currency_decimal():
    assert format_currency(8.5) == "€8.50"

def test_format_currency_zero():
    assert format_currency(0) == "€0.00"

def test_get_week_start_on_monday():
    monday = date(2026, 5, 11)
    assert get_week_start(monday) == monday

def test_get_week_start_on_friday():
    friday = date(2026, 5, 15)
    assert get_week_start(friday) == date(2026, 5, 11)

def test_get_week_start_on_sunday():
    sunday = date(2026, 5, 17)
    assert get_week_start(sunday) == date(2026, 5, 11)

def test_get_month():
    assert get_month(date(2026, 5, 15)) == "2026-05"

def test_budget_color_low():
    assert budget_color(30, 90) == "accent"

def test_budget_color_warning():
    assert budget_color(70, 90) == "warning"

def test_budget_color_danger():
    assert budget_color(85, 90) == "danger"
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_utils.py -v
```

Expected: multiple ImportError or AttributeError failures.

- [ ] **Step 3: Create `app/utils.py`**

```python
from datetime import date, timedelta

def format_currency(amount: float) -> str:
    return f"€{amount:.2f}"

def get_week_start(d: date = None) -> date:
    if d is None:
        d = date.today()
    return d - timedelta(days=d.weekday())

def get_month(d: date = None) -> str:
    if d is None:
        d = date.today()
    return d.strftime("%Y-%m")

def budget_color(spent: float, budget: float) -> str:
    if budget == 0:
        return "danger"
    pct = spent / budget * 100
    if pct >= 90:
        return "danger"
    if pct >= 75:
        return "warning"
    return "accent"
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_utils.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add app/utils.py tests/test_utils.py
git commit -m "feat: utils module — currency formatting, week/month helpers"
```

---

## Task 4: parser.py + tests

**Files:**
- Create: `app/parser.py`
- Create: `tests/test_parser.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_parser.py
import pytest
from app.parser import parse_message

def test_basic_expense():
    result = parse_message("14 kebab")
    assert result["type"] == "Expense"
    assert result["amount"] == 14.0
    assert result["description"] == "kebab"

def test_minus_prefix_is_expense():
    result = parse_message("-50 dinner")
    assert result["type"] == "Expense"
    assert result["amount"] == 50.0

def test_plus_prefix_is_income():
    result = parse_message("+314 DUO income")
    assert result["type"] == "Income"
    assert result["amount"] == 314.0
    assert result["description"] == "duo income"

def test_decimal_dot():
    result = parse_message("8.50 coffee")
    assert result["amount"] == 8.50

def test_decimal_comma():
    result = parse_message("8,50 coffee")
    assert result["amount"] == 8.50

def test_investment_keyword_overrides_type():
    result = parse_message("100 degiro etf")
    assert result["type"] == "Investment"

def test_transfer_keyword_overrides_type():
    result = parse_message("200 savings")
    assert result["type"] == "Transfer"

def test_income_prefix_not_overridden_by_keyword():
    result = parse_message("+200 savings refund")
    assert result["type"] == "Income"

def test_is_impulse_true():
    result = parse_message("25 impulse buy")
    assert result["is_impulse"] is True

def test_is_impulse_false():
    result = parse_message("14 kebab")
    assert result["is_impulse"] is False

def test_invalid_message_raises():
    with pytest.raises(ValueError):
        parse_message("no amount here")

def test_week_start_is_monday():
    result = parse_message("5 coffee")
    from datetime import datetime, date
    from app.utils import get_week_start
    week_start = get_week_start(date.today()).strftime("%Y-%m-%d")
    assert result["week_start"] == week_start
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_parser.py -v
```

Expected: ImportError or multiple failures.

- [ ] **Step 3: Create `app/parser.py`**

```python
import re
from datetime import datetime, date
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
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_parser.py -v
```

Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add app/parser.py tests/test_parser.py
git commit -m "feat: parser module — Telegram message → structured dict"
```

---

## Task 5: categories.py + tests

**Files:**
- Create: `app/categories.py`
- Create: `tests/test_categories.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_categories.py
from unittest.mock import patch, MagicMock
from app.categories import get_category, _keyword_match

def test_food_kebab():
    assert get_category("kebab") == "Food"

def test_food_coffee():
    assert get_category("coffee with a friend") == "Food"

def test_food_grocery():
    assert get_category("lidl groceries") == "Food"

def test_social_date():
    assert get_category("date at cinema") == "Social"

def test_transport_uber():
    assert get_category("uber home") == "Transport"

def test_transport_ns():
    assert get_category("ns train ticket") == "Transport"

def test_project_api():
    assert get_category("api credits openai") == "Project"

def test_health_gym():
    assert get_category("gym monthly") == "Health"

def test_income_duo():
    assert get_category("duo payment") == "Income"

def test_investment_degiro():
    assert get_category("degiro etf") == "Investment"

def test_keyword_match_returns_none_for_unknown():
    assert _keyword_match("xyz123 unknownterm") is None

def test_ai_fallback_openai(monkeypatch):
    monkeypatch.setattr("app.categories.config.OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr("app.categories.config.ANTHROPIC_API_KEY", "")

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Food"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("app.categories.OpenAI", return_value=mock_client):
        result = get_category("donor wrap")

    assert result == "Food"

def test_ai_fallback_anthropic(monkeypatch):
    monkeypatch.setattr("app.categories.config.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.categories.config.ANTHROPIC_API_KEY", "ant-test")

    mock_response = MagicMock()
    mock_response.content[0].text = "Food"
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("app.categories.Anthropic", return_value=mock_client):
        result = get_category("donor wrap")

    assert result == "Food"

def test_no_key_returns_other(monkeypatch):
    monkeypatch.setattr("app.categories.config.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.categories.config.ANTHROPIC_API_KEY", "")
    assert get_category("xyzunknown123") == "Other"
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_categories.py -v
```

Expected: ImportError or multiple failures.

- [ ] **Step 3: Create `app/categories.py`**

```python
from app import config

# Imported at module level so tests can patch them cleanly.
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None  # type: ignore

KEYWORDS: dict[str, list[str]] = {
    "Food": [
        "lunch", "dinner", "coffee", "kebab", "snack", "groceries", "pizza",
        "burger", "sushi", "sandwich", "supermarket", "takeaway", "bread",
        "ah", "lidl", "albert", "aldi", "jumbo", "restaurant", "eten", "brood",
    ],
    "Social": [
        "date", "drinks", "party", "cinema", "friends", "bar", "club",
        "concert", "festival", "tickets", "borrel",
    ],
    "Transport": [
        "fuel", "train", "bus", "uber", "parking", "taxi", "metro",
        "tram", "ns", "ov", "benzine", "trein",
    ],
    "Project": [
        "api", "domain", "hosting", "software", "tool", "credits",
        "subscription", "server", "claude", "openai", "railway",
    ],
    "Health": [
        "gym", "supplement", "doctor", "medicine", "pharmacy", "dentist",
        "sport", "fitness", "apotheek",
    ],
    "Clothing": [
        "clothes", "shoes", "jacket", "shirt", "pants", "zara",
        "h&m", "nike", "adidas", "kleding",
    ],
    "Education": [
        "book", "course", "udemy", "school", "university", "coursera",
        "boek", "cursus",
    ],
    "Impulse": ["impulse", "random", "unnecessary"],
    "Income": [
        "salary", "duo", "uncle", "refund", "gift", "freelance",
        "loon", "salaris", "oom",
    ],
    "Investment": ["etf", "stock", "crypto", "degiro", "investing"],
    "Transfer": ["savings", "portfolio", "transfer", "spaarrekening"],
}

_AI_PROMPT = (
    "You are a personal finance categorizer. Given this expense description, "
    "return exactly one category from this list:\n"
    "Food, Social, Transport, Project, Health, Clothing, Education, Impulse, "
    "Income, Investment, Transfer, Other\n\n"
    'Description: "{description}"\n'
    "Reply with the category name only. No explanation."
)

def _keyword_match(description: str) -> str | None:
    desc_lower = description.lower()
    for category, keywords in KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return None

def _ai_categorize(description: str) -> str:
    prompt = _AI_PROMPT.format(description=description)

    if config.OPENAI_API_KEY and OpenAI is not None:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
        )
        return response.choices[0].message.content.strip()

    if config.ANTHROPIC_API_KEY and Anthropic is not None:
        client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()

    return "Other"

def get_category(description: str) -> str:
    matched = _keyword_match(description)
    if matched:
        return matched
    try:
        return _ai_categorize(description)
    except Exception:
        return "Other"
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_categories.py -v
```

Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add app/categories.py tests/test_categories.py
git commit -m "feat: categories module — keyword match + AI fallback"
```

---

## Task 6: budget.py + tests

**Files:**
- Create: `app/budget.py`
- Create: `tests/test_budget.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_budget.py
from datetime import date
from app.budget import calculate_weekly_status, calculate_monthly_summary

TRANSACTIONS = [
    {
        "week_start": "2026-05-11", "month": "2026-05",
        "type": "Expense", "amount": 14.0, "category": "Food",
        "is_impulse": False, "notes": "",
    },
    {
        "week_start": "2026-05-11", "month": "2026-05",
        "type": "Expense", "amount": 20.5, "category": "Social",
        "is_impulse": False, "notes": "",
    },
    {
        "week_start": "2026-05-11", "month": "2026-05",
        "type": "Income", "amount": 314.0, "category": "Income",
        "is_impulse": False, "notes": "",
    },
    {
        "week_start": "2026-05-11", "month": "2026-05",
        "type": "Expense", "amount": 99.0, "category": "Other",
        "is_impulse": False, "notes": "[UNDONE]",
    },
]

REF = date(2026, 5, 15)

def test_weekly_spent_excludes_income_and_undone():
    result = calculate_weekly_status(TRANSACTIONS, 90.0, REF)
    assert result["weekly_spent"] == 34.5

def test_weekly_remaining():
    result = calculate_weekly_status(TRANSACTIONS, 90.0, REF)
    assert result["remaining"] == 55.5

def test_pct_used():
    result = calculate_weekly_status(TRANSACTIONS, 90.0, REF)
    assert round(result["pct_used"], 1) == 38.3

def test_remaining_never_negative():
    result = calculate_weekly_status(TRANSACTIONS, 10.0, REF)
    assert result["remaining"] == 0.0

def test_monthly_spent():
    result = calculate_monthly_summary(TRANSACTIONS, REF)
    assert result["monthly_spent"] == 34.5

def test_monthly_income():
    result = calculate_monthly_summary(TRANSACTIONS, REF)
    assert result["monthly_income"] == 314.0

def test_net_cashflow():
    result = calculate_monthly_summary(TRANSACTIONS, REF)
    assert result["net_cashflow"] == 279.5

def test_by_category_sorted_descending():
    result = calculate_monthly_summary(TRANSACTIONS, REF)
    amounts = list(result["by_category"].values())
    assert amounts == sorted(amounts, reverse=True)

def test_impulse_total():
    txns = TRANSACTIONS + [{
        "week_start": "2026-05-11", "month": "2026-05",
        "type": "Expense", "amount": 30.0, "category": "Impulse",
        "is_impulse": True, "notes": "",
    }]
    result = calculate_monthly_summary(txns, REF)
    assert result["impulse_total"] == 30.0
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_budget.py -v
```

Expected: ImportError or multiple failures.

- [ ] **Step 3: Create `app/budget.py`**

```python
from datetime import date
from app.utils import get_week_start, get_month

def calculate_weekly_status(
    transactions: list[dict],
    budget: float,
    reference_date: date = None,
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
    reference_date: date = None,
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
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_budget.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add app/budget.py tests/test_budget.py
git commit -m "feat: budget module — weekly status and monthly summary"
```

---

## Task 7: sheets.py + tests

**Files:**
- Create: `app/sheets.py`
- Create: `tests/test_sheets.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_sheets.py
from unittest.mock import patch, MagicMock, call
from app.sheets import append_transaction, get_all_transactions, undo_last_transaction

PARSED = {
    "amount": 14.0,
    "description": "kebab",
    "type": "Expense",
    "is_impulse": False,
    "timestamp": "2026-05-15 12:00:00",
    "date": "2026-05-15",
    "week_start": "2026-05-11",
    "month": "2026-05",
}

def _mock_sheet(records=None, num_rows=1):
    sheet = MagicMock()
    sheet.get_all_records.return_value = records or []
    return sheet

def _patch_sheet(sheet):
    return patch("app.sheets._get_sheet", return_value=sheet)

def test_append_transaction_appends_correct_row():
    sheet = _mock_sheet(records=[{"ID": 1}])
    with _patch_sheet(sheet):
        row_id = append_transaction(PARSED, "Food")

    assert row_id == 2
    appended = sheet.append_row.call_args[0][0]
    assert appended[0] == 2          # ID
    assert appended[5] == "Expense"  # Type
    assert appended[6] == 14.0       # Amount
    assert appended[7] == "kebab"    # Description
    assert appended[8] == "Food"     # Category
    assert appended[11] == "FALSE"   # Is_Impulse

def test_get_all_transactions_normalizes_fields():
    raw = [{
        "ID": 1, "Timestamp": "2026-05-15 12:00:00", "Date": "2026-05-15",
        "Week_Start": "2026-05-11", "Month": "2026-05", "Type": "Expense",
        "Amount": 14.0, "Description": "kebab", "Category": "Food",
        "Tag": "", "Payment_Type": "", "Is_Impulse": "FALSE",
        "Is_Necessary": "", "Notes": "",
    }]
    sheet = _mock_sheet(records=raw)
    with _patch_sheet(sheet):
        result = get_all_transactions()

    assert len(result) == 1
    t = result[0]
    assert t["amount"] == 14.0
    assert t["is_impulse"] is False
    assert t["category"] == "Food"

def test_undo_last_transaction_writes_undone_note():
    raw = [
        {"ID": 1, "Amount": 14.0, "Description": "kebab"},
        {"ID": 2, "Amount": 8.5, "Description": "coffee"},
    ]
    sheet = _mock_sheet(records=raw)
    with _patch_sheet(sheet):
        result = undo_last_transaction()

    assert result["Description"] == "coffee"
    sheet.update_cell.assert_called_once_with(3, 14, "[UNDONE]")

def test_undo_on_empty_sheet_returns_none():
    sheet = _mock_sheet(records=[])
    with _patch_sheet(sheet):
        result = undo_last_transaction()
    assert result is None
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_sheets.py -v
```

Expected: ImportError or multiple failures.

- [ ] **Step 3: Create `app/sheets.py`**

```python
import json
import gspread
from google.oauth2.service_account import Credentials
from app import config

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_SHEET_NAME = "Transactions"
_HEADERS = [
    "ID", "Timestamp", "Date", "Week_Start", "Month",
    "Type", "Amount", "Description", "Category", "Tag",
    "Payment_Type", "Is_Impulse", "Is_Necessary", "Notes",
]

def _get_sheet() -> gspread.Worksheet:
    creds_dict = json.loads(config.GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=_SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    try:
        return spreadsheet.worksheet(_SHEET_NAME)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(_SHEET_NAME, rows=1000, cols=len(_HEADERS))
        sheet.append_row(_HEADERS)
        return sheet

def append_transaction(parsed: dict, category: str) -> int:
    sheet = _get_sheet()
    existing = sheet.get_all_records()
    new_id = len(existing) + 1

    row = [
        new_id,
        parsed["timestamp"],
        parsed["date"],
        parsed["week_start"],
        parsed["month"],
        parsed["type"],
        parsed["amount"],
        parsed["description"],
        category,
        "",   # Tag
        "",   # Payment_Type
        "TRUE" if parsed["is_impulse"] else "FALSE",
        "",   # Is_Necessary
        "",   # Notes
    ]
    sheet.append_row(row)
    return new_id

def get_all_transactions() -> list[dict]:
    sheet = _get_sheet()
    records = sheet.get_all_records()
    return [
        {
            "id": r.get("ID"),
            "timestamp": r.get("Timestamp"),
            "date": r.get("Date"),
            "week_start": r.get("Week_Start"),
            "month": r.get("Month"),
            "type": r.get("Type"),
            "amount": float(r.get("Amount") or 0),
            "description": r.get("Description", ""),
            "category": r.get("Category", "Other"),
            "tag": r.get("Tag", ""),
            "payment_type": r.get("Payment_Type", ""),
            "is_impulse": r.get("Is_Impulse") in ("TRUE", True),
            "is_necessary": r.get("Is_Necessary", ""),
            "notes": r.get("Notes", ""),
        }
        for r in records
    ]

def undo_last_transaction() -> dict | None:
    sheet = _get_sheet()
    records = sheet.get_all_records()
    if not records:
        return None
    last_row_index = len(records) + 1  # +1 for header
    notes_col = _HEADERS.index("Notes") + 1   # 1-indexed
    sheet.update_cell(last_row_index, notes_col, "[UNDONE]")
    return records[-1]
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_sheets.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/sheets.py tests/test_sheets.py
git commit -m "feat: sheets module — Google Sheets read/write/undo"
```

---

## Task 8: commands.py

**Files:**
- Create: `app/commands.py`

- [ ] **Step 1: Create `app/commands.py`**

```python
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes
from app import sheets, budget as budget_module, config
from app.parser import parse_message
from app.categories import get_category
from app.utils import format_currency

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    try:
        parsed = parse_message(text)
    except ValueError:
        await update.message.reply_text(
            "Couldn't parse that. Try: '14 kebab' or '+314 DUO income'."
        )
        return

    category = get_category(parsed["description"])
    sheets.append_transaction(parsed, category)

    transactions = sheets.get_all_transactions()
    status = budget_module.calculate_weekly_status(transactions, config.WEEKLY_BUDGET)

    reply = (
        f"Logged: {format_currency(parsed['amount'])} — "
        f"{parsed['description']} — {category}.\n"
        f"Weekly spent: {format_currency(status['weekly_spent'])} / "
        f"{format_currency(status['weekly_budget'])}.\n"
        f"Remaining: {format_currency(status['remaining'])} "
        f"({100 - status['pct_used']:.0f}% left)."
    )
    await update.message.reply_text(reply)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Finance Logger ready.\n\n"
        "Log a transaction:\n"
        "  14 kebab\n"
        "  8.50 coffee\n"
        "  -50 dinner\n"
        "  +314 DUO\n"
        "  200 savings\n\n"
        "Commands: /help /today /week /month /income /undo /summary /budget"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Examples:\n"
        "  14 kebab          → expense, Food\n"
        "  8.50 coffee       → expense, Food\n"
        "  +314 DUO income   → income\n"
        "  200 savings       → transfer\n"
        "  100 degiro etf    → investment\n"
        "  25 impulse buy    → marked as impulse\n\n"
        "Prefix + for income. No prefix or - for expense.\n"
        "Transfer/investment detected from description."
    )


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    transactions = sheets.get_all_transactions()
    today_str = date.today().strftime("%Y-%m-%d")
    today_txns = [
        t for t in transactions
        if t["date"] == today_str
        and "[UNDONE]" not in (t["notes"] or "")
    ]

    if not today_txns:
        await update.message.reply_text("No transactions today.")
        return

    lines = [f"Today ({today_str}):"]
    total = 0.0
    for t in today_txns:
        lines.append(f"  {format_currency(t['amount'])} — {t['description']} — {t['category']}")
        if t["type"] == "Expense":
            total += t["amount"]
    lines.append(f"\nTotal spent: {format_currency(total)}")
    await update.message.reply_text("\n".join(lines))


async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    transactions = sheets.get_all_transactions()
    status = budget_module.calculate_weekly_status(transactions, config.WEEKLY_BUDGET)
    await update.message.reply_text(
        f"Week from {status['week_start']}:\n"
        f"Spent: {format_currency(status['weekly_spent'])} / {format_currency(status['weekly_budget'])}\n"
        f"Remaining: {format_currency(status['remaining'])} ({100 - status['pct_used']:.0f}% left)"
    )


async def cmd_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    transactions = sheets.get_all_transactions()
    summary = budget_module.calculate_monthly_summary(transactions)

    lines = [f"Month {summary['month']} — by category:"]
    for cat, amount in summary["by_category"].items():
        lines.append(f"  {cat}: {format_currency(amount)}")
    lines.append(f"\nTotal: {format_currency(summary['monthly_spent'])}")
    lines.append(f"Impulse: {format_currency(summary['impulse_total'])}")
    await update.message.reply_text("\n".join(lines))


async def cmd_income(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    transactions = sheets.get_all_transactions()
    summary = budget_module.calculate_monthly_summary(transactions)
    month = summary["month"]

    income_txns = [
        t for t in transactions
        if t["month"] == month
        and t["type"] == "Income"
        and "[UNDONE]" not in (t["notes"] or "")
    ]

    lines = [f"Income {month}:"]
    for t in income_txns:
        lines.append(f"  +{format_currency(t['amount'])} — {t['description']}")
    lines.append(f"\nTotal: {format_currency(summary['monthly_income'])}")
    await update.message.reply_text("\n".join(lines))


async def cmd_undo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    undone = sheets.undo_last_transaction()
    if not undone:
        await update.message.reply_text("No transactions to undo.")
        return
    amount = float(undone.get("Amount", 0))
    desc = undone.get("Description", "")
    await update.message.reply_text(f"Undone: {format_currency(amount)} — {desc}")


async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    transactions = sheets.get_all_transactions()
    weekly = budget_module.calculate_weekly_status(transactions, config.WEEKLY_BUDGET)
    monthly = budget_module.calculate_monthly_summary(transactions)
    top_cat = (
        max(monthly["by_category"], key=monthly["by_category"].get)
        if monthly["by_category"] else "—"
    )

    await update.message.reply_text(
        f"Summary:\n"
        f"Week: {format_currency(weekly['weekly_spent'])} / "
        f"{format_currency(weekly['weekly_budget'])} ({weekly['pct_used']:.0f}% used)\n"
        f"Month spent: {format_currency(monthly['monthly_spent'])}\n"
        f"Month income: {format_currency(monthly['monthly_income'])}\n"
        f"Net: {format_currency(monthly['net_cashflow'])}\n"
        f"Top: {top_cat}"
    )


async def cmd_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    transactions = sheets.get_all_transactions()
    status = budget_module.calculate_weekly_status(transactions, config.WEEKLY_BUDGET)
    pct = status["pct_used"]
    bar_filled = min(10, int(pct / 10))
    bar = "█" * bar_filled + "░" * (10 - bar_filled)

    await update.message.reply_text(
        f"Weekly budget:\n"
        f"[{bar}] {pct:.0f}%\n"
        f"{format_currency(status['weekly_spent'])} / {format_currency(status['weekly_budget'])}\n"
        f"Remaining: {format_currency(status['remaining'])}"
    )
```

- [ ] **Step 2: Verify it imports without error**

```bash
python -c "from app.commands import handle_message, cmd_start; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/commands.py
git commit -m "feat: commands module — all Telegram handlers"
```

---

## Task 9: bot.py

**Files:**
- Create: `app/bot.py`

- [ ] **Step 1: Create `app/bot.py`**

```python
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from app import config
from app.commands import (
    handle_message,
    cmd_start, cmd_help, cmd_today, cmd_week,
    cmd_month, cmd_income, cmd_undo, cmd_summary, cmd_budget,
)

def create_ptb_app() -> Application:
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("today", cmd_today))
    application.add_handler(CommandHandler("week", cmd_week))
    application.add_handler(CommandHandler("month", cmd_month))
    application.add_handler(CommandHandler("income", cmd_income))
    application.add_handler(CommandHandler("undo", cmd_undo))
    application.add_handler(CommandHandler("summary", cmd_summary))
    application.add_handler(CommandHandler("budget", cmd_budget))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    return application
```

- [ ] **Step 2: Create `run_polling.py`** (local dev only)

```python
#!/usr/bin/env python3
"""Local development only. Runs the bot in polling mode (no webhook needed)."""
import asyncio
from app.bot import create_ptb_app

async def main() -> None:
    ptb_app = create_ptb_app()
    await ptb_app.initialize()
    await ptb_app.start()
    await ptb_app.updater.start_polling()
    print("Bot running in polling mode. Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        await ptb_app.updater.stop()
        await ptb_app.stop()
        await ptb_app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Commit**

```bash
git add app/bot.py run_polling.py
git commit -m "feat: bot module — PTB Application factory + polling script"
```

---

## Task 10: dashboard.py

**Files:**
- Create: `app/dashboard.py`
- Create: `tests/test_dashboard.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_dashboard.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

MOCK_TRANSACTIONS = [
    {
        "id": 1, "date": "2026-05-15", "week_start": "2026-05-11",
        "month": "2026-05", "type": "Expense", "amount": 14.0,
        "description": "kebab", "category": "Food", "is_impulse": False,
        "notes": "", "tag": "", "payment_type": "", "is_necessary": "",
        "timestamp": "2026-05-15 12:00:00",
    },
]

@pytest.fixture
def client():
    """TestClient with PTB lifespan mocked out and LOCAL_POLLING=True
    so no webhook registration is attempted."""
    from app.dashboard import app
    with patch("app.dashboard.create_ptb_app") as mock_factory, \
         patch("app.dashboard.config.LOCAL_POLLING", True):
        mock_ptb = AsyncMock()
        mock_factory.return_value = mock_ptb
        with TestClient(app) as c:
            yield c

def test_home_returns_200(client):
    with patch("app.dashboard.sheets.get_all_transactions", return_value=MOCK_TRANSACTIONS):
        response = client.get("/")
    assert response.status_code == 200

def test_home_contains_transaction_data(client):
    with patch("app.dashboard.sheets.get_all_transactions", return_value=MOCK_TRANSACTIONS):
        response = client.get("/")
    assert "kebab" in response.text

def test_categories_returns_200(client):
    with patch("app.dashboard.sheets.get_all_transactions", return_value=MOCK_TRANSACTIONS):
        response = client.get("/categories")
    assert response.status_code == 200

def test_transactions_returns_200(client):
    with patch("app.dashboard.sheets.get_all_transactions", return_value=MOCK_TRANSACTIONS):
        response = client.get("/transactions")
    assert response.status_code == 200

def test_webhook_rejects_bad_secret():
    from app.dashboard import app
    with patch("app.dashboard.create_ptb_app") as mock_factory, \
         patch("app.dashboard.config.LOCAL_POLLING", True), \
         patch("app.dashboard.config.TELEGRAM_WEBHOOK_SECRET", "correct-secret"):
        mock_ptb = AsyncMock()
        mock_factory.return_value = mock_ptb
        with TestClient(app) as client:
            response = client.post(
                "/webhook",
                json={"update_id": 1},
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
            )
    assert response.status_code == 403
```

- [ ] **Step 2: Create `app/dashboard.py`**

```python
from contextlib import asynccontextmanager
from telegram import Update
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app import config, sheets
from app import budget as budget_module
from app.bot import create_ptb_app
from app.utils import format_currency, budget_color

_ptb_app = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ptb_app
    _ptb_app = create_ptb_app()
    await _ptb_app.initialize()
    await _ptb_app.start()

    if not config.LOCAL_POLLING and config.WEBHOOK_BASE_URL:
        await _ptb_app.bot.set_webhook(
            url=f"{config.WEBHOOK_BASE_URL}/webhook",
            secret_token=config.TELEGRAM_WEBHOOK_SECRET,
        )

    yield

    await _ptb_app.stop()
    await _ptb_app.shutdown()

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["format_currency"] = format_currency
templates.env.filters["budget_color"] = budget_color

@app.post("/webhook")
async def webhook(request: Request) -> Response:
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if config.TELEGRAM_WEBHOOK_SECRET and secret != config.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")
    data = await request.json()
    update = Update.de_json(data, _ptb_app.bot)
    await _ptb_app.process_update(update)
    return Response(status_code=200)

@app.get("/")
async def home(request: Request):
    transactions = sheets.get_all_transactions()
    weekly = budget_module.calculate_weekly_status(transactions, config.WEEKLY_BUDGET)
    monthly = budget_module.calculate_monthly_summary(transactions)
    recent = list(reversed(transactions))[:10]
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active_page": "home",
        "weekly": weekly,
        "monthly": monthly,
        "recent_transactions": recent,
    })

@app.get("/categories")
async def categories_page(request: Request):
    transactions = sheets.get_all_transactions()
    monthly = budget_module.calculate_monthly_summary(transactions)
    top_category = (
        max(monthly["by_category"], key=monthly["by_category"].get)
        if monthly["by_category"] else None
    )
    max_amount = max(monthly["by_category"].values()) if monthly["by_category"] else 1.0
    return templates.TemplateResponse("categories.html", {
        "request": request,
        "active_page": "categories",
        "monthly": monthly,
        "top_category": top_category,
        "max_amount": max_amount,
    })

@app.get("/transactions")
async def transactions_page(request: Request):
    transactions = sheets.get_all_transactions()
    return templates.TemplateResponse("transactions.html", {
        "request": request,
        "active_page": "transactions",
        "transactions": list(reversed(transactions)),
    })
```

- [ ] **Step 3: Run tests — confirm they pass**

```bash
pytest tests/test_dashboard.py -v
```

Expected: 5 passed.

- [ ] **Step 4: Commit**

```bash
git add app/dashboard.py tests/test_dashboard.py
git commit -m "feat: dashboard module — FastAPI routes, webhook, lifespan"
```

---

## Task 11: style.css (Liquid Glass Design System)

**Files:**
- Create: `app/static/style.css`

- [ ] **Step 1: Create `app/static/style.css`**

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Design tokens ── */
:root {
  --bg:               #080c14;
  --brand-blue:       #3F5AF5;
  --brand-blue-hover: #5B76F7;
  --glass-bg:         rgba(255, 255, 255, 0.05);
  --glass-tint:       rgba(63, 90, 245, 0.06);
  --glass-border:     rgba(255, 255, 255, 0.10);
  --glass-border-top: rgba(255, 255, 255, 0.22);
  --glass-blur:       blur(40px) saturate(180%);
  --glass-shadow:     0 8px 32px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.12);
  --radius-card:      20px;
  --radius-pill:      100px;
  --text-primary:     #ffffff;
  --text-secondary:   rgba(255, 255, 255, 0.50);
  --success:          #10B981;
  --warning:          #F59E0B;
  --danger:           #EF4444;
}

/* ── Reset ── */
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

/* ── Base ── */
body {
  background-color: var(--bg);
  background-image: radial-gradient(ellipse at 50% -10%, rgba(63,90,245,0.15) 0%, transparent 65%);
  min-height: 100vh;
  font-family: 'Inter', sans-serif;
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
}

/* ── Glass card ── */
.glass-card {
  background: var(--glass-tint);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-border);
  border-top-color: var(--glass-border-top);
  box-shadow: var(--glass-shadow);
  border-radius: var(--radius-card);
  padding: 24px;
}

/* ── Nav ── */
nav {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 32px;
  background: rgba(8, 12, 20, 0.72);
  backdrop-filter: blur(60px) saturate(200%);
  -webkit-backdrop-filter: blur(60px) saturate(200%);
  border-bottom: 1px solid var(--glass-border);
}

.nav-logo {
  font-size: 16px;
  font-weight: 700;
  background: linear-gradient(135deg, #3F5AF5, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-right: 16px;
}

nav a {
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  padding: 6px 16px;
  border-radius: var(--radius-pill);
  transition: background 0.18s, color 0.18s;
}

nav a:hover { color: var(--text-primary); background: rgba(255,255,255,0.06); }
nav a.active { color: var(--text-primary); background: rgba(63,90,245,0.18); }

/* ── Layout ── */
.container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 36px 24px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 28px;
}

/* ── KPI grid ── */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 28px;
}

.kpi-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.kpi-value {
  font-size: 26px;
  font-weight: 700;
  line-height: 1;
}

.kpi-value.accent  { color: var(--brand-blue); }
.kpi-value.positive { color: var(--success); }
.kpi-value.warning  { color: var(--warning); }
.kpi-value.danger   { color: var(--danger); }

.kpi-sub {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

/* ── Progress bar ── */
.progress-track {
  height: 4px;
  background: rgba(255,255,255,0.08);
  border-radius: var(--radius-pill);
  overflow: hidden;
  margin-top: 10px;
}

.progress-fill {
  height: 100%;
  border-radius: var(--radius-pill);
  background: var(--brand-blue);
  transition: width 0.4s ease;
}

.progress-fill.warning { background: var(--warning); }
.progress-fill.danger  { background: var(--danger); }

/* ── Section header ── */
.section-header {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--text-secondary);
  margin-bottom: 18px;
}

/* ── Table ── */
.glass-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.glass-table th {
  text-align: left;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--text-secondary);
  padding: 10px 16px;
  border-bottom: 1px solid var(--glass-border);
}

.glass-table td {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}

.glass-table tr:last-child td { border-bottom: none; }

.glass-table tr.undone td {
  opacity: 0.3;
  text-decoration: line-through;
}

/* ── Pills ── */
.pill {
  display: inline-block;
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 500;
  background: rgba(63,90,245,0.14);
  color: var(--brand-blue);
  border: 1px solid rgba(63,90,245,0.22);
}

.pill.income     { background: rgba(16,185,129,0.12); color: var(--success); border-color: rgba(16,185,129,0.22); }
.pill.transfer   { background: rgba(245,158,11,0.12);  color: var(--warning); border-color: rgba(245,158,11,0.22); }
.pill.investment { background: rgba(167,139,250,0.12); color: #a78bfa;        border-color: rgba(167,139,250,0.22); }
.pill.impulse    { background: rgba(239,68,68,0.12);   color: var(--danger);  border-color: rgba(239,68,68,0.22); }

/* ── Category bar ── */
.cat-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}

.cat-row:last-child { border-bottom: none; }

.cat-name  { width: 120px; font-size: 14px; flex-shrink: 0; }
.cat-track { flex: 1; height: 5px; background: rgba(255,255,255,0.07); border-radius: var(--radius-pill); overflow: hidden; }
.cat-fill  { height: 100%; border-radius: var(--radius-pill); background: var(--brand-blue); }
.cat-fill.top { background: linear-gradient(90deg, #3F5AF5, #a78bfa); }
.cat-amount { width: 80px; text-align: right; font-size: 14px; font-weight: 600; }

/* ── Responsive ── */
@media (max-width: 640px) {
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .container { padding: 20px 16px; }
  nav { padding: 12px 16px; }
  .kpi-value { font-size: 20px; }
  .glass-card { padding: 16px; }
  .glass-table th, .glass-table td { padding: 10px 10px; font-size: 13px; }
}
```

- [ ] **Step 2: Commit**

```bash
git add app/static/style.css
git commit -m "feat: liquid glass design system — CSS tokens and components"
```

---

## Task 12: HTML Templates

**Files:**
- Create: `app/templates/base.html`
- Create: `app/templates/dashboard.html`
- Create: `app/templates/categories.html`
- Create: `app/templates/transactions.html`

- [ ] **Step 1: Create `app/templates/base.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Life OS — Finance</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <nav>
    <span class="nav-logo">Life OS</span>
    <a href="/" class="{{ 'active' if active_page == 'home' else '' }}">Dashboard</a>
    <a href="/categories" class="{{ 'active' if active_page == 'categories' else '' }}">Categories</a>
    <a href="/transactions" class="{{ 'active' if active_page == 'transactions' else '' }}">Transactions</a>
  </nav>
  <div class="container">
    {% block content %}{% endblock %}
  </div>
</body>
</html>
```

- [ ] **Step 2: Create `app/templates/dashboard.html`**

```html
{% extends "base.html" %}
{% block content %}

<div class="kpi-grid">

  <div class="glass-card">
    <div class="kpi-label">Weekly Spent</div>
    <div class="kpi-value {{ weekly.pct_used | budget_color(weekly.weekly_budget) }}">
      {{ weekly.weekly_spent | format_currency }}
    </div>
    <div class="progress-track">
      <div class="progress-fill {{ weekly.pct_used | budget_color(weekly.weekly_budget) }}"
           style="width: {{ [weekly.pct_used, 100] | min }}%"></div>
    </div>
    <div class="kpi-sub">of {{ weekly.weekly_budget | format_currency }} budget</div>
  </div>

  <div class="glass-card">
    <div class="kpi-label">Weekly Remaining</div>
    <div class="kpi-value {% if weekly.remaining == 0 %}danger{% else %}accent{% endif %}">
      {{ weekly.remaining | format_currency }}
    </div>
    <div class="kpi-sub">{{ (100 - weekly.pct_used) | round(0) | int }}% remaining</div>
  </div>

  <div class="glass-card">
    <div class="kpi-label">Monthly Spent</div>
    <div class="kpi-value">{{ monthly.monthly_spent | format_currency }}</div>
    <div class="kpi-sub">{{ monthly.month }}</div>
  </div>

  <div class="glass-card">
    <div class="kpi-label">Monthly Income</div>
    <div class="kpi-value positive">{{ monthly.monthly_income | format_currency }}</div>
    <div class="kpi-sub">this month</div>
  </div>

  <div class="glass-card">
    <div class="kpi-label">Net Cash Flow</div>
    <div class="kpi-value {% if monthly.net_cashflow >= 0 %}positive{% else %}danger{% endif %}">
      {{ monthly.net_cashflow | format_currency }}
    </div>
    <div class="kpi-sub">income − expenses</div>
  </div>

</div>

<div class="glass-card">
  <div class="section-header">Recent Transactions</div>
  {% if recent_transactions %}
  <table class="glass-table">
    <thead>
      <tr>
        <th>Date</th>
        <th>Description</th>
        <th>Category</th>
        <th>Amount</th>
        <th>Type</th>
      </tr>
    </thead>
    <tbody>
      {% for t in recent_transactions %}
      <tr class="{{ 'undone' if '[UNDONE]' in (t.notes or '') else '' }}">
        <td>{{ t.date }}</td>
        <td>{{ t.description }}</td>
        <td><span class="pill">{{ t.category }}</span></td>
        <td>{{ t.amount | format_currency }}</td>
        <td>
          <span class="pill {{ t.type | lower }}">{{ t.type }}</span>
          {% if t.is_impulse %}<span class="pill impulse" style="margin-left:4px">impulse</span>{% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <p style="color: var(--text-secondary); font-size: 14px;">No transactions yet. Send a message to your bot to get started.</p>
  {% endif %}
</div>

{% endblock %}
```

- [ ] **Step 3: Create `app/templates/categories.html`**

```html
{% extends "base.html" %}
{% block content %}

<div class="kpi-grid" style="margin-bottom: 28px;">
  <div class="glass-card">
    <div class="kpi-label">Total Spent</div>
    <div class="kpi-value">{{ monthly.monthly_spent | format_currency }}</div>
    <div class="kpi-sub">{{ monthly.month }}</div>
  </div>
  <div class="glass-card">
    <div class="kpi-label">Impulse Spending</div>
    <div class="kpi-value {% if monthly.impulse_total > 0 %}danger{% else %}positive{% endif %}">
      {{ monthly.impulse_total | format_currency }}
    </div>
    <div class="kpi-sub">marked as impulse</div>
  </div>
  {% if top_category %}
  <div class="glass-card">
    <div class="kpi-label">Biggest Category</div>
    <div class="kpi-value" style="font-size: 20px;">{{ top_category }}</div>
    <div class="kpi-sub">{{ monthly.by_category[top_category] | format_currency }}</div>
  </div>
  {% endif %}
</div>

<div class="glass-card">
  <div class="section-header">Spending by Category — {{ monthly.month }}</div>
  {% if monthly.by_category %}
    {% for cat, amount in monthly.by_category.items() %}
    <div class="cat-row">
      <div class="cat-name">{{ cat }}</div>
      <div class="cat-track">
        <div class="cat-fill {{ 'top' if cat == top_category else '' }}"
             style="width: {{ (amount / max_amount * 100) | round(1) }}%"></div>
      </div>
      <div class="cat-amount">{{ amount | format_currency }}</div>
    </div>
    {% endfor %}
  {% else %}
    <p style="color: var(--text-secondary); font-size: 14px;">No expenses this month yet.</p>
  {% endif %}
</div>

{% endblock %}
```

- [ ] **Step 4: Create `app/templates/transactions.html`**

```html
{% extends "base.html" %}
{% block content %}

<div class="glass-card">
  <div class="section-header">All Transactions — newest first</div>

  <!-- AUTH TODO: Add authentication before making this dashboard public.
       Recommended: FastAPI HTTP Basic Auth dependency on all routes.
       Without auth, anyone with the Railway URL can see your finances. -->

  {% if transactions %}
  <table class="glass-table">
    <thead>
      <tr>
        <th>Date</th>
        <th>Type</th>
        <th>Amount</th>
        <th>Description</th>
        <th>Category</th>
        <th>Impulse</th>
      </tr>
    </thead>
    <tbody>
      {% for t in transactions %}
      <tr class="{{ 'undone' if '[UNDONE]' in (t.notes or '') else '' }}">
        <td>{{ t.date }}</td>
        <td><span class="pill {{ t.type | lower }}">{{ t.type }}</span></td>
        <td>{{ t.amount | format_currency }}</td>
        <td>{{ t.description }}</td>
        <td><span class="pill">{{ t.category }}</span></td>
        <td>
          {% if t.is_impulse %}
            <span class="pill impulse">yes</span>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
    <p style="color: var(--text-secondary); font-size: 14px;">No transactions yet.</p>
  {% endif %}
</div>

{% endblock %}
```

- [ ] **Step 5: Commit**

```bash
git add app/templates/
git commit -m "feat: Jinja2 templates — dashboard, categories, transactions"
```

---

## Task 13: Full Test Suite + Deployment Files

**Files:**
- Verify: `requirements.txt`
- Create: final README section (in-repo, not a separate file)

- [ ] **Step 1: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass. Fix any failures before continuing.

- [ ] **Step 2: Verify the dashboard starts locally**

```bash
uvicorn app.dashboard:app --reload --port 8000
```

Expected: server starts, no import errors. Visit `http://localhost:8000` — should render the dashboard (will show "No transactions" since Sheet is empty or credentials not set).

- [ ] **Step 3: Run the bot locally in polling mode to test Telegram**

```bash
python run_polling.py
```

Then send `14 kebab` to your bot in Telegram. Expected: bot replies with confirmation and budget status.

- [ ] **Step 4: Commit everything**

```bash
git add .
git commit -m "feat: complete Finance Life OS Module 1"
```

---

## Setup Guide (run once before testing)

### Create a Telegram Bot

1. Open Telegram, search `@BotFather`
2. Send `/newbot`, follow prompts, get your token
3. Set `TELEGRAM_BOT_TOKEN=<token>` in `.env`

### Create Google Sheets + Service Account

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project
3. Enable **Google Sheets API**
4. Go to **IAM & Admin → Service Accounts** → Create service account
5. Create a JSON key → download the file
6. Copy the JSON file's entire contents as a single line: `cat key.json | tr -d '\n'`
7. Set `GOOGLE_SERVICE_ACCOUNT_JSON=<that string>` in `.env`
8. Create a Google Sheet, copy the ID from the URL (`/d/<SHEET_ID>/edit`)
9. Set `GOOGLE_SHEET_ID=<id>` in `.env`
10. Share the sheet with the service account email (found in the JSON as `client_email`)

### Deploy to Railway

1. Push repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add all env vars from `.env.example` in Railway's environment settings
4. Set `WEBHOOK_BASE_URL=https://<your-app>.railway.app`
5. Deploy — Railway auto-detects the Procfile
6. After first successful deploy, the webhook is registered automatically on startup

---

## Self-Review Checklist

### Spec Coverage

| Spec section | Task |
|---|---|
| Parsing rules (+/-/no prefix, amount, description) | Task 4 |
| Transfer/Investment keyword override | Task 4 |
| Is_Impulse detection | Task 4 |
| Keyword categorisation | Task 5 |
| AI fallback (OpenAI + Anthropic) | Task 5 |
| Google Sheets 14-column schema | Task 7 |
| append_transaction, get_all_transactions, undo | Task 7 |
| /undo marks [UNDONE], doesn't delete | Task 7 |
| Weekly budget calculation | Task 6 |
| Monthly summary + by_category | Task 6 |
| All 9 Telegram commands | Task 8 |
| handle_message + budget reply | Task 8 |
| PTB Application factory | Task 9 |
| Local polling script | Task 9 |
| FastAPI webhook endpoint + secret verification | Task 10 |
| /  /categories  /transactions routes | Task 10 |
| Liquid glass design tokens | Task 11 |
| KPI cards + progress bars + pills + tables | Task 11–12 |
| Budget bar colour thresholds | Task 11–12 |
| [UNDONE] rows dimmed in tables | Task 12 |
| AUTH TODO comment in transactions.html | Task 12 |
| Procfile + .env.example + .gitignore | Task 1 |
| Railway deployment steps | Setup Guide |
