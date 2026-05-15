#!/usr/bin/env python3
"""
Comprehensive handoff generator. Run before ending a Claude session.

Writes:
  - handoff/latest.md        (human-readable handoff)
  - handoff/start_next_session_prompt.md  (updated, for next account)

Updates agent_state in PostgreSQL and sends a Telegram notification.

Usage:
    python scripts/create_handoff.py
"""
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from app.telegram import send_telegram_message
from app.database import write_agent_state, read_latest_agent_state

HANDOFF_PATH = REPO_ROOT / "handoff" / "latest.md"
STARTUP_PROMPT_PATH = REPO_ROOT / "handoff" / "start_next_session_prompt.md"

STARTUP_PROMPT = """\
# LifeOS — Next Session Startup Prompt

Paste this as your first message when starting a new Claude session on this repo.

---

I'm continuing work on the LifeOS repo (finance-lifeos).

Please read in this order before doing anything:
1. CLAUDE.md
2. docs/architecture.md
3. docs/current-status.md
4. handoff/latest.md

Then:
- Confirm the current state
- Run `pytest` and confirm all tests pass
- Ask what I'd like to work on next

Rules:
- Do NOT rebuild existing functionality
- Do NOT modify existing passing tests
- Do NOT change the database schema without explicit instruction
- Do NOT commit broken code
- Notify me via `python scripts/notify_me.py` when decisions, blockers, or completions occur
"""

TELEGRAM_MESSAGE = (
    "🔄 Session handoff needed.\n"
    "Switch account now.\n\n"
    "1. Run: claude logout\n"
    "2. Run: claude login\n"
    "3. Open this repo\n"
    "4. Read handoff/latest.md"
)


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT)] + args,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _build_handoff(now: str, git_status: str, git_log: str, last_state: dict | None) -> str:
    files_section = git_status if git_status else "No uncommitted changes."
    log_section = git_log if git_log else "No recent commits."
    s = last_state or {}
    current_module = s.get("current_module") or "Unknown"
    current_task = s.get("current_task") or "Unknown"
    next_task = s.get("next_task") or "See docs/current-status.md"
    blocker = s.get("blocker") or "None"

    return f"""\
# Handoff — {now}

## What Was Done
- Session ended. See recent commits below.
- Last module: {current_module}
- Last task: {current_task}

## Files Changed
{files_section}

## Recent Commits
{log_section}

## Current State
Session handoff triggered. Review git log and docs/current-status.md for full picture.

## Bugs / Blockers
{blocker}

## Next Exact Task
{next_task}

## Startup Prompt
See handoff/start_next_session_prompt.md — paste it as your first message in the new session.

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
- Never modify the transactions table schema.
- Never delete files without explicit approval.
"""


def main() -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    git_status = _git(["status", "--short"])
    git_log = _git(["log", "--oneline", "-5"])
    last_state = read_latest_agent_state()

    content = _build_handoff(now, git_status, git_log, last_state)

    try:
        HANDOFF_PATH.parent.mkdir(parents=True, exist_ok=True)
        HANDOFF_PATH.write_text(content, encoding="utf-8")
        print(f"✓ Handoff written to {HANDOFF_PATH}")
    except Exception as e:
        print(f"✗ Could not write handoff file: {e}")

    try:
        STARTUP_PROMPT_PATH.write_text(STARTUP_PROMPT, encoding="utf-8")
        print(f"✓ Startup prompt written to {STARTUP_PROMPT_PATH}")
    except Exception as e:
        print(f"✗ Could not write startup prompt: {e}")

    write_agent_state({
        "status_type": "handoff",
        "severity": "warning",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": "Session handoff created.",
        "git_summary": git_log,
        "handoff_path": "handoff/latest.md",
        "startup_prompt_path": "handoff/start_next_session_prompt.md",
        "current_module": (last_state or {}).get("current_module"),
        "next_task": (last_state or {}).get("next_task"),
    })

    sent = send_telegram_message(TELEGRAM_MESSAGE)
    if sent:
        print("✓ Telegram notification sent.")
    else:
        print("✗ Telegram notification failed (handoff files still written).")


if __name__ == "__main__":
    main()
