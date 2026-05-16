# Module 1.1 — Net Worth Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add manual net worth tracking with historical snapshots, Telegram commands, and a premium dashboard page to LifeOS.

**Architecture:** New `net_worth_snapshots` DB table owned by this module. Logic lives in `app/networth.py`. Parsing in `app/networth_parser.py`. Commands added to existing `app/commands.py`; routing in `handle_message` detects net worth messages before the finance parser runs. Dashboard at `/networth` extends the existing Jinja2 + glass-card design; Chart.js loaded only on that page.

**Tech Stack:** SQLAlchemy 2.0 Core (same as existing), GPT-4o-mini AI parse + regex fallback, Chart.js 4.4 CDN, python-telegram-bot 20.7

---

## File Map

| Action | File | What changes |
|--------|------|-------------|
| Modify | `app/database.py` | Add `net_worth_snapshots` table + 3 CRUD functions |
| Create | `app/networth_parser.py` | `is_net_worth_message()`, `parse_net_worth_message()` |
| Create | `app/networth.py` | `calculate_net_worth()`, `calculate_goal_progress()`, `calculate_change()`, `ascii_progress_bar()` |
| Modify | `app/commands.py` | Add `_handle_net_worth_message()`, `cmd_networth`, `cmd_networth_history`, `cmd_goal`; route in `handle_message` |
| Modify | `app/bot.py` | Register 3 new commands wrapped with `owner_only` |
| Modify | `app/dashboard.py` | Add `/networth` GET route |
| Modify | `app/templates/base.html` | Add "Net Worth" nav link |
| Create | `app/templates/networth.html` | Full net worth dashboard page |
| Modify | `app/static/style.css` | Add `.progress-fill.positive`, `.cat-fill.danger-fill`, `.danger` |
| Create | `tests/test_networth_db.py` | DB insert/retrieval/calculation tests |
| Create | `tests/test_networth_parser.py` | Parser trigger detection + field extraction tests |
| Create | `tests/test_networth_logic.py` | Logic/goal calculation tests |
| Create | `tests/test_networth_commands.py` | Telegram command handler tests |
| Modify | `docs/current-status.md` | Mark 1.1 in progress → done |
| Modify | `docs/architecture.md` | Add 1.1 data model + routes |
| Modify | `docs/roadmap.md` | Mark 1.1 done |

---

## Task 1: Database Layer

**Files:**
- Modify: `app/database.py`
- Create: `tests/test_networth_db.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_networth_db.py`:

```python
import pytest
from sqlalchemy import create_engine
from app import database as db

@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(db, "_engine", engine)
    db.init_db()
    yield engine

def test_create_snapshot_returns_id():
    row_id = db.create_net_worth_snapshot({"cash": 1000.0})
    assert row_id == 1

def test_create_snapshot_calculates_total_net_worth():
    db.create_net_worth_snapshot({
        "cash": 1000.0,
        "investments": 5000.0,
        "crypto": 500.0,
        "savings": 2000.0,
        "other_assets": 0.0,
        "liabilities": 1000.0,
    })
    snap = db.get_latest_net_worth_snapshot()
    assert snap["total_net_worth"] == pytest.approx(7500.0)

def test_create_snapshot_liabilities_subtracted():
    db.create_net_worth_snapshot({"cash": 5000.0, "liabilities": 2000.0})
    snap = db.get_latest_net_worth_snapshot()
    assert snap["total_net_worth"] == pytest.approx(3000.0)

def test_get_latest_returns_none_when_empty():
    assert db.get_latest_net_worth_snapshot() is None

def test_get_latest_returns_most_recent():
    db.create_net_worth_snapshot({"cash": 1000.0})
    db.create_net_worth_snapshot({"cash": 2000.0})
    snap = db.get_latest_net_worth_snapshot()
    assert snap["cash"] == pytest.approx(2000.0)

def test_get_history_empty():
    assert db.get_net_worth_history() == []

def test_get_history_returns_oldest_first():
    db.create_net_worth_snapshot({"cash": 1000.0, "notes": "first"})
    db.create_net_worth_snapshot({"cash": 2000.0, "notes": "second"})
    history = db.get_net_worth_history()
    assert len(history) == 2
    assert history[0]["notes"] == "first"
    assert history[1]["notes"] == "second"

def test_get_history_respects_limit():
    for i in range(10):
        db.create_net_worth_snapshot({"cash": float(i * 100)})
    history = db.get_net_worth_history(limit=5)
    assert len(history) == 5

def test_snapshot_defaults_missing_fields_to_zero():
    db.create_net_worth_snapshot({"investments": 8000.0})
    snap = db.get_latest_net_worth_snapshot()
    assert snap["cash"] == pytest.approx(0.0)
    assert snap["liabilities"] == pytest.approx(0.0)
    assert snap["total_net_worth"] == pytest.approx(8000.0)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_networth_db.py -v
```

Expected: `ImportError` or `AttributeError` — `create_net_worth_snapshot` does not exist.

- [ ] **Step 3: Add table + CRUD functions to `app/database.py`**

Add the table definition after the `agent_state` table (around line 50), before `init_db()`:

