# Current Status — LifeOS

_Last updated: 2026-05-15_

---

## System Health

| Check | Status |
|-------|--------|
| Tests | ✅ 173 / 173 passing |
| Railway deploy | ✅ Live at https://lifeos-aw.up.railway.app |
| Telegram bot | ✅ Webhook active |
| PostgreSQL | ✅ Railway-managed |
| AI parsing | ✅ GPT-4o-mini (regex fallback if no key) |

---

## Module 1.0 — Finance Cashflow Tracker

**Status: ✅ COMPLETE**

### What Works

- **Natural language parsing**: Send any message → AI extracts amount, type, description, category, impulse flag
- **Regex fallback**: Works without OpenAI/Anthropic API keys
- **Transaction types**: Expense, Income, Transfer, Investment — all detected correctly
- **Categorisation**: 12 categories, AI-assisted with keyword fallback
- **Bot commands** (all working):
  - `/start` — welcome and usage
  - `/help` — examples
  - `/today` — today's transactions
  - `/week` — weekly spend vs budget
  - `/month` — monthly by-category breakdown
  - `/income` — monthly income summary
  - `/undo` — mark last transaction undone (sets notes=`[UNDONE]`)
  - `/summary` — compact weekly + monthly overview
  - `/budget` — ASCII progress bar
- **Dashboard pages** (all working):
  - `/` — KPIs (weekly, monthly), recent transactions
  - `/categories` — monthly spend by category + progress bars
  - `/transactions` — full transaction history
- **PostgreSQL**: Single `transactions` table, stable schema
- **Deployment**: Railway, auto-deploys from `master`

### Known Limitations / Deferred

- Dashboard has **no authentication** — do not share the URL publicly
- `tag`, `payment_type`, `is_necessary` columns exist in DB but are unused (reserved for future)
- `sheets.py` still present (legacy Google Sheets stub) — harmless, not imported anywhere active
- Undo marks a note on the record but does not delete it — by design

### Do Not Touch

- `app/database.py` — schema is stable; any change breaks existing data
- `tests/` — 74 tests must remain passing
- `app/parser.py` — AI prompt is tuned; do not change without testing against edge cases
- `Procfile` — Railway uses this exactly as written

---

## Module 1.1 — Net Worth Tracker

**Status: ✅ COMPLETE**

### What Works
- Natural language snapshot logging via Telegram: "net worth cash 2k investments 8k savings 3k"
- AI parse (GPT-4o-mini) + regex fallback with `k` suffix support and `debt`→`liabilities` alias
- PostgreSQL `net_worth_snapshots` table — append-only historical snapshots, never overwritten
- **Live net worth calculation**: baseline snapshot + (income transactions) − (expense transactions) since baseline timestamp
  - Ignores Transfer, Investment, and [UNDONE] transactions
  - Automatically coupled to `/transactions` data
- **Monthly net worth change KPI**: compares live net worth to latest pre-month snapshot
  - Returns "Insufficient history" if no prior snapshot exists
- Bot commands (all owner-gated):
  - `/networth` — shows live net worth as primary total; baseline as context
  - `/networth_history` — last 5 snapshots with running delta
  - `/goal` — single €30K progress with ASCII progress bar
- Message routing: `handle_message` auto-detects net worth messages before finance parser
- Dashboard page `/networth`:
  - **Live Net Worth** KPI (baseline + income − expenses since baseline)
  - **Monthly Net Worth Change** KPI (compares to previous month; "Insufficient history" if not available)
  - Single €30K goal card with progress bar
  - Asset allocation bar chart
  - Chart.js line chart with live net worth appended as final "Live" point
  - Recent snapshots table
  - Empty-state UX with Telegram onboarding instructions
- **Production database**: clean baseline snapshot (id=4, €15,000 other_assets) established 2026-05-16

### Key Files
- `app/networth_parser.py` — natural language → asset fields
- `app/networth.py` — `calculate_live_net_worth()`, `calculate_monthly_change()`, goal calculations
- `app/commands.py` — bot handlers using live net worth
- `app/dashboard.py` — `/networth` route with live NW + monthly change
- `app/templates/networth.html` — KPI cards and chart with live point

### Do Not Touch
- `net_worth_snapshots` table — append-only by design; do not alter schema or delete rows
- `calculate_live_net_worth()` and `calculate_monthly_change()` — coupled to transaction parser

---

## Module 1.2 — Portfolio / Accounts Tracker

**Status: 🔲 NOT STARTED**

Nothing built. See `docs/roadmap.md` for spec.

---

## Module 1.3 — Screenshot / CSV Import

**Status: 🔲 NOT STARTED**

Nothing built. See `docs/roadmap.md` for spec.

---

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
- `app/auth.py` — `is_owner()` + `owner_only()` wrapper; all bot handlers gated to `TELEGRAM_OWNER_CHAT_ID`

### What's Left (for future sessions)
- `/resolve` command to mark decisions/actions as resolved
- Proactive notifications (e.g., daily summary)

---

## Module 2 — Goals Tracker

**Status: 🔲 NOT STARTED**

Nothing built.

---

## Module 3 — Health / Workout Tracker

**Status: 🔲 NOT STARTED**

Nothing built.

---

## Module 4 — Unified Dashboard

**Status: 🔲 NOT STARTED**

Nothing built.

---

## Dependencies & Versions (requirements.txt)

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-telegram-bot==20.7
sqlalchemy==2.0.36
psycopg2-binary==2.9.12
Jinja2==3.1.4
python-dotenv==1.0.1
openai==1.30.1
anthropic==0.26.1
httpx==0.25.2
pytest==8.2.1
pytest-asyncio==0.23.6
```

Do not upgrade without testing — PTB 20.x and SQLAlchemy 2.x have strict compatibility constraints.

---

## Environment Variables

| Variable | Required | Notes |
|----------|----------|-------|
| `TELEGRAM_BOT_TOKEN` | Yes | From BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | Yes | Any random string |
| `DATABASE_URL` | Yes | Auto-set by Railway; use `sqlite:///./lifeos.db` locally |
| `OPENAI_API_KEY` | Recommended | GPT-4o-mini parsing |
| `ANTHROPIC_API_KEY` | Optional | Claude Haiku fallback |
| `WEBHOOK_BASE_URL` | Yes (prod) | Railway URL, no trailing slash |
| `WEEKLY_BUDGET` | No | Default: 90 (euros) |
| `LOCAL_POLLING` | No | Set `true` for local dev |
