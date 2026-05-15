import logging
import os
import httpx

_log = logging.getLogger(__name__)


def send_telegram_message(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_OWNER_CHAT_ID", "")

    if not token:
        _log.warning("TELEGRAM_BOT_TOKEN is not set")
        return False
    if not chat_id:
        _log.warning("TELEGRAM_OWNER_CHAT_ID is not set")
        return False

    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10.0,
        )
        if response.status_code == 200:
            return True
        _log.warning("Telegram API returned %s: %s", response.status_code, response.text)
        return False
    except Exception as e:
        _log.warning("Failed to send Telegram message: %s", e)
        return False
