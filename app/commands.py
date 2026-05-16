import logging
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes
from app import database as sheets, budget as budget_module, config
from app.parser import parse_message
from app.categories import get_category
from app.utils import format_currency
from app.networth_parser import is_net_worth_message, parse_net_worth_message
from app.networth import GOALS, calculate_goal_progress, ascii_progress_bar, calculate_live_net_worth

_log = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if is_net_worth_message(text):
        await _handle_net_worth_message(update, context, text)
        return
    try:
        parsed = parse_message(text)
    except ValueError:
        await update.message.reply_text(
            "I couldn't find an amount in that message.\n\n"
            "Try something like:\n"
            "  14 kebab\n"
            "  spent 8.50 on coffee\n"
            "  +314 DUO income"
        )
        return

    # Use AI-provided category if available, otherwise keyword/AI fallback
    category = parsed.get("category") or get_category(parsed["description"])

    sheets.append_transaction(parsed, category)

    transactions = sheets.get_all_transactions()
    status = budget_module.calculate_weekly_status(transactions, config.WEEKLY_BUDGET)

    pct_left = 100 - status["pct_used"]
    if pct_left < 10:
        budget_note = "⚠️ Almost out of budget!"
    elif pct_left < 25:
        budget_note = "Getting close to your limit."
    else:
        budget_note = f"{pct_left:.0f}% of weekly budget left."

    reply = (
        f"Got it — {format_currency(parsed['amount'])} on {parsed['description']} ({category}).\n"
        f"Weekly: {format_currency(status['weekly_spent'])} / {format_currency(status['weekly_budget'])}. "
        f"{budget_note}"
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


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app import database
    state = database.read_latest_agent_state()
    if not state:
        await update.message.reply_text(
            "No state recorded yet.\n"
            "Run: python scripts/notify_me.py progress \"message\""
        )
        return
    ts = (state.get("timestamp") or "")[:16].replace("T", " ")
    lines = [f"📊 Status — {ts} UTC\n"]
    if state.get("current_module"):
        lines.append(f"Module: {state['current_module']}")
    if state.get("current_task"):
        lines.append(f"Task: {state['current_task']}")
    if state.get("progress_message"):
        lines.append(f"Progress: {state['progress_message']}")
    lines.append(f"Blocker: {state.get('blocker') or 'None'}")
    if state.get("git_summary"):
        first_line = state["git_summary"].splitlines()[0]
        lines.append(f"Git: {first_line}")
    await update.message.reply_text("\n".join(lines))


async def cmd_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app import database
    state = database.read_latest_agent_state()
    if not state or not state.get("next_task"):
        await update.message.reply_text("No next task recorded yet.")
        return
    ts = (state.get("timestamp") or "")[:16].replace("T", " ")
    await update.message.reply_text(
        f"⏭ Next task:\n{state['next_task']}\n(Recorded: {ts} UTC)"
    )


async def cmd_git(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app import database
    state = database.read_latest_agent_state()
    if not state or not state.get("git_summary"):
        await update.message.reply_text("No git summary recorded yet.")
        return
    ts = (state.get("timestamp") or "")[:16].replace("T", " ")
    await update.message.reply_text(
        f"🔀 Git summary:\n{state['git_summary']}\n(Recorded: {ts} UTC)"
    )


async def cmd_handoff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app import database
    state = database.read_latest_agent_state(status_type="handoff")
    if not state:
        await update.message.reply_text(
            "No handoff recorded yet.\n"
            "Run: python scripts/create_handoff.py"
        )
        return
    ts = (state.get("timestamp") or "")[:16].replace("T", " ")
    lines = [f"🔄 Last handoff: {ts} UTC\n"]
    if state.get("current_module"):
        lines.append(f"Module: {state['current_module']}")
    if state.get("next_task"):
        lines.append(f"Next: {state['next_task']}")
    lines.append("Read handoff/latest.md for full startup prompt.")
    await update.message.reply_text("\n".join(lines))


async def _handle_net_worth_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    from app import database
    fields = parse_net_worth_message(text)
    total = (
        fields.get("cash", 0.0) + fields.get("investments", 0.0)
        + fields.get("crypto", 0.0) + fields.get("savings", 0.0)
        + fields.get("other_assets", 0.0) - fields.get("liabilities", 0.0)
    )
    if total == 0.0 and all(v == 0.0 for v in fields.values()):
        await update.message.reply_text(
            "Couldn't parse net worth. Try:\n"
            "  net worth cash 2000 investments 5000\n"
            "  net worth cash 2k savings 3k crypto 500"
        )
        return
    database.create_net_worth_snapshot(fields)
    lines = ["✅ Net worth saved!\n"]
    for label, key in [("Cash", "cash"), ("Investments", "investments"),
                       ("Crypto", "crypto"), ("Savings", "savings"),
                       ("Other", "other_assets"), ("Liabilities", "liabilities")]:
        val = fields.get(key, 0.0)
        if val > 0:
            lines.append(f"  {label}: {format_currency(val)}")
    lines.append(f"\nTotal: {format_currency(total)}")
    await update.message.reply_text("\n".join(lines))


async def cmd_networth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app import database
    snap = database.get_latest_net_worth_snapshot()
    if not snap:
        await update.message.reply_text(
            "No net worth data yet.\n\n"
            "Log your first snapshot:\n"
            "  net worth cash 2000 investments 5000 savings 3000"
        )
        return
    transactions = database.get_all_transactions()
    live_nw = calculate_live_net_worth(snap, transactions)
    date_str = (snap.get("timestamp") or "")[:10]
    lines = ["💰 Net Worth (Live)\n"]
    lines.append(f"Total: {format_currency(live_nw)}")
    lines.append(f"Baseline ({date_str}): {format_currency(snap['total_net_worth'])}")
    for label, key in [("Cash", "cash"), ("Investments", "investments"),
                       ("Crypto", "crypto"), ("Savings", "savings"),
                       ("Other Assets", "other_assets"), ("Liabilities", "liabilities")]:
        val = snap.get(key, 0.0)
        if val > 0:
            lines.append(f"  {label}: {format_currency(val)}")
    await update.message.reply_text("\n".join(lines))


async def cmd_networth_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app import database
    history = database.get_net_worth_history(limit=5)
    if not history:
        await update.message.reply_text(
            "No net worth history yet.\n"
            "Send: net worth cash 2000 investments 5000"
        )
        return
    lines = ["📈 Net Worth History\n"]
    for i, snap in enumerate(history):
        date_str = (snap.get("timestamp") or "")[:10]
        total = snap["total_net_worth"]
        if i == 0:
            lines.append(f"{date_str}: {format_currency(total)}")
        else:
            prev = history[i - 1]["total_net_worth"]
            delta = total - prev
            sign = "+" if delta >= 0 else ""
            lines.append(f"{date_str}: {format_currency(total)} ({sign}{format_currency(delta)})")
    await update.message.reply_text("\n".join(lines))


async def cmd_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app import database
    snap = database.get_latest_net_worth_snapshot()
    if not snap:
        await update.message.reply_text(
            "No net worth data yet. Log a snapshot first:\n"
            "  net worth cash 2000 investments 5000"
        )
        return
    transactions = database.get_all_transactions()
    live_nw = calculate_live_net_worth(snap, transactions)
    lines = ["🎯 Financial Goals\n"]
    for goal in GOALS:
        progress = calculate_goal_progress(live_nw, goal["target"])
        bar = ascii_progress_bar(progress["pct"])
        if progress["achieved"]:
            lines.append(f"{goal['label']}: {bar} ✅ Achieved!")
        else:
            lines.append(
                f"{goal['label']}: {bar} {progress['pct']}%\n"
                f"  {format_currency(progress['remaining'])} to go"
            )
    await update.message.reply_text("\n".join(lines))
