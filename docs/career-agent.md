# Career Agent — Codex-first operation

Codex is the control plane. The `/career` dashboard is a protected, read-only view of opportunities, evidence, drafts and status.

## What to ask in chat

- “Run de Career Agent voor vandaag.”
- “Laat mijn beste vacature en de score-uitleg zien.”
- “Pas de motivatiebrief aan, maar gebruik alleen bevestigde feiten.”
- “Ik heb sollicitatie 1 gecontroleerd; keur de materialen goed.”
- “Exporteer het cv als PDF.”
- “Ik heb het LinkedIn-bericht zelf verstuurd; registreer dat.”
- “Voeg dit project als bevestigd bewijs toe aan mijn kennisbank.”

Codex translates those requests to the smallest matching command:

```bash
python3 scripts/career_agent.py status
python3 scripts/career_agent.py fact-set project "Project name" "Verified description" --status user_confirmed
python3 scripts/career_agent.py run
python3 scripts/career_agent.py approve 1
python3 scripts/career_agent.py export 1 cv pdf /tmp/cv.pdf
python3 scripts/career_agent.py contact-sent 1
```

Against Railway, run the same command with the production environment loaded. `CAREER_ACCESS_KEY` is unrelated to these commands: it only protects the browser page with HTTP Basic authentication (`lifeos` as username).

## Boundaries

- Approval never submits an application.
- Outreach is drafted only; the user sends it manually.
- CAPTCHA and ambiguous questions always stop for human input.
- Claims must already exist as user-confirmed or document-verified facts.

## Flagship GitHub portfolio

The Career knowledge base tracks four user-selected flagship projects:

1. [Life OS](https://github.com/arryaetil/life-os) — AI product development
2. [BackyardAI](https://github.com/arryaetil/poolpipeline) — visual AI with a commercial application
3. [KYC4etil](https://github.com/arryaetil/KYC4etil) — human-in-the-loop evidence research
4. [Network Economics Paper](https://github.com/arryaetil/07-network-paper) — network analysis and econometric research

These links and descriptions were verified against the public repository READMEs. Public profile pinning and repository edits remain separate actions.
