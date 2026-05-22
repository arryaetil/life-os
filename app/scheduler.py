import logging
from datetime import date

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

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
    scheduler.add_job(
        job_daily_journal_reminder,
        CronTrigger(hour=8, minute=0, timezone=_TZ),
        id="daily_journal",
    )
    scheduler.add_job(
        job_friday_networth_reminder,
        CronTrigger(day_of_week="fri", hour=18, minute=0, timezone=_TZ),
        id="friday_nw",
    )
    scheduler.add_job(
        job_monday_weekly_summary,
        CronTrigger(day_of_week="mon", hour=9, minute=0, timezone=_TZ),
        id="monday_summary",
    )
    scheduler.add_job(
        job_monthly_review,
        CronTrigger(day=1, hour=9, minute=0, timezone=_TZ),
        id="monthly_review",
    )
    return scheduler
