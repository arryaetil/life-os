# Finance Life OS — Module 1

Telegram bot + web dashboard for logging personal expenses and income to Google Sheets.

## How It Works

Send a Telegram message → bot parses it → logs to Google Sheets → replies with budget status.
Open the dashboard → reads Google Sheets → shows spending overview.

## Message Format

| Message | Result |
|---|---|
| `14 kebab` | €14 expense, category auto-detected |
| `8.50 coffee` | €8.50 expense |
| `-50 dinner` | €50 expense (same as no prefix) |
| `+314 DUO` | €314 income |
| `200 savings` | transfer (keyword detected) |
| `100 degiro etf` | investment (keyword detected) |
| `25 impulse buy` | expense, marked as impulse |

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

## Setup

### 1. Create a Telegram Bot

1. Open Telegram → search `@BotFather`
2. Send `/newbot`, follow prompts
3. Copy the token → set `TELEGRAM_BOT_TOKEN` in `.env`

### 2. Google Sheets + Service Account

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project
3. Enable **Google Sheets API**
4. Go to **IAM & Admin → Service Accounts** → Create service account
5. Create a JSON key → download
6. Set `GOOGLE_SERVICE_ACCOUNT_JSON` to the entire file contents as a single line:
   ```bash
   cat your-key.json | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin)))"
   ```
7. Create a Google Sheet → copy the ID from the URL (`/d/<SHEET_ID>/edit`)
8. Set `GOOGLE_SHEET_ID` in `.env`
9. Share the sheet with the service account's `client_email`

### 3. Configure Environment

```bash
cp .env.example .env
# Fill in all values in .env
```

### 4. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running Locally

### Bot only (polling mode — no webhook needed)

```bash
source .venv/bin/activate
LOCAL_POLLING=true python run_polling.py
```

### Dashboard only

```bash
source .venv/bin/activate
uvicorn app.dashboard:app --reload --port 8000
```

Open http://localhost:8000

### Both together (local dev)

Terminal 1:
```bash
LOCAL_POLLING=true python run_polling.py
```

Terminal 2:
```bash
uvicorn app.dashboard:app --reload --port 8000
```

## Deploy to Railway

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add all environment variables from `.env.example` in Railway's settings:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_WEBHOOK_SECRET` (generate a random string)
   - `GOOGLE_SHEET_ID`
   - `GOOGLE_SERVICE_ACCOUNT_JSON`
   - `WEBHOOK_BASE_URL` = `https://your-app.railway.app`
   - `WEEKLY_BUDGET` = `90`
   - `LOCAL_POLLING` = `false`
4. Deploy — Railway uses the `Procfile` automatically
5. The webhook registers automatically on startup

> **Dashboard auth:** The dashboard is currently unprotected. Before sharing the URL, add HTTP Basic Auth to `app/dashboard.py` routes.

## Testing the Bot

After setup:
1. Find your bot in Telegram
2. Send `/start`
3. Send `14 kebab` — should reply with logged confirmation and budget status
4. Open your Railway URL to see the dashboard

## Testing the Dashboard

```bash
uvicorn app.dashboard:app --reload
```

Open http://localhost:8000 — shows empty state if no transactions yet.

## AI Category Fallback

Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (or both) in `.env`. The bot uses keyword matching first (free, instant) and only calls the AI when no keyword matches. Costs fractions of a cent per unknown transaction.

## Architecture

```
finance-lifeos/
  app/
    config.py      — environment variables
    utils.py       — currency formatting, date helpers
    parser.py      — parse Telegram message → structured dict
    categories.py  — keyword match + AI fallback
    budget.py      — weekly/monthly calculations
    sheets.py      — Google Sheets I/O
    commands.py    — Telegram bot handlers
    bot.py         — PTB Application factory
    dashboard.py   — FastAPI app (webhook + dashboard routes)
    templates/     — Jinja2 HTML templates
    static/        — CSS (liquid glass design system)
  tests/           — 70+ tests, all passing
  run_polling.py   — local dev: run bot without webhook
  Procfile         — Railway start command
```

## Recommended Next Upgrades

After the MVP works:

1. **Dashboard auth** — Add HTTP Basic Auth before sharing the URL
2. **Month/week selector** — Browse historical data in the dashboard
3. **Charts** — Add Chart.js bar/line charts for spending trends
4. **Module 2** — Habits & Routines tracker following the same pattern
5. **Net worth tracker** — Connect Degiro/bank data
6. **Weekly review** — Auto-generated summary every Monday
