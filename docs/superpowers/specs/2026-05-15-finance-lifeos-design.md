# Finance Life OS — Module 1: Personal Finance Logger + Dashboard
**Date:** 2026-05-15  
**Status:** Approved  
**Author:** Arrya Willems

---

## 1. Overview

Module 1 of a personal Life OS. A Telegram bot that logs expenses and income to Google Sheets, paired with a web dashboard that visualises the data. Built to be always-on, low-friction, and extensible into future modules (habits, goals, net worth, etc.).

**Core loop:**
1. Send a Telegram message → bot parses it → logs to Google Sheets → replies with budget status
2. Open the dashboard → reads Google Sheets → shows spending overview

---

## 2. Architecture

### Deployment
Single Railway web service. FastAPI is the backbone — it serves the dashboard AND receives Telegram webhook calls. On startup, FastAPI registers the Railway public URL with Telegram so messages flow in automatically. No polling loop.

```
You (Telegram) → HTTPS POST → Railway (/webhook)
                                     ↓
                               python-telegram-bot
                                     ↓
                    parser → category detector → sheets writer
                                     ↓
                             budget calculator
                                     ↓
                             Telegram reply ←

Browser → Railway (/ /categories /transactions)
                ↓
           FastAPI + Jinja2
                ↓
          Google Sheets reader
```

### Tech Stack
- **Python 3.11+**
- **FastAPI** — web framework, handles both webhook route and dashboard routes
- **Uvicorn** — ASGI server that listens for incoming HTTP connections
- **python-telegram-bot v20** — async Telegram bot library, webhook mode
- **gspread** — Google Sheets read/write via service account
- **openai / anthropic** — AI category fallback (whichever SDK key is available)
- **Jinja2** — HTML templating for dashboard pages
- **python-dotenv** — loads `.env` file into environment

### Source of Truth
Google Sheets is the only data store. No database. The dashboard reads fresh from Sheets on every page load.

---

## 3. Project Structure

```
finance-lifeos/
  app/
    bot.py           # PTB Application setup, webhook integration with FastAPI
    dashboard.py     # FastAPI app, all web routes
    config.py        # Reads env vars, exposes as Python constants
    parser.py        # Parses raw Telegram message → structured dict
    sheets.py        # All Google Sheets I/O (append row, read all rows)
    categories.py    # Keyword match + AI fallback categorisation
    budget.py        # Weekly budget calculations (no I/O, pure math)
    commands.py      # Telegram command handlers (/week, /today, /undo, etc.)
    utils.py         # Shared helpers (format currency, get week start, etc.)
    templates/
      base.html      # Shared layout, nav, CSS imports
      dashboard.html # Home page
      categories.html
      transactions.html
    static/
      style.css      # All styling — liquid glass design system
  requirements.txt
  .env.example
  .gitignore
  Procfile           # web: uvicorn app.dashboard:app --host 0.0.0.0 --port $PORT
```

---

## 4. Message Parsing

### Rules

| Message | Type | Amount | Description |
|---|---|---|---|
| `14 kebab` | Expense | 14.00 | kebab |
| `-50 dinner` | Expense | 50.00 | dinner |
| `8.50 coffee date` | Expense | 8.50 | coffee date |
| `+314 DUO income` | Income | 314.00 | DUO income |
| `+150 uncle` | Income | 150.00 | uncle |
| `200 savings` | Transfer | 200.00 | savings |
| `100 degiro etf` | Investment | 100.00 | degiro etf |

**Prefix logic:**
- `+` prefix → Income
- `-` prefix → Expense
- No prefix → Expense (default)

**Type override by keyword (no prefix needed):**
- Transfer keywords: `savings`, `portfolio`, `transfer`, `spaarrekening`
- Investment keywords: `degiro`, `etf`, `stock`, `crypto`, `invest`, `investing`

**Is_Impulse:** `True` only if the word `impulse` appears in the description.

**Unsupported fields** (left empty, fillable manually in Sheet): `Tag`, `Payment_Type`, `Is_Necessary`, `Notes`

