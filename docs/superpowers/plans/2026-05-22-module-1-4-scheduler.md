# Module 1.4 — Proactive Scheduled Notifications

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add APScheduler to send proactive Telegram notifications (daily journal reminder, Friday NW check-in, Monday weekly summary, monthly review) and polish `/today`, `/week`, `/month`, `/nw` commands.

**Architecture:** A `BackgroundScheduler` (APScheduler 3.x) starts inside the FastAPI `lifespan` context. Each job pulls live data from the DB, formats a message, and calls the existing `send_telegram_message()`. Commands are improved in `app/commands.py` and registered in `app/bot.py`.

**Tech Stack:** APScheduler 3.x, pytz, existing `app/telegram.py`, `app/database.py`, `app/budget.py`, `app/networth.py`

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `requirements.txt` | Modify | Add `apscheduler==3.10.4` and `pytz==2024.1` |
| `app/scheduler.py` | Create | 4 job functions + `create_scheduler()` |
| `app/dashboard.py` | Modify | Start/stop scheduler in `lifespan` |
| `app/commands.py` | Modify | Improve `/today`, `/week`, `/month`; add `/nw` |
| `app/bot.py` | Modify | Register `/nw` command handler |
| `tests/test_scheduler.py` | Create | Unit tests for all 4 jobs |

---

## Task 1: Add dependencies

- [ ] Add to `requirements.txt`:
```
apscheduler==3.10.4
pytz==2024.1
```
- [ ] Run: `pip install apscheduler==3.10.4 pytz==2024.1`
- [ ] Commit: `chore: add apscheduler and pytz`

---

## Task 2: Create `app/scheduler.py`

- [ ] Write failing tests in `tests/test_scheduler.py`
- [ ] Implement `app/scheduler.py`
- [ ] Run tests, verify pass
- [ ] Commit: `feat(1.4): scheduler jobs`

**Tests:**
```python
from unittest.mock import patch, MagicMock
from app.scheduler import (
    job_daily_journal_reminder,
    job_friday_networth_reminder,
    job_monday_weekly_summary,
    job_monthly_review,
    create_scheduler,
)

def make_txns():
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")
    week_start = today
    return [{"date": today, "week_start": week_start, "month": "2026-05",
             "type": "Expense", "amount": 14.0, "description": "food",
             "category": "Food", "notes": "", "tag": ""}]

def make_snap():
    return {"total_net_worth": 16000.0, "cash": 5000.0, "investments": 11000.0,
            "crypto": 0.0, "savings": 0.0, "other_assets": 0.0, "liabilities": 0.0,
            "timestamp": "2026-05-16T10:00:00+00:00"}

@patch("app.scheduler.send_telegram_message")
@patch("app.scheduler.database.get_all_transactions")
def test_daily_reminder_sends(mock_txns, mock_send):
    mock_txns.return_value = []
    job_daily_journal_reminder()
    mock_send.assert_called_once()
    assert "Journal" in mock_send.call_args[0][0]

@patch("app.scheduler.send_telegram_message")
@patch("app.scheduler.database.get_latest_net_worth_snapshot")
@patch("app.scheduler.database.get_all_transactions")
def test_friday_reminder_includes_nw(mock_txns, mock_snap, mock_send):
    mock_txns.return_value = make_txns()
    mock_snap.return_value = make_snap()
    job_friday_networth_reminder()
    mock_send.assert_called_once()
    assert "16" in mock_send.call_args[0][0]

@patch("app.scheduler.send_telegram_message")
@patch("app.scheduler.database.get_all_transactions")
def test_monday_summary_includes_spent(mock_txns, mock_send):
    mock_txns.return_value = make_txns()
    job_monday_weekly_summary()
    mock_send.assert_called_once()
    assert "Week" in mock_send.call_args[0][0]

@patch("app.scheduler.send_telegram_message")
@patch("app.scheduler.database.get_latest_net_worth_snapshot")
@patch("app.scheduler.database.get_all_transactions")
def test_monthly_review_includes_goal(mock_txns, mock_snap, mock_send):
    mock_txns.return_value = make_txns()
    mock_snap.return_value = make_snap()
    job_monthly_review()
    mock_send.assert_called_once()
    assert "30" in mock_send.call_args[0][0]

def test_create_scheduler_returns_scheduler():
    s = create_scheduler()
    assert s is not None
    assert len(s.get_jobs()) == 4
```

