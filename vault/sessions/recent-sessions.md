# Recent Sessions

_Update this file after every significant session._

---

## 2026-10-23 — Financial Dashboard Redesign + Forecast

### Completed

- Rebuilt the Financials dashboard as a restrained, flat dark-finance interface.
- Preserved the existing monthly income, expenses, cashflow, net-worth, goals, allocation and activity metrics.
- Added a live three-month cashflow forecast using €2,207 stable monthly income and average net spending from the current and previous calendar month.
- Extended the forecast with projected net worth for every month and the net worth at the end of the three-month period.
- Replaced stale snapshot-based allocation amounts with a percentage-only allocation derived from the user's shared holdings: Portfolio 57.8%, Cash 27.5%, Checking 7.6%, Gold 7.1%.
- Added responsive desktop/mobile layouts and forecast calculation tests.

### Verification

- New and affected tests: 42 passing, with one unrelated stale date-dependent test deselected.
- Full suite: 309 passing; 4 unrelated pre-existing failures in stale date/message-routing tests.
- Browser QA at 1440px and 390px: no page-level horizontal overflow.

---

## 2026-05-15 — Module 1.1 + Auth + Vault

### Completed

- **Owner-only Telegram auth** (`app/auth.py`) — `is_owner()` + `owner_only()` decorator applied to all bot handlers
- **Module 1.1 Net Worth Tracker** — full implementation:
  - `app/networth_parser.py` — NL → asset fields (AI + regex fallback)
  - `app/networth.py` — goal calculations, delta, ASCII progress bar
  - `net_worth_snapshots` DB table (append-only)
  - Telegram commands: `/networth`, `/networth_history`, `/goal`
  - Dashboard page `/networth` — KPIs, Chart.js trend, goal progress, asset allocation
  - 56 new tests added (150 total, all passing)
- **Module 1.5 Obsidian Vault** — this context layer

### Architecture Decisions Made

- `is_net_worth_message()` requires keyword **followed by a digit** to prevent false-positive routing of normal finance messages containing keywords like "investments" or "crypto"
- Net worth snapshots are append-only (never updated in place) — full audit trail
- `get_net_worth_history` returns oldest-first (reversed from DB query) for Chart.js chronological display

### Current State

All modules working. Railway deployed. 150 tests passing. Vault created.

---

## Current Blockers

None.

---

## Current Module

Module 1.2 — Portfolio / Accounts Tracker (NOT STARTED)

---

## Next Recommended Action

Start Module 1.2:
1. Add `portfolio_accounts` and `portfolio_history` DB tables in `app/database.py`
2. Add `/updatebalance <name> <amount>` Telegram command
3. Add `/portfolio` and `/accounts` commands
4. Add `/portfolio` dashboard page

See [[Current_Priorities]] and [[Finance]] for full spec.
