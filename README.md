# Life OS — Module 1: Personal Finance

Telegram bot + web dashboard for logging personal expenses and income. Send a natural message → bot understands it with AI → logs to PostgreSQL → replies with budget status. Dashboard visualises everything live.

**Live:** https://lifeos-aw.up.railway.app

## How It Works

Send anything natural to your bot → AI parses it → logged to database → budget status reply.
Open the dashboard → reads database → shows spending overview.

## Message Format

Just write naturally — the AI figures it out:

| Message | Result |
|---|---|
| `14 kebab` | €14 expense, Food |
| `spent 8.50 on coffee this morning` | €8.50 expense, Food |
| `filled up the car, 65 euros` | €65 expense, Transport |
| `+314 DUO` | €314 income |
| `just got 500 from uncle` | €500 income |
| `200 to savings` | transfer |
| `100 degiro etf` | investment |
| `25 impulse buy` | expense, marked as impulse |

No rigid format required. Prefix `+` for income if the AI misses it.

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome and usage guide |
| `/help` | Example messages |
| `/today` | Today's transactions |
| `/week` | Weekly spending and remaining budget |
| `/month` | Monthly breakdown by category |
| `/income` | Monthly income |
| `/undo` | Mark last transaction as undone |
| `/summary` | Compact weekly + monthly overview |
| `/budget` | Weekly budget progress bar |

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | From BotFather |
| `TELEGRAM_OWNER_CHAT_ID` | No | Your personal Telegram chat ID (message @userinfobot to find it) |
| `TELEGRAM_WEBHOOK_SECRET` | Yes | Any random string |
| `DATABASE_URL` | Yes | Auto-set by Railway PostgreSQL |
| `WEBHOOK_BASE_URL` | Yes | Your Railway app URL |
| `OPENAI_API_KEY` | Recommended | For AI message parsing |
| `ANTHROPIC_API_KEY` | Optional | Alternative to OpenAI |
| `WEEKLY_BUDGET` | No | Default: 90 |
| `LOCAL_POLLING` | No | Set `true` for local dev |

## Setup

### 1. Create a Telegram Bot

1. Open Telegram → search `@BotFather`
2. Send `/newbot`, follow prompts
3. Copy the token → set `TELEGRAM_BOT_TOKEN` in Railway

### 2. Deploy to Railway

1. Fork/clone this repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub → select this repo
3. Add a **PostgreSQL** database: New → Database → PostgreSQL (Railway auto-sets `DATABASE_URL`)
4. Set environment variables in your service:
   - `TELEGRAM_BOT_TOKEN` — from BotFather
   - `TELEGRAM_WEBHOOK_SECRET` — any random string e.g. `mysecret123`
   - `WEBHOOK_BASE_URL` — your Railway URL e.g. `https://lifeos-aw.up.railway.app`
   - `OPENAI_API_KEY` — from platform.openai.com
   - `WEEKLY_BUDGET` — `90`
   - `LOCAL_POLLING` — `false`
5. Deploy — Railway uses the `Procfile` automatically
6. Register the webhook once (replace with your values):
   ```
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<RAILWAY_URL>/webhook&secret_token=<SECRET>"
   ```

### 3. Local Development

```bash
git clone https://github.com/arryaetil/life-os
cd life-os
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in .env — DATABASE_URL defaults to local SQLite, no setup needed
```

**Run bot locally (polling mode — no webhook needed):**
```bash
LOCAL_POLLING=true python run_polling.py
```

**Run dashboard locally:**
```bash
uvicorn app.dashboard:app --reload --port 8000
```

Open http://localhost:8000

## AI Parsing

The bot uses GPT-4o-mini (or Claude Haiku as fallback) to understand natural language messages. It extracts amount, type, description, and category in one call — no rigid format required.

Falls back to keyword-based regex parsing if no AI key is set. Cost: fractions of a cent per message.

## Session Handoff

When a Claude Code session ends or nears its token limit, run this script to write a handoff file and receive a Telegram notification with instructions to switch accounts and continue:

```bash
python scripts/handoff_notify.py
```

This writes `handoff/latest.md` with current git state and a startup prompt for the next session, then sends a Telegram message to your `TELEGRAM_OWNER_CHAT_ID`.

Requires `TELEGRAM_OWNER_CHAT_ID` in your `.env`. Find your chat ID by messaging `@userinfobot` on Telegram.

## Architecture

```
life-os/
  app/
    config.py      — environment variables
    utils.py       — currency formatting, date helpers
    parser.py      — AI-powered message parser (regex fallback)
    categories.py  — keyword match + AI fallback categoriser
    budget.py      — weekly/monthly budget calculations
    database.py    — PostgreSQL I/O via SQLAlchemy
    commands.py    — Telegram bot handlers
    bot.py         — PTB Application factory
    dashboard.py   — FastAPI app (webhook + dashboard routes)
    templates/     — Jinja2 HTML templates (liquid glass UI)
    static/        — CSS design system
  tests/           — 74 tests, all passing
  run_polling.py   — local dev: run bot without webhook
  Procfile         — Railway start command
```

## Dashboard

Three pages at your Railway URL:

- **/** — Weekly/monthly KPIs + recent transactions
- **/categories** — Monthly spending by category with progress bars
- **/transactions** — Full transaction history

> **Auth note:** Dashboard is currently unprotected. Add HTTP Basic Auth before sharing the URL publicly.

## Life OS Roadmap

This is Module 1. Planned modules:

- Module 2: Habits & Routines tracker
- Module 3: Goals & Projects
- Module 4: Net Worth tracker (assets, investments, savings)
- Module 5: Weekly Review — auto-generated every Monday
- Module 6: Calendar + email integrations
- Module 7: Unified Life OS dashboard
