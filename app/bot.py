from telegram.ext import Application, CommandHandler, MessageHandler, filters
from app import config
from app.auth import owner_only
from app.commands import (
    handle_message, handle_photo,
    cmd_start, cmd_help, cmd_today, cmd_week,
    cmd_month, cmd_income, cmd_undo, cmd_summary, cmd_budget,
    cmd_status, cmd_next, cmd_git, cmd_handoff,
    cmd_networth, cmd_networth_history, cmd_goal, cmd_nw,
)

def create_ptb_app() -> Application:
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", owner_only(cmd_start)))
    application.add_handler(CommandHandler("help", owner_only(cmd_help)))
    application.add_handler(CommandHandler("today", owner_only(cmd_today)))
    application.add_handler(CommandHandler("week", owner_only(cmd_week)))
    application.add_handler(CommandHandler("month", owner_only(cmd_month)))
    application.add_handler(CommandHandler("income", owner_only(cmd_income)))
    application.add_handler(CommandHandler("undo", owner_only(cmd_undo)))
    application.add_handler(CommandHandler("summary", owner_only(cmd_summary)))
    application.add_handler(CommandHandler("budget", owner_only(cmd_budget)))
    application.add_handler(CommandHandler("status", owner_only(cmd_status)))
    application.add_handler(CommandHandler("next", owner_only(cmd_next)))
    application.add_handler(CommandHandler("git", owner_only(cmd_git)))
    application.add_handler(CommandHandler("handoff", owner_only(cmd_handoff)))
    application.add_handler(CommandHandler("networth", owner_only(cmd_networth)))
    application.add_handler(CommandHandler("networth_history", owner_only(cmd_networth_history)))
    application.add_handler(CommandHandler("goal", owner_only(cmd_goal)))
    application.add_handler(CommandHandler("nw", owner_only(cmd_nw)))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, owner_only(handle_message))
    )
    application.add_handler(
        MessageHandler(filters.PHOTO, owner_only(handle_photo))
    )

    return application
