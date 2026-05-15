# Agent Control Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the minimum Agent Control Layer so Claude Code can work autonomously while the user supervises via Telegram from their phone.

**Architecture:** A new `agent_state` PostgreSQL table stores live snapshots written by CLI scripts. Four new Telegram bot commands read from this table and work from Railway. Two CLI scripts (`notify_me.py`, `create_handoff.py`) let Claude push state and notifications during autonomous work.

**Tech Stack:** Python 3.13, SQLAlchemy 2.x (existing), python-telegram-bot 20.7 (existing), httpx (existing), pytest with monkeypatch for DB isolation.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `app/database.py` | Modify | Add `agent_state` table + `write_agent_state()` + `read_latest_agent_state()` |
| `app/commands.py` | Modify | Add `cmd_status`, `cmd_next`, `cmd_git`, `cmd_handoff` handlers |
| `app/bot.py` | Modify | Register 4 new commands |
| `scripts/notify_me.py` | Create | Typed notification CLI for Claude to use during autonomous work |
| `scripts/create_handoff.py` | Create | Comprehensive handoff generator (files + DB + Telegram) |
| `handoff/start_next_session_prompt.md` | Create | Static startup prompt for next Claude session |
| `CLAUDE.md` | Modify | Add Autonomous Workflow Rules section |
| `README.md` | Modify | Add Autonomous Claude Workflow section |
| `docs/current-status.md` | Modify | Mark Module 1.4 as IN PROGRESS |
| `tests/test_agent_state.py` | Create | DB function unit tests |
| `tests/test_notify.py` | Create | notify_me.py format function unit tests |

---

## Task 1: agent_state table + DB functions (TDD)

**Files:**
- Modify: `app/database.py`
- Create: `tests/test_agent_state.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_agent_state.py`:

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


def test_read_returns_none_when_empty():
    assert db.read_latest_agent_state() is None


def test_write_and_read():
    db.write_agent_state({
        "status_type": "progress",
        "severity": "info",
        "requires_user_action": False,
        "resolved": False,
        "progress_message": "Test progress",
    })
    state = db.read_latest_agent_state()
    assert state is not None
    assert state["status_type"] == "progress"
    assert state["progress_message"] == "Test progress"
    assert state["severity"] == "info"


def test_read_returns_latest():
    db.write_agent_state({"status_type": "progress", "progress_message": "first"})
    db.write_agent_state({"status_type": "error", "progress_message": "second"})
    state = db.read_latest_agent_state()
    assert state["progress_message"] == "second"
    assert state["status_type"] == "error"


def test_timestamp_auto_set():
    db.write_agent_state({"status_type": "progress"})
    state = db.read_latest_agent_state()
    assert state["timestamp"] is not None
    assert "T" in state["timestamp"]


def test_read_by_status_type():
    db.write_agent_state({"status_type": "progress", "progress_message": "p1"})
    db.write_agent_state({"status_type": "handoff", "progress_message": "h1"})
    db.write_agent_state({"status_type": "progress", "progress_message": "p2"})
    handoff_state = db.read_latest_agent_state(status_type="handoff")
    assert handoff_state["status_type"] == "handoff"
    assert handoff_state["progress_message"] == "h1"


def test_read_by_type_returns_none_when_no_match():
    db.write_agent_state({"status_type": "progress"})
    state = db.read_latest_agent_state(status_type="handoff")
    assert state is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/arryawillems/finance-lifeos && source .venv/bin/activate && pytest tests/test_agent_state.py -v
```

Expected: `AttributeError: module 'app.database' has no attribute 'read_latest_agent_state'`

- [ ] **Step 3: Add `agent_state` table and functions to `app/database.py`**

Add after the existing `transactions` table definition and before `init_db()`. The full updated file:

```python
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    MetaData, Table, insert, select, update, desc,
)
from app import config
from datetime import datetime, timezone

# Railway uses postgres://, SQLAlchemy 2.0 needs postgresql://
_db_url = config.DATABASE_URL.replace("postgres://", "postgresql://", 1)
_engine = create_engine(_db_url)
_metadata = MetaData()

