# Roadmap — LifeOS

## Vision

A personal operating system delivered through Telegram and a web dashboard. Each module tracks one life domain. Modules share a single database and a unified dashboard. All input is natural language via Telegram; the dashboard is read-only visualisation.

---

## Module Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ DONE | Feature complete, tested, deployed |
| 🔄 IN PROGRESS | Actively being built |
| 🔲 NOT STARTED | Planned, requirements defined |
| ⏸ DEFERRED | Deprioritised, revisit later |

---

## Module 1 — Finance (Cashflow Tracker)

**Goal:** Track every euro in and out. Know weekly budget status instantly.

### 1.0 — Cashflow Tracker ✅ DONE

- Natural language Telegram input (AI-parsed via GPT-4o-mini)
- Regex fallback parser when no AI key
- Transaction types: Expense, Income, Transfer, Investment
- Categories: Food, Social, Transport, Project, Health, Clothing, Education, Impulse, Income, Investment, Transfer, Other
- Impulse flag (AI-detected)
- PostgreSQL storage via SQLAlchemy
- Bot commands: `/start` `/help` `/today` `/week` `/month` `/income` `/undo` `/summary` `/budget`
- Web dashboard: home (KPIs), categories, transactions
- Deployed on Railway at https://lifeos-aw.up.railway.app
- 74 passing tests

### 1.1 — Net Worth Tracker ✅ DONE

**Goal:** Snapshot total net worth across all accounts/assets at any point in time.

- Natural language Telegram input ("net worth cash 2k investments 8k savings 3k")
- AI parse (GPT-4o-mini) + regex fallback, `k` suffix, `debt`→liabilities alias
- DB table: `net_worth_snapshots` — append-only historical snapshots
- Bot commands: `/networth`, `/networth_history`, `/goal`
- Dashboard page: `/networth` — KPIs, goal progress (€25K + €30K), asset allocation bars, Chart.js trend chart, snapshots table

**Acceptance criteria met:**
- ✅ Can log a net worth snapshot in <15 seconds via Telegram
- ✅ Dashboard shows current net worth and Chart.js trend chart

### 1.2 — Portfolio / Accounts Tracker 🔲 NOT STARTED

**Goal:** Track balance history for each individual account (bank, broker, savings).

- New DB tables: `portfolio_accounts`, `portfolio_history`
- Bot commands: `/portfolio`, `/accounts`, `/updatebalance <name> <amount>`
- Dashboard page: `/portfolio`
  - Table of accounts with current balance + last updated
  - Per-account balance history (sparkline or small chart)

**Acceptance criteria:**
- Can update a specific account balance in one Telegram message
- Dashboard shows all accounts at a glance

### 1.3 — Screenshot / CSV Portfolio Import 🔲 NOT STARTED

**Goal:** Bulk-import portfolio data without manual entry.

- Telegram photo → GPT-4o vision parse → INSERT into `portfolio_history`
- Telegram document (CSV) → pandas parse → batch INSERT
- Bot command: `/import` (triggers upload flow with instructions)
- Validation: reject if required columns missing; reply with error

**Acceptance criteria:**
- Can import a DeGiro or DEGIRO-style CSV export
- Can photograph a broker app screenshot and have balances extracted

### 1.4 — Agent Control Layer + Telegram Notifications 🔲 NOT STARTED

**Goal:** Proactive push notifications and scheduled reports without user prompting.

- Scheduled jobs (Railway cron or APScheduler):
  - Monday 08:00: weekly budget summary
  - 1st of month 09:00: monthly cashflow review
  - Sunday 20:00: net worth snapshot reminder
- New config: `TELEGRAM_CHAT_ID`
- Bot push messages use existing format functions
- No new bot commands required (internal scheduler only)

**Acceptance criteria:**
- Receives Monday weekly summary without sending any message
- Can disable/enable notifications via a single env var

---

## Module 2 — Goals Tracker 🔲 NOT STARTED

**Goal:** Track personal goals with measurable progress.

- DB tables: `goals` (id, title, target, unit, deadline, status), `goal_progress` (goal_id, date, value, notes)
- Bot commands: `/addgoal <title> <target> <unit>`, `/goals`, `/logprogress <goal_id> <value>`
- Dashboard page: `/goals`
  - List of goals with progress bars
  - Deadline countdown
- Integration with Module 1: financial goals can reference cashflow data

**Acceptance criteria:**
- Can create a goal ("Save €5000 by Dec") in one message
- Dashboard shows progress bars for all active goals

---

## Module 3 — Health / Workout Tracker 🔲 NOT STARTED

**Goal:** Track workouts and body metrics over time.

- DB tables: `workouts` (id, date, type, duration_min, notes), `body_metrics` (id, date, weight_kg, notes)
- Bot commands: `/workout <type> <duration>`, `/weight <value>`, `/health`
- Dashboard page: `/health`
  - Weight trend chart
  - Workout frequency heatmap (weekly)
  - Last 10 workouts

**Acceptance criteria:**
- Log a workout in one Telegram message
- Dashboard shows weight trend for the last 30 days

---

## Module 4 — Unified LifeOS Dashboard 🔲 NOT STARTED

**Goal:** Single landing page showing critical KPIs from all active modules.

- Route: GET / (replaces current finance-only home)
- Sections:
  - Finance: weekly budget, net worth delta, monthly cashflow
  - Goals: top 3 active goals with progress
  - Health: last workout, current weight
- Navigation bar linking to all module dashboards
- Mobile-responsive

**Acceptance criteria:**
- All active modules have a section on the home page
- Loads in <1 second (no external API calls on page load)

---

## Implementation Order

```
1.1 Net Worth → 1.2 Portfolio → 1.3 CSV Import → 1.4 Notifications
→ 2.0 Goals → 3.0 Health → 4.0 Unified Dashboard
```

Each module is self-contained. Do not skip ahead — later modules depend on earlier ones being stable.

---

## Future / Deferred

- OAuth/Basic Auth for dashboard (security)
- Multi-user support (currently single-user)
- Mobile PWA
- Automated weekly PDF report
- Integration with Google Calendar (Module 4 era)
