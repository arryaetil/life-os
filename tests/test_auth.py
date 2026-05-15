from unittest.mock import AsyncMock, MagicMock, patch
from app.auth import is_owner, owner_only


def _make_update(chat_id: int) -> MagicMock:
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


# --- is_owner ---

def test_is_owner_returns_true_when_id_matches():
    update = _make_update(12345)
    with patch("app.auth.config") as mock_cfg:
        mock_cfg.TELEGRAM_OWNER_CHAT_ID = "12345"
        assert is_owner(update) is True


def test_is_owner_returns_false_when_id_mismatch():
    update = _make_update(99999)
    with patch("app.auth.config") as mock_cfg:
        mock_cfg.TELEGRAM_OWNER_CHAT_ID = "12345"
        assert is_owner(update) is False


def test_is_owner_returns_false_when_owner_id_not_configured():
    update = _make_update(12345)
    with patch("app.auth.config") as mock_cfg:
        mock_cfg.TELEGRAM_OWNER_CHAT_ID = ""
        assert is_owner(update) is False


# --- owner_only ---

async def test_owner_only_blocks_non_owner_with_unauthorized_reply():
    update = _make_update(99999)
    context = MagicMock()
    handler = AsyncMock()

    with patch("app.auth.config") as mock_cfg:
        mock_cfg.TELEGRAM_OWNER_CHAT_ID = "12345"
        wrapped = owner_only(handler)
        await wrapped(update, context)

    update.message.reply_text.assert_called_once_with("Unauthorized.")
    handler.assert_not_called()


async def test_owner_only_allows_owner_to_call_handler():
    update = _make_update(12345)
    context = MagicMock()
    handler = AsyncMock()

    with patch("app.auth.config") as mock_cfg:
        mock_cfg.TELEGRAM_OWNER_CHAT_ID = "12345"
        wrapped = owner_only(handler)
        await wrapped(update, context)

    handler.assert_called_once_with(update, context)
    update.message.reply_text.assert_not_called()
