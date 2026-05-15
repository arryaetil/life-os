# Current Priorities

_Last updated: 2026-05-15_

---

## Module Roadmap

```
1.0 Finance ✅ → 1.1 Net Worth ✅ → 1.2 Portfolio → 1.3 CSV Import → 1.4 Notifications
→ 2.0 Goals → 3.0 Health → 4.0 Unified Dashboard
```

Each module must be complete and tested before starting the next.

---

## Immediate Next Priority

**Module 1.2 — Portfolio / Accounts Tracker**

Goal: Track balance history for each individual account (bank, broker, savings).

- New DB tables: `portfolio_accounts`, `portfolio_history`
- Bot commands: `/portfolio`, `/accounts`, `/updatebalance <name> <amount>`
- Dashboard page: `/portfolio` — per-account balances + history

Acceptance criteria:
- Can update a specific account balance in one Telegram message
- Dashboard shows all accounts at a glance

---

## What NOT to Build Yet

- RAG, vector databases, embeddings, semantic search — not until later modules
- Multi-user support — single-user only for now
- OAuth/Basic Auth for dashboard — deferred
- Mobile PWA — deferred
- Automated PDF reports — deferred
- Google Calendar integration — Module 4 era
- Goals tracker (Module 2) — after Module 1.2
- Health tracker (Module 3) — after Module 2

---

## Stabilisation Priorities

- Keep 150 tests passing at all times
- Never modify `transactions` table schema
- Keep Railway auto-deploy working from `master`
- Keep Telegram webhook active
- Keep agent_state table and handoff system working

---

## Current Operational Goals

- Build Module 1.2 (Portfolio/Accounts)
- Complete Module 1.4 (finish `/resolve` command, proactive daily summary)
- Maintain clean vault context after each session
