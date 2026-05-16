import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_update(text: str):
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


async def test_reply_a_no_pending_returns_no_active_decision():
    from app.commands import handle_message
    update = _make_update("A")
    with patch("app.database.read_pending_action", return_value=None):
        await handle_message(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "No active agent decision" in reply
    assert "couldn't find an amount" not in reply


async def test_reply_done_no_pending_returns_no_active_decision():
    from app.commands import handle_message
    update = _make_update("DONE")
    with patch("app.database.read_pending_action", return_value=None):
        await handle_message(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "No active agent decision" in reply
    assert "couldn't find an amount" not in reply


async def test_reply_b_with_pending_decision_resolves_and_confirms():
    from app.commands import handle_message
    pending = {
        "id": 42,
        "status_type": "decision",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": "Which DB?",
    }
    update = _make_update("B")
    with patch("app.database.read_pending_action", return_value=pending), \
         patch("app.database.resolve_agent_state") as mock_resolve:
        await handle_message(update, MagicMock())
    mock_resolve.assert_called_once_with(42)
    reply = update.message.reply_text.call_args[0][0]
    assert "Decision received: B" in reply


async def test_reply_done_with_pending_manual_action_confirms_done():
    from app.commands import handle_message
    pending = {
        "id": 7,
        "status_type": "manual_action",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": "Add key to Railway",
    }
    update = _make_update("done")
    with patch("app.database.read_pending_action", return_value=pending), \
         patch("app.database.resolve_agent_state"):
        await handle_message(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "Manual action marked as done" in reply


async def test_normal_expense_still_parsed():
    from app.commands import handle_message
    update = _make_update("14 kebab")
    parsed = {
        "timestamp": "2026-05-16T10:00:00+00:00",
        "date": "2026-05-16",
        "week_start": "2026-05-13",
        "month": "2026-05",
        "type": "Expense",
        "amount": 14.0,
        "description": "kebab",
        "category": "Food",
        "is_impulse": False,
    }
    with patch("app.parser.parse_message", return_value=parsed), \
         patch("app.categories.get_category", return_value="Food"), \
         patch("app.database.append_transaction", return_value=1), \
         patch("app.database.get_all_transactions", return_value=[]), \
         patch("app.budget.calculate_weekly_status", return_value={
             "weekly_spent": 14.0, "weekly_budget": 90.0,
             "remaining": 76.0, "pct_used": 15.6, "week_start": "2026-05-13",
         }):
        await handle_message(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "kebab" in reply
    assert "Got it" in reply


async def test_yes_reply_not_parsed_as_expense():
    from app.commands import handle_message
    update = _make_update("yes")
    with patch("app.database.read_pending_action", return_value=None):
        await handle_message(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "No active agent decision" in reply


async def test_c_reply_with_pending_error_state_resolves():
    from app.commands import handle_message
    pending = {
        "id": 99,
        "status_type": "error",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": "Tests failing",
    }
    update = _make_update("C")
    with patch("app.database.read_pending_action", return_value=pending), \
         patch("app.database.resolve_agent_state") as mock_resolve:
        await handle_message(update, MagicMock())
    mock_resolve.assert_called_once_with(99)


async def test_lifeos_question_answered_by_ai_not_expense_parser():
    from app.commands import handle_message
    update = _make_update("What is my net worth?")
    with patch("app.intent_classifier.classify_intent", return_value="lifeos_question"), \
         patch("app.ai_agent.answer_lifeos_question", return_value="Your net worth is €15,000."), \
         patch("app.database.get_latest_net_worth_snapshot", return_value=None), \
         patch("app.database.get_all_transactions", return_value=[]):
        await handle_message(update, MagicMock())
    calls = [c[0][0] for c in update.message.reply_text.call_args_list]
    assert any("€15,000" in r or "net worth" in r.lower() for r in calls)
    assert all("couldn't find an amount" not in r for r in calls)


async def test_action_request_proposes_and_stores_pending_decision():
    from app.commands import handle_message
    update = _make_update("Build the next module")
    with patch("app.intent_classifier.classify_intent", return_value="action_request"), \
         patch("app.ai_agent.propose_action", return_value="I propose to build Module 1.2. Reply A to approve or B to cancel."), \
         patch("app.database.write_agent_state") as mock_write:
        await handle_message(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "Module 1.2" in reply or "propose" in reply.lower()
    assert "Reply A" in reply or "A to approve" in reply
    mock_write.assert_called_once()


async def test_unknown_intent_asks_for_clarification():
    from app.commands import handle_message
    update = _make_update("hello there")
    with patch("app.intent_classifier.classify_intent", return_value="unknown"), \
         patch("app.parser.parse_message", side_effect=ValueError("no amount")):
        await handle_message(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "clarify" in reply.lower() or "not sure" in reply.lower()
    assert "couldn't find an amount" not in reply
