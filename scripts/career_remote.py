#!/usr/bin/env python3
"""Operate the live Career Agent over HTTPS, for Claude Code and Codex.

Needs LIFEOS_CAREER_KEY (the CAREER_ACCESS_KEY set in Railway) in the environment.
LIFEOS_URL defaults to the production dashboard. The key is never printed.
"""

import argparse
import json
import os
from pathlib import Path
import sys

import httpx

DEFAULT_URL = "https://lifeos-aw.up.railway.app"


def _print(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operate the live Life OS Career Agent")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="Show ranked jobs and the current application")
    commands.add_parser("discover", help="Fetch Adzuna vacancies now and score them")
    add = commands.add_parser("add-jobs", help="Send vacancies found by web research (JSON file, or - for stdin)")
    add.add_argument("file")
    add.add_argument("--agent", default="claude", help="Who found them, e.g. claude or codex")
    prepare = commands.add_parser("prepare", help="Prepare review materials for one job id")
    prepare.add_argument("job_id", type=int)
    approve = commands.add_parser("approve", help="Approve reviewed materials for manual submission")
    approve.add_argument("application_id", type=int)
    return parser


def request(method: str, path: str, client: httpx.Client, **kwargs) -> dict:
    response = client.request(method, path, **kwargs)
    if response.status_code == 401:
        return {"ok": False, "error": "Unauthorized: LIFEOS_CAREER_KEY does not match CAREER_ACCESS_KEY in Railway"}
    if response.status_code >= 400:
        return {"ok": False, "status": response.status_code, "error": response.text[:500]}
    return response.json()


def main(argv: list[str] | None = None, client: httpx.Client | None = None) -> int:
    args = build_parser().parse_args(argv)
    key = os.environ.get("LIFEOS_CAREER_KEY", "")
    if client is None and not key:
        _print({"ok": False, "error": "Set LIFEOS_CAREER_KEY in your environment first"})
        return 1
    client = client or httpx.Client(
        base_url=os.environ.get("LIFEOS_URL", DEFAULT_URL), auth=("lifeos", key), timeout=120,
    )
    with client:
        if args.command == "status":
            result = request("GET", "/api/career/status", client)
        elif args.command == "discover":
            result = request("POST", "/api/career/discover", client)
        elif args.command == "add-jobs":
            raw = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
            jobs = json.loads(raw)
            jobs = jobs.get("jobs", jobs) if isinstance(jobs, dict) else jobs
            result = request("POST", "/api/career/jobs", client, json={"jobs": jobs, "agent": args.agent})
        elif args.command == "prepare":
            result = request("POST", f"/api/career/jobs/{args.job_id}/prepare", client)
        else:
            result = request("POST", f"/api/career/applications/{args.application_id}/approve", client)
    _print(result)
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
