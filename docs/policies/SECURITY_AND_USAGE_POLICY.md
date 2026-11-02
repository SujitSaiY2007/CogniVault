# Security and Usage Policy

## Secrets
Keep keys in local environment or supported secret storage. Never commit .env, tokens or credentials. `.env.example` contains placeholders.

## Data
Use synthetic demo identities. Avoid real student personal data without appropriate lawful basis and safeguards. If multi-user hosting is implemented, enforce owner-level isolation for uploaded files and histories and document retention/deletion.

## Guest and registered-user direction
Guests may browse and use limited tutor/practice; guest history is session-only. Registered-user persistent history is required only where supported by real authentication and persistence. These are product decisions, not evidence of implementation.

## Usage limits
Planned limits include query counts, file size/count, storage, assessment attempts and request frequency. Enforce server-side. UI-only counters are not security. Do not invent remaining counts or promise zero cost.

## Public deployment gate
Verify auth, authorization, file validation, rate limits, durable storage, user isolation, retention/deletion, secrets, logging, provider terms and failure states. Public deployment is not verified complete.


---

## Final overhaul decision — 2026-10-11

The authoritative next-phase plan is [`docs/FINAL_OVERHAUL_PLAN.md`](docs/FINAL_OVERHAUL_PLAN.md). This section supersedes earlier forward-looking instructions where they conflict; prior entries remain preserved as history.

**Current direction:** controlled Agno-first overhaul with v0-generated Next.js/TypeScript frontend, Python Agno AgentOS backend, Ollama/local model baseline, SQLite + FTS5 + local ChromaDB, local embeddings, deterministic evidence/assessment verification, and existing BKT logic. See the final plan for exact decisions, acceptance gates, branch rules, and the only three executor prompts.

**Execution model:** exactly three implementation chats: (1) Agno/evidence foundation, (2) frontend and adaptive learning loop, (3) evaluation, hardening and submission. Implementation must proceed on dedicated phase branches; preserve all legacy Streamlit code, source data, tests, PDFs, and Git history. Do not force-push, reset, delete/rename branches, close/merge PR #1, change visibility, or merge implementation to main without explicit approval.

**Truthfulness gate:** the plan is locked; implementation and acceptance are not yet proven. Organizer requirements are the acceptance baseline. Never claim a requirement, test, metric, deployment, video or submission is complete without reproducible evidence.


## Final overhaul decision (2026-10-11)
The authoritative forward plan is `docs/FINAL_OVERHAUL_PLAN.md`. The stack is local-first: Agno AgentOS/Python, v0-generated Next.js frontend, Ollama, SQLite/FTS5 and local ChromaDB. Keep secrets server-side; never ship model/API keys to the browser or commit `.env`. Hosted free tiers are optional and must not be assumed unlimited. Preserve legacy code/history. The new stack is not accepted until tested.
