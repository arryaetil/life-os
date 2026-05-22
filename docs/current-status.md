# Current Status — LifeOS

_Last updated: 2026-05-22_

---

## System Health

| Check | Status |
|-------|--------|
| Tests | ✅ 81 passing |
| Railway deploy | ✅ Live at https://lifeos-aw.up.railway.app |
| Telegram bot | ✅ Webhook active |
| PostgreSQL | ✅ Railway-managed |
| AI parsing | ✅ GPT-4o-mini (regex fallback if no key) |
| Scheduler | ✅ APScheduler running in lifespan |

---

## Module 1.0 — Finance Cashflow Tracker ✅ DONE

- Natural language expense/income logging via Telegram (Dutch + English)
- Bulk expense logging: send a multi-line list, each line logged separately
- Categories: 12 standard + dynamic AI-suggested
- Bot: `/today`, `/week`, `/month`, `/income`, `/undo`, `/summary`, `/budget`
- Dashboard: `/expenses`, `/categories`, `/transactions` (inline edit + delete)
- PWA: installable on iPhone home screen, bottom tab bar, safe area insets

## Module 1.1 — Net Worth Tracker ✅ DONE

- Snapshot logging via Telegram: "net worth cash 2k investments 8k"
- Live net worth = baseline snapshot + income − expenses since baseline
- `nw_excluded` tag: historical expenses excluded from NW calculation
- Bot: `/networth`, `/networth_history`, `/goal`, `/nw`
- Dashboard: live NW KPI, monthly change, Chart.js progression, asset allocation, goals
- Baseline: €15,000 set 2026-05-16

## Module 1.4 — Agent Control + Proactive Notifications ✅ DONE

- Scheduled notifications (APScheduler, Europe/Amsterdam timezone):
  - Daily 08:00 — journal reminder
  - Friday 18:00 — net worth check-in with live figure
  - Monday 09:00 — weekly spend vs budget summary
  - 1st of month 09:00 — full monthly review with NW delta + goal %
- `app/telegram.py` — `send_telegram_message()` utility
- `agent_state` table — live state tracking for autonomous sessions
- Bot: `/status`, `/next`, `/git`, `/handoff`, `/nw`
- Auth: all handlers owner-gated via `TELEGRAM_OWNER_CHAT_ID`

## Tim Grover Coach ✅ DONE (built this session, not a formal module)

- All non-transaction Telegram messages route to the coach
- Tim Grover personality: direct, no sugarcoating, €30k goal as measuring stick
- 3-layer context per message: vault memory (long-term) + live financial data + last 5 messages
- `conversations` table: every message stored permanently
- `vault_memory` table: compressed coach insights, survives redeploys
- Auto-updates coach-memory.md every 10 messages, syncs to Obsidian vault
- Reads `vault/personal/goals.md` and `vault/personal/values.md`

---

## Next: Module 1.2 — Portfolio / Accounts Tracker

- New DB tables: `portfolio_accounts`, `portfolio_history`
- Bot commands: `/portfolio`, `/accounts`, `/updatebalance <name> <amount>`
- Dashboard page: `/portfolio` — per-account balances + history

---

## Do Not Touch

- `transactions` table schema — stable, do not alter
- `net_worth_snapshots` table — append-only, do not delete rows
- `app/parser.py` AI prompt — tuned, test before changing
- `Procfile` — Railway uses this exactly as written

---

## Environment Variables

| Variable | Required | Notes |
|----------|----------|-------|
| `TELEGRAM_BOT_TOKEN` | Yes | From BotFather |
| `TELEGRAM_OWNER_CHAT_ID` | Yes | Your Telegram user ID |
| `TELEGRAM_WEBHOOK_SECRET` | Yes | Any random string |
| `DATABASE_URL` | Yes | Auto-set by Railway |
| `OPENAI_API_KEY` | Yes | GPT-4o-mini for parsing + coach |
| `ANTHROPIC_API_KEY` | Optional | Claude Haiku fallback |
| `WEBHOOK_BASE_URL` | Yes (prod) | Railway URL, no trailing slash |
| `WEEKLY_BUDGET` | No | Default: 90 (euros) |
| `LOCAL_POLLING` | No | Set `true` for local dev |
