# Architecture — LifeOS

## Overview

LifeOS is a personal life-management system built as independent modules sharing a single PostgreSQL database on Railway. Each module exposes functionality via a Telegram bot (commands/natural language) and a web dashboard.

---

## Module 1.0: Finance Cashflow Tracker

### Runtime

| Layer | Technology |
|-------|-----------|
| Bot framework | python-telegram-bot 20.7 |
| Web framework | FastAPI 0.111 |
| ORM | SQLAlchemy 2.0 (Core, not ORM layer) |
| Database | PostgreSQL (Railway-managed) |
| AI parsing | OpenAI GPT-4o-mini (primary), Claude Haiku (fallback) |
| Templates | Jinja2 |
| Deploy | Railway (Procfile: `uvicorn app.dashboard:app`) |
| Python | 3.13 |

### Data Model

**Table: `transactions`**

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | auto-increment |
| timestamp | String | `YYYY-MM-DD HH:MM:SS` |
| date | String | `YYYY-MM-DD` |
| week_start | String | Monday of the week |
| month | String | `YYYY-MM` |
| type | String | `Expense \| Income \| Transfer \| Investment` |
| amount | Float | always positive |
| description | String | 1-3 word label |
| category | String | see categories below |
| tag | String | unused, reserved |
| payment_type | String | unused, reserved |
| is_impulse | Boolean | flagged by AI |
| is_necessary | String | unused, reserved |
| notes | String | `[UNDONE]` marker lives here |

**Categories:** Food, Social, Transport, Project, Health, Clothing, Education, Impulse, Income, Investment, Transfer, Other

**Table: `net_worth_snapshots`** (Module 1.1)

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | auto-increment |
| timestamp | String | ISO 8601 UTC |
| cash | Float | 0.0 if not provided |
| investments | Float | 0.0 if not provided |
| crypto | Float | 0.0 if not provided |
| savings | Float | 0.0 if not provided |
| other_assets | Float | 0.0 if not provided |
| liabilities | Float | positive; subtracted in total |
| total_net_worth | Float | calculated: assets − liabilities |
| notes | String | optional user note |

### Request Flow

```
Telegram message
  → POST /webhook (FastAPI)
  → Signature check (X-Telegram-Bot-Api-Secret-Token)
  → python-telegram-bot dispatches handler
  → parse_message() — AI or regex
  → get_category() — AI or keyword match
  → append_transaction() — SQLAlchemy INSERT
  → calculate_weekly_status() — budget reply
  → reply_text()
```

### Dashboard Routes

| Route | Template | Data |
|-------|----------|------|
| GET / | dashboard.html | weekly KPIs, monthly summary, recent 10 |
| GET /categories | categories.html | monthly by-category breakdown |
| GET /transactions | transactions.html | full history |
| GET /networth | networth.html | net worth KPIs, goal progress, Chart.js trend, snapshots |
| POST /webhook | — | Telegram update handler |

### Key Files

| File | Responsibility |
|------|---------------|
| `app/config.py` | All env vars, single import point |
| `app/database.py` | All DB I/O (no raw SQL elsewhere) |
| `app/parser.py` | Message → transaction dict |
| `app/categories.py` | description → category string |
| `app/budget.py` | weekly/monthly aggregations |
| `app/commands.py` | All Telegram handlers |
| `app/dashboard.py` | FastAPI app, webhook, dashboard routes |
| `app/bot.py` | PTB Application factory |
| `app/utils.py` | format_currency, get_week_start, get_month |
| `app/networth_parser.py` | Natural language → net worth asset fields |
| `app/networth.py` | Goal calculations, change delta, ASCII progress bar |
| `app/auth.py` | `is_owner()` + `owner_only()` handler wrapper |

---

## Planned Module Architecture

### Module 1.1: Net Worth Tracker
- New DB table: `net_worth_snapshots` (date, category, label, amount)
- Categories: cash, savings, investments, property, crypto, debt
- Bot commands: `/networth`, `/addaccount`, `/snapshot`
- Dashboard page: `/networth` — time series chart + current breakdown
- Manual entry via Telegram; no external API calls in this module

### Module 1.2: Portfolio/Accounts Tracker
- New DB table: `portfolio_accounts` (id, name, type, institution, balance, currency, last_updated)
- New DB table: `portfolio_history` (account_id, date, balance)
- Bot commands: `/portfolio`, `/accounts`, `/updatebalance <account> <amount>`
- Dashboard page: `/portfolio` — per-account balances + history

### Module 1.3: Screenshot/CSV Portfolio Import
- Accepts Telegram photo or document
- Screenshot path: OCR (Tesseract or GPT-4o vision) → structured parse → INSERT
- CSV path: pandas parse → validate columns → INSERT
- Bot command: `/import` (triggers upload flow)

### Module 1.4: Agent Control Layer + Telegram Notifications
- Scheduled jobs (APScheduler or Railway cron) for:
  - Weekly budget summary (Monday morning)
  - Monthly review (1st of month)
  - Net worth snapshot reminder
- Proactive push notifications from bot to user (no user message needed)
- New config: `TELEGRAM_CHAT_ID` — owner's chat ID for push messages

### Module 2: Goals Tracker
- DB tables: `goals`, `goal_progress`
- Bot commands: `/addgoal`, `/goals`, `/logprogress`
- Dashboard page: `/goals`

### Module 3: Health/Workout Tracker
- DB tables: `workouts`, `body_metrics`
- Bot commands: `/workout`, `/weight`, `/health`
- Dashboard page: `/health`

### Module 4: Unified LifeOS Dashboard
- Root dashboard aggregating all modules
- Single `/` route showing KPIs from all active modules
- Navigation between module dashboards

---

## Naming Conventions

- Bot command handlers: `cmd_<name>` in `commands.py`
- DB functions: verbs — `append_*`, `get_*`, `update_*`
- Route handlers: `<page>_page` for GET, descriptive noun for POST
- New module files: `app/<module_name>/` subdirectory when module has >2 files

## Cross-Module Database Rules

- All modules share the same PostgreSQL instance
- Each module owns its own tables — no cross-table JOINs between modules
- `init_db()` in `database.py` must `create_all` for all module tables
- Migrations: use `CREATE TABLE IF NOT EXISTS` via SQLAlchemy MetaData; no Alembic needed at this scale

## Security Notes

- Dashboard has no authentication yet — do not expose sensitive data on public routes
- Webhook is protected by `X-Telegram-Bot-Api-Secret-Token` header
- Never log full Telegram update payloads (may contain user data)
- `.env` is gitignored; `.env.example` has no real values
