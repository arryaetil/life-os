from contextlib import asynccontextmanager
from datetime import datetime
from telegram import Update
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app import config, database as sheets
from app import budget as budget_module
from app.bot import create_ptb_app
from app.utils import format_currency, budget_color, get_week_start, get_month
from app import networth as nw_module
from app.categories import get_category, get_available_categories

VALID_TRANSACTION_TYPES = {"Expense", "Income", "Transfer", "Investment"}

_ptb_app = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ptb_app
    sheets.init_db()
    _ptb_app = create_ptb_app()
    await _ptb_app.initialize()
    await _ptb_app.start()

    if not config.LOCAL_POLLING and config.WEBHOOK_BASE_URL:
        await _ptb_app.bot.set_webhook(
            url=f"{config.WEBHOOK_BASE_URL.rstrip('/')}/webhook",
            secret_token=config.TELEGRAM_WEBHOOK_SECRET,
        )

    from app.scheduler import create_scheduler
    _scheduler = create_scheduler()
    _scheduler.start()

    yield

    _scheduler.shutdown(wait=False)
    await _ptb_app.stop()
    await _ptb_app.shutdown()

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["format_currency"] = format_currency
templates.env.filters["budget_color"] = lambda pct: budget_color(pct)

@app.post("/webhook")
async def webhook(request: Request) -> Response:
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if config.TELEGRAM_WEBHOOK_SECRET and secret != config.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")
    data = await request.json()
    update = Update.de_json(data, _ptb_app.bot)
    await _ptb_app.process_update(update)
    return Response(status_code=200)

@app.get("/")
async def home(request: Request):
    return await financials_page(request)

@app.get("/expenses")
async def expenses_page(request: Request):
    transactions = sheets.get_all_transactions()
    weekly = budget_module.calculate_weekly_status(transactions, config.WEEKLY_BUDGET)
    monthly = budget_module.calculate_monthly_summary(transactions)
    recent = list(reversed(transactions))[:10]
    return templates.TemplateResponse(request, "dashboard.html", {
        "active_page": "expenses",
        "weekly": weekly,
        "monthly": monthly,
        "recent_transactions": recent,
    })

@app.get("/categories")
async def categories_page(request: Request):
    transactions = sheets.get_all_transactions()
    monthly = budget_module.calculate_monthly_summary(transactions)
    top_category = (
        max(monthly["by_category"], key=monthly["by_category"].get)
        if monthly["by_category"] else None
    )
    max_amount = max(monthly["by_category"].values()) if monthly["by_category"] else 1.0
    return templates.TemplateResponse(request, "categories.html", {
        "active_page": "categories",
        "monthly": monthly,
        "top_category": top_category,
        "max_amount": max_amount,
    })

@app.get("/transactions")
async def transactions_page(request: Request):
    transactions = sheets.get_all_transactions()
    sorted_txns = sorted(
        transactions,
        key=lambda t: (t.get("date", ""), t.get("timestamp", "")),
        reverse=True,
    )
    return templates.TemplateResponse(request, "transactions.html", {
        "active_page": "transactions",
        "transactions": sorted_txns,
    })

@app.get("/financials")
async def financials_page(request: Request):
    latest = sheets.get_latest_net_worth_snapshot()
    history = sheets.get_net_worth_history(limit=30)
    all_transactions = sheets.get_all_transactions()
    monthly = budget_module.calculate_monthly_summary(all_transactions)
    selected_range = request.query_params.get("range", "ALL").upper()
    if selected_range not in nw_module.CHART_RANGES:
        selected_range = "ALL"
    live_nw = nw_module.calculate_live_net_worth(latest, all_transactions)
    chart_series = nw_module.build_net_worth_chart_series(
        latest,
        all_transactions,
        chart_range=selected_range,
    )
    monthly_change = nw_module.calculate_previous_month_change(history)
    goals = [
        {**g, **nw_module.calculate_goal_progress(live_nw, g["target"])}
        for g in nw_module.GOALS
    ]
    allocation = []
    max_asset = 1.0
    if latest:
        raw = [
            {"label": "Cash",         "amount": latest["cash"],         "color": ""},
            {"label": "Investments",  "amount": latest["investments"],   "color": ""},
            {"label": "Crypto",       "amount": latest["crypto"],        "color": ""},
            {"label": "Savings",      "amount": latest["savings"],       "color": ""},
            {"label": "Other Assets", "amount": latest["other_assets"],  "color": ""},
            {"label": "Liabilities",  "amount": latest["liabilities"],   "color": "danger"},
        ]
        allocation = [a for a in raw if a["amount"] > 0]
        pos_amounts = [a["amount"] for a in allocation]
        max_asset = max(pos_amounts) if pos_amounts else 1.0
    chart_labels = [s["label"] for s in chart_series]
    chart_values = [s["total_net_worth"] for s in chart_series]
    activity_feed = nw_module.build_net_worth_activity_feed(latest, all_transactions)
    return templates.TemplateResponse(request, "networth.html", {
        "active_page": "financials",
        "latest": latest,
        "live_nw": live_nw,
        "history": history,
        "monthly": monthly,
        "monthly_change": monthly_change,
        "goals": goals,
        "allocation": allocation,
        "max_asset": max_asset,
        "chart_labels": chart_labels,
        "chart_values": chart_values,
        "chart_ranges": nw_module.CHART_RANGES,
        "selected_range": selected_range,
        "activity_feed": activity_feed,
    })

@app.get("/networth")
async def networth_page(request: Request):
    return await financials_page(request)


@app.put("/api/transactions/{tx_id}")
async def api_update_transaction(tx_id: int, request: Request):
    data = await request.json()
    tx = sheets.get_transaction_by_id(tx_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    sheets.update_transaction(tx_id, data)
    return JSONResponse({"ok": True})


@app.delete("/api/transactions/{tx_id}")
async def api_delete_transaction(tx_id: int):
    tx = sheets.get_transaction_by_id(tx_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    sheets.delete_transaction(tx_id)
    return JSONResponse({"ok": True})


@app.get("/api/categories")
async def api_get_categories():
    return JSONResponse(get_available_categories())


@app.post("/api/transactions")
async def api_create_transaction(request: Request):
    data = await request.json()

    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Amount must be a number")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")

    tx_type = data.get("type", "Expense")
    if tx_type not in VALID_TRANSACTION_TYPES:
        raise HTTPException(status_code=400, detail="Invalid transaction type")

    description = (data.get("description") or "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="Description is required")

    date_str = data.get("date") or datetime.now().strftime("%Y-%m-%d")
    try:
        tx_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")

    category = (data.get("category") or "").strip()
    if not category:
        category = get_category(description)

    parsed = {
        "timestamp": datetime.combine(tx_date, datetime.now().time()).strftime("%Y-%m-%d %H:%M:%S"),
        "date": tx_date.strftime("%Y-%m-%d"),
        "week_start": get_week_start(tx_date).strftime("%Y-%m-%d"),
        "month": get_month(tx_date),
        "type": tx_type,
        "amount": amount,
        "description": description,
        "is_impulse": bool(data.get("is_impulse", False)),
    }

    tx_id = sheets.append_transaction(parsed, category)
    return JSONResponse({"ok": True, "id": tx_id, "category": category})
