#!/usr/bin/env python3
"""
Send a structured decision request to Telegram and write to agent_state.

Usage:
    python scripts/ask_user.py \
        --question "Which database should we use?" \
        --options "A) PostgreSQL — already in use" "B) SQLite — simpler, no infra" \
        --recommendation "A — PostgreSQL is already configured in Railway"
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from app.telegram import send_telegram_message
from app.database import write_agent_state


def format_decision_message(question: str, options: list[str], recommendation: str) -> str:
    lines = ["🤔 Decision needed:", question, "", "Options:"]
    lines.extend(options)
    if recommendation:
        lines += ["", "Recommendation:", recommendation]
    lines += ["", "Reply with A/B/C."]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a structured decision request to Telegram")
    parser.add_argument("--question", required=True, help="The decision question")
    parser.add_argument(
        "--options", nargs="+", required=True,
        help="Options list, e.g. 'A) PostgreSQL' 'B) SQLite'",
    )
    parser.add_argument(
        "--recommendation", default="",
        help="Short recommendation with reasoning, e.g. 'A — already configured'",
    )
    args = parser.parse_args()

    text = format_decision_message(args.question, args.options, args.recommendation)

    write_agent_state({
        "status_type": "decision",
        "severity": "warning",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": args.question,
        "metadata_json": json.dumps({
            "options": args.options,
            "recommendation": args.recommendation,
        }),
    })

    sent = send_telegram_message(text)
    if sent:
        print("Decision sent to Telegram. Waiting for user response.")
    else:
        print("✗ Telegram failed (state written to DB).")


if __name__ == "__main__":
    main()
