# Claude Code Prompt — Module 1.4: Proactive Notifications

_Paste this as your first message when starting a Claude Code session to build Module 1.4._

---

## Prompt

Read `CLAUDE.md` and the full context loading order before touching any code. Then read `vault/hubs/Agent_Control.md` and `vault/projects/finance-lifeos.md` to understand what's already built.

**Your task is to complete Module 1.4 — Proactive Scheduled Notifications.**

---

### What's already built (do not rebuild)

- `app/telegram.py` — `send_telegram_message(text)` works
- `scripts/notify_me.py` — typed CLI notification tool
- `agent_state` DB table — live state tracking
- `/status`, `/next`, `/git`, `/handoff` bot commands
- `app/auth.py` — owner-only auth
- `app/agent_control.py` — reply routing

---

### What to build

**1. Scheduled notification job (`app/scheduler.py`)**

Create a background scheduler using APScheduler (already in requirements or add it). Register it in `app/dashboard.py` on app startup via `lifespan`. It must survive Railway deploys.

Jobs to implement:

| Job | Schedule | Message |
|-----|----------|---------|
| Daily journal reminder | Every day 08:00 CET | `📓 Journal — {date}. Log today before you forget.` |
| Friday net worth reminder | Every Friday 18:00 CET | `💰 Friday check-in. Update your net worth snapshot. Current: €{latest_nw}` |
| Monday weekly summary | Every Monday 09:00 CET | See format below |
| Monthly review | 1st of month 09:00 CET | See format below |

**Monday weekly summary format:**
```
📊 Week {WW} summary
Spent last 7 days: €{amount}
vs weekly budget (€{budget}): {over/under} by €{delta}
Net worth: €{latest_nw}
```

**Monthly review format:**
```
📅 {Month} review
Spent: €{total} ({vs_budget}% of budget)
Net worth: €{latest_nw} ({delta_vs_last_month:+.0f} vs last month)
Goal progress: {progress}% to €30k
```

**2. New Telegram commands**

| Command | What it does |
|---------|-------------|
| `/today` | Today's spending + remaining daily budget |
| `/week` | This week's spending summary + budget status |
| `/month` | This month's summary |
| `/nw` | Latest net worth snapshot + progress to €30k goal |

These already partially exist — clean them up and make sure they work reliably.

**3. `/resolve` command (optional, low priority)**

Alternative to inline reply routing. `/resolve yes` or `/resolve A` resolves the latest pending agent decision. Only build this if the inline reply routing has issues.

---

### Technical requirements

- APScheduler with `BackgroundScheduler`, timezone-aware (`Europe/Amsterdam`)
- Jobs pull live data from DB — no hardcoded values
- Jobs must be idempotent (safe to fire twice)
- All DB calls go through `app/database.py` — no raw SQL elsewhere
- New commands go in `app/commands.py` + registered in `app/bot.py`
- Scheduler starts in `lifespan` context in `app/dashboard.py`

---

### Tests required

Add tests in `tests/test_scheduler.py`:
- Test each job sends the right message format
- Test with mock DB data
- Test idempotency (calling job twice doesn't break anything)
- Mock `send_telegram_message` so no real Telegram calls in tests

Keep all 150+ existing tests passing.

---

### Acceptance criteria

- [ ] APScheduler running in Railway without crashing
- [ ] Daily journal reminder fires at 08:00 CET
- [ ] Friday NW reminder fires with live net worth figure
- [ ] Monday summary fires with correct spend + budget figures
- [ ] Monthly review fires on 1st with correct figures
- [ ] `/today`, `/week`, `/month`, `/nw` commands work in Telegram
- [ ] All new tests passing, no existing tests broken
- [ ] Committed with message `feat(1.4): proactive scheduled notifications`
- [ ] Deployed to Railway and verified live

---

### Environment variables needed

All already in Railway:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_OWNER_CHAT_ID`
- `DATABASE_URL`
- `WEEKLY_BUDGET`

No new env vars required.

---

### Do not build

- RAG, embeddings, semantic search
- Multi-user support
- Push notifications to mobile
- Goals tracker (Module 2.0)
- Health tracker (Module 3.0)