transactions = Table(
    "transactions",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", String),
    Column("date", String),
    Column("week_start", String),
    Column("month", String),
    Column("type", String),
    Column("amount", Float),
    Column("description", String),
    Column("category", String),
    Column("tag", String, default=""),
    Column("payment_type", String, default=""),
    Column("is_impulse", Boolean, default=False),
    Column("is_necessary", String, default=""),
    Column("notes", String, default=""),
)

agent_state = Table(
    "agent_state",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", String),
    Column("status_type", String),
    Column("severity", String),
    Column("requires_user_action", Boolean, default=False),
    Column("resolved", Boolean, default=False),
    Column("current_module", String),
    Column("current_task", String),
    Column("progress_message", String),
    Column("blocker", String),
    Column("next_task", String),
    Column("git_summary", String),
    Column("handoff_path", String),
    Column("startup_prompt_path", String),
    Column("metadata_json", String),
)


def init_db() -> None:
    _metadata.create_all(_engine)


def append_transaction(parsed: dict, category: str) -> int:
    with _engine.connect() as conn:
        result = conn.execute(
            insert(transactions).values(
                timestamp=parsed["timestamp"],
                date=parsed["date"],
                week_start=parsed["week_start"],
                month=parsed["month"],
                type=parsed["type"],
                amount=parsed["amount"],
                description=parsed["description"],
                category=category,
                tag="",
                payment_type="",
                is_impulse=parsed["is_impulse"],
                is_necessary="",
                notes="",
            )
        )
        conn.commit()
        return result.inserted_primary_key[0]


def get_all_transactions() -> list[dict]:
    with _engine.connect() as conn:
        result = conn.execute(select(transactions).order_by(transactions.c.id))
        return [dict(row._mapping) for row in result]


def undo_last_transaction() -> dict | None:
    with _engine.connect() as conn:
        result = conn.execute(
            select(transactions).order_by(desc(transactions.c.id)).limit(1)
        )
        row = result.fetchone()
        if row is None:
            return None
        record = dict(row._mapping)
        conn.execute(
            update(transactions)
            .where(transactions.c.id == record["id"])
            .values(notes="[UNDONE]")
        )
        conn.commit()
        return record


def write_agent_state(fields: dict) -> None:
    if "timestamp" not in fields:
        fields = {**fields, "timestamp": datetime.now(timezone.utc).isoformat()}
    with _engine.connect() as conn:
        conn.execute(insert(agent_state).values(**fields))
        conn.commit()


def read_latest_agent_state(status_type: str | None = None) -> dict | None:
    with _engine.connect() as conn:
        if status_type:
            q = (
                select(agent_state)
                .where(agent_state.c.status_type == status_type)
                .order_by(desc(agent_state.c.id))
                .limit(1)
            )
        else:
            q = select(agent_state).order_by(desc(agent_state.c.id)).limit(1)
        result = conn.execute(q)
        row = result.fetchone()
        if row is None:
            return None
        return dict(row._mapping)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_agent_state.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Run full suite to confirm no regressions**

```bash
pytest -q
```

Expected: `85 passed` (79 + 6 new)

- [ ] **Step 6: Commit**

```bash
git add app/database.py tests/test_agent_state.py
git commit -m "feat(db): add agent_state table with write/read functions"
```

---

## Task 2: scripts/notify_me.py + tests (TDD)

**Files:**
- Create: `scripts/notify_me.py`
- Create: `tests/test_notify.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_notify.py`:

```python
import sys
from pathlib import Path

# Allow importing from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from notify_me import _format_message, STATUS_SEVERITY, REQUIRES_ACTION, TYPE_ALIASES


def test_progress_format():
    result = _format_message("progress", "Dashboard started", [])
    assert result == "✅ Progress: Dashboard started"


def test_decision_format():
    result = _format_message("decision", "Choose DB", ["A: PostgreSQL", "B: Supabase"])
    assert "🤔 Decision needed:" in result
    assert "Choose DB" in result
    assert "A: PostgreSQL" in result
    assert "B: Supabase" in result
    assert "Reply with your choice." in result


def test_action_format():
    result = _format_message("manual_action", "Add API key to Railway", [])
    assert "🔧 Manual action needed:" in result
    assert "Add API key to Railway" in result
    assert "Reply DONE when complete." in result


def test_error_format():
    result = _format_message("error", "Tests failing in test_budget.py", [])
    assert "❌ Error:" in result
    assert "Tests failing in test_budget.py" in result


def test_completion_format():
    result = _format_message("completion", "Net worth tracker done.", [])
    assert "🎉 Complete:" in result
    assert "Net worth tracker done." in result


def test_handoff_format():
    result = _format_message("handoff", "", [])
    assert "🔄 Session handoff needed." in result
    assert "claude logout" in result
    assert "handoff/latest.md" in result


def test_severity_mapping():
    assert STATUS_SEVERITY["progress"] == "info"
    assert STATUS_SEVERITY["decision"] == "warning"
    assert STATUS_SEVERITY["manual_action"] == "warning"
    assert STATUS_SEVERITY["error"] == "error"
    assert STATUS_SEVERITY["completion"] == "info"
    assert STATUS_SEVERITY["handoff"] == "warning"


def test_requires_action_mapping():
    assert REQUIRES_ACTION["progress"] is False
    assert REQUIRES_ACTION["decision"] is True
    assert REQUIRES_ACTION["manual_action"] is True
    assert REQUIRES_ACTION["error"] is True
    assert REQUIRES_ACTION["completion"] is False
    assert REQUIRES_ACTION["handoff"] is True


def test_type_aliases():
    assert TYPE_ALIASES["action"] == "manual_action"
    assert TYPE_ALIASES["complete"] == "completion"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_notify.py -v
```

Expected: `ModuleNotFoundError: No module named 'notify_me'`

- [ ] **Step 3: Create `scripts/notify_me.py`**

```python
#!/usr/bin/env python3
"""
Typed notification CLI for Claude to use during autonomous work.

Usage:
    python scripts/notify_me.py progress "Dashboard started"
    python scripts/notify_me.py decision "Choose DB" "A: PostgreSQL" "B: Supabase"
    python scripts/notify_me.py action "Add OPENAI_API_KEY to Railway"
    python scripts/notify_me.py error "Tests failing in test_budget.py"
    python scripts/notify_me.py complete "Net worth tracker done."
    python scripts/notify_me.py handoff
"""
import sys
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from app.telegram import send_telegram_message
from app.database import write_agent_state

STATUS_SEVERITY = {
    "progress": "info",
    "decision": "warning",
    "manual_action": "warning",
    "error": "error",
    "completion": "info",
    "handoff": "warning",
}

REQUIRES_ACTION = {
    "progress": False,
    "decision": True,
    "manual_action": True,
    "error": True,
    "completion": False,
    "handoff": True,
}

TYPE_ALIASES = {
    "action": "manual_action",
    "complete": "completion",
}


def _git_summary() -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "log", "--oneline", "-5"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _format_message(status_type: str, message: str, options: list[str]) -> str:
    if status_type == "progress":
        return f"✅ Progress: {message}"
    if status_type == "decision":
        lines = ["🤔 Decision needed:", message] + options + ["Reply with your choice."]
        return "\n".join(lines)
    if status_type == "manual_action":
        return f"🔧 Manual action needed:\n{message}\nReply DONE when complete."
    if status_type == "error":
        return f"❌ Error:\n{message}"
    if status_type == "completion":
        return f"🎉 Complete:\n{message}"
    if status_type == "handoff":
        return (
            "🔄 Session handoff needed.\n"
            "Switch account now.\n\n"
            "1. Run: claude logout\n"
            "2. Run: claude login\n"
            "3. Open this repo\n"
            "4. Read handoff/latest.md"
        )
    return f"📌 {message}"


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("Usage: notify_me.py <type> [message] [options...]")
        print("Types: progress, decision, action, error, complete, handoff")
        sys.exit(1)

    raw_type = args[0]
    message = args[1] if len(args) > 1 else ""
    options = args[2:] if len(args) > 2 else []

    status_type = TYPE_ALIASES.get(raw_type, raw_type)

    if status_type not in STATUS_SEVERITY:
        print(f"Unknown type: {raw_type}. Valid: progress, decision, action, error, complete, handoff")
        sys.exit(1)

    telegram_text = _format_message(status_type, message, options)
    git_summary = _git_summary()
    metadata = json.dumps({"options": options}) if options else None

    write_agent_state({
        "status_type": status_type,
        "severity": STATUS_SEVERITY[status_type],
        "requires_user_action": REQUIRES_ACTION[status_type],
        "resolved": False,
        "progress_message": message,
        "git_summary": git_summary,
        "metadata_json": metadata,
    })

    sent = send_telegram_message(telegram_text)
    if sent:
        print(f"✓ [{status_type}] Notification sent.")
    else:
        print(f"✗ [{status_type}] Telegram failed (state written to DB).")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_notify.py -v
```