```python
net_worth_snapshots = Table(
    "net_worth_snapshots",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", String),
    Column("cash", Float, default=0.0),
    Column("investments", Float, default=0.0),
    Column("crypto", Float, default=0.0),
    Column("savings", Float, default=0.0),
    Column("other_assets", Float, default=0.0),
    Column("liabilities", Float, default=0.0),
    Column("total_net_worth", Float),
    Column("notes", String, default=""),
)
```

Add CRUD functions at the end of `app/database.py`:

```python
def create_net_worth_snapshot(fields: dict) -> int:
    total = (
        fields.get("cash", 0.0)
        + fields.get("investments", 0.0)
        + fields.get("crypto", 0.0)
        + fields.get("savings", 0.0)
        + fields.get("other_assets", 0.0)
        - fields.get("liabilities", 0.0)
    )
    now = datetime.now(timezone.utc).isoformat()
    with _engine.connect() as conn:
        result = conn.execute(
            insert(net_worth_snapshots).values(
                timestamp=fields.get("timestamp", now),
                cash=fields.get("cash", 0.0),
                investments=fields.get("investments", 0.0),
                crypto=fields.get("crypto", 0.0),
                savings=fields.get("savings", 0.0),
                other_assets=fields.get("other_assets", 0.0),
                liabilities=fields.get("liabilities", 0.0),
                total_net_worth=total,
                notes=fields.get("notes", ""),
            )
        )
        conn.commit()
        return result.inserted_primary_key[0]


def get_latest_net_worth_snapshot() -> dict | None:
    with _engine.connect() as conn:
        result = conn.execute(
            select(net_worth_snapshots)
            .order_by(desc(net_worth_snapshots.c.id))
            .limit(1)
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None


def get_net_worth_history(limit: int = 30) -> list[dict]:
    with _engine.connect() as conn:
        result = conn.execute(
            select(net_worth_snapshots)
            .order_by(desc(net_worth_snapshots.c.id))
            .limit(limit)
        )
        rows = [dict(row._mapping) for row in result]
        return list(reversed(rows))
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_networth_db.py -v
```

Expected: 9 PASSED.

- [ ] **Step 5: Confirm full suite still passes**

```bash
python -m pytest -v
```

Expected: all previous tests still pass + 9 new.

- [ ] **Step 6: Commit**

```bash
git add app/database.py tests/test_networth_db.py
git commit -m "feat(1.1): add net_worth_snapshots table and CRUD functions"
```

---

## Task 2: Net Worth Parser

**Files:**
- Create: `app/networth_parser.py`
- Create: `tests/test_networth_parser.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_networth_parser.py`:

```python
from app.networth_parser import is_net_worth_message, parse_net_worth_message
import pytest


# --- is_net_worth_message ---

def test_detects_net_worth_prefix():
    assert is_net_worth_message("net worth cash 3000 investments 9000") is True

def test_detects_update_net_worth():
    assert is_net_worth_message("update net worth cash 2500 savings 4000") is True

def test_detects_networth_no_space():
    assert is_net_worth_message("networth cash 2k") is True

def test_detects_nw_abbreviation():
    assert is_net_worth_message("nw cash 2k savings 5k") is True

def test_detects_two_nw_keywords():
    assert is_net_worth_message("investments 12k crypto 3k liabilities 1k") is True

def test_detects_three_nw_keywords():
    assert is_net_worth_message("cash 2k savings 5k investments 10k") is True

def test_rejects_regular_transaction():
    assert is_net_worth_message("14 kebab food") is False

def test_rejects_single_nw_keyword_no_trigger():
    # "savings" alone without "net worth" prefix and only 1 NW keyword
    assert is_net_worth_message("50 savings account transfer") is False


# --- parse_net_worth_message (regex path, no AI key) ---

def test_parses_full_message():
    result = parse_net_worth_message("net worth cash 3000 investments 9000 crypto 2000")
    assert result["cash"] == pytest.approx(3000.0)
    assert result["investments"] == pytest.approx(9000.0)
    assert result["crypto"] == pytest.approx(2000.0)

def test_parses_k_suffix():
    result = parse_net_worth_message("net worth cash 2k savings 5k investments 10k")
    assert result["cash"] == pytest.approx(2000.0)
    assert result["savings"] == pytest.approx(5000.0)
    assert result["investments"] == pytest.approx(10000.0)

def test_parses_liabilities():
    result = parse_net_worth_message("net worth investments 12k liabilities 2k")
    assert result["liabilities"] == pytest.approx(2000.0)

def test_parses_debt_as_liabilities():
    result = parse_net_worth_message("net worth savings 3000 debt 500")
    assert result["liabilities"] == pytest.approx(500.0)

def test_parses_total_only():
    result = parse_net_worth_message("net worth 15k total")
    # Total stored in other_assets when no categories found
    total = (
        result["cash"] + result["investments"] + result["crypto"]
        + result["savings"] + result["other_assets"] - result["liabilities"]
    )
    assert total == pytest.approx(15000.0)

def test_missing_fields_default_to_zero():
    result = parse_net_worth_message("net worth cash 3000")
    assert result["investments"] == pytest.approx(0.0)
    assert result["liabilities"] == pytest.approx(0.0)

def test_returns_all_expected_keys():
    result = parse_net_worth_message("net worth cash 1000")
    assert set(result.keys()) == {"cash", "investments", "crypto", "savings", "other_assets", "liabilities"}
```

