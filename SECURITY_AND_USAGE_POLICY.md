# Security & Usage Policy

## Secrets

- API keys belong only in local environment configuration or an approved secret manager.
- .env must never be committed.
- .env.example contains variable names only.
- No personal passwords or credentials belong in the repository.

## Demo Accounts

Use synthetic demo identities only. Do not store real user credentials or real student records.

## Learner Data

Store only the minimum data needed for the demo: learner ID, topic mastery state, assessment interaction metadata, and recommendation evidence. Avoid unnecessary personal attributes.

## Usage Controls

A lightweight quota layer controls:

- requests per user/session,
- model token usage where available,
- ingestion volume,
- assessment generation volume.

Actual limits are configuration values chosen after provider/model measurement. They are not cost guarantees.

## Failure Behavior

- API unavailable → explicit service-unavailable state; no fabricated output.
- Retrieval failure → insufficient-evidence state.
- Citation mapping failure → no grounded answer.
- Question verification failure → question rejected.
- Quota exceeded → explicit limit state.

## Source and License Safety

Do not commit large/private course files without permission. Track source provenance and licensing in the corpus manifest.

## Security Acceptance

A release cannot pass if repository scans reveal real credentials or if failure modes can silently fabricate grounded output.
