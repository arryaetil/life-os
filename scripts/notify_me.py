#!/usr/bin/env python3
"""
Typed notification CLI for Claude to use during autonomous work.

Usage:
    python scripts/notify_me.py progress "Dashboard started"
    python scripts/notify_me.py decision "Choose DB" "A: PostgreSQL" "B: Supabase"
    python scripts/notify_me.py action "Add OPENAI_API_KEY to Railway"
    python scripts/notify_me.py error "Tests failing in test_budget.py"
    python scripts/notify_me.py complete "Net worth tracker done."
    python scripts/notify_me.py handoff
"""
import sys
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from app.telegram import send_telegram_message
from app.database import write_agent_state

STATUS_SEVERITY = {
    "progress": "info",
    "decision": "warning",
    "manual_action": "warning",
    "error": "error",
    "completion": "info",
    "handoff": "warning",
}

REQUIRES_ACTION = {
    "progress": False,
    "decision": True,
    "manual_action": True,
    "error": True,
    "completion": False,
    "handoff": True,
}

TYPE_ALIASES = {
    "action": "manual_action",
    "complete": "completion",
}


def _git_summary() -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "log", "--oneline", "-5"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _format_message(status_type: str, message: str, options: list[str]) -> str:
    if status_type == "progress":
        return f"✅ Progress: {message}"
    if status_type == "decision":
        lines = ["🤔 Decision needed:", message] + options + ["Reply with your choice."]
        return "\n".join(lines)
    if status_type == "manual_action":
        return f"🔧 Manual action needed:\n{message}\nReply DONE when complete."
    if status_type == "error":
        return f"❌ Error:\n{message}"
    if status_type == "completion":
        return f"🎉 Complete:\n{message}"
    if status_type == "handoff":
        return (
            "🔄 Session handoff needed.\n"
            "Switch account now.\n\n"
            "1. Run: claude logout\n"
            "2. Run: claude login\n"
            "3. Open this repo\n"
            "4. Read handoff/latest.md"
        )
    return f"📌 {message}"


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("Usage: notify_me.py <type> [message] [options...]")
        print("Types: progress, decision, action, error, complete, handoff")
        sys.exit(1)

    raw_type = args[0]
    message = args[1] if len(args) > 1 else ""
    options = args[2:] if len(args) > 2 else []

    status_type = TYPE_ALIASES.get(raw_type, raw_type)

    if status_type not in STATUS_SEVERITY:
        print(f"Unknown type: {raw_type}. Valid: progress, decision, action, error, complete, handoff")
        sys.exit(1)

    telegram_text = _format_message(status_type, message, options)
    git_summary = _git_summary()
    metadata = json.dumps({"options": options}) if options else None

    write_agent_state({
        "status_type": status_type,
        "severity": STATUS_SEVERITY[status_type],
        "requires_user_action": REQUIRES_ACTION[status_type],
        "resolved": False,
        "progress_message": message,
        "git_summary": git_summary,
        "metadata_json": metadata,
    })

    sent = send_telegram_message(telegram_text)
    if sent:
        print(f"✓ [{status_type}] Notification sent.")
    else:
        print(f"✗ [{status_type}] Telegram failed (state written to DB).")


if __name__ == "__main__":
    main()