- [ ] **Step 2: Run to confirm they fail**

```bash
python -m pytest tests/test_networth_parser.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.networth_parser'`

- [ ] **Step 3: Create `app/networth_parser.py`**

```python
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
    'Rules: missing fields = 0, "k" suffix = ×1000, liabilities/debt are positive numbers.\n'
    'Message: "{text}"'
)


def _parse_amount(raw: str) -> float:
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
    _fields = ["cash", "investments", "crypto", "savings", "other_assets", "liabilities"]
    ai = _ai_parse(text)
    if ai and any(float(ai.get(f, 0)) > 0 for f in _fields):
        return {f: float(ai.get(f, 0.0)) for f in _fields}
    return _regex_parse(text)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_networth_parser.py -v
```

Expected: 14 PASSED.

- [ ] **Step 5: Full suite**

```bash
python -m pytest -v
```

Expected: all passing.

- [ ] **Step 6: Commit**

```bash
git add app/networth_parser.py tests/test_networth_parser.py
git commit -m "feat(1.1): add net worth message parser with AI + regex fallback"
```

---

## Task 3: Net Worth Logic Module

**Files:**
- Create: `app/networth.py`
- Create: `tests/test_networth_logic.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_networth_logic.py`:

```python
import pytest
from app.networth import (
    calculate_net_worth,
    calculate_goal_progress,
    calculate_change,
    ascii_progress_bar,
    GOALS,
)


def test_calculate_net_worth_sums_assets():
    snap = {"cash": 1000.0, "investments": 5000.0, "crypto": 500.0,
            "savings": 2000.0, "other_assets": 0.0, "liabilities": 0.0}
    assert calculate_net_worth(snap) == pytest.approx(8500.0)


def test_calculate_net_worth_subtracts_liabilities():
    snap = {"cash": 5000.0, "investments": 0.0, "crypto": 0.0,
            "savings": 0.0, "other_assets": 0.0, "liabilities": 1500.0}
    assert calculate_net_worth(snap) == pytest.approx(3500.0)


def test_calculate_net_worth_handles_missing_keys():
    assert calculate_net_worth({"cash": 2000.0}) == pytest.approx(2000.0)


def test_goal_progress_pct_correct():
    result = calculate_goal_progress(12500.0, 25000.0)
    assert result["pct"] == pytest.approx(50.0)


def test_goal_progress_remaining_correct():
    result = calculate_goal_progress(12500.0, 25000.0)
    assert result["remaining"] == pytest.approx(12500.0)


def test_goal_progress_not_achieved():
    result = calculate_goal_progress(12500.0, 25000.0)
    assert result["achieved"] is False


def test_goal_progress_achieved():
    result = calculate_goal_progress(25000.0, 25000.0)
    assert result["achieved"] is True
    assert result["remaining"] == pytest.approx(0.0)


def test_goal_progress_over_100_clamped():
    result = calculate_goal_progress(30000.0, 25000.0)
    assert result["pct"] == pytest.approx(100.0)
    assert result["remaining"] == pytest.approx(0.0)


def test_calculate_change_returns_none_for_single_snapshot():
    history = [{"total_net_worth": 10000.0}]
    assert calculate_change(history) is None


def test_calculate_change_positive_delta():
    history = [
        {"total_net_worth": 10000.0},
        {"total_net_worth": 12000.0},
    ]
    result = calculate_change(history)
    assert result["delta"] == pytest.approx(2000.0)
    assert result["direction"] == "up"


def test_calculate_change_negative_delta():
    history = [
        {"total_net_worth": 12000.0},
        {"total_net_worth": 10000.0},
    ]
    result = calculate_change(history)
    assert result["delta"] == pytest.approx(-2000.0)
    assert result["direction"] == "down"


def test_calculate_change_empty_returns_none():
    assert calculate_change([]) is None


def test_ascii_progress_bar_full():
    assert ascii_progress_bar(100.0) == "▓▓▓▓▓▓▓▓▓▓"


def test_ascii_progress_bar_empty():
    assert ascii_progress_bar(0.0) == "░░░░░░░░░░"


def test_ascii_progress_bar_half():
    bar = ascii_progress_bar(50.0)
    assert bar == "▓▓▓▓▓░░░░░"


def test_goals_has_25k_and_30k():
    targets = {g["target"] for g in GOALS}
    assert 25_000.0 in targets
    assert 30_000.0 in targets
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_networth_logic.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.networth'`

- [ ] **Step 3: Create `app/networth.py`**

```python
GOALS = [
    {"label": "€25K", "target": 25_000.0},
    {"label": "€30K", "target": 30_000.0},
]


def calculate_net_worth(snapshot: dict) -> float:
    return (
        snapshot.get("cash", 0.0)
        + snapshot.get("investments", 0.0)
        + snapshot.get("crypto", 0.0)
        + snapshot.get("savings", 0.0)
        + snapshot.get("other_assets", 0.0)
        - snapshot.get("liabilities", 0.0)
    )


def calculate_goal_progress(current: float, target: float) -> dict:
    pct = min(100.0, (current / target * 100.0) if target > 0 else 0.0)
    remaining = max(0.0, target - current)
    return {
        "target": target,
        "pct": round(pct, 1),
        "remaining": remaining,
        "achieved": current >= target,
    }


def calculate_change(history: list[dict]) -> dict | None:
    if len(history) < 2:
        return None
    prev = history[-2]["total_net_worth"]
    latest = history[-1]["total_net_worth"]
    delta = latest - prev
    return {"delta": delta, "direction": "up" if delta >= 0 else "down"}


def ascii_progress_bar(pct: float, width: int = 10) -> str:
    filled = min(width, int(pct / 100.0 * width))
    return "▓" * filled + "░" * (width - filled)
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
python -m pytest tests/test_networth_logic.py -v
```