**Implementation:**
```python
import logging
from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from app import database, budget as budget_module, config
from app.networth import calculate_live_net_worth
from app.telegram import send_telegram_message
from app.utils import format_currency

_log = logging.getLogger(__name__)
_TZ = pytz.timezone("Europe/Amsterdam")


def job_daily_journal_reminder() -> None:
    today = date.today().strftime("%Y-%m-%d")
    send_telegram_message(f"Journal — {today}. Log today before you forget.")


def job_friday_networth_reminder() -> None:
    try:
        snap = database.get_latest_net_worth_snapshot()
        txns = database.get_all_transactions()
        live_nw = calculate_live_net_worth(snap, txns)
        send_telegram_message(
            f"Friday check-in. Update your net worth snapshot.\n"
            f"Current: {format_currency(live_nw)}"
        )
    except Exception as exc:
        _log.warning("friday job failed: %s", exc)
        send_telegram_message("Friday check-in. Update your net worth snapshot.")


def job_monday_weekly_summary() -> None:
    try:
        txns = database.get_all_transactions()
        status = budget_module.calculate_weekly_status(txns, config.WEEKLY_BUDGET)
        delta = status["weekly_budget"] - status["weekly_spent"]
        direction = "under" if delta >= 0 else "over"
        send_telegram_message(
            f"Week {date.today().strftime('%W')} summary\n"
            f"Spent last 7 days: {format_currency(status['weekly_spent'])}\n"
            f"vs budget ({format_currency(status['weekly_budget'])}): "
            f"{direction} by {format_currency(abs(delta))}"
        )
    except Exception as exc:
        _log.warning("monday job failed: %s", exc)


def job_monthly_review() -> None:
    try:
        txns = database.get_all_transactions()
        snap = database.get_latest_net_worth_snapshot()
        live_nw = calculate_live_net_worth(snap, txns)
        monthly = budget_module.calculate_monthly_summary(txns)
        history = database.get_net_worth_history(limit=2)
        delta_nw = (
            live_nw - history[-2]["total_net_worth"]
            if len(history) >= 2 else 0.0
        )
        progress = live_nw / 30_000 * 100
        send_telegram_message(
            f"{monthly['month']} review\n"
            f"Spent: {format_currency(monthly['monthly_spent'])}\n"
            f"Net worth: {format_currency(live_nw)} ({delta_nw:+.0f} vs last month)\n"
            f"Goal: {progress:.1f}% to 30k"
        )
    except Exception as exc:
        _log.warning("monthly job failed: %s", exc)


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=_TZ)
    scheduler.add_job(job_daily_journal_reminder,
                      CronTrigger(hour=8, minute=0, timezone=_TZ))
    scheduler.add_job(job_friday_networth_reminder,
                      CronTrigger(day_of_week="fri", hour=18, minute=0, timezone=_TZ))
    scheduler.add_job(job_monday_weekly_summary,
                      CronTrigger(day_of_week="mon", hour=9, minute=0, timezone=_TZ))
    scheduler.add_job(job_monthly_review,
                      CronTrigger(day=1, hour=9, minute=0, timezone=_TZ))
    return scheduler
```

---

## Task 3: Wire scheduler into `app/dashboard.py`

- [ ] Import and start scheduler in `lifespan`
- [ ] Commit: `feat(1.4): start scheduler in lifespan`

```python
# In lifespan, after _ptb_app.start():
from app.scheduler import create_scheduler
_scheduler = create_scheduler()
_scheduler.start()
# In lifespan teardown (after yield):
_scheduler.shutdown(wait=False)
```

---

## Task 4: Add `/nw` command + polish existing commands

- [ ] Add `cmd_nw` to `app/commands.py`
- [ ] Register in `app/bot.py`
- [ ] Commit: `feat(1.4): /nw command`

```python
async def cmd_nw(update, context):
    snap = sheets.get_latest_net_worth_snapshot()
    txns = sheets.get_all_transactions()
    live_nw = calculate_live_net_worth(snap, txns)
    progress = live_nw / 30_000 * 100
    await update.message.reply_text(
        f"Net worth: {format_currency(live_nw)}\n"
        f"Goal: {progress:.1f}% to 30k\n"
        f"Remaining: {format_currency(30_000 - live_nw)}"
    )
```

---

## Task 5: Final test run + push

- [ ] `pytest` — all tests pass
- [ ] `git push origin master`
