# Handoff Notification v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable `send_telegram_message()` utility and a CLI script that writes `handoff/latest.md` and sends a Telegram handoff notification.

**Architecture:** `app/telegram.py` is a new, synchronous Telegram utility module imported by all future modules. `scripts/handoff_notify.py` is a standalone CLI that gathers git context, writes the handoff file, and calls the utility. Config gets one new optional env var.

**Tech Stack:** Python 3.13, httpx (already in requirements), python-dotenv, unittest.mock for tests.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `app/telegram.py` | Create | `send_telegram_message(text) -> bool` |
| `app/config.py` | Modify | Add `TELEGRAM_OWNER_CHAT_ID` optional env var |
| `scripts/handoff_notify.py` | Create | CLI: write handoff file + send notification |
| `tests/test_telegram.py` | Create | Unit tests for `send_telegram_message` |
| `README.md` | Modify | Add `TELEGRAM_OWNER_CHAT_ID` to env table + handoff script usage |

---

## Task 1: Add `TELEGRAM_OWNER_CHAT_ID` to config

**Files:**
- Modify: `app/config.py`

- [ ] **Step 1: Add the env var**

Open `app/config.py`. It currently ends at line 13. Add one line after the existing vars:

```python
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_WEBHOOK_SECRET: str = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./lifeos.db")
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
WEEKLY_BUDGET: float = float(os.environ.get("WEEKLY_BUDGET", "90"))
WEBHOOK_BASE_URL: str = os.environ.get("WEBHOOK_BASE_URL", "")
LOCAL_POLLING: bool = os.environ.get("LOCAL_POLLING", "false").lower() == "true"
TELEGRAM_OWNER_CHAT_ID: str = os.environ.get("TELEGRAM_OWNER_CHAT_ID", "")
```

- [ ] **Step 2: Verify existing tests still pass**

```bash
cd /Users/arryawillems/finance-lifeos && source .venv/bin/activate && pytest -q
```

Expected: `74 passed` — no regressions.

- [ ] **Step 3: Commit**

```bash
git add app/config.py
git commit -m "feat(config): add TELEGRAM_OWNER_CHAT_ID env var"
```

---

## Task 2: Create `app/telegram.py` (TDD)

**Files:**
- Create: `app/telegram.py`
- Create: `tests/test_telegram.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_telegram.py` with this exact content:

```python
import pytest
from unittest.mock import patch, MagicMock
from app.telegram import send_telegram_message


def test_send_success(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "12345")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("httpx.post", return_value=mock_resp):
        assert send_telegram_message("hello") is True


def test_send_missing_token(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "12345")
    assert send_telegram_message("hello") is False


def test_send_missing_chat_id(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "")
    assert send_telegram_message("hello") is False


def test_send_api_error(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "12345")
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad Request"
    with patch("httpx.post", return_value=mock_resp):
        assert send_telegram_message("hello") is False


def test_send_network_failure(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "12345")
    with patch("httpx.post", side_effect=Exception("connection refused")):
        assert send_telegram_message("hello") is False
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_telegram.py -v
```