Expected: 17 PASSED.

- [ ] **Step 5: Full suite**

```bash
python -m pytest -v
```

- [ ] **Step 6: Commit**

```bash
git add app/networth.py tests/test_networth_logic.py
git commit -m "feat(1.1): add net worth logic module with goal tracking"
```

---

## Task 4: Telegram Commands + Message Routing

**Files:**
- Modify: `app/commands.py`
- Modify: `app/bot.py`
- Create: `tests/test_networth_commands.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_networth_commands.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_update():
    update = MagicMock()
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


SNAPSHOT = {
    "id": 1,
    "timestamp": "2026-05-15T10:00:00+00:00",
    "cash": 2000.0,
    "investments": 8000.0,
    "crypto": 500.0,
    "savings": 3000.0,
    "other_assets": 0.0,
    "liabilities": 500.0,
    "total_net_worth": 13000.0,
    "notes": "",
}


async def test_cmd_networth_no_data_replies_with_message():
    from app.commands import cmd_networth
    update = _make_update()
    with patch("app.database.get_latest_net_worth_snapshot", return_value=None):
        await cmd_networth(update, MagicMock())
    update.message.reply_text.assert_called_once()
    assert "No net worth" in update.message.reply_text.call_args[0][0]


async def test_cmd_networth_shows_total():
    from app.commands import cmd_networth
    update = _make_update()
    with patch("app.database.get_latest_net_worth_snapshot", return_value=SNAPSHOT):
        await cmd_networth(update, MagicMock())
    text = update.message.reply_text.call_args[0][0]
    assert "13000.00" in text


async def test_cmd_networth_history_no_data():
    from app.commands import cmd_networth_history
    update = _make_update()
    with patch("app.database.get_net_worth_history", return_value=[]):
        await cmd_networth_history(update, MagicMock())
    update.message.reply_text.assert_called_once()
    assert "No" in update.message.reply_text.call_args[0][0]


async def test_cmd_networth_history_shows_entries():
    from app.commands import cmd_networth_history
    update = _make_update()
    history = [SNAPSHOT, {**SNAPSHOT, "id": 2, "total_net_worth": 14000.0, "timestamp": "2026-05-16T10:00:00+00:00"}]
    with patch("app.database.get_net_worth_history", return_value=history):
        await cmd_networth_history(update, MagicMock())
    text = update.message.reply_text.call_args[0][0]
    assert "13000.00" in text
    assert "14000.00" in text


async def test_cmd_goal_shows_25k_and_30k():
    from app.commands import cmd_goal
    update = _make_update()
    with patch("app.database.get_latest_net_worth_snapshot", return_value=SNAPSHOT):
        await cmd_goal(update, MagicMock())
    text = update.message.reply_text.call_args[0][0]
    assert "25K" in text or "25k" in text
    assert "30K" in text or "30k" in text


async def test_cmd_goal_no_data():
    from app.commands import cmd_goal
    update = _make_update()
    with patch("app.database.get_latest_net_worth_snapshot", return_value=None):
        await cmd_goal(update, MagicMock())
    update.message.reply_text.assert_called_once()
    assert "No net worth" in update.message.reply_text.call_args[0][0]
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_networth_commands.py -v
```

Expected: `ImportError` — `cmd_networth` not defined in `app.commands`.

- [ ] **Step 3: Add imports and commands to `app/commands.py`**

Add these imports at the top of `app/commands.py` (after existing imports):

```python
from app.networth_parser import is_net_worth_message, parse_net_worth_message
from app.networth import GOALS, calculate_goal_progress, calculate_change, ascii_progress_bar
```

Add the private helper and new command handlers at the end of `app/commands.py`:

