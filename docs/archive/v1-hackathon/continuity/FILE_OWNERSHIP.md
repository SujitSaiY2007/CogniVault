# File Ownership and Mutation Policy

## Immutable user-uploaded references
Do not edit, replace, rename, move or delete:
- `Important Details.pdf`
- `Multimodal AI Hackathon 2026 - Submission Guidelines.pdf`
- `Problem Statements.pdf`
- `Track D.pdf`

Use these materials as sources when needed; do not silently replace their rules with assumptions.

## Project-authored control documents
Root Markdown files and `docs/*.md` are project control files and should be reconciled when necessary, including README, architecture, objective, state, handoff, decisions, test/evaluation, demo/submission plans and Chat 0 technical lock status.

## Scaffold placeholders
Keep `app/.gitkeep`, `data/.gitkeep`, `evaluation/.gitkeep`, and `tests/.gitkeep` on main. They reflect the original scaffold. Do not delete folders without checking their purpose/history.

## Historical records
Preserve Chat 0 technical lock and prior-art rationale. Mark obsolete workflow instructions as historical/superseded instead of erasing history.

## Safety
Main's current update is documentation-only. Do not alter application code on main or imply that phase branches were merged.