### Parsing Flow
```
raw_text → strip prefix (+/-) → extract first number as amount
         → remaining text = description
         → check Investment/Transfer keywords → override Type if matched
         → pass to categories.py
```

---

## 5. Categorisation

### Flow
1. Keyword scan of description (case-insensitive, substring match)
2. If match found → return category (free, instant)
3. If no match → AI fallback:
   - If `OPENAI_API_KEY` set → call GPT-4o-mini
   - Elif `ANTHROPIC_API_KEY` set → call Claude Haiku
   - Else → return `"Other"`

### Keyword Map

| Category | Keywords |
|---|---|
| Food | lunch, dinner, coffee, kebab, snack, groceries, pizza, burger, sushi, sandwich, supermarket, takeaway, bread, ah, lidl, albert, aldi, jumbo, restaurant |
| Social | date, drinks, party, cinema, friends, bar, club, concert, festival, tickets |
| Transport | fuel, train, bus, uber, parking, taxi, metro, tram, ns, ov, benzine |
| Project | api, domain, hosting, software, tool, credits, subscription, server, claude, openai, railway |
| Health | gym, supplement, doctor, medicine, pharmacy, dentist, sport, fitness |
| Clothing | clothes, shoes, jacket, shirt, pants, zara, h&m, nike, adidas |
| Education | book, course, udemy, school, university, coursera |
| Impulse | impulse, random, unnecessary |
| Income | salary, duo, uncle, refund, gift, freelance, loon, salaris |
| Investment | etf, stock, crypto, degiro, investing |
| Transfer | savings, portfolio, transfer, spaarrekening |

### AI Fallback Prompt
```
You are a personal finance categorizer. Given this expense description, 
return exactly one category from this list:
Food, Social, Transport, Project, Health, Clothing, Education, Impulse, 
Income, Investment, Transfer, Other

Description: "{description}"
Reply with the category name only. No explanation.
```

---

## 6. Google Sheets Schema

Sheet name: `Transactions`

| Column | Type | Example | Source |
|---|---|---|---|
| ID | Integer | 42 | Auto-incremented (count existing rows + 1) |
| Timestamp | String | 2026-05-15 14:32:01 | `datetime.now()` |
| Date | String | 2026-05-15 | From timestamp |
| Week_Start | String | 2026-05-11 | Previous Monday |
| Month | String | 2026-05 | YYYY-MM |
| Type | String | Expense | From parser |
| Amount | Float | 14.00 | From parser |
| Description | String | kebab | From parser |
| Category | String | Food | From categories.py |
| Tag | String | _(empty)_ | Manual |
| Payment_Type | String | _(empty)_ | Manual |
| Is_Impulse | Boolean | FALSE | From parser |
| Is_Necessary | String | _(empty)_ | Manual |
| Notes | String | _(empty)_ | Manual |

The header row is row 1. All data appended from row 2 onward. `/undo` adds `"[UNDONE]"` to the Notes column of the last row rather than deleting it — history is preserved.

---

## 7. Budget System

- **Default weekly budget:** €90
- **Week:** Monday → Sunday
- **Scope:** Expenses only (Income/Transfer/Investment excluded from budget calc)

After every expense logged, the bot replies:
```
Logged: €14.00 — kebab — Food.
Weekly spent: €34.50 / €90.00.
Remaining: €55.50 (62% left).
```

Budget bar thresholds (for dashboard):
- < 75% used → blue
- 75–90% used → amber
- > 90% used → red

---

## 8. Telegram Commands

| Command | Description |
|---|---|
| `/start` | Welcome message, explains how to log transactions |
| `/help` | Show example messages and command list |
| `/today` | All transactions logged today |
| `/week` | Weekly spending total and remaining budget |
| `/month` | Monthly spending broken down by category |
| `/income` | Monthly income total and sources |
| `/undo` | Marks last transaction as undone (adds [UNDONE] to Notes) |
| `/summary` | Compact overview: week + month + top category |
| `/budget` | Current weekly budget status with progress |

---

## 9. Dashboard

### Pages

