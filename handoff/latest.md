# Handoff — 2026-05-16 12:10 UTC

## What Was Done
- Session ended. See recent commits below.
- Last module: Unknown
- Last task: Unknown

## Files Changed
?? .obsidian/
?? 2026-05-15.md
?? Untitled.canvas
?? docs/superpowers/plans/2026-05-15-module-1-1-net-worth.md
?? docs/superpowers/plans/2026-05-15-module-1-1-refinements.md
?? docs/superpowers/plans/2026-05-16-agent-control-ux-bugs.md
?? docs/superpowers/plans/2026-05-16-autonomous-session-protocol.md
?? docs/superpowers/plans/2026-05-16-conversational-agent-v1.md
?? docs/superpowers/plans/2026-05-16-nl-parsing-and-categories.md

## Recent Commits
a9ad123 feat(parser): ask clarification when AI signals low confidence instead of logging
2224a88 feat(parser): Dutch+English AI prompt, confidence/clarification support, Dutch regex fallback
b333802 feat(parser): add normalize_category — synonym map prevents category duplication
acb286a fix(1.1): normalize timestamp separator before comparison in calculate_live_net_worth
f172def docs(1.4): handoff after conversational agent v1

## Current State
Session handoff triggered. Review git log and docs/current-status.md for full picture.

## Bugs / Blockers
None

## Next Exact Task
See docs/current-status.md

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
