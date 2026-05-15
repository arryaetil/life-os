# Design: Session Handoff Notification v1

_Date: 2026-05-15_

## Overview

When a Claude Code session ends or nears its token limit, the agent writes a handoff file and sends a Telegram message prompting the user to switch accounts and continue. Telegram is the primary communication channel for all LifeOS modules — this feature establishes the foundational messaging utility.

---

## Components

### `app/telegram.py` (new)

Reusable Telegram messaging utility used by all current and future modules.

```python
send_telegram_message(text: str) -> bool
```

- Uses `httpx` (already in `requirements.txt`) for a synchronous POST to the Telegram Bot API
- Reads `TELEGRAM_BOT_TOKEN` and `TELEGRAM_OWNER_CHAT_ID` from environment
- Returns `True` on success, `False` on any failure
- Never raises — all errors are caught and printed; callers do not need try/except
- Does not log or transmit `.env` content or secrets

### `app/config.py` (modified)

Add one optional env var:

```python
TELEGRAM_OWNER_CHAT_ID: str = os.environ.get("TELEGRAM_OWNER_CHAT_ID", "")
```

`TELEGRAM_BOT_TOKEN` already exists. Both are optional at import time — the app does not break if either is missing; `send_telegram_message()` handles the missing-credential case gracefully.

### `scripts/handoff_notify.py` (new)

Standalone CLI script. Run manually when ending a session or when tokens are running low.

**Steps:**
1. Load `.env` via `python-dotenv`
2. Run `git status --short` and `git log --oneline -5` — capture output
3. Read current `handoff/latest.md` if it exists
4. Write updated `handoff/latest.md` using the CLAUDE.md handoff template, including:
   - Current date/time (UTC)
   - What was done (from existing handoff + git log)
   - Files changed (from `git status`)
   - Current state summary
   - Next recommended task
   - Startup prompt for the next Claude session
5. Call `send_telegram_message()` with the handoff notification text
6. Print confirmation or error to stdout

**Telegram message format:**
```
Claude session handoff needed.
Switch account now.

1. Run: claude logout
2. Run: claude login
3. Open this repo
4. Paste the startup prompt from handoff/latest.md
```

**Error behaviour (all non-fatal):**
| Failure | Behaviour |
|---------|-----------|
| Missing `TELEGRAM_BOT_TOKEN` | Print error, skip send, still write handoff |
| Missing `TELEGRAM_OWNER_CHAT_ID` | Print error, skip send, still write handoff |
| Telegram API error | Print error + HTTP status, still write handoff |
| `handoff/latest.md` write failure | Print error, still attempt send |

### `tests/test_telegram.py` (new)

Unit tests using `unittest.mock.patch` on `httpx.post`:

| Test | Scenario |
|------|----------|
| `test_send_success` | 200 response → returns `True` |
| `test_send_missing_token` | Empty `TELEGRAM_BOT_TOKEN` → returns `False`, prints error |
| `test_send_missing_chat_id` | Empty `TELEGRAM_OWNER_CHAT_ID` → returns `False`, prints error |
| `test_send_api_error` | Non-200 response → returns `False`, prints status |
| `test_send_network_failure` | `httpx` raises exception → returns `False`, prints error |

---

## Data Flow

```
scripts/handoff_notify.py
  ├── git status / git log
  ├── read handoff/latest.md
  ├── write handoff/latest.md (updated)
  └── app.telegram.send_telegram_message(text)
        └── POST api.telegram.org/bot{TOKEN}/sendMessage
              → returns True/False
```

---

## Environment Variables

| Variable | Required | Notes |
|----------|----------|-------|
| `TELEGRAM_BOT_TOKEN` | Yes (for send) | Already in config.py |
| `TELEGRAM_OWNER_CHAT_ID` | Yes (for send) | New — your personal chat ID |

To find your chat ID: message `@userinfobot` on Telegram.

---

## Files Changed

| File | Change |
|------|--------|
| `app/telegram.py` | Created |
| `app/config.py` | Add `TELEGRAM_OWNER_CHAT_ID` |
| `scripts/handoff_notify.py` | Created |
| `tests/test_telegram.py` | Created |
| `README.md` | Add usage section for handoff script |

---

## Out of Scope (v1)

- Automatic triggering (no hook or cron — manual run only)
- Rich Telegram message formatting (plain text only)
- Two-way Telegram commands for handoff acknowledgement
- Multiple chat IDs / group notifications
