# Handoff — 2026-05-15

## What Was Done

- Created autonomous work protocol for the repo
- Created `CLAUDE.md` — mandatory reading, rules, handoff template, env setup
- Created `docs/architecture.md` — system design, data model, module boundaries, naming conventions
- Created `docs/roadmap.md` — full roadmap for all 8 modules with acceptance criteria
- Created `docs/current-status.md` — ground-truth status of every module and feature
- Created `handoff/latest.md` (this file) — session handoff template established

No features were implemented. No files were changed other than documentation.

## Files Changed

- `CLAUDE.md` — created (new)
- `docs/architecture.md` — created (new)
- `docs/roadmap.md` — created (new)
- `docs/current-status.md` — created (new)
- `handoff/latest.md` — created (new, this file)

## Current State

Module 1.0 (Finance Cashflow Tracker) is fully complete and deployed. 74 tests pass. The Railway deployment is live at https://lifeos-aw.up.railway.app. The codebase is clean with no in-progress work. The repo now has a complete autonomous work protocol in place.

## Bugs / Blockers

None. All 74 tests pass. Deploy is healthy.

Minor non-blocking notes:
- `app/sheets.py` is a legacy stub (Google Sheets era) — not imported anywhere, harmless, can be deleted in a future cleanup pass
- Dashboard has no authentication — low priority until sharing externally

## Next Exact Task

**Start Module 1.1 — Net Worth Tracker**

1. Read `docs/architecture.md` section "Module 1.1" for the data model
2. Read `docs/roadmap.md` section "1.1" for acceptance criteria
3. Add `net_worth_snapshots` table to `app/database.py`:
   ```python
   net_worth_snapshots = Table(
       "net_worth_snapshots", _metadata,
       Column("id", Integer, primary_key=True, autoincrement=True),
       Column("date", String),          # YYYY-MM-DD
       Column("category", String),      # Cash|Savings|Investments|Property|Crypto|Debt
       Column("label", String),         # e.g. "ING Savings", "DeGiro"
       Column("amount", Float),         # negative for debt
   )
   ```
4. Add DB functions in `database.py`: `append_net_worth_snapshot()`, `get_net_worth_snapshots()`
5. Add bot commands in `commands.py`: `/networth`, `/snapshot`
6. Add dashboard route in `dashboard.py`: `GET /networth`
7. Create template `app/templates/networth.html`
8. Write tests in `tests/test_networth.py`
9. Update `docs/current-status.md` module 1.1 status to IN PROGRESS then DONE
10. Commit with message: `feat(1.1): add net worth tracker`

## Commands to Run

```bash
# Verify clean state before starting
pytest

# After implementing 1.1
pytest
pytest tests/test_networth.py -v

# Local dev
LOCAL_POLLING=true python run_polling.py
uvicorn app.dashboard:app --reload --port 8000
```

## Environment Variables Needed

```
TELEGRAM_BOT_TOKEN=<from BotFather>
TELEGRAM_WEBHOOK_SECRET=<random string>
DATABASE_URL=sqlite:///./lifeos.db   # local dev
OPENAI_API_KEY=<optional but recommended>
ANTHROPIC_API_KEY=<optional>
WEBHOOK_BASE_URL=https://lifeos-aw.up.railway.app
WEEKLY_BUDGET=90
LOCAL_POLLING=true   # local dev only
```

## Do-Not-Touch Warnings

- `app/database.py` lines 1–54: existing `transactions` table definition — do not modify columns or types
- `tests/` — all 74 tests must remain passing; never delete or skip tests
- `Procfile` — Railway uses this exactly as written; do not change
- `app/parser.py` — AI prompt is tuned; changes require testing against 10+ edge cases
- `requirements.txt` — do not upgrade versions without explicit instruction
