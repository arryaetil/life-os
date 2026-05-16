# Handoff — 2026-05-16 10:26 UTC

## What Was Done
- Session ended. See recent commits below.
- Last module: Unknown
- Last task: Unknown

## Files Changed
M docs/current-status.md
 M handoff/latest.md
?? .obsidian/
?? 2026-05-15.md
?? Untitled.canvas
?? docs/superpowers/plans/2026-05-15-module-1-1-net-worth.md
?? docs/superpowers/plans/2026-05-15-module-1-1-refinements.md

## Recent Commits
55d4b76 feat(1.1): refine net worth dashboard — monthly change KPI, live NW, single 30K goal, live chart point
e5d4ebc feat(1.1): dashboard uses live net worth and monthly change KPI
4aa12cb test(1.1): add parser test for 'net worth 15k' k-suffix without breakdown
b43acc1 feat(1.1): use live net worth in cmd_networth and cmd_goal; single 30K goal
f932a25 fix(1.1): sort pre-month history defensively in calculate_monthly_change

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