Expected: `ImportError: cannot import name 'send_telegram_message' from 'app.telegram'` (module doesn't exist yet).

- [ ] **Step 3: Create `app/telegram.py`**

```python
import os
import httpx


def send_telegram_message(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_OWNER_CHAT_ID", "")

    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set")
        return False
    if not chat_id:
        print("ERROR: TELEGRAM_OWNER_CHAT_ID is not set")
        return False

    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10.0,
        )
        if response.status_code == 200:
            return True
        print(f"ERROR: Telegram API returned {response.status_code}: {response.text}")
        return False
    except Exception as e:
        print(f"ERROR: Failed to send Telegram message: {e}")
        return False
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_telegram.py -v
```

Expected:
```
tests/test_telegram.py::test_send_success PASSED
tests/test_telegram.py::test_send_missing_token PASSED
tests/test_telegram.py::test_send_missing_chat_id PASSED
tests/test_telegram.py::test_send_api_error PASSED
tests/test_telegram.py::test_send_network_failure PASSED
5 passed
```

- [ ] **Step 5: Run the full test suite**

```bash
pytest -q
```

Expected: `79 passed` (74 original + 5 new).

- [ ] **Step 6: Commit**

```bash
git add app/telegram.py tests/test_telegram.py
git commit -m "feat(telegram): add send_telegram_message utility with tests"
```

---

## Task 3: Create `scripts/handoff_notify.py`

**Files:**
- Create: `scripts/handoff_notify.py`

- [ ] **Step 1: Create the `scripts/` directory and the script**

```bash
mkdir -p /Users/arryawillems/finance-lifeos/scripts
```

Create `scripts/handoff_notify.py` with this exact content:

```python
#!/usr/bin/env python3
"""
Run this script at the end of a Claude session to write handoff/latest.md
and notify yourself via Telegram to switch accounts and continue.

Usage:
    python scripts/handoff_notify.py
"""
import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

from app.telegram import send_telegram_message  # noqa: E402 (after sys.path insert)

HANDOFF_PATH = REPO_ROOT / "handoff" / "latest.md"

TELEGRAM_MESSAGE = (
    "Claude session handoff needed.\n"
    "Switch account now.\n\n"
    "1. Run: claude logout\n"
    "2. Run: claude login\n"
    "3. Open this repo\n"
    "4. Paste the startup prompt from handoff/latest.md"
)


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT)] + args,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _build_handoff(now: str, git_status: str, git_log: str) -> str:
    files_section = git_status if git_status else "No uncommitted changes."
    log_section = git_log if git_log else "No recent commits."
    return f"""\
# Handoff — {now}

## What Was Done
- Session ended. See recent commits and git status below for context.

## Files Changed
{files_section}

## Recent Commits
{log_section}

## Current State
Session handoff triggered manually. Review git log above and docs/current-status.md for full picture.

## Bugs / Blockers
- None known. Verify with: pytest

## Next Exact Task
1. Read CLAUDE.md
2. Read docs/current-status.md
3. Read handoff/latest.md (this file)
4. Run pytest to confirm clean state
5. Continue from where the last session left off

## Startup Prompt
Paste this into your first message after logging in:

> I'm continuing work on the LifeOS repo (finance-lifeos).
> Please read CLAUDE.md, docs/current-status.md, and handoff/latest.md before doing anything.
> Then confirm the current state and ask what I'd like to work on next.

## Commands to Run
```bash
pytest
uvicorn app.dashboard:app --reload
```

## Environment Variables Needed
- TELEGRAM_BOT_TOKEN
- TELEGRAM_OWNER_CHAT_ID
- DATABASE_URL
- OPENAI_API_KEY
- WEBHOOK_BASE_URL
- WEEKLY_BUDGET (default: 90)
- LOCAL_POLLING (true for local dev)

## Do-Not-Touch Warnings
- See CLAUDE.md for full list.
"""


def main() -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    git_status = _git(["status", "--short"])
    git_log = _git(["log", "--oneline", "-5"])

    content = _build_handoff(now, git_status, git_log)

    try:
        HANDOFF_PATH.parent.mkdir(parents=True, exist_ok=True)
        HANDOFF_PATH.write_text(content, encoding="utf-8")
        print(f"✓ Handoff written to {HANDOFF_PATH}")
    except Exception as e:
        print(f"✗ Could not write handoff file: {e}")

    sent = send_telegram_message(TELEGRAM_MESSAGE)
    if sent:
        print("✓ Telegram notification sent.")
    else:
        print("✗ Telegram notification failed (handoff file still written).")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the script runs without crashing (missing creds are safe)**

```bash
cd /Users/arryawillems/finance-lifeos && source .venv/bin/activate && python scripts/handoff_notify.py
```

Expected output (if `TELEGRAM_OWNER_CHAT_ID` not set in `.env`):
```
✓ Handoff written to .../handoff/latest.md
ERROR: TELEGRAM_OWNER_CHAT_ID is not set
✗ Telegram notification failed (handoff file still written).
```

Verify the handoff file was written:
```bash
head -5 handoff/latest.md
```

Expected: First line is `# Handoff — <current date> UTC`.

- [ ] **Step 3: Run full test suite to confirm no regressions**

```bash
pytest -q
```

Expected: `79 passed`.

- [ ] **Step 4: Commit**

```bash
git add scripts/handoff_notify.py
git commit -m "feat(scripts): add handoff_notify.py CLI script"
```

---

## Task 4: Update README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add `TELEGRAM_OWNER_CHAT_ID` to the environment variables table**

In `README.md`, find the Environment Variables table. Add a new row after `TELEGRAM_BOT_TOKEN`:

```markdown
| `TELEGRAM_OWNER_CHAT_ID` | No | Your personal Telegram chat ID (message @userinfobot to find it) |
```

- [ ] **Step 2: Add a Session Handoff section**

Append this section before the `## Architecture` section in `README.md`:

```markdown
## Session Handoff

When a Claude Code session ends or nears its token limit, run this script to write a handoff file and receive a Telegram notification with instructions to switch accounts and continue:

```bash
python scripts/handoff_notify.py
```

This writes `handoff/latest.md` with current git state and a startup prompt for the next session, then sends a Telegram message to your `TELEGRAM_OWNER_CHAT_ID`.

Requires `TELEGRAM_OWNER_CHAT_ID` in your `.env`. Find your chat ID by messaging `@userinfobot` on Telegram.
```

- [ ] **Step 3: Run tests one final time**

```bash
pytest -q
```

Expected: `79 passed`.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add session handoff script usage and TELEGRAM_OWNER_CHAT_ID to README"
```

---

## Final Verification

- [ ] **Confirm test count**

```bash
pytest -v | tail -5
```

Expected: `79 passed, 0 failed`.

- [ ] **Confirm new files exist**

```bash
ls app/telegram.py scripts/handoff_notify.py tests/test_telegram.py
```

- [ ] **Confirm git log**

```bash
git log --oneline -5
```

Expected (newest first):
```
docs: add session handoff script usage and TELEGRAM_OWNER_CHAT_ID to README
feat(scripts): add handoff_notify.py CLI script
feat(telegram): add send_telegram_message utility with tests
feat(config): add TELEGRAM_OWNER_CHAT_ID env var
```