```python
async def _handle_net_worth_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    from app import database
    fields = parse_net_worth_message(text)
    total = (
        fields.get("cash", 0.0) + fields.get("investments", 0.0)
        + fields.get("crypto", 0.0) + fields.get("savings", 0.0)
        + fields.get("other_assets", 0.0) - fields.get("liabilities", 0.0)
    )
    if total == 0.0 and all(v == 0.0 for v in fields.values()):
        await update.message.reply_text(
            "Couldn't parse net worth. Try:\n"
            "  net worth cash 2000 investments 5000\n"
            "  net worth cash 2k savings 3k crypto 500"
        )
        return
    database.create_net_worth_snapshot(fields)
    lines = ["✅ Net worth saved!\n"]
    for label, key in [("Cash", "cash"), ("Investments", "investments"),
                       ("Crypto", "crypto"), ("Savings", "savings"),
                       ("Other", "other_assets"), ("Liabilities", "liabilities")]:
        val = fields.get(key, 0.0)
        if val > 0:
            lines.append(f"  {label}: {format_currency(val)}")
    lines.append(f"\nTotal: {format_currency(total)}")
    await update.message.reply_text("\n".join(lines))


async def cmd_networth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app import database
    snap = database.get_latest_net_worth_snapshot()
    if not snap:
        await update.message.reply_text(
            "No net worth data yet.\n\n"
            "Log your first snapshot:\n"
            "  net worth cash 2000 investments 5000 savings 3000"
        )
        return
    date_str = (snap.get("timestamp") or "")[:10]
    lines = [f"💰 Net Worth — {date_str}\n"]
    for label, key in [("Cash", "cash"), ("Investments", "investments"),
                       ("Crypto", "crypto"), ("Savings", "savings"),
                       ("Other Assets", "other_assets"), ("Liabilities", "liabilities")]:
        val = snap.get(key, 0.0)
        if val > 0:
            lines.append(f"{label}: {format_currency(val)}")
    lines.append(f"\nTotal: {format_currency(snap['total_net_worth'])}")
    await update.message.reply_text("\n".join(lines))


async def cmd_networth_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app import database
    history = database.get_net_worth_history(limit=5)
    if not history:
        await update.message.reply_text(
            "No net worth history yet.\n"
            "Send: net worth cash 2000 investments 5000"
        )
        return
    lines = ["📈 Net Worth History\n"]
    for i, snap in enumerate(history):
        date_str = (snap.get("timestamp") or "")[:10]
        total = snap["total_net_worth"]
        if i == 0:
            lines.append(f"{date_str}: {format_currency(total)}")
        else:
            prev = history[i - 1]["total_net_worth"]
            delta = total - prev
            sign = "+" if delta >= 0 else ""
            lines.append(f"{date_str}: {format_currency(total)} ({sign}{format_currency(delta)})")
    await update.message.reply_text("\n".join(lines))


async def cmd_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app import database
    snap = database.get_latest_net_worth_snapshot()
    if not snap:
        await update.message.reply_text(
            "No net worth data yet. Log a snapshot first:\n"
            "  net worth cash 2000 investments 5000"
        )
        return
    current = snap["total_net_worth"]
    lines = ["🎯 Financial Goals\n"]
    for goal in GOALS:
        progress = calculate_goal_progress(current, goal["target"])
        bar = ascii_progress_bar(progress["pct"])
        if progress["achieved"]:
            lines.append(f"{goal['label']}: {bar} ✅ Achieved!")
        else:
            lines.append(
                f"{goal['label']}: {bar} {progress['pct']}%\n"
                f"  {format_currency(progress['remaining'])} to go"
            )
    await update.message.reply_text("\n".join(lines))
```

Also update `handle_message` to route net worth messages. Find the existing `handle_message` function and add the routing check at the top (after `text = update.message.text.strip()`):

Existing start of `handle_message`:
```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    try:
        parsed = parse_message(text)
```

Change to:
```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if is_net_worth_message(text):
        await _handle_net_worth_message(update, context, text)
        return
    try:
        parsed = parse_message(text)
```

- [ ] **Step 4: Register new commands in `app/bot.py`**

Add these three lines inside `create_ptb_app()` after the `handoff` handler:

```python
application.add_handler(CommandHandler("networth", owner_only(cmd_networth)))
application.add_handler(CommandHandler("networth_history", owner_only(cmd_networth_history)))
application.add_handler(CommandHandler("goal", owner_only(cmd_goal)))
```

Also add the three new commands to the import at the top of `bot.py`:

```python
from app.commands import (
    handle_message,
    cmd_start, cmd_help, cmd_today, cmd_week,
    cmd_month, cmd_income, cmd_undo, cmd_summary, cmd_budget,
    cmd_status, cmd_next, cmd_git, cmd_handoff,
    cmd_networth, cmd_networth_history, cmd_goal,
)
```

- [ ] **Step 5: Run command tests**

```bash
python -m pytest tests/test_networth_commands.py -v
```

Expected: 6 PASSED.

- [ ] **Step 6: Full suite**

```bash
python -m pytest -v
```

Expected: all passing.

- [ ] **Step 7: Commit**

```bash
git add app/commands.py app/bot.py tests/test_networth_commands.py
git commit -m "feat(1.1): add /networth /networth_history /goal commands + message routing"
```

---

## Task 5: Dashboard Route + Template + CSS

**Files:**
- Modify: `app/dashboard.py`
- Modify: `app/templates/base.html`
- Create: `app/templates/networth.html`
- Modify: `app/static/style.css`

- [ ] **Step 1: Write a failing dashboard test**

Add to `tests/test_dashboard.py` (append at the end of the existing file):

