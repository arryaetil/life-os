# CLAUDE.md — LifeOS Autonomous Work Protocol

## Purpose

This file is the **primary contract** for any AI agent (Claude, ChatGPT, or other) working in this repository. Read this before touching any file. The repo is the single source of truth; sessions may rotate when tokens run out — this protocol ensures seamless continuation.

---

## Mandatory Reading Order (Every Session)

1. `CLAUDE.md` (this file)
2. `docs/architecture.md` — system design, data model, module boundaries
3. `docs/current-status.md` — what works, what is broken, what is stubbed
4. `handoff/latest.md` — last session's context, next exact task, warnings

If any of these files is missing or stale (last updated >2 sessions ago), regenerate it before doing feature work.

---

## Core Rules

### Never Rebuild Working Features
- Check `docs/current-status.md` before implementing anything.
- If a feature is marked **DONE**, do not rewrite it, refactor it, or "improve" it unless explicitly tasked.
- When in doubt, read the code and run the tests first.

### Preserve Tests
- The test suite (`tests/`) has 74 passing tests. Never reduce that count.
- Before ending a session, run `pytest` and ensure all tests still pass.
- New features must come with new tests.

### Work Module by Module
- Complete one module (or sub-module) before starting another.
- Never leave a module half-implemented at session end.
- Stub unfinished work with a clear `# TODO(module-X.Y): <description>` comment.

### Commit Stable Changes
- Commit after each completed, tested feature or sub-task.
- Commit message format: `<type>(<scope>): <description>` — e.g. `feat(1.1): add net worth table`
- Never commit broken tests or un-runnable code.

### Handoff Before Ending
- Before ending a session (or when tokens are running low), write `handoff/latest.md` using the template below.
- The handoff file is the only thing the next session can rely on beyond the code itself.

---

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

---

## Handoff Template

When ending a session, write `handoff/latest.md` with exactly this structure:

```markdown
# Handoff — <date YYYY-MM-DD>

## What Was Done
- Bullet list of completed work this session

## Files Changed
- path/to/file.py — what changed

## Current State
One paragraph describing the repo state right now.

## Bugs / Blockers
- Known issues or blockers, or "None"

## Next Exact Task
Step-by-step instructions for the next agent to continue work.

## Commands to Run
```bash
# Commands the next agent should run to verify state
pytest
uvicorn app.dashboard:app --reload
```

## Environment Variables Needed
- TELEGRAM_BOT_TOKEN
- OPENAI_API_KEY
- DATABASE_URL
- WEBHOOK_BASE_URL
- TELEGRAM_WEBHOOK_SECRET
- WEEKLY_BUDGET (default: 90)
- LOCAL_POLLING (true for local dev)

## Do-Not-Touch Warnings
- Files/features that must not be modified
```

---

## Environment Setup

```bash
# From repo root
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in .env values
```

### Local Dev (no webhook needed)
```bash
LOCAL_POLLING=true python run_polling.py   # Telegram bot
uvicorn app.dashboard:app --reload         # Dashboard at http://localhost:8000
```

### Run Tests
```bash
pytest                  # All tests
pytest tests/test_parser.py -v  # Specific file
```

### Deploy
- Deployment is on Railway. Push to `master` triggers auto-deploy.
- Railway auto-sets `DATABASE_URL` from the attached PostgreSQL plugin.
- Register webhook once after first deploy:
  ```bash
  curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<RAILWAY_URL>/webhook&secret_token=<SECRET>"
  ```

---

## Module Registry

| Module | Name | Status |
|--------|------|--------|
| 1.0 | Finance cashflow tracker | DONE |
| 1.1 | Net Worth tracker | NOT STARTED |
| 1.2 | Portfolio/accounts tracker | NOT STARTED |
| 1.3 | Screenshot/CSV portfolio import | NOT STARTED |
| 1.4 | Agent control layer + Telegram notifications | NOT STARTED |
| 2.0 | Goals tracker | NOT STARTED |
| 3.0 | Health/workout tracker | NOT STARTED |
| 4.0 | Unified LifeOS dashboard | NOT STARTED |

Update this table as modules are completed.

---

## Repo Layout

```
finance-lifeos/
  app/
    config.py        — env vars
    utils.py         — currency, date helpers
    parser.py        — AI parser (GPT-4o-mini) + regex fallback
    categories.py    — transaction categorisation
    budget.py        — weekly/monthly calculations
    database.py      — PostgreSQL via SQLAlchemy
    commands.py      — Telegram bot command handlers
    bot.py           — PTB Application factory
    dashboard.py     — FastAPI app (webhook + dashboard routes)
    templates/       — Jinja2 HTML templates
    static/          — CSS
  tests/             — 74 passing tests
  docs/              — architecture, roadmap, status
  handoff/           — session handoff files
  run_polling.py     — local dev polling runner
  Procfile           — Railway start command
  requirements.txt
  .env.example
```

---

## Live URL

https://lifeos-aw.up.railway.app

---

## Contact / Owner

Arrya Willems — arrya.willems@gmail.com
