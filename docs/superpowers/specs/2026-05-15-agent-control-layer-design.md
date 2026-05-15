# Design: Agent Control Layer (Module 1.4 v1)

_Date: 2026-05-15_

## Overview

Build the minimum Agent Control Layer that allows Claude Code to work autonomously inside this repo while the user supervises from their phone via Telegram.

**Telegram = mobile control panel / notification layer**
**Claude Code = implementation/build agent**
**LifeOS repo/docs = persistent memory + source of truth**
**PostgreSQL = structured data layer**

AI accounts/sessions are temporary workers. The repo, docs, handoff files, and database are the permanent memory layer.

---

## Scope

**In scope:**
- `agent_state` PostgreSQL table for live state
- `scripts/notify_me.py` — typed notification CLI for Claude to run
- `scripts/create_handoff.py` — comprehensive handoff generator
- Four new bot commands: `/status`, `/next`, `/handoff`, `/git`
- `handoff/start_next_session_prompt.md` — static startup prompt for next session
- `CLAUDE.md` autonomous workflow rules
- `README.md` Autonomous Claude Workflow section
- `docs/current-status.md` update

**Out of scope:**
- Full conversational AI interface
- Agent orchestration / task queues
- RAG memory system
- Voice assistant
- Apple Health integration
- ChatGPT/MCP integration

---

## Data Layer

### `agent_state` table

Insert-only. Bot commands always read the most recent row. Scripts write rows.

```python
agent_state = Table(
    "agent_state", _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", String),              # ISO 8601 UTC: "2026-05-15T14:30:00+00:00"
    Column("status_type", String),            # progress|decision|manual_action|error|completion|handoff
    Column("severity", String),               # info|warning|error|critical
    Column("requires_user_action", String),   # "true"/"false" stored as string for SQLite compat
    Column("resolved", String),               # "true"/"false"
    Column("current_module", String),
    Column("current_task", String),
    Column("progress_message", String),
    Column("blocker", String),
    Column("next_task", String),
    Column("git_summary", String),
    Column("handoff_path", String),
    Column("startup_prompt_path", String),
    Column("metadata_json", String),          # JSON string for A/B/C options etc.
)
```

> Note: Boolean fields stored as String ("true"/"false") for SQLite/PostgreSQL compatibility, matching existing codebase patterns.

### DB functions in `app/database.py`

```python
def write_agent_state(fields: dict) -> None
def read_latest_agent_state() -> dict | None
```

- `write_agent_state` inserts a new row; fills `timestamp` automatically if not provided
- `read_latest_agent_state` returns `SELECT * FROM agent_state ORDER BY id DESC LIMIT 1` as a dict, or `None` if empty

---

## Scripts

### `scripts/notify_me.py`

Typed notification CLI. Claude runs this during autonomous work.

**Usage:**
```bash
python scripts/notify_me.py progress "Dashboard started"
python scripts/notify_me.py decision "Choose DB" "A: PostgreSQL" "B: Supabase"
python scripts/notify_me.py action "Add OPENAI_API_KEY to Railway"
python scripts/notify_me.py error "Tests failing in test_budget.py"
python scripts/notify_me.py complete "Net worth tracker done. 89 tests passing."
python scripts/notify_me.py handoff
```

**Each call:**
1. Formats a typed Telegram message
2. Sends via `app.telegram.send_telegram_message()`
3. Inserts a row into `agent_state` (auto-collects git summary)
4. Prints confirmation

**Telegram message formats:**

```
# progress
✅ Progress: Dashboard started

# decision
🤔 Decision needed:
Choose DB
A: PostgreSQL
B: Supabase
Reply with your choice.

# action (manual_action)
🔧 Manual action needed:
Add OPENAI_API_KEY to Railway
Reply DONE when complete.

# error
❌ Error:
Tests failing in test_budget.py

# complete (completion)
🎉 Complete:
Net worth tracker done. 89 tests passing.

# handoff
🔄 Session handoff needed.
Switch account now.
1. Run: claude logout
2. Run: claude login
3. Open this repo
4. Read handoff/latest.md
```

**`status_type` → `severity` + `requires_user_action` mapping:**

| status_type    | severity | requires_user_action |
|---------------|----------|---------------------|
| progress      | info     | false               |
| decision      | warning  | true                |
| manual_action | warning  | true                |
| error         | error    | true                |
| completion    | info     | false               |
| handoff       | warning  | true                |

### `scripts/create_handoff.py`

Comprehensive handoff generator. Replaces `scripts/handoff_notify.py` use for end-of-session handoffs (handoff_notify.py remains intact).

**Each call:**
1. Runs `git status --short` and `git log --oneline -5`
2. Reads last `agent_state` row for context
3. Writes `handoff/latest.md` (full CLAUDE.md template format)
4. Writes `handoff/start_next_session_prompt.md`
5. Inserts row into `agent_state` with `status_type=handoff`
6. Sends Telegram handoff notification

---

## Bot Commands

All four commands are read-only. Only scripts write to `agent_state`.