Expected: `10 passed`

- [ ] **Step 5: Smoke test the script**

```bash
cd /Users/arryawillems/finance-lifeos && source .venv/bin/activate && python scripts/notify_me.py progress "Agent control layer implementation started"
```

Expected: Telegram message received on phone + console output `✓ [progress] Notification sent.`

- [ ] **Step 6: Run full suite**

```bash
pytest -q
```

Expected: `95 passed` (85 + 10 new)

- [ ] **Step 7: Commit**

```bash
git add scripts/notify_me.py tests/test_notify.py
git commit -m "feat(scripts): add notify_me.py typed notification CLI"
```

---

## Task 3: scripts/create_handoff.py

**Files:**
- Create: `scripts/create_handoff.py`
- Create: `handoff/start_next_session_prompt.md`

- [ ] **Step 1: Create `handoff/start_next_session_prompt.md`**

```markdown
# LifeOS — Next Session Startup Prompt

Paste this as your first message when starting a new Claude session on this repo.

---

I'm continuing work on the LifeOS repo (finance-lifeos).

Please read in this order before doing anything:
1. CLAUDE.md
2. docs/architecture.md
3. docs/current-status.md
4. handoff/latest.md

Then:
- Confirm the current state
- Run `pytest` and confirm all tests pass
- Ask what I'd like to work on next

Rules:
- Do NOT rebuild existing functionality
- Do NOT modify existing passing tests
- Do NOT change the database schema without explicit instruction
- Do NOT commit broken code
- Notify me via `python scripts/notify_me.py` when decisions, blockers, or completions occur
```

- [ ] **Step 2: Create `scripts/create_handoff.py`**

