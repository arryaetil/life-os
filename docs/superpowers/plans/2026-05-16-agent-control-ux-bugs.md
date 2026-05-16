# Agent Control UX Bugs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two UX bugs: (1) task completion incorrectly triggers "session handoff needed" notification, and (2) agent-control replies (A/B/C/DONE) are parsed as expense transactions.

**Architecture:** Three-layer fix — (a) add `--silent` flag to `create_handoff.py` so it can update files without sending the disruptive Telegram notification; (b) add `app/agent_control.py` with `is_agent_reply()` detection; (c) update `handle_message()` in `app/commands.py` to route agent replies before finance parsing, with DB-backed pending-action resolution.

**Tech Stack:** Python 3.13, python-telegram-bot 20.7, SQLAlchemy 2.0, pytest 8.2.1

**Baseline:** 179 tests passing. Never reduce this count.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `app/agent_control.py` | Create | `is_agent_reply(text)` — pure function, no side effects |
| `app/database.py` | Modify | `read_pending_action()` + `resolve_agent_state(state_id)` |
| `app/commands.py` | Modify | `handle_agent_reply()` + updated `handle_message()` routing |
| `scripts/create_handoff.py` | Modify | Add `--silent` flag; silent = write files but skip Telegram |
| `tests/test_agent_control.py` | Create | Tests for `is_agent_reply` |
| `tests/test_agent_state.py` | Modify | Tests for `read_pending_action`, `resolve_agent_state` |
| `tests/test_message_routing.py` | Create | Integration tests for message routing |
| `tests/test_create_handoff.py` | Create | Test `--silent` flag behavior |
| `docs/autonomous-session-protocol.md` | Modify | Clarify completion vs handoff, add reply routing section |
| `vault/hubs/Agent_Control.md` | Modify | Update with new reply routing + resolve capability |
| `CLAUDE.md` | Modify | Completion workflow: use `--silent`, don't send handoff on task complete |

---

## Task 1: Create `app/agent_control.py` — `is_agent_reply()` + tests

**Files:**
- Create: `app/agent_control.py`
- Create: `tests/test_agent_control.py`

- [ ] **Step 1: Write tests first**

Create `tests/test_agent_control.py`:

```python
from app.agent_control import is_agent_reply


def test_single_letters_are_replies():
    for letter in ("A", "B", "C", "D", "a", "b", "c", "d"):
        assert is_agent_reply(letter) is True, f"Expected {letter!r} to be a reply"


def test_done_case_insensitive():
    assert is_agent_reply("DONE") is True
    assert is_agent_reply("done") is True
    assert is_agent_reply("Done") is True


def test_yes_no_are_replies():
    assert is_agent_reply("yes") is True
    assert is_agent_reply("no") is True
    assert is_agent_reply("YES") is True


def test_approve_variants():
    assert is_agent_reply("approve") is True
    assert is_agent_reply("approved") is True
    assert is_agent_reply("reject") is True


def test_continue_stop():
    assert is_agent_reply("continue") is True
    assert is_agent_reply("stop") is True


def test_expense_message_is_not_reply():
    assert is_agent_reply("14 kebab") is False
    assert is_agent_reply("spent 8.50 coffee") is False
    assert is_agent_reply("net worth 15000") is False


def test_whitespace_is_trimmed():
    assert is_agent_reply("  A  ") is True
    assert is_agent_reply("  done  ") is True


def test_empty_string_is_not_reply():
    assert is_agent_reply("") is False


def test_partial_match_is_not_reply():
    assert is_agent_reply("ab") is False
    assert is_agent_reply("donezo") is False


def test_sentence_starting_with_reply_token_is_not_reply():
    assert is_agent_reply("A great idea") is False
    assert is_agent_reply("yes please") is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_agent_control.py -v 2>&1 | tail -5
```

Expected: `ModuleNotFoundError: No module named 'app.agent_control'`

- [ ] **Step 3: Create `app/agent_control.py`**

