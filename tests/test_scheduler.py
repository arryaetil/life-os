from unittest.mock import patch
from datetime import date


def make_txns():
    today = date.today().strftime("%Y-%m-%d")
    return [
        {
            "date": today,
            "week_start": today,
            "month": "2026-05",
            "type": "Expense",
            "amount": 14.0,
            "description": "food",
            "category": "Food",
            "notes": "",
            "tag": "",
            "is_impulse": False,
        }
    ]


def make_snap():
    return {
        "total_net_worth": 16000.0,
        "cash": 5000.0,
        "investments": 11000.0,
        "crypto": 0.0,
        "savings": 0.0,
        "other_assets": 0.0,
        "liabilities": 0.0,
        "timestamp": "2026-05-16T10:00:00+00:00",
    }


@patch("app.scheduler.send_telegram_message")
@patch("app.scheduler.database.get_all_transactions")
def test_daily_reminder_sends(mock_txns, mock_send):
    from app.scheduler import job_daily_journal_reminder
    mock_txns.return_value = []
    job_daily_journal_reminder()
    mock_send.assert_called_once()
    assert "Journal" in mock_send.call_args[0][0]


@patch("app.scheduler.send_telegram_message")
@patch("app.scheduler.database.get_latest_net_worth_snapshot")
@patch("app.scheduler.database.get_all_transactions")
def test_friday_reminder_includes_nw(mock_txns, mock_snap, mock_send):
    from app.scheduler import job_friday_networth_reminder
    mock_txns.return_value = make_txns()
    mock_snap.return_value = make_snap()
    job_friday_networth_reminder()
    mock_send.assert_called_once()
    assert "16" in mock_send.call_args[0][0]


@patch("app.scheduler.send_telegram_message")
@patch("app.scheduler.database.get_all_transactions")
def test_monday_summary_includes_week(mock_txns, mock_send):
    from app.scheduler import job_monday_weekly_summary
    mock_txns.return_value = make_txns()
    job_monday_weekly_summary()
    mock_send.assert_called_once()
    assert "Week" in mock_send.call_args[0][0]


@patch("app.scheduler.send_telegram_message")
@patch("app.scheduler.database.get_net_worth_history")
@patch("app.scheduler.database.get_latest_net_worth_snapshot")
@patch("app.scheduler.database.get_all_transactions")
def test_monthly_review_includes_goal(mock_txns, mock_snap, mock_history, mock_send):
    from app.scheduler import job_monthly_review
    mock_txns.return_value = make_txns()
    mock_snap.return_value = make_snap()
    mock_history.return_value = [make_snap(), make_snap()]
    job_monthly_review()
    mock_send.assert_called_once()
    assert "30" in mock_send.call_args[0][0]


@patch("app.scheduler.send_telegram_message")
@patch("app.scheduler.database.get_all_transactions")
def test_monday_summary_idempotent(mock_txns, mock_send):
    from app.scheduler import job_monday_weekly_summary
    mock_txns.return_value = make_txns()
    job_monday_weekly_summary()
    job_monday_weekly_summary()
    assert mock_send.call_count == 2


def test_create_scheduler_has_five_jobs():
    from app.scheduler import create_scheduler
    s = create_scheduler()
    s.start()
    assert len(s.get_jobs()) == 5
    s.shutdown(wait=False)