**`/` — Home**
- KPI cards: Weekly Spent, Weekly Remaining, Monthly Spent, Monthly Income, Net Cash Flow
- Weekly budget progress bar (colour changes at thresholds)
- Recent 10 transactions table

**`/categories` — Category Overview**
- Monthly spending by category (table + mini progress bars)
- Impulse spending total
- Biggest category this month highlighted

**`/transactions` — All Transactions**
- Full table, newest first
- Columns: Date, Type, Amount, Description, Category, Is_Impulse
- [UNDONE] rows visually dimmed

All pages show **current month / current week only**. No date selector in MVP.

> **AUTH TODO**: Before making the dashboard public, add authentication here. Recommended: HTTP Basic Auth via FastAPI dependency, or a simple secret token in the URL query param. Without this, anyone with the Railway URL can see your finances.

### Design System

**Brand:** CloudCast Analytics blue × Apple Liquid Glass

| Token | Value |
|---|---|
| Background | `#080c14` |
| Brand blue | `#3F5AF5` |
| Blue glow | `radial-gradient(ellipse at 50% 0%, rgba(63,90,245,0.15) 0%, transparent 70%)` |
| Glass background | `rgba(255,255,255,0.05)` |
| Glass border | `1px solid rgba(255,255,255,0.10)` |
| Glass border-top | `1px solid rgba(255,255,255,0.22)` (specular highlight) |
| Glass blur | `backdrop-filter: blur(40px) saturate(180%)` |
| Glass shadow | `0 8px 32px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.12)` |
| Card tint | `rgba(63,90,245,0.06)` |
| Border radius (cards) | `20px` |
| Border radius (pills) | `100px` |
| Font | Inter (Google Fonts) |
| Text primary | `#ffffff` |
| Text secondary | `rgba(255,255,255,0.50)` |
| Accent | `#3F5AF5` |
| Accent hover | `#5B76F7` |
| Warning | `#F59E0B` (amber) |
| Danger | `#EF4444` (red) |

**Layer depth:**
1. Background + glow (deepest)
2. Cards (blur: 40px, low tint)
3. Nav bar (blur: 60px, slightly more opaque)
4. Tooltips/modals (blur: 80px, most opaque)

---

## 10. Environment Variables

```env
TELEGRAM_BOT_TOKEN=        # From BotFather
TELEGRAM_WEBHOOK_SECRET=   # Random string, used to verify webhook calls
GOOGLE_SHEET_ID=           # From Google Sheets URL
GOOGLE_SERVICE_ACCOUNT_JSON= # Full JSON string of service account key
OPENAI_API_KEY=            # Optional — for AI category fallback
ANTHROPIC_API_KEY=         # Optional — fallback if OpenAI not set
WEEKLY_BUDGET=90           # Default weekly budget in EUR
LOCAL_POLLING=false        # Set to true for local dev (skips webhook, uses polling)
```

---

## 11. Deployment

### Railway
- Single web service
- Start command: `uvicorn app.dashboard:app --host 0.0.0.0 --port $PORT`
- Environment variables set in Railway dashboard
- On first deploy, register webhook: `https://your-app.railway.app/webhook`
- Railway provides HTTPS automatically — required for Telegram webhooks

### Procfile
```
web: uvicorn app.dashboard:app --host 0.0.0.0 --port $PORT
```

### Local development
- Bot + dashboard: `uvicorn app.dashboard:app --reload` (webhook won't work locally without a tunnel)
- For local bot testing: use ngrok to expose localhost, then register the ngrok URL as webhook
- Or: run bot in polling mode locally by setting `LOCAL_POLLING=true` env var

---

## 12. Future Modules (Life OS Roadmap)

This module is intentionally self-contained. Future modules will be added as separate apps or services:

- Module 2: Habits & Routines tracker
- Module 3: Goals & Projects
- Module 4: Net Worth tracker (assets, investments, savings)
- Module 5: Weekly Review dashboard
- Module 6: Calendar + email integrations
- Module 7: Unified Life OS dashboard

Each module will follow the same pattern: Telegram bot input → Google Sheets storage → FastAPI dashboard.
