# Agent Control Hub

[[LifeOS]] → Module 1.4

---

## What Is Built (Partial)

**Supervision infrastructure for Claude autonomous work.**

- `app/telegram.py` — `send_telegram_message(text) -> bool` utility
- `scripts/notify_me.py` — typed notification CLI
- `scripts/create_handoff.py` — comprehensive handoff generator
- `agent_state` PostgreSQL table — live state written by scripts, read by bot
- Bot commands: `/status`, `/next`, `/git`, `/handoff`
- `app/auth.py` — `is_owner()` + `owner_only()` handler wrapper

---

## Owner-Only Auth

All bot handlers are wrapped with `owner_only()` from `app/auth.py`. Only messages from `TELEGRAM_OWNER_CHAT_ID` are processed. All others receive "Unauthorized."

```python
# Pattern used in app/bot.py
application.add_handler(CommandHandler("today", owner_only(cmd_today)))
```

---

## Notification Workflow

Claude pushes updates to user via Telegram during autonomous work:

```bash
python scripts/notify_me.py progress "Starting net worth dashboard"
python scripts/notify_me.py decision "Choose DB approach" "A: append-only" "B: update-in-place"
python scripts/notify_me.py action "Add OPENAI_API_KEY to Railway env vars"
python scripts/notify_me.py error "Tests failing: test_networth_db.py"
python scripts/notify_me.py complete "Module 1.1 done. 150 tests passing."
```

Each call writes to `agent_state` table AND sends Telegram message.

---

## Telegram Supervision Commands

| Command | Data source | What it shows |
|---------|-------------|--------------|
| `/status` | `agent_state` DB | Current module, task, progress, blockers |
| `/next` | `agent_state` DB | Recommended next task |
| `/git` | `agent_state` DB | Recent commits summary |
| `/handoff` | `agent_state` DB | Last session handoff info |

---

## Session Handoff Process

When Claude's session nears token limit:

1. `python scripts/create_handoff.py` — writes `handoff/latest.md`, updates `handoff/start_next_session_prompt.md`, writes PostgreSQL state, sends Telegram notification
2. User receives Telegram message with continuation instructions
3. User runs `claude logout` → `claude login` (new account)
4. User pastes `handoff/start_next_session_prompt.md` as first message in new session

---

## What's Left to Build

- `/resolve` command to mark decisions/actions as resolved
- Proactive scheduled notifications (Monday weekly summary, 1st of month review, Sunday NW reminder)
- `TELEGRAM_CHAT_ID` env var for push messages (distinct from `TELEGRAM_OWNER_CHAT_ID`)