```python
#!/usr/bin/env python3
"""
Comprehensive handoff generator. Run before ending a Claude session.

Writes:
  - handoff/latest.md        (human-readable handoff)
  - handoff/start_next_session_prompt.md  (updated, for next account)

Updates agent_state in PostgreSQL and sends a Telegram notification.

Usage:
    python scripts/create_handoff.py
"""
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from app.telegram import send_telegram_message
from app.database import write_agent_state, read_latest_agent_state

HANDOFF_PATH = REPO_ROOT / "handoff" / "latest.md"
STARTUP_PROMPT_PATH = REPO_ROOT / "handoff" / "start_next_session_prompt.md"

STARTUP_PROMPT = """\
# LifeOS — Next Session Startup Prompt

Paste this as your first message when starting a new Claude session on this repo.

---

I'm continuing work on the LifeOS repo (finance-lifeos).

Please read in this order before doing anything:
1. CLAUDE.md
2. docs/architecture.md
3. docs/current-status.md
4. handoff/latest.md

Then:
- Confirm the current state
- Run `pytest` and confirm all tests pass
- Ask what I'd like to work on next

Rules:
- Do NOT rebuild existing functionality
- Do NOT modify existing passing tests
- Do NOT change the database schema without explicit instruction
- Do NOT commit broken code
- Notify me via `python scripts/notify_me.py` when decisions, blockers, or completions occur
"""

TELEGRAM_MESSAGE = (
    "🔄 Session handoff needed.\n"
    "Switch account now.\n\n"
    "1. Run: claude logout\n"
    "2. Run: claude login\n"
    "3. Open this repo\n"
    "4. Read handoff/latest.md"
)


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT)] + args,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _build_handoff(now: str, git_status: str, git_log: str, last_state: dict | None) -> str:
    files_section = git_status if git_status else "No uncommitted changes."
    log_section = git_log if git_log else "No recent commits."
    s = last_state or {}
    current_module = s.get("current_module") or "Unknown"
    current_task = s.get("current_task") or "Unknown"
    next_task = s.get("next_task") or "See docs/current-status.md"
    blocker = s.get("blocker") or "None"

    return f"""\
# Handoff — {now}

## What Was Done
- Session ended. See recent commits below.
- Last module: {current_module}
- Last task: {current_task}

## Files Changed
{files_section}

## Recent Commits
{log_section}

## Current State
Session handoff triggered. Review git log and docs/current-status.md for full picture.

## Bugs / Blockers
{blocker}

## Next Exact Task
{next_task}

## Startup Prompt
See handoff/start_next_session_prompt.md — paste it as your first message in the new session.

## Commands to Run
```bash
pytest
uvicorn app.dashboard:app --reload
```

## Environment Variables Needed
- TELEGRAM_BOT_TOKEN
- TELEGRAM_OWNER_CHAT_ID
- DATABASE_URL
- OPENAI_API_KEY
- WEBHOOK_BASE_URL
- WEEKLY_BUDGET (default: 90)
- LOCAL_POLLING (true for local dev)

## Do-Not-Touch Warnings
- See CLAUDE.md for full list.
- Never modify the transactions table schema.
- Never delete files without explicit approval.
"""


def main() -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    git_status = _git(["status", "--short"])
    git_log = _git(["log", "--oneline", "-5"])
    last_state = read_latest_agent_state()

    content = _build_handoff(now, git_status, git_log, last_state)

    try:
        HANDOFF_PATH.parent.mkdir(parents=True, exist_ok=True)
        HANDOFF_PATH.write_text(content, encoding="utf-8")
        print(f"✓ Handoff written to {HANDOFF_PATH}")
    except Exception as e:
        print(f"✗ Could not write handoff file: {e}")

    try:
        STARTUP_PROMPT_PATH.write_text(STARTUP_PROMPT, encoding="utf-8")
        print(f"✓ Startup prompt written to {STARTUP_PROMPT_PATH}")
    except Exception as e:
        print(f"✗ Could not write startup prompt: {e}")

    write_agent_state({
        "status_type": "handoff",
        "severity": "warning",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": "Session handoff created.",
        "git_summary": git_log,
        "handoff_path": "handoff/latest.md",
        "startup_prompt_path": "handoff/start_next_session_prompt.md",
        "current_module": (last_state or {}).get("current_module"),
        "next_task": (last_state or {}).get("next_task"),
    })

    sent = send_telegram_message(TELEGRAM_MESSAGE)
    if sent:
        print("✓ Telegram notification sent.")
    else:
        print("✗ Telegram notification failed (handoff files still written).")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Smoke test**

```bash
cd /Users/arryawillems/finance-lifeos && source .venv/bin/activate && python scripts/create_handoff.py
```

Expected output:
```
✓ Handoff written to .../handoff/latest.md
✓ Startup prompt written to .../handoff/start_next_session_prompt.md
✓ Telegram notification sent.
```

Verify handoff was written:
```bash
head -10 handoff/latest.md
```

Expected: `# Handoff — <current date> UTC`

- [ ] **Step 4: Run full suite**

```bash
pytest -q
```

Expected: `95 passed` — no regressions

- [ ] **Step 5: Commit**

```bash
git add scripts/create_handoff.py handoff/start_next_session_prompt.md
git commit -m "feat(scripts): add create_handoff.py and startup prompt template"
```

---

## Task 4: Bot commands /status, /next, /git, /handoff

**Files:**
- Modify: `app/commands.py`
- Modify: `app/bot.py`

- [ ] **Step 1: Add 4 command handlers to `app/commands.py`**

Add these four functions at the end of `app/commands.py`, after the existing `cmd_budget` function:

