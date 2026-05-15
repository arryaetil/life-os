import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_update():
    update = MagicMock()
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


SNAPSHOT = {
    "id": 1,
    "timestamp": "2026-05-15T10:00:00+00:00",
    "cash": 2000.0,
    "investments": 8000.0,
    "crypto": 500.0,
    "savings": 3000.0,
    "other_assets": 0.0,
    "liabilities": 500.0,
    "total_net_worth": 13000.0,
    "notes": "",
}


async def test_cmd_networth_no_data_replies_with_message():
    from app.commands import cmd_networth
    update = _make_update()
    with patch("app.database.get_latest_net_worth_snapshot", return_value=None):
        await cmd_networth(update, MagicMock())
    update.message.reply_text.assert_called_once()
    assert "No net worth" in update.message.reply_text.call_args[0][0]


async def test_cmd_networth_shows_total():
    from app.commands import cmd_networth
    update = _make_update()
    with patch("app.database.get_latest_net_worth_snapshot", return_value=SNAPSHOT):
        await cmd_networth(update, MagicMock())
    text = update.message.reply_text.call_args[0][0]
    assert "13000.00" in text


async def test_cmd_networth_history_no_data():
    from app.commands import cmd_networth_history
    update = _make_update()
    with patch("app.database.get_net_worth_history", return_value=[]):
        await cmd_networth_history(update, MagicMock())
    update.message.reply_text.assert_called_once()
    assert "No" in update.message.reply_text.call_args[0][0]


async def test_cmd_networth_history_shows_entries():
    from app.commands import cmd_networth_history
    update = _make_update()
    history = [SNAPSHOT, {**SNAPSHOT, "id": 2, "total_net_worth": 14000.0, "timestamp": "2026-05-16T10:00:00+00:00"}]
    with patch("app.database.get_net_worth_history", return_value=history):
        await cmd_networth_history(update, MagicMock())
    text = update.message.reply_text.call_args[0][0]
    assert "13000.00" in text
    assert "14000.00" in text


async def test_cmd_goal_shows_25k_and_30k():
    from app.commands import cmd_goal
    update = _make_update()
    with patch("app.database.get_latest_net_worth_snapshot", return_value=SNAPSHOT):
        await cmd_goal(update, MagicMock())
    text = update.message.reply_text.call_args[0][0]
    assert "25K" in text or "25k" in text
    assert "30K" in text or "30k" in text


async def test_cmd_goal_no_data():
    from app.commands import cmd_goal
    update = _make_update()
    with patch("app.database.get_latest_net_worth_snapshot", return_value=None):
        await cmd_goal(update, MagicMock())
    update.message.reply_text.assert_called_once()
    assert "No net worth" in update.message.reply_text.call_args[0][0]
