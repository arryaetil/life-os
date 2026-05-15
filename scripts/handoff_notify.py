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
