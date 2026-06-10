import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_photo_update():
    update = MagicMock()
    update.message.photo = [MagicMock(file_id="file_abc")]
    update.message.reply_text = AsyncMock()
    update.effective_chat.id = 123
    return update


def _make_context(user_data=None):
    context = MagicMock()
    context.bot.send_chat_action = AsyncMock()
    context.bot.get_file = AsyncMock()
    context.bot.get_file.return_value.download_as_bytearray = AsyncMock(
        return_value=bytearray(b"fake_image_bytes")
    )
    context.user_data = user_data if user_data is not None else {}
    return context


def _clear_transaction(overrides=None):
    t = {
        "amount": 7.57, "type": "Expense", "description": "groceries",
        "category": "Food", "is_impulse": False, "confidence": 0.95,
        "needs_clarification": False, "clarification_question": "",
        "date": "2026-06-08", "timestamp": "2026-06-08 10:00:00",
        "week_start": "2026-06-02", "month": "2026-06",
    }
    if overrides:
        t.update(overrides)
    return t


async def test_handle_photo_empty_result_sends_error():
    update = _make_photo_update()
    context = _make_context()

    with patch("app.commands.parse_image", return_value=[]):
        from app.commands import handle_photo
        await handle_photo(update, context)

    reply = update.message.reply_text.call_args[0][0]
    assert "Couldn't read" in reply
    assert "image_session" not in context.user_data


async def test_handle_photo_clear_transactions_skips_to_confirmation():
    update = _make_photo_update()
    context = _make_context()
    transactions = [_clear_transaction()]

    with patch("app.commands.parse_image", return_value=transactions):
        from app.commands import handle_photo
        await handle_photo(update, context)

    assert context.user_data["image_session"]["awaiting_confirmation"] is True
    reply = update.message.reply_text.call_args[0][0]
    assert "Ready to log" in reply
    assert "groceries" in reply


async def test_handle_photo_unclear_transaction_asks_first_question():
    update = _make_photo_update()
    context = _make_context()
    transactions = [
        _clear_transaction({
            "description": "ticketing", "amount": 351.98, "category": "Other",
            "confidence": 0.4, "needs_clarification": True,
            "clarification_question": "TicketingPayments -€351.98 — what was this for?",
            "date": "2026-06-07",
        })
    ]

    with patch("app.commands.parse_image", return_value=transactions):
        from app.commands import handle_photo
        await handle_photo(update, context)

    session = context.user_data["image_session"]
    assert session["awaiting_confirmation"] is False
    assert session["cursor"] == 0
    reply = update.message.reply_text.call_args[0][0]
    assert "TicketingPayments" in reply


async def test_handle_photo_mixed_transactions_asks_first_unclear_only():
    update = _make_photo_update()
    context = _make_context()
    transactions = [
        _clear_transaction(),  # clear
        _clear_transaction({
            "description": "gelredome", "needs_clarification": True,
            "clarification_question": "What was Gelredome?", "category": "Other",
        }),  # unclear
    ]

    with patch("app.commands.parse_image", return_value=transactions):
        from app.commands import handle_photo
        await handle_photo(update, context)

    session = context.user_data["image_session"]
    assert len(session["clarifications"]) == 1
    assert session["clarifications"][0][0] == 1  # index of unclear transaction
    reply = update.message.reply_text.call_args[0][0]
    assert "Gelredome" in reply
