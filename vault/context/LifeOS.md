# LifeOS

**LifeOS is a personal operating system delivered through Telegram and a web dashboard.**

Input arrives via Telegram natural language. The dashboard is read-only visualisation. All data lives in a single PostgreSQL database. Claude Code sessions are replaceable implementation workers. The vault is the memory layer that survives session rotation.

---

## What Is Built

| Module | Name | Status |
|--------|------|--------|
| 1.0 | Finance Cashflow Tracker | DONE |
| 1.1 | Net Worth Tracker | DONE |
| 1.4 | Agent Control Layer (partial) | IN PROGRESS |

**Module 1.0** — Log every expense, income, transfer, investment in natural language. AI parses the message (GPT-4o-mini, Claude Haiku fallback, regex fallback). Stored in `transactions` table. Dashboard shows weekly KPIs, category breakdown, full history.

**Module 1.1** — Snapshot net worth across assets at any point in time. Natural language input ("net worth cash 2k investments 8k"). Append-only `net_worth_snapshots` table. Dashboard shows trend chart, goal progress (€25K / €30K), asset allocation.

**Module 1.4 (partial)** — Telegram supervision commands (`/status`, `/next`, `/git`, `/handoff`). `notify_me.py` for Claude→user push notifications. `create_handoff.py` for session continuity. `agent_state` DB table. Owner-only auth on all bot handlers.

---

## Architecture

```
Telegram message
  → POST /webhook (FastAPI on Railway)
  → owner auth check
  → route: net worth OR finance
  → AI parse → DB insert
  → reply with status

Web browser
  → GET /networth or / etc. (FastAPI on Railway)
  → DB read → Jinja2 render → HTML response
```

**Stack:**
- Bot framework: python-telegram-bot 20.7
- Web: FastAPI 0.111 + Jinja2
- ORM: SQLAlchemy 2.0 Core
- DB: PostgreSQL (Railway-managed)
- AI: OpenAI GPT-4o-mini (primary), Claude Haiku (fallback)
- Deploy: Railway (auto-deploy from master)
- Python: 3.13

**Live URL:** https://lifeos-aw.up.railway.app

---

## How Telegram, Railway, PostgreSQL, Dashboard, and Claude Interact

- **Telegram** — only input/output channel for the user and Claude notifications
- **Railway** — hosts FastAPI app and PostgreSQL; auto-deploys from `master`
- **PostgreSQL** — single source of truth for all module data
- **Dashboard** — read-only visualisation at Railway URL, no auth currently
- **Claude Code** — implementation worker; reads vault first, codes, commits, notifies via Telegram

---

## Core Principle

> **Vault = memory layer. AI sessions = replaceable workers.**

Claude sessions rotate when tokens run out. The vault, codebase, and handoff files are the only continuity. A new session reading vault files should be productive in minutes without scanning the repo.

---

## Future Vision

Modules to build:
- 1.2 Portfolio/Accounts Tracker
- 1.3 CSV/Screenshot Import
- 2.0 Goals Tracker
- 3.0 Health/Workout Tracker
- 4.0 Unified LifeOS Dashboard

See [[Current_Priorities]] and [[finance-lifeos]] for roadmap details.
