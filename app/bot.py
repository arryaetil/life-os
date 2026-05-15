from telegram.ext import Application, CommandHandler, MessageHandler, filters
from app import config
from app.commands import (
    handle_message,
    cmd_start, cmd_help, cmd_today, cmd_week,
    cmd_month, cmd_income, cmd_undo, cmd_summary, cmd_budget,
)

def create_ptb_app() -> Application:
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("today", cmd_today))
    application.add_handler(CommandHandler("week", cmd_week))
    application.add_handler(CommandHandler("month", cmd_month))
    application.add_handler(CommandHandler("income", cmd_income))
    application.add_handler(CommandHandler("undo", cmd_undo))
    application.add_handler(CommandHandler("summary", cmd_summary))
    application.add_handler(CommandHandler("budget", cmd_budget))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    return application
