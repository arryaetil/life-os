#!/usr/bin/env python3
"""Thin command surface for operating the Career Agent through Codex."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import database
from app.career import build_application_document


def _print(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operate the Life OS Career Agent")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="Show the current Career dashboard state")

    run = commands.add_parser("run", help="Run the idempotent daily Career scan")
    run.add_argument("--date")
    run.add_argument("--minimum-score", type=int, default=65)

    approve = commands.add_parser("approve", help="Approve reviewed materials for manual submission")
    approve.add_argument("application_id", type=int)

    sent = commands.add_parser("contact-sent", help="Record outreach that the user sent manually")
    sent.add_argument("contact_id", type=int)

    export = commands.add_parser("export", help="Export verified application materials")
    export.add_argument("application_id", type=int)
    export.add_argument("kind", choices=("cv", "motivation"))
    export.add_argument("format", choices=("docx", "pdf"))
    export.add_argument("output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    database.init_db()
    try:
        if args.command == "status":
            _print(database.get_career_dashboard())
        elif args.command == "run":
            _print(database.run_career_daily(args.date, args.minimum_score))
        elif args.command == "approve":
            _print(database.approve_career_application(args.application_id))
        elif args.command == "contact-sent":
            database.mark_career_contact_sent(args.contact_id)
            _print({"ok": True, "boundary": "Recorded only; Life OS sent no message."})
        elif args.command == "export":
            application, job = database.get_career_application_bundle(args.application_id)
            document = build_application_document(application, job, args.kind, args.format)
            args.output.write_bytes(document.read())
            _print({"ok": True, "output": str(args.output.resolve())})
    except (LookupError, ValueError) as exc:
        _print({"ok": False, "error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