```python
"""Agent-control reply detection for the Telegram bot."""

_AGENT_REPLY_TOKENS = frozenset({
    "a", "b", "c", "d",
    "yes", "no",
    "done",
    "approve", "approved",
    "reject",
    "continue",
    "stop",
})


def is_agent_reply(text: str) -> bool:
    """Return True if text is a recognized agent-control reply token.

    Matches exactly (after stripping whitespace and lowercasing).
    Partial matches like 'A great idea' return False.
    """
    return text.strip().lower() in _AGENT_REPLY_TOKENS
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_agent_control.py -v 2>&1 | tail -15
```

Expected: All 10 tests PASS.

- [ ] **Step 5: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -3
```

Expected: 189 passed (179 + 10 new).

- [ ] **Step 6: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add app/agent_control.py tests/test_agent_control.py && git commit -m "feat(1.4): add agent_control.is_agent_reply — detects A/B/C/DONE/yes/no/etc"
```

---

## Task 2: Add `read_pending_action()` + `resolve_agent_state()` to `app/database.py` + tests

**Files:**
- Modify: `app/database.py`
- Modify: `tests/test_agent_state.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_agent_state.py`:

```python
def test_read_pending_action_returns_none_when_empty():
    assert db.read_pending_action() is None


def test_read_pending_action_returns_none_when_resolved():
    db.write_agent_state({
        "status_type": "decision",
        "requires_user_action": True,
        "resolved": True,
    })
    assert db.read_pending_action() is None


def test_read_pending_action_returns_latest_unresolved():
    db.write_agent_state({
        "status_type": "decision",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": "first question",
    })
    db.write_agent_state({
        "status_type": "manual_action",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": "second question",
    })
    result = db.read_pending_action()
    assert result is not None
    assert result["progress_message"] == "second question"


def test_read_pending_action_ignores_progress_rows():
    db.write_agent_state({
        "status_type": "progress",
        "requires_user_action": False,
        "resolved": False,
    })
    assert db.read_pending_action() is None


def test_resolve_agent_state_marks_row_resolved():
    db.write_agent_state({
        "status_type": "decision",
        "requires_user_action": True,
        "resolved": False,
    })
    pending = db.read_pending_action()
    assert pending is not None
    db.resolve_agent_state(pending["id"])
    assert db.read_pending_action() is None


def test_resolve_agent_state_only_affects_target_row():
    db.write_agent_state({
        "status_type": "decision",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": "first",
    })
    db.write_agent_state({
        "status_type": "manual_action",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": "second",
    })
    first = db.read_latest_agent_state(status_type="decision")
    db.resolve_agent_state(first["id"])
    # second should still be pending
    still_pending = db.read_pending_action()
    assert still_pending is not None
    assert still_pending["progress_message"] == "second"
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_agent_state.py -v 2>&1 | tail -10
```

Expected: FAIL — `AttributeError: module 'app.database' has no attribute 'read_pending_action'`

- [ ] **Step 3: Add functions to `app/database.py`**

At the end of `app/database.py`, append these two functions (they use `update` which is already imported from sqlalchemy):

```python
_PENDING_ACTION_TYPES = ("decision", "manual_action", "error", "handoff")


def read_pending_action() -> dict | None:
    """Return the latest unresolved agent_state row that requires user action."""
    with _engine.connect() as conn:
        q = (
            select(agent_state)
            .where(
                agent_state.c.requires_user_action == True,
                agent_state.c.resolved == False,
                agent_state.c.status_type.in_(_PENDING_ACTION_TYPES),
            )
            .order_by(desc(agent_state.c.id))
            .limit(1)
        )
        result = conn.execute(q)
        row = result.fetchone()
        return dict(row._mapping) if row else None


def resolve_agent_state(state_id: int) -> None:
    """Mark a specific agent_state row as resolved=True."""
    with _engine.connect() as conn:
        conn.execute(
            update(agent_state)
            .where(agent_state.c.id == state_id)
            .values(resolved=True)
        )
        conn.commit()
```

