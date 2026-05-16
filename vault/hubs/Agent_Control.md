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
- `app/agent_control.py` — `is_agent_reply(text)` detects A/B/C/DONE/yes/no/approve/reject/continue/stop
- Reply routing in `handle_message()` — agent replies routed before finance parsing
- `database.read_pending_action()` — queries latest unresolved action-requiring state
- `database.resolve_agent_state(id)` — marks a pending state resolved when user replies

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

## Conversational AI Layer (v1)

The bot handles four intents via `app/intent_classifier.py` + `app/ai_agent.py`:

**Routing priority in `handle_message`:**
1. Agent-control reply (A/B/C/DONE/yes/no) → resolve pending decision
2. Net worth update (NW keywords + amount) → save snapshot
3. `classify_intent()` → lifeos_question / action_request / finance_transaction / unknown

**LifeOS questions** → `app/ai_agent.answer_lifeos_question()`
- Loads compressed vault context pack (`app/vault_context.py`, max 8000 chars)
- Injects live financial data if question is finance-related
- Calls OpenAI GPT-4o-mini; graceful fallback if no key

**Action requests** → `app/ai_agent.propose_action()`
- Returns a proposal — never executes directly
- Asks for A/B confirmation
- Stores pending decision in `agent_state`

**Context pack files** (loaded by `app/vault_context.py`):
CLAUDE.md, vault/context/LifeOS.md, Current_Priorities.md, User_Profile.md,
vault/hubs/Architecture.md, Finance.md, Agent_Control.md,
vault/projects/finance-lifeos.md, vault/sessions/recent-sessions.md, handoff/latest.md

---

## What's Left to Build

- `/resolve` command as an alternative to inline reply routing (optional)
- Proactive scheduled notifications (Monday weekly summary, 1st of month review)

## Reply Routing

Agent-control replies are recognized before finance parsing. Recognized tokens (case-insensitive, exact match):

```
a, b, c, d, yes, no, done, approve, approved, reject, continue, stop
```

When the bot receives one of these:
1. Checks for an unresolved `agent_state` row with `requires_user_action=True`
2. If found: resolves it, sends "Decision received: X." or "Manual action marked as done."
3. If not found: sends "No active agent decision is waiting."

## Completion vs Handoff

| Scenario | Command | Telegram sent? |
|----------|---------|---------------|
| Task finished, session continues | `notify_me.py complete "..."` | ✅ "🎉 Complete: ..." |
| Update files silently | `create_handoff.py --silent` | ❌ Nothing |
| Session ending, switch account | `create_handoff.py` | ✅ "🔄 Session handoff needed" |