```python
def test_networth_page_returns_200(client):
    with patch("app.dashboard.sheets.get_net_worth_history", return_value=[]), \
         patch("app.dashboard.sheets.get_latest_net_worth_snapshot", return_value=None):
        response = client.get("/networth")
    assert response.status_code == 200

def test_networth_page_empty_state(client):
    with patch("app.dashboard.sheets.get_net_worth_history", return_value=[]), \
         patch("app.dashboard.sheets.get_latest_net_worth_snapshot", return_value=None):
        response = client.get("/networth")
    assert "No net worth" in response.text or "No Net Worth" in response.text

def test_networth_page_shows_total_when_data(client):
    snap = {
        "id": 1, "timestamp": "2026-05-15T10:00:00+00:00",
        "cash": 2000.0, "investments": 8000.0, "crypto": 0.0,
        "savings": 3000.0, "other_assets": 0.0, "liabilities": 0.0,
        "total_net_worth": 13000.0, "notes": "",
    }
    with patch("app.dashboard.sheets.get_net_worth_history", return_value=[snap]), \
         patch("app.dashboard.sheets.get_latest_net_worth_snapshot", return_value=snap):
        response = client.get("/networth")
    assert "13000.00" in response.text
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_dashboard.py::test_networth_page_returns_200 -v
```

Expected: `404` — route doesn't exist yet.

- [ ] **Step 3: Add `/networth` route to `app/dashboard.py`**

Add these imports at the top of `dashboard.py` (after existing imports):

```python
from app import networth as nw_module
```

Add the route at the end of `dashboard.py` (before any trailing newline):

```python
@app.get("/networth")
async def networth_page(request: Request):
    latest = sheets.get_latest_net_worth_snapshot()
    history = sheets.get_net_worth_history(limit=30)
    change = nw_module.calculate_change(history)
    goals = [
        {**g, **nw_module.calculate_goal_progress(
            latest["total_net_worth"] if latest else 0.0, g["target"]
        )}
        for g in nw_module.GOALS
    ]
    allocation = []
    max_asset = 1.0
    if latest:
        raw = [
            {"label": "Cash",        "amount": latest["cash"],        "color": ""},
            {"label": "Investments", "amount": latest["investments"],  "color": ""},
            {"label": "Crypto",      "amount": latest["crypto"],       "color": ""},
            {"label": "Savings",     "amount": latest["savings"],      "color": ""},
            {"label": "Other Assets","amount": latest["other_assets"], "color": ""},
            {"label": "Liabilities", "amount": latest["liabilities"],  "color": "danger"},
        ]
        allocation = [a for a in raw if a["amount"] > 0]
        pos_amounts = [a["amount"] for a in allocation]
        max_asset = max(pos_amounts) if pos_amounts else 1.0
    chart_labels = [s["timestamp"][:10] for s in history]
    chart_values = [s["total_net_worth"] for s in history]
    return templates.TemplateResponse(request, "networth.html", {
        "active_page": "networth",
        "latest": latest,
        "history": history,
        "change": change,
        "goals": goals,
        "allocation": allocation,
        "max_asset": max_asset,
        "chart_labels": chart_labels,
        "chart_values": chart_values,
    })
```

- [ ] **Step 4: Add "Net Worth" to `app/templates/base.html` nav**

In `base.html`, find the nav links block:
```html
    <a href="/transactions" class="{{ 'active' if active_page == 'transactions' else '' }}">Transactions</a>
```

Add after it:
```html
    <a href="/networth" class="{{ 'active' if active_page == 'networth' else '' }}">Net Worth</a>
```

- [ ] **Step 5: Create `app/templates/networth.html`**