```python
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app import database
    state = database.read_latest_agent_state()
    if not state:
        await update.message.reply_text(
            "No state recorded yet.\n"
            "Run: python scripts/notify_me.py progress \"message\""
        )
        return
    ts = (state.get("timestamp") or "")[:16].replace("T", " ")
    lines = [f"📊 Status — {ts} UTC\n"]
    if state.get("current_module"):
        lines.append(f"Module: {state['current_module']}")
    if state.get("current_task"):
        lines.append(f"Task: {state['current_task']}")
    if state.get("progress_message"):
        lines.append(f"Progress: {state['progress_message']}")
    lines.append(f"Blocker: {state.get('blocker') or 'None'}")
    if state.get("git_summary"):
        first_line = state["git_summary"].splitlines()[0]
        lines.append(f"Git: {first_line}")
    await update.message.reply_text("\n".join(lines))


async def cmd_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app import database
    state = database.read_latest_agent_state()
    if not state or not state.get("next_task"):
        await update.message.reply_text("No next task recorded yet.")
        return
    ts = (state.get("timestamp") or "")[:16].replace("T", " ")
    await update.message.reply_text(
        f"⏭ Next task:\n{state['next_task']}\n(Recorded: {ts} UTC)"
    )


async def cmd_git(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app import database
    state = database.read_latest_agent_state()
    if not state or not state.get("git_summary"):
        await update.message.reply_text("No git summary recorded yet.")
        return
    ts = (state.get("timestamp") or "")[:16].replace("T", " ")
    await update.message.reply_text(
        f"🔀 Git summary:\n{state['git_summary']}\n(Recorded: {ts} UTC)"
    )


async def cmd_handoff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app import database
    state = database.read_latest_agent_state(status_type="handoff")
    if not state:
        await update.message.reply_text(
            "No handoff recorded yet.\n"
            "Run: python scripts/create_handoff.py"
        )
        return
    ts = (state.get("timestamp") or "")[:16].replace("T", " ")
    lines = [f"🔄 Last handoff: {ts} UTC\n"]
    if state.get("current_module"):
        lines.append(f"Module: {state['current_module']}")
    if state.get("next_task"):
        lines.append(f"Next: {state['next_task']}")
    lines.append("Read handoff/latest.md for full startup prompt.")
    await update.message.reply_text("\n".join(lines))
```

- [ ] **Step 2: Register the 4 new commands in `app/bot.py`**

Replace the entire contents of `app/bot.py` with:

```python
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from app import config
from app.commands import (
    handle_message,
    cmd_start, cmd_help, cmd_today, cmd_week,
    cmd_month, cmd_income, cmd_undo, cmd_summary, cmd_budget,
    cmd_status, cmd_next, cmd_git, cmd_handoff,
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
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("next", cmd_next))
    application.add_handler(CommandHandler("git", cmd_git))
    application.add_handler(CommandHandler("handoff", cmd_handoff))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    return application
```

- [ ] **Step 3: Run full test suite**

```bash
cd /Users/arryawillems/finance-lifeos && source .venv/bin/activate && pytest -q
```

Expected: `95 passed` — no regressions (bot command handlers are not unit tested separately as they require PTB async fixtures not used in this codebase)

- [ ] **Step 4: Smoke test locally**

```bash
LOCAL_POLLING=true python run_polling.py &
sleep 3
# Send /status to your bot from phone
# Expected reply: "No state recorded yet. Run: python scripts/notify_me.py..."
# Then:
python scripts/notify_me.py progress "Testing /status command"
# Send /status again — should now show the progress message
kill %1
```

- [ ] **Step 5: Commit**

```bash
git add app/commands.py app/bot.py
git commit -m "feat(bot): add /status /next /git /handoff commands"
```

---

## Task 5: Docs and rules updates

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `docs/current-status.md`

- [ ] **Step 1: Add Autonomous Workflow Rules to `CLAUDE.md`**

Add this section after the existing `## Core Rules` section in `CLAUDE.md`:

```markdown
## Autonomous Workflow Rules

### Notify via Telegram
Run `python scripts/notify_me.py <type> "<message>"` whenever:
- A decision is needed from the user → `notify_me.py decision "..." "A:..." "B:..."`
- Manual setup is required (Railway env vars, etc.) → `notify_me.py action "..."`
- Deployment approval is needed → `notify_me.py action "..."`
- Tests fail unexpectedly → `notify_me.py error "..."`
- A module or task completes → `notify_me.py complete "..."`
- A blocker occurs → `notify_me.py error "Blocked: ..."`
- Session/context/token limit is nearing → run `create_handoff.py` immediately

### Create Handoff Before Stopping
Always run `python scripts/create_handoff.py` before ending a session or when tokens are running low. This writes `handoff/latest.md`, updates `handoff/start_next_session_prompt.md`, writes state to PostgreSQL, and sends a Telegram notification.

### Never
- Read, print, or commit `.env` content or secrets via any tool or notification
- Delete files without explicit user approval
- Modify the `transactions` table schema
- Rebuild a module marked DONE in `docs/current-status.md`
- Access files outside the repo root
- Skip tests before committing a completed feature
```

