# Design: Photo Expense Logging via Telegram

**Date:** 2026-06-10  
**Status:** Approved

---

## Overview

Add the ability to send banking app screenshots (Bunq, iDEAL, Tikkie, Revolut, etc.) to the Telegram bot and have all visible transactions extracted, clarified, and logged with correct dates and categories. Manual text entry and regular conversation remain completely unchanged.

---

## Section 1: Image Parsing (`parser.py`)

### New function: `parse_image(photo_bytes: bytes) -> list[dict]`

1. Base64-encodes the photo bytes
2. Calls **GPT-4o** (vision) with a prompt tuned for Dutch/English banking screenshots
3. Prompt instructs GPT-4o to:
   - Extract every visible transaction
   - Resolve relative date headers ("Today", "Yesterday", "Monday 8 June") to real `YYYY-MM-DD` dates using today's date as anchor
   - Return a JSON array where each item has: `amount`, `type` (Expense/Income/Transfer/Investment), `description` (clean English lowercase), `category`, `is_impulse`, `source_date`, `confidence` (0.0–1.0), `needs_clarification` (bool), `clarification_question` (string or empty)
4. Each transaction dict gets time fields injected (`timestamp`, `date` = `source_date`, `week_start`, `month`) before being returned
5. On API error or unparseable image → returns empty list; handler shows a friendly error message

### Confidence / clarification rules (applied by GPT-4o in prompt)
- `confidence >= 0.8` and merchant is recognisable → no clarification needed
- Cryptic merchant codes (e.g. `BCK*SHELL HOGEWEI`, `EXPLOITATIE GELREDOME`) → GPT-4o asks a short natural-language question
- Missing or ambiguous amount sign → flagged for clarification

### Existing text parser (`parse_message`, `_ai_parse`, `_regex_parse`) is untouched.

---

## Section 2: Conversation State Machine (`commands.py`)

### New handler: `handle_photo`

Registered in `bot.py` with `filters.PHOTO`. Flow:

```
1. Download highest-resolution photo bytes from Telegram
2. Call parse_image(bytes)
3. If empty list → reply "Couldn't read any transactions from that screenshot. Try a clearer image."
4. Store session in context.user_data["image_session"]
5. If any transactions need clarification → ask first question
6. Else → skip straight to confirmation preview
```

### Session object (`context.user_data["image_session"]`)

```python
{
    "transactions": [...],          # full parsed list
    "clarifications": [(i, q), ...],# (transaction_index, question) for unclear ones
    "cursor": 0,                    # current clarification question index
    "awaiting_confirmation": False, # True when all questions answered
}
```

### Clarification loop

- Bot asks one natural-language question per unclear transaction
- User replies freely in any language (Dutch or English)
- GPT-4o-mini interprets the reply and updates `description` and `category` on that transaction, or marks it for skipping if the user says to ignore it
- After all questions answered → move to confirmation preview

### Confirmation preview

```
Ready to log 8 transactions:

1. 2026-06-10  bunq              -€20.00   (Fee)
2. 2026-06-09  Hr RHJ Winkens   +€10.00   (Income)
3. 2026-06-09  Esso Born         -€20.40   (Transport)
...

Reply 'yes' to log all, 'no' to cancel, or tell me which ones to leave out.
```

### Confirmation reply (natural language, processed by GPT-4o-mini)

User can say anything:
- *"yes"* / *"ja"* → log all
- *"no"* / *"nee"* → discard all, reply "Cancelled."
- *"leave out the bunq one"* / *"skip the investment transfer"* / *"don't log 1 and 7"* → GPT resolves to indices, logs the rest
- *"yes but not the ticketing payments"* → same

After logging: *"Logged 6 transactions. Skipped: bunq (-€20.00), TicketingPayments (-€351.98)."* + weekly budget status line.

### Priority 0 in `handle_message`

`handle_message` checks for `context.user_data.get("image_session")` before all other intent checks. If an active session exists, the text reply is routed to the session handler (clarification or confirmation). Otherwise falls through to the normal text flow unchanged.

---

## Section 3: Dashboard & Data Correctness

- Transactions logged from screenshots call the exact same `database.append_transaction()` as text-entered ones
- **No schema changes**
- `date` field is set to `source_date` extracted from the screenshot — `/today`, `/week`, `/month`, summary, and dashboard all reflect the correct historical date
- `description` is cleaned merchant name in English lowercase
- `category`, `type`, `is_impulse` go through the same `normalize_category` pipeline as text transactions
- Image-sourced transactions are indistinguishable from manually typed ones in the dashboard

---

## Section 4: Bot Registration (`bot.py`)

Two additions only:

```python
from app.commands import handle_photo  # new import

application.add_handler(
    MessageHandler(filters.PHOTO, owner_only(handle_photo))
)
```

All existing handlers remain unchanged.

---

## What Stays the Same

- Manual text entry (`14 kebab`, `8.50 koffie`) → unchanged
- Regular conversation / coaching → unchanged  
- All 179+ existing tests → untouched
- No database schema changes
- No new files — all changes in `parser.py`, `commands.py`, `bot.py`

---

## Environment Variables

No new env vars needed. Uses existing `OPENAI_API_KEY` for GPT-4o vision calls.

---

## Out of Scope

- PDF/receipt file imports
- CSV import
- Editing a logged transaction after confirmation
- Multi-photo sessions (one screenshot per message)