Note: `update` is already imported at the top of `database.py` — verify with `grep "from sqlalchemy" app/database.py`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_agent_state.py -v 2>&1 | tail -15
```

Expected: All tests PASS (existing 6 + new 6).

- [ ] **Step 5: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -3
```

Expected: 195 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add app/database.py tests/test_agent_state.py && git commit -m "feat(1.4): add read_pending_action and resolve_agent_state to database"
```

---

## Task 3: Update `app/commands.py` — agent reply routing + tests

**Files:**
- Modify: `app/commands.py`
- Create: `tests/test_message_routing.py`

- [ ] **Step 1: Write failing routing tests**

Create `tests/test_message_routing.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_update(text: str):
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


async def test_reply_a_no_pending_returns_no_active_decision():
    from app.commands import handle_message
    update = _make_update("A")
    with patch("app.database.read_pending_action", return_value=None):
        await handle_message(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "No active agent decision" in reply
    assert "couldn't find an amount" not in reply


async def test_reply_done_no_pending_returns_no_active_decision():
    from app.commands import handle_message
    update = _make_update("DONE")
    with patch("app.database.read_pending_action", return_value=None):
        await handle_message(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "No active agent decision" in reply
    assert "couldn't find an amount" not in reply


async def test_reply_b_with_pending_decision_resolves_and_confirms():
    from app.commands import handle_message
    pending = {
        "id": 42,
        "status_type": "decision",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": "Which DB?",
    }
    update = _make_update("B")
    with patch("app.database.read_pending_action", return_value=pending), \
         patch("app.database.resolve_agent_state") as mock_resolve:
        await handle_message(update, MagicMock())
    mock_resolve.assert_called_once_with(42)
    reply = update.message.reply_text.call_args[0][0]
    assert "Decision received: B" in reply


async def test_reply_done_with_pending_manual_action_confirms_done():
    from app.commands import handle_message
    pending = {
        "id": 7,
        "status_type": "manual_action",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": "Add key to Railway",
    }
    update = _make_update("done")
    with patch("app.database.read_pending_action", return_value=pending), \
         patch("app.database.resolve_agent_state"):
        await handle_message(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "Manual action marked as done" in reply


async def test_normal_expense_still_parsed():
    from app.commands import handle_message
    update = _make_update("14 kebab")
    parsed = {
        "timestamp": "2026-05-16T10:00:00+00:00",
        "date": "2026-05-16",
        "week_start": "2026-05-13",
        "month": "2026-05",
        "type": "Expense",
        "amount": 14.0,
        "description": "kebab",
        "category": "Food",
        "is_impulse": False,
    }
    with patch("app.parser.parse_message", return_value=parsed), \
         patch("app.categories.get_category", return_value="Food"), \
         patch("app.database.append_transaction", return_value=1), \
         patch("app.database.get_all_transactions", return_value=[]), \
         patch("app.budget.calculate_weekly_status", return_value={
             "weekly_spent": 14.0, "weekly_budget": 90.0,
             "remaining": 76.0, "pct_used": 15.6, "week_start": "2026-05-13",
         }):
        await handle_message(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "kebab" in reply
    assert "Got it" in reply


async def test_yes_reply_not_parsed_as_expense():
    from app.commands import handle_message
    update = _make_update("yes")
    with patch("app.database.read_pending_action", return_value=None):
        await handle_message(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "No active agent decision" in reply


async def test_c_reply_with_pending_error_state_resolves():
    from app.commands import handle_message
    pending = {
        "id": 99,
        "status_type": "error",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": "Tests failing",
    }
    update = _make_update("C")
    with patch("app.database.read_pending_action", return_value=pending), \
         patch("app.database.resolve_agent_state") as mock_resolve:
        await handle_message(update, MagicMock())
    mock_resolve.assert_called_once_with(99)
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_message_routing.py -v 2>&1 | tail -10
```

Expected: FAIL — `A` gets parsed as expense → "I couldn't find an amount".

- [ ] **Step 3: Update `app/commands.py`**

**Add import** at the top with the other imports:

```python
from app.agent_control import is_agent_reply
```

**Add `handle_agent_reply` function** — insert it just before the existing `_handle_net_worth_message` function:

```python
async def handle_agent_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    from app import database
    pending = database.read_pending_action()
    if pending is None:
        await update.message.reply_text(
            "No active agent decision is waiting. Use /status to see current state."
        )
        return
    database.resolve_agent_state(pending["id"])
    token = text.strip().upper()
    if pending["status_type"] == "manual_action":
        reply = "Manual action marked as done."
    else:
        reply = f"Decision received: {token}. I'll continue with that direction."
    await update.message.reply_text(reply)
```

**Update `handle_message`** — replace the first 3 lines of the function body:

Current:
```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if is_net_worth_message(text):
        await _handle_net_worth_message(update, context, text)
        return
    try:
```

Replace with:
```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if is_agent_reply(text):
        await handle_agent_reply(update, context, text)
        return
    if is_net_worth_message(text):
        await _handle_net_worth_message(update, context, text)
        return
    try:
```

- [ ] **Step 4: Run routing tests to verify they pass**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_message_routing.py -v 2>&1 | tail -15
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -3
```

Expected: 202 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add app/commands.py tests/test_message_routing.py && git commit -m "fix(1.4): route agent replies before finance parsing — A/B/C/DONE no longer trigger expense parser"
```

---

## Task 4: Add `--silent` flag to `create_handoff.py` + test

**Files:**
- Modify: `scripts/create_handoff.py`
- Create: `tests/test_create_handoff.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_create_handoff.py`:

```python
import sys
import importlib
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def _run_handoff(monkeypatch, tmp_path, extra_args=None):
    """Helper: run create_handoff.main() with mocked dependencies."""
    argv = ["create_handoff.py"] + (extra_args or [])
    monkeypatch.setattr(sys, "argv", argv)

    import create_handoff
    importlib.reload(create_handoff)

    with patch("app.telegram.send_telegram_message", return_value=True) as mock_tg, \
         patch("app.database.write_agent_state"), \
         patch("app.database.read_latest_agent_state", return_value=None), \
         patch("subprocess.run", return_value=MagicMock(stdout="abc123 commit", returncode=0)), \
         patch.object(create_handoff, "HANDOFF_PATH", tmp_path / "latest.md"), \
         patch.object(create_handoff, "STARTUP_PROMPT_PATH", tmp_path / "prompt.md"):
        create_handoff.main()

    return mock_tg


def test_silent_mode_skips_telegram(monkeypatch, tmp_path):
    mock_tg = _run_handoff(monkeypatch, tmp_path, extra_args=["--silent"])
    mock_tg.assert_not_called()


def test_normal_mode_sends_telegram(monkeypatch, tmp_path):
    mock_tg = _run_handoff(monkeypatch, tmp_path, extra_args=[])
    mock_tg.assert_called_once()


def test_silent_mode_still_writes_handoff_file(monkeypatch, tmp_path):
    _run_handoff(monkeypatch, tmp_path, extra_args=["--silent"])
    assert (tmp_path / "latest.md").exists()
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_create_handoff.py -v 2>&1 | tail -10
```

Expected: FAIL — `unrecognized arguments: --silent`

- [ ] **Step 3: Update `scripts/create_handoff.py`**

Add argparse and `--silent` flag. The current `main()` function has no argument parsing. Replace the entire `main()` function with:

```python
def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Generate session handoff files")
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Write handoff files and DB state but skip Telegram notification",
    )
    args = parser.parse_args()

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

    if args.silent:
        print("✓ Silent mode: handoff files written, Telegram notification skipped.")
        return

    sent = send_telegram_message(TELEGRAM_MESSAGE)
    if sent:
        print("✓ Telegram notification sent.")
    else:
        print("✗ Telegram notification failed (handoff files still written).")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_create_handoff.py -v 2>&1 | tail -10
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -3
```

Expected: 205 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add scripts/create_handoff.py tests/test_create_handoff.py && git commit -m "fix(1.4): add --silent flag to create_handoff.py — writes files without Telegram notification"
```

---

## Task 5: Update docs — autonomous-session-protocol.md, Agent_Control.md, CLAUDE.md

**Files:**
- Modify: `docs/autonomous-session-protocol.md`
- Modify: `vault/hubs/Agent_Control.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update `docs/autonomous-session-protocol.md`**

Read the file first, then make these targeted edits:

**Edit 1** — After the "Complete" section (the `notify_me.py complete` block), add a new "Completion vs Handoff" section:

```markdown
### Completion vs Handoff — Important Distinction

**Task complete** → use `notify_me.py complete`. The session continues.
**Session ending** → use `create_handoff.py`. Telegram sends "session handoff needed."

Do NOT run `create_handoff.py` after every task. Run it only when:
- Context / token limit is near
- Work must stop and continue in a new session
- Switching Claude accounts

To update handoff files without sending a disruptive Telegram notification:
```bash
python scripts/create_handoff.py --silent  # writes files, no Telegram
```
```

**Edit 2** — Add a new "Replying to Claude" section before "What Claude Does When It Needs a Decision":

```markdown
### Replying to Decisions and Manual Actions

When Claude sends a decision or manual action notification, reply directly in Telegram:

| Situation | Your reply |
|-----------|-----------|
| Decision with options A/B/C | Reply: `A`, `B`, or `C` |
| Manual action completed | Reply: `done` or `DONE` |
| Approve something | Reply: `approve` or `yes` |
| Reject something | Reply: `reject` or `no` |

The bot routes these replies before any finance parsing — they will NOT be interpreted as expenses.

If no decision is currently waiting:
> "No active agent decision is waiting. Use /status to see current state."
```

- [ ] **Step 2: Update `vault/hubs/Agent_Control.md`**

Read the file first, then make these targeted edits:

**Edit 1** — Update the bulleted list under "What Is Built (Partial)" to add:

```markdown
- `app/agent_control.py` — `is_agent_reply(text)` detects agent-control reply tokens
- Reply routing in `handle_message()` — A/B/C/DONE/yes/no routed before finance parsing
- `database.read_pending_action()` — queries latest unresolved action-requiring state
- `database.resolve_agent_state(id)` — marks a pending state resolved when user replies
```

**Edit 2** — Replace the "What's Left to Build" section:

```markdown
## What's Left to Build

- `/resolve` command as an alternative to inline reply routing (optional, for future convenience)
- Proactive scheduled notifications (Monday weekly summary, 1st of month review, Sunday NW reminder)

## Reply Routing

Agent-control replies are recognized before finance parsing:

```python
# Tokens recognized as agent replies (case-insensitive, exact match):
{"a", "b", "c", "d", "yes", "no", "done",
 "approve", "approved", "reject", "continue", "stop"}
```

When the bot receives one of these tokens:
1. Checks for an unresolved `agent_state` row with `requires_user_action=True`
2. If found: resolves it, sends confirmation
3. If not found: sends "No active agent decision is waiting"

## Completion vs Handoff

| Scenario | Script | Telegram sent? |
|----------|--------|---------------|
| Task finished, session continues | `notify_me.py complete "..."` | ✅ "🎉 Complete: ..." |
| Update files silently, no notification | `create_handoff.py --silent` | ❌ Nothing |
| Session ending, switch account | `create_handoff.py` | ✅ "🔄 Session handoff needed" |
```

- [ ] **Step 3: Update `CLAUDE.md`**

Read the file first, then make this targeted edit.

Find the "Create Handoff Before Stopping" section:

```
### Create Handoff Before Stopping
Always run `python scripts/create_handoff.py` before ending a session or when tokens are running low. This writes `handoff/latest.md`, updates `handoff/start_next_session_prompt.md`, writes state to PostgreSQL, and sends a Telegram notification.
```

Replace with:

```
### Create Handoff Before Stopping

**Completion vs handoff — these are different:**

- **Task complete, session continues** → `python scripts/notify_me.py complete "..."` only.
- **Session ending (tokens low, account switch needed)** → `python scripts/create_handoff.py` — writes handoff files AND sends "session handoff needed" Telegram notification.
- **Update handoff files without Telegram** → `python scripts/create_handoff.py --silent`.

Never run `create_handoff.py` (without `--silent`) after a normal task completion. It sends a disruptive "session handoff needed" notification that is misleading when the session is not actually ending.
```

- [ ] **Step 4: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -3
```

Expected: 205 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add docs/autonomous-session-protocol.md vault/hubs/Agent_Control.md CLAUDE.md && git commit -m "docs(1.4): document completion vs handoff distinction and agent reply routing"
```

---

## Task 6: Final verification + Telegram completion + commit

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -5
```

Expected: 205 passed (179 baseline + 26 new), 0 failed.

- [ ] **Step 2: Send Telegram completion notification (NOT handoff)**

```bash
cd /Users/arryawillems/finance-lifeos && python scripts/notify_me.py complete "Agent control UX bugs fixed. Reply routing live (A/B/C/DONE → no expense parse). --silent flag added to create_handoff.py. 205 tests passing."
```

- [ ] **Step 3: Update handoff files silently**

```bash
cd /Users/arryawillems/finance-lifeos && python scripts/create_handoff.py --silent
```

Expected: Files written, NO Telegram notification.

- [ ] **Step 4: Commit handoff if changed**

```bash
cd /Users/arryawillems/finance-lifeos && git add handoff/ && git diff --cached --quiet || git commit -m "docs(1.4): handoff after agent control UX fixes"
```

- [ ] **Step 5: Push**

```bash
cd /Users/arryawillems/finance-lifeos && git push origin master
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| Completion = "task completed", not "session handoff" | Task 4 (`--silent`), Task 5 (CLAUDE.md rule) |
| Handoff only when explicitly running create_handoff.py, context low, or session ending | Task 5 (docs) |
| Reply routing priority before finance parsing | Task 3 (`handle_message` update) |
| Recognize A/B/C/D/yes/no/done/approve/reject/approved/continue/stop as agent replies | Task 1 (`is_agent_reply`) |
| Agent replies NOT parsed as expenses | Task 3 (routing check) |
| If unresolved pending action: store response, mark resolved, send confirmation | Task 2 (`resolve_agent_state`), Task 3 (`handle_agent_reply`) |
| "Decision received: B. I'll continue." confirmation | Task 3 (`handle_agent_reply`) |
| "Manual action marked as done." confirmation | Task 3 (`handle_agent_reply`) |
| If no active decision: "No active agent decision is waiting." | Task 3 (`handle_agent_reply`) |
| Finance parsing only if not command, not agent reply, not net worth | Task 3 (routing order) |
| Tests: A/B/C don't trigger expense parser | Task 3 (`test_message_routing.py`) |
| Tests: DONE doesn't trigger expense parser | Task 3 (`test_message_routing.py`) |
| Tests: completion does not create handoff notification | Task 4 (`test_create_handoff.py::test_silent_mode_skips_telegram`) |
| Tests: unresolved decision can be resolved | Tasks 2+3 |
| Tests: normal expenses still work | Task 3 (`test_normal_expense_still_parsed`) |
| docs/autonomous-session-protocol.md updated | Task 5 |
| vault/hubs/Agent_Control.md updated | Task 5 |
| Telegram completion notification (not handoff) | Task 6 |
| Commit stable changes | All tasks |

**No gaps found.**

**Placeholder scan:** No TBD, no "similar to Task N", all code complete.

**Type consistency:**
- `is_agent_reply(text: str) -> bool` — defined in Task 1, imported and used in Task 3. ✓
- `read_pending_action() -> dict | None` — defined in Task 2, called in Task 3. ✓
- `resolve_agent_state(state_id: int) -> None` — defined in Task 2, called in Task 3. ✓
- `handle_agent_reply(update, context, text)` — defined and called in Task 3. ✓
- `create_handoff.py --silent` — defined in Task 4, referenced in Task 5 docs. ✓