- [ ] **Step 2: Add Autonomous Claude Workflow section to `README.md`**

Add this section before the existing `## Architecture` section in `README.md`:

```markdown
## Autonomous Claude Workflow

Claude Code can work autonomously on this repo while you supervise from Telegram.

### How it works

1. Start Claude Code with full repo access (`bypassPermissions` mode set in `.claude/settings.local.json`)
2. Claude works on tasks, using `scripts/notify_me.py` to push updates
3. You receive Telegram notifications and reply when decisions are needed
4. When Claude's session ends, it runs `scripts/create_handoff.py`
5. You receive a handoff notification, switch Claude accounts, and paste the startup prompt

### Supervision commands (send from Telegram)

| Command | What it shows |
|---------|--------------|
| `/status` | Current module, task, progress, blockers |
| `/next` | Recommended next task |
| `/git` | Recent commits summary |
| `/handoff` | Last session handoff info |

### Notification types Claude sends

| Script | When |
|--------|------|
| `notify_me.py progress "..."` | Task started or milestone hit |
| `notify_me.py decision "..." "A:..." "B:..."` | Choice needed from you |
| `notify_me.py action "..."` | Manual step needed (Railway, etc.) |
| `notify_me.py error "..."` | Test failure or blocker |
| `notify_me.py complete "..."` | Module or task finished |
| `create_handoff.py` | Session ending, switch accounts |

### Switching accounts

When you get a handoff notification:
1. `claude logout`
2. `claude login` (new account)
3. Open this repo
4. Paste the contents of `handoff/start_next_session_prompt.md` as your first message
```

- [ ] **Step 3: Update `docs/current-status.md` Module 1.4 status**

Find the Module 1.4 section and replace:

```markdown
## Module 1.4 — Agent Control Layer + Notifications

**Status: 🔲 NOT STARTED**

Nothing built. See `docs/roadmap.md` for spec.
```

With:

```markdown
## Module 1.4 — Agent Control Layer + Notifications

**Status: 🔶 IN PROGRESS**

### What Works
- `app/telegram.py` — `send_telegram_message(text) -> bool` reusable utility
- `scripts/notify_me.py` — typed notification CLI (progress/decision/action/error/complete/handoff)
- `scripts/create_handoff.py` — comprehensive handoff generator
- `scripts/handoff_notify.py` — basic handoff (legacy, preserved)
- `agent_state` PostgreSQL table — live state written by scripts, read by bot
- Bot commands: `/status`, `/next`, `/git`, `/handoff` — read from PostgreSQL, work from Railway
- `handoff/start_next_session_prompt.md` — static startup prompt for next session

### What's Left (for future sessions)
- Inbound command authentication (only respond to TELEGRAM_OWNER_CHAT_ID)
- `/resolve` command to mark decisions/actions as resolved
- Proactive notifications (e.g., daily summary)
```

- [ ] **Step 4: Run full test suite one final time**

```bash
pytest -q
```

Expected: `95 passed`

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md README.md docs/current-status.md
git commit -m "docs: add autonomous workflow rules and supervision guide"
```

---

## Final Verification

- [ ] **Confirm test count**

```bash
pytest -v | tail -5
```

Expected: `95 passed, 0 failed`

- [ ] **Confirm all new files exist**

```bash
ls scripts/notify_me.py scripts/create_handoff.py \
   handoff/start_next_session_prompt.md \
   tests/test_agent_state.py tests/test_notify.py
```

- [ ] **Confirm git log**

```bash
git log --oneline -6
```

Expected (newest first):
```
docs: add autonomous workflow rules and supervision guide
feat(bot): add /status /next /git /handoff commands
feat(scripts): add create_handoff.py and startup prompt template
feat(scripts): add notify_me.py typed notification CLI
feat(db): add agent_state table with write/read functions
```

- [ ] **End-to-end smoke test**

```bash
# 1. Send a progress notification
python scripts/notify_me.py progress "Agent control layer complete"
# Expected: Telegram message received on phone

# 2. Check /status from phone
# Expected: shows "Agent control layer complete"

# 3. Generate handoff
python scripts/create_handoff.py
# Expected: handoff/latest.md written, Telegram handoff message received

# 4. Check /handoff from phone
# Expected: shows last handoff timestamp and next task
```
