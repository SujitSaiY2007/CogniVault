# Chat Continuity Protocol

## Roles
- User: product owner and final visual acceptance.
- ChatGPT: coordinator, reviewer, evidence interpreter and continuity maintainer.
- Antigravity: repository executor.

## Every chat begins
Read `PROJECT_STATE.md`, `CURRENT_OBJECTIVE.md`, `CURRENT_HANDOFF.md`, `NEXT_CHAT_PROMPT.md` and the relevant phase report. Fetch actual Git refs. Ask for pending AG output before issuing duplicate tasks.

## During work
Use one scoped task at a time. Preserve uploads and branches. Distinguish specified/reported/tested/browser-accepted/submitted. AppTest does not replace browser acceptance. Do not advance to another UI screen until user approves current screen.

## Every closure
Inspect final refs/diff; accurately record tests and browser checks; update README and all relevant control docs; preserve historical decisions as history; keep user PDFs untouched; create the next numbered prompt and name its first action; list all incomplete items.

## Branch policy
No deletion, rename, reset, force-push or merge into main without explicit user authorization. PR #1 remains open/draft unless the user explicitly changes that decision.
