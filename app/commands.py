import logging
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes
from app import database as sheets, budget as budget_module, config
from app.parser import parse_message
from app.categories import get_category
from app.utils import format_currency

_log = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    try:
        parsed = parse_message(text)
    except ValueError:
        await update.message.reply_text(
            "Couldn't parse that. Try: '14 kebab' or '+314 DUO income'."
        )
        return

    category = get_category(parsed["description"])
    sheets.append_transaction(parsed, category)

    transactions = sheets.get_all_transactions()
    status = budget_module.calculate_weekly_status(transactions, config.WEEKLY_BUDGET)

    reply = (
        f"Logged: {format_currency(parsed['amount'])} — "
        f"{parsed['description']} — {category}.\n"
        f"Weekly spent: {format_currency(status['weekly_spent'])} / "
        f"{format_currency(status['weekly_budget'])}.\n"
        f"Remaining: {format_currency(status['remaining'])} "
        f"({100 - status['pct_used']:.0f}% left)."
    )
    await update.message.reply_text(reply)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Finance Logger ready.\n\n"
        "Log a transaction:\n"
        "  14 kebab\n"
        "  8.50 coffee\n"
        "  -50 dinner\n"
        "  +314 DUO\n"
        "  200 savings\n\n"
        "Commands: /help /today /week /month /income /undo /summary /budget"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Examples:\n"
        "  14 kebab          → expense, Food\n"
        "  8.50 coffee       → expense, Food\n"
        "  +314 DUO income   → income\n"
        "  200 savings       → transfer\n"
        "  100 degiro etf    → investment\n"
        "  25 impulse buy    → marked as impulse\n\n"
        "Prefix + for income. No prefix or - for expense.\n"
        "Transfer/investment detected from description."
    )


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    transactions = sheets.get_all_transactions()
    today_str = date.today().strftime("%Y-%m-%d")
    today_txns = [
        t for t in transactions
        if t["date"] == today_str
        and "[UNDONE]" not in (t["notes"] or "")
    ]

    if not today_txns:
        await update.message.reply_text("No transactions today.")
        return

    lines = [f"Today ({today_str}):"]
    total = 0.0
    for t in today_txns:
        lines.append(f"  {format_currency(t['amount'])} — {t['description']} — {t['category']}")
        if t["type"] == "Expense":
            total += t["amount"]
    lines.append(f"\nTotal spent: {format_currency(total)}")
    await update.message.reply_text("\n".join(lines))


async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    transactions = sheets.get_all_transactions()
    status = budget_module.calculate_weekly_status(transactions, config.WEEKLY_BUDGET)
    await update.message.reply_text(
        f"Week from {status['week_start']}:\n"
        f"Spent: {format_currency(status['weekly_spent'])} / {format_currency(status['weekly_budget'])}\n"
        f"Remaining: {format_currency(status['remaining'])} ({100 - status['pct_used']:.0f}% left)"
    )


async def cmd_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    transactions = sheets.get_all_transactions()
    summary = budget_module.calculate_monthly_summary(transactions)

    lines = [f"Month {summary['month']} — by category:"]
    for cat, amount in summary["by_category"].items():
        lines.append(f"  {cat}: {format_currency(amount)}")
    lines.append(f"\nTotal: {format_currency(summary['monthly_spent'])}")
    lines.append(f"Impulse: {format_currency(summary['impulse_total'])}")
    await update.message.reply_text("\n".join(lines))


async def cmd_income(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    transactions = sheets.get_all_transactions()
    summary = budget_module.calculate_monthly_summary(transactions)
    month = summary["month"]

    income_txns = [
        t for t in transactions
        if t["month"] == month
        and t["type"] == "Income"
        and "[UNDONE]" not in (t["notes"] or "")
    ]

    lines = [f"Income {month}:"]
    for t in income_txns:
        lines.append(f"  +{format_currency(t['amount'])} — {t['description']}")
    lines.append(f"\nTotal: {format_currency(summary['monthly_income'])}")
    await update.message.reply_text("\n".join(lines))


async def cmd_undo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    undone = sheets.undo_last_transaction()
    if not undone:
        await update.message.reply_text("No transactions to undo.")
        return
    amount = float(undone.get("amount", 0))
    desc = undone.get("description", "")
    await update.message.reply_text(f"Undone: {format_currency(amount)} — {desc}")


async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    transactions = sheets.get_all_transactions()
    weekly = budget_module.calculate_weekly_status(transactions, config.WEEKLY_BUDGET)
    monthly = budget_module.calculate_monthly_summary(transactions)
    top_cat = (
        max(monthly["by_category"], key=monthly["by_category"].get)
        if monthly["by_category"] else "—"
    )

    await update.message.reply_text(
        f"Summary:\n"
        f"Week: {format_currency(weekly['weekly_spent'])} / "
        f"{format_currency(weekly['weekly_budget'])} ({weekly['pct_used']:.0f}% used)\n"
        f"Month spent: {format_currency(monthly['monthly_spent'])}\n"
        f"Month income: {format_currency(monthly['monthly_income'])}\n"
        f"Net: {format_currency(monthly['net_cashflow'])}\n"
        f"Top: {top_cat}"
    )


async def cmd_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    transactions = sheets.get_all_transactions()
    status = budget_module.calculate_weekly_status(transactions, config.WEEKLY_BUDGET)
    pct = status["pct_used"]
    bar_filled = min(10, int(pct / 10))
    bar = "█" * bar_filled + "░" * (10 - bar_filled)

    await update.message.reply_text(
        f"Weekly budget:\n"
        f"[{bar}] {pct:.0f}%\n"
        f"{format_currency(status['weekly_spent'])} / {format_currency(status['weekly_budget'])}\n"
        f"Remaining: {format_currency(status['remaining'])}"
    )
