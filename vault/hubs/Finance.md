# Finance Hub

[[LifeOS]] → Module 1.0 + 1.1

---

## Module 1.0 — Cashflow Tracker (DONE)

Natural language expense/income/transfer/investment logging via Telegram. AI parses messages (GPT-4o-mini → Claude Haiku → regex fallback). 12 categories, impulse flag detection.

**DB table:** `transactions`
Columns: id, timestamp, date, week_start, month, type, amount, description, category, tag, payment_type, is_impulse, is_necessary, notes

**Telegram commands:**
| Command | What it does |
|---------|-------------|
| `/start` | Welcome and usage |
| `/help` | Example messages |
| `/today` | Today's transactions |
| `/week` | Weekly spend vs budget |
| `/month` | Monthly by-category breakdown |
| `/income` | Monthly income summary |
| `/undo` | Mark last transaction undone |
| `/summary` | Compact weekly + monthly overview |
| `/budget` | ASCII progress bar |

**Dashboard routes:**
| Route | Content |
|-------|---------|
| `/` | Weekly KPIs, monthly summary, recent 10 |
| `/categories` | Monthly spend by category + progress bars |
| `/transactions` | Full transaction history |

---

## Module 1.1 — Net Worth Tracker (DONE)

Append-only net worth snapshots. Natural language input: "net worth cash 2k investments 8k savings 3k". AI parse + regex fallback with `k` suffix and `debt`→`liabilities` alias.

**DB table:** `net_worth_snapshots`
Columns: id, timestamp, cash, investments, crypto, savings, other_assets, liabilities, total_net_worth, notes

`total_net_worth` is always calculated at insert: `(cash + investments + crypto + savings + other_assets) − liabilities`

**Telegram commands:**
| Command | What it does |
|---------|-------------|
| `/networth` | Latest snapshot with breakdown |
| `/networth_history` | Last 5 snapshots with running delta |
| `/goal` | €25K and €30K progress with ASCII bars |

**Dashboard route:** `/networth`
- Net worth KPI card + change-since-last KPI
- Goal progress cards (€25K, €30K)
- Asset allocation bar chart
- Chart.js trend chart (shown when 2+ snapshots exist)
- Recent snapshots table

**Key files:**
- `app/networth_parser.py` — natural language → asset fields
- `app/networth.py` — goal calculations, delta, ASCII progress bar

---

## Finance Architecture

```
Telegram message
  → is_net_worth_message(text)?
    yes → networth_parser → create_net_worth_snapshot()
    no  → parse_message() → append_transaction()
  → reply with status/confirmation
```

---

## Finance Roadmap

- 1.2 Portfolio/Accounts Tracker — next
- 1.3 Screenshot/CSV Import
- 1.4 Proactive notifications (weekly summary, monthly review, NW reminder)