```html
{% extends "base.html" %}
{% block content %}

<div class="kpi-grid">

  <div class="glass-card">
    <div class="kpi-label">Net Worth</div>
    {% if latest %}
    <div class="kpi-value {% if latest.total_net_worth >= 0 %}positive{% else %}danger{% endif %}">
      {{ latest.total_net_worth | format_currency }}
    </div>
    <div class="kpi-sub">as of {{ latest.timestamp[:10] }}</div>
    {% else %}
    <div class="kpi-value" style="color: var(--text-secondary);">—</div>
    <div class="kpi-sub">No data yet</div>
    {% endif %}
  </div>

  <div class="glass-card">
    <div class="kpi-label">Change</div>
    {% if change %}
    <div class="kpi-value {% if change.delta >= 0 %}positive{% else %}danger{% endif %}">
      {% if change.delta >= 0 %}+{% endif %}{{ change.delta | format_currency }}
    </div>
    <div class="kpi-sub">since last snapshot</div>
    {% else %}
    <div class="kpi-value" style="color: var(--text-secondary);">—</div>
    <div class="kpi-sub">Need 2+ snapshots</div>
    {% endif %}
  </div>

  {% for goal in goals %}
  <div class="glass-card">
    <div class="kpi-label">Goal {{ goal.label }}</div>
    <div class="kpi-value {% if goal.achieved %}positive{% else %}accent{% endif %}">
      {{ goal.pct }}%
    </div>
    <div class="progress-track">
      <div class="progress-fill {% if goal.achieved %}positive{% endif %}"
           style="width: {{ goal.pct }}%"></div>
    </div>
    <div class="kpi-sub">
      {% if goal.achieved %}
        🎉 Achieved!
      {% else %}
        {{ goal.remaining | format_currency }} to go
      {% endif %}
    </div>
  </div>
  {% endfor %}

</div>

{% if latest %}

<div class="glass-card" style="margin-bottom: 20px;">
  <div class="section-header">Asset Allocation</div>
  {% if allocation %}
    {% for a in allocation %}
    <div class="cat-row">
      <div class="cat-name">{{ a.label }}</div>
      <div class="cat-track">
        <div class="cat-fill {% if a.color == 'danger' %}danger-fill{% endif %}"
             style="width: {{ (a.amount / max_asset * 100) | round(1) }}%"></div>
      </div>
      <div class="cat-amount {% if a.color == 'danger' %}danger{% endif %}">
        {{ a.amount | format_currency }}
      </div>
    </div>
    {% endfor %}
  {% else %}
    <p style="color: var(--text-secondary); font-size: 14px;">No asset breakdown available.</p>
  {% endif %}
</div>

<div class="glass-card" style="margin-bottom: 20px;">
  <div class="section-header">Net Worth Over Time</div>
  {% if history | length >= 2 %}
  <div style="position: relative; height: 240px;">
    <canvas id="nwChart"></canvas>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <script>
    (function() {
      const ctx = document.getElementById('nwChart');
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: {{ chart_labels | tojson }},
          datasets: [{
            label: 'Net Worth',
            data: {{ chart_values | tojson }},
            borderColor: '#3F5AF5',
            backgroundColor: 'rgba(63,90,245,0.08)',
            fill: true,
            tension: 0.4,
            pointBackgroundColor: '#3F5AF5',
            pointBorderColor: '#3F5AF5',
            pointRadius: 4,
            pointHoverRadius: 6,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: 'rgba(8,12,20,0.9)',
              borderColor: 'rgba(255,255,255,0.1)',
              borderWidth: 1,
              callbacks: {
                label: function(ctx) { return '€' + ctx.parsed.y.toFixed(2); }
              }
            }
          },
          scales: {
            x: {
              ticks: { color: 'rgba(255,255,255,0.45)', font: { size: 11 } },
              grid:  { color: 'rgba(255,255,255,0.05)' }
            },
            y: {
              ticks: {
                color: 'rgba(255,255,255,0.45)',
                font: { size: 11 },
                callback: function(v) { return '€' + v.toLocaleString(); }
              },
              grid: { color: 'rgba(255,255,255,0.05)' }
            }
          }
        }
      });
    })();
  </script>
  {% else %}
  <p style="color: var(--text-secondary); font-size: 14px; line-height: 1.7;">
    Log more snapshots to see your net worth trend.<br>
    Send via Telegram: <code style="background:rgba(255,255,255,0.08);padding:2px 8px;border-radius:4px;">net worth cash 2000 investments 5000</code>
  </p>
  {% endif %}
</div>

<div class="glass-card">
  <div class="section-header">Recent Snapshots</div>
  <table class="glass-table">
    <thead>
      <tr>
        <th>Date</th>
        <th>Net Worth</th>
        <th>Cash</th>
        <th>Investments</th>
        <th>Savings</th>
        <th>Liabilities</th>
      </tr>
    </thead>
    <tbody>
      {% for s in history | reverse %}
      <tr>
        <td>{{ s.timestamp[:10] }}</td>
        <td><strong>{{ s.total_net_worth | format_currency }}</strong></td>
        <td>{{ s.cash | format_currency }}</td>
        <td>{{ s.investments | format_currency }}</td>
        <td>{{ s.savings | format_currency }}</td>
        <td>{{ s.liabilities | format_currency }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

{% else %}

<div class="glass-card">
  <div class="section-header">No Net Worth Data Yet</div>
  <p style="color: var(--text-secondary); font-size: 14px; line-height: 1.9;">
    Log your first snapshot via Telegram:<br><br>
    <code style="background:rgba(255,255,255,0.08);padding:4px 10px;border-radius:6px;display:inline-block;margin-bottom:8px;">net worth cash 2000 investments 5000 savings 3000</code><br>
    <code style="background:rgba(255,255,255,0.08);padding:4px 10px;border-radius:6px;display:inline-block;margin-bottom:8px;">net worth cash 2k savings 5k investments 10k</code><br><br>
    Or send <code style="background:rgba(255,255,255,0.08);padding:2px 6px;border-radius:4px;">/networth</code> to the bot.
  </p>
</div>

{% endif %}

{% endblock %}
```

- [ ] **Step 6: Add missing CSS to `app/static/style.css`**

Append to the end of `app/static/style.css`:

```css
/* ── Net Worth additions ── */
.progress-fill.positive { background: var(--success); }
.cat-fill.danger-fill   { background: var(--danger); }
.danger                 { color: var(--danger); }
```

- [ ] **Step 7: Run dashboard tests**

```bash
python -m pytest tests/test_dashboard.py -v
```

Expected: all PASSED including the 3 new net worth tests.

- [ ] **Step 8: Full suite**

```bash
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add app/dashboard.py app/templates/base.html app/templates/networth.html app/static/style.css tests/test_dashboard.py
git commit -m "feat(1.1): add /networth dashboard page with Chart.js trend chart"
```

---

## Task 6: Documentation + Notifications + Final Commit

**Files:**
- Modify: `docs/current-status.md`
- Modify: `docs/architecture.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Run full test suite — confirm all pass**

```bash
python -m pytest -v
```

Record the final count. Expected: 99 existing + ~46 new = ~145 passing.

- [ ] **Step 2: Update `docs/current-status.md`**

Update the Module 1.1 section to:

```markdown
## Module 1.1 — Net Worth Tracker