Registered in `app/bot.py`, implemented in `app/commands.py`.

### `/status`

Reads latest `agent_state` row.

```
📊 Status — 2026-05-15 14:30 UTC

Module: 1.1 Net Worth Tracker
Task: Adding net_worth_snapshots table
Progress: DB schema done, writing tests
Blocker: None
Git: feat(1.1): add net worth table
```

Fallback if no state: "No state recorded yet. Run `python scripts/notify_me.py` from your session."

### `/next`

Reads `next_task` from latest `agent_state` row.

```
⏭ Next task:
Implement /networth bot command and dashboard route.
(Recorded: 2026-05-15 14:30 UTC)
```

Fallback: "No next task recorded yet."

### `/git`

Reads `git_summary` from latest `agent_state` row.

```
🔀 Git summary:
feat(1.1): add net worth table
feat(telegram): add send_telegram_message
feat(config): add TELEGRAM_OWNER_CHAT_ID
(Recorded: 2026-05-15 14:30 UTC)
```

Fallback: "No git summary recorded yet."

### `/handoff`

Reads latest `agent_state` row where `status_type = handoff`.

```
🔄 Last handoff: 2026-05-15 14:30 UTC

Module: 1.1 Net Worth Tracker
Next: Implement dashboard route.
Read handoff/latest.md for full startup prompt.
```

Fallback: "No handoff recorded yet. Run `python scripts/create_handoff.py`."

---

## Static Files

### `handoff/start_next_session_prompt.md`

Static file committed to the repo. Paste as first message in a new Claude session.

```markdown
I'm continuing work on the LifeOS repo (finance-lifeos).

Please read in this order before doing anything:
1. CLAUDE.md
2. docs/architecture.md
3. docs/current-status.md
4. handoff/latest.md

Then confirm the current state, confirm all tests pass, and ask what to work on next.

Do NOT rebuild existing functionality.
Do NOT modify existing tests.
Do NOT change the database schema without explicit instruction.
```

---

## CLAUDE.md Additions

Add an **Autonomous Workflow Rules** section:

```markdown
## Autonomous Workflow Rules

### Notify via Telegram
Run `python scripts/notify_me.py <type> "<message>"` whenever:
- A decision is needed from the user
- Manual setup is required (Railway env vars, etc.)
- Deployment approval is needed
- Tests fail unexpectedly
- A module or task completes
- A blocker occurs
- Session/context/token limit is nearing

### Create Handoff Before Stopping
Always run `python scripts/create_handoff.py` before ending a session or when tokens are running low.

### Never
- Read, print, or commit `.env` content or secrets
- Delete files without explicit user approval
- Modify the `transactions` table schema
- Rebuild a module marked DONE in current-status.md
- Access files outside the repo root
```

---

## File Map

| File | Action |
|------|--------|
| `app/database.py` | Add `agent_state` table, `write_agent_state()`, `read_latest_agent_state()` |
| `app/commands.py` | Add `cmd_status`, `cmd_next`, `cmd_handoff`, `cmd_git` handlers |
| `app/bot.py` | Register `/status`, `/next`, `/handoff`, `/git` |
| `scripts/notify_me.py` | Create typed notification CLI |
| `scripts/create_handoff.py` | Create comprehensive handoff generator |
| `handoff/start_next_session_prompt.md` | Create static startup prompt |
| `CLAUDE.md` | Add Autonomous Workflow Rules section |
| `README.md` | Add Autonomous Claude Workflow section |
| `docs/current-status.md` | Mark Module 1.4 as IN PROGRESS |
| `tests/test_agent_state.py` | Unit tests for DB functions |
| `tests/test_notify.py` | Unit tests for notify_me.py logic |

---

## Testing

### `tests/test_agent_state.py`
- `test_write_and_read_agent_state` — write a row, read it back, verify fields
- `test_read_returns_none_when_empty` — empty table returns None
- `test_read_returns_latest` — multiple rows, read returns most recent

### `tests/test_notify.py`
- `test_progress_message_format` — progress type formats correctly
- `test_decision_message_format` — decision with options formats correctly
- `test_action_message_format` — manual_action formats correctly
- `test_error_message_format` — error type formats correctly
- `test_completion_message_format` — completion formats correctly
- `test_handoff_message_format` — handoff formats correctly
- `test_severity_mapping` — each status_type maps to correct severity
- `test_requires_action_mapping` — correct requires_user_action per type

---

## Autonomous Supervision Loop

```
Claude works autonomously
  → if fine: continue, run notify_me.py progress periodically
  → if decision needed: notify_me.py decision "..." "A:..." "B:..."
  → if manual setup needed: notify_me.py action "..."
  → if tests fail: notify_me.py error "..."
  → if complete: notify_me.py complete "..."
  → if session limit nearing:
      create_handoff.py  (writes files + DB + sends Telegram)
      → next account reads handoff/latest.md + start_next_session_prompt.md
```

User on phone sees all notifications. Sends `/status`, `/next`, `/git`, `/handoff` to check in anytime.
