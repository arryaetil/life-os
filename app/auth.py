from telegram import Update
from telegram.ext import ContextTypes
from app import config


def is_owner(update: Update) -> bool:
    owner_id = config.TELEGRAM_OWNER_CHAT_ID
    if not owner_id:
        return False
    return str(update.effective_chat.id) == str(owner_id)


def owner_only(handler):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_owner(update):
            await update.message.reply_text("Unauthorized.")
            return
        return await handler(update, context)
    return wrapper
