from contextlib import asynccontextmanager
from telegram import Update
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app import config, database as sheets
from app import budget as budget_module
from app.bot import create_ptb_app
from app.utils import format_currency, budget_color

_ptb_app = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ptb_app
    sheets.init_db()          # Create table if not exists
    _ptb_app = create_ptb_app()
    await _ptb_app.initialize()
    await _ptb_app.start()

    if not config.LOCAL_POLLING and config.WEBHOOK_BASE_URL:
        await _ptb_app.bot.set_webhook(
            url=f"{config.WEBHOOK_BASE_URL}/webhook",
            secret_token=config.TELEGRAM_WEBHOOK_SECRET,
        )

    yield

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
    transactions = sheets.get_all_transactions()
    weekly = budget_module.calculate_weekly_status(transactions, config.WEEKLY_BUDGET)
    monthly = budget_module.calculate_monthly_summary(transactions)
    recent = list(reversed(transactions))[:10]
    return templates.TemplateResponse(request, "dashboard.html", {
        "active_page": "home",
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
    return templates.TemplateResponse(request, "transactions.html", {
        "active_page": "transactions",
        "transactions": list(reversed(transactions)),
    })