**Status: ✅ COMPLETE**

### What Works
- Natural language snapshot logging: "net worth cash 2k investments 8k"
- AI parse (GPT-4o-mini) + regex fallback with "k" suffix support
- PostgreSQL `net_worth_snapshots` table — append-only, never overwrites
- Bot commands: `/networth` (latest + breakdown), `/networth_history` (last 5), `/goal` (€25K + €30K progress with progress bars)
- Message routing: `handle_message` auto-detects net worth messages before finance parser
- Dashboard page `/networth`: net worth KPI, change KPI, goal progress cards, asset allocation bars, Chart.js trend chart, snapshots table
- Empty-state UX: helpful onboarding messages when no data exists

### Do Not Touch
- `net_worth_snapshots` table — never delete or alter; append-only by design
```

Update the system health test count and tests line.

- [ ] **Step 3: Update `docs/architecture.md`**

Add to the data model section after the `agent_state` table:

```markdown
**Table: `net_worth_snapshots`**

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | auto-increment |
| timestamp | String | ISO 8601 UTC |
| cash | Float | 0.0 if not provided |
| investments | Float | 0.0 if not provided |
| crypto | Float | 0.0 if not provided |
| savings | Float | 0.0 if not provided |
| other_assets | Float | 0.0 if not provided |
| liabilities | Float | positive; subtracted in total |
| total_net_worth | Float | calculated: assets − liabilities |
| notes | String | optional user note |
```

Add to dashboard routes:
```
| GET /networth | networth.html | net worth KPI, goals, chart, snapshots |
```

Add to key files:
```
| `app/networth_parser.py` | Natural language → net worth fields |
| `app/networth.py`        | Goal calculations, change delta, progress bar |
```

- [ ] **Step 4: Update `docs/roadmap.md`**

Change Module 1.1 status from `🔲 NOT STARTED` to `✅ DONE` and update the description.

- [ ] **Step 5: Send Telegram completion notification**

```bash
python scripts/notify_me.py complete "Module 1.1 Net Worth Tracker complete. DB table, AI+regex parser, /networth /networth_history /goal commands, /networth dashboard with Chart.js trend chart. All tests passing."
```

- [ ] **Step 6: Commit docs**

```bash
git add docs/current-status.md docs/architecture.md docs/roadmap.md
git commit -m "docs(1.1): update architecture, status, roadmap for net worth module"
```

- [ ] **Step 7: Update handoff**

```bash
python scripts/create_handoff.py
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] DB table with all required fields (id, timestamp, cash, investments, crypto, savings, other_assets, liabilities, total_net_worth, notes)
- [x] Store historical snapshots, never overwrite — append-only `create_net_worth_snapshot`
- [x] `total_net_worth` calculated consistently in `create_net_worth_snapshot`
- [x] DB helper: create snapshot, get latest, get history — ✓ Task 1
- [x] Natural language logging with all example patterns — ✓ Task 2
- [x] AI parse + regex fallback — ✓ Task 2
- [x] `/networth` command — ✓ Task 4
- [x] `/networth_history` command — ✓ Task 4
- [x] `/goal` command with €25K + €30K + progress bar — ✓ Task 4
- [x] Dashboard: current net worth KPI — ✓ Task 5
- [x] Dashboard: monthly change KPI — ✓ Task 5
- [x] Dashboard: progress toward €25K and €30K — ✓ Task 5
- [x] Dashboard: asset allocation breakdown — ✓ Task 5
- [x] Dashboard: recent snapshots table — ✓ Task 5
- [x] Dashboard: Chart.js trend chart — ✓ Task 5
- [x] Empty state when only one snapshot — ✓ Task 5 (template shows no chart, helpful message)
- [x] Tests: DB, parser, logic, commands, dashboard — ✓ Tasks 1-5
- [x] Documentation updates — ✓ Task 6
- [x] Scope: no brokerage APIs, no CSV, no OCR, no live pricing — ✓ scope respected throughout

**Placeholder scan:** No TBDs, all code blocks are complete.

**Type consistency:**
- `create_net_worth_snapshot(fields: dict) -> int` — used in Task 1 tests, Task 4 handler ✓
- `get_latest_net_worth_snapshot() -> dict | None` — used in Task 1 tests, Task 4 commands, Task 5 route ✓
- `get_net_worth_history(limit=30) -> list[dict]` — used in Task 1 tests, Task 4 commands, Task 5 route ✓
- `parse_net_worth_message(text) -> dict` — returns `{cash, investments, crypto, savings, other_assets, liabilities}` — used in Task 2 tests, Task 4 handler ✓
- `is_net_worth_message(text) -> bool` — used in Task 2 tests, Task 4 `handle_message` ✓
- `calculate_goal_progress(current, target) -> dict` — returns `{target, pct, remaining, achieved}` — used in Task 3 tests, Task 4 `cmd_goal`, Task 5 route ✓
- `calculate_change(history) -> dict | None` — returns `{delta, direction}` — used in Task 3 tests, Task 5 route ✓
- `ascii_progress_bar(pct, width=10) -> str` — used in Task 3 tests, Task 4 `cmd_goal` ✓
- `GOALS` — list of `{label, target}` — used in Task 3 tests, Task 4 `cmd_goal`, Task 5 route ✓
