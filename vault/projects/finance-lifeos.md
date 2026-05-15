# finance-lifeos

**Live URL:** https://lifeos-aw.up.railway.app
**Repo:** `/Users/arryawillems/finance-lifeos`
**Branch:** master (auto-deploys to Railway)

---

## Stack

- Python 3.13 / FastAPI 0.111 / python-telegram-bot 20.7
- SQLAlchemy 2.0 Core / PostgreSQL (Railway)
- Jinja2 3.1.4 / Chart.js 4.4.0
- OpenAI GPT-4o-mini (primary AI) / Claude Haiku (fallback)
- pytest 8.2.1 / pytest-asyncio 0.23.6

---

## Deployed Modules

| Module | Status | Key files |
|--------|--------|-----------|
| 1.0 Finance Cashflow | ✅ DONE | `app/parser.py`, `app/commands.py`, `app/budget.py` |
| 1.1 Net Worth | ✅ DONE | `app/networth_parser.py`, `app/networth.py` |
| 1.4 Agent Control (partial) | 🔶 IN PROGRESS | `app/auth.py`, `app/telegram.py`, `scripts/` |

---

## Modules Not Built

- 1.2 Portfolio / Accounts Tracker
- 1.3 Screenshot / CSV Import
- 1.4 Proactive notifications (partial — infrastructure done, scheduling not done)
- 2.0 Goals Tracker
- 3.0 Health / Workout Tracker
- 4.0 Unified Dashboard

---

## Tests

**150 passing** (`pytest` from repo root)

Test files:
- `tests/test_parser.py` — finance message parsing
- `tests/test_budget.py` — weekly/monthly calculations
- `tests/test_database.py` — DB operations
- `tests/test_categories.py` — category detection
- `tests/test_auth.py` — owner access control
- `tests/test_networth_parser.py` — NW message detection + parsing
- `tests/test_networth_db.py` — NW DB operations
- `tests/test_networth_logic.py` — goal calculations, delta, progress bar
- `tests/test_networth_commands.py` — NW Telegram handlers
- `tests/test_dashboard.py` — dashboard routes

---

## DB Tables

| Table | Module | Notes |
|-------|--------|-------|
| `transactions` | 1.0 | Never modify schema |
| `net_worth_snapshots` | 1.1 | Append-only, never overwritten |
| `agent_state` | 1.4 | Live session state |

---

## Known Limitations

- Dashboard has no authentication (do not share URL publicly)
- `tag`, `payment_type`, `is_necessary` columns exist but are unused (reserved)
- `sheets.py` still present (legacy Google Sheets stub, not imported anywhere active)
- Module 1.4 notifications are manual-push only; scheduled push not yet built

---

## Next Milestones

1. Module 1.2 — Portfolio/Accounts Tracker
2. Complete Module 1.4 — `/resolve` command + proactive scheduled notifications
3. Module 2.0 — Goals Tracker
