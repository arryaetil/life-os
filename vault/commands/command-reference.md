# Command Reference

---

## Telegram Bot Commands

All commands are owner-only (gated by `TELEGRAM_OWNER_CHAT_ID`).

### Finance (Module 1.0)

| Command | Description |
|---------|-------------|
| `/start` | Welcome and usage guide |
| `/help` | Example messages |
| `/today` | Today's transactions |
| `/week` | Weekly spend vs budget |
| `/month` | Monthly breakdown by category |
| `/income` | Monthly income summary |
| `/undo` | Mark last transaction as undone |
| `/summary` | Compact weekly + monthly overview |
| `/budget` | Weekly budget ASCII progress bar |

### Net Worth (Module 1.1)

| Command | Description |
|---------|-------------|
| `/networth` | Latest snapshot with full breakdown |
| `/networth_history` | Last 5 snapshots with running delta |
| `/goal` | €25K and €30K goal progress with ASCII bars |

### Agent Control (Module 1.4)

| Command | Description |
|---------|-------------|
| `/status` | Current module, task, progress, blockers |
| `/next` | Recommended next task |
| `/git` | Recent commits summary |
| `/handoff` | Last session handoff info |

### Natural Language

Send any natural message to log a transaction:
- `14 kebab` → €14 expense, Food
- `+500 salary` → €500 income
- `net worth cash 2k investments 8k` → net worth snapshot

---

## Script Commands

### notify_me.py

```bash
python scripts/notify_me.py progress "Message"
python scripts/notify_me.py decision "Question" "A: option A" "B: option B"
python scripts/notify_me.py action "Manual step needed"
python scripts/notify_me.py error "Failure description"
python scripts/notify_me.py complete "What was finished"
```

### create_handoff.py

```bash
python scripts/create_handoff.py
```

Writes `handoff/latest.md`, updates `handoff/start_next_session_prompt.md`, writes PostgreSQL state, sends Telegram notification.

---

## Development Commands

```bash
# Run all tests
pytest

# Run specific file
pytest tests/test_networth_parser.py -v

# Run local bot (polling mode)
LOCAL_POLLING=true python run_polling.py

# Run dashboard locally
uvicorn app.dashboard:app --reload --port 8000

# Register webhook (Railway, run once after first deploy)
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<RAILWAY_URL>/webhook&secret_token=<SECRET>"
```

---

## Claude Workflow Commands

### Start a session

Read these files in order:
1. `CLAUDE.md`
2. `vault/context/LifeOS.md`
3. `vault/context/Current_Priorities.md`
4. `vault/hubs/Architecture.md`
5. `vault/projects/finance-lifeos.md`
6. `vault/sessions/recent-sessions.md`
7. `handoff/latest.md`

### End a session

```bash
pytest                              # verify tests pass
python scripts/create_handoff.py    # write handoff + notify
```

Then update `vault/sessions/recent-sessions.md`.

---

## Notification Types Reference

| Type | When to use |
|------|-------------|
| `progress` | Task started, milestone reached |
| `decision` | Choice needed from user |
| `action` | Manual step needed (Railway, env vars) |
| `error` | Test failure, blocker, unexpected issue |
| `complete` | Module or significant task finished |
