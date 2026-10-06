# Security & Usage Policy

## Secrets

- API keys belong only in local environment configuration or an approved secret manager.
- .env must never be committed.
- .env.example contains variable names only.
- No personal passwords or credentials belong in the repository.

## Demo Accounts

Use synthetic demo identities only. Do not store real user credentials.

## Usage Controls

A lightweight quota layer is planned to control:
- requests per user/session,
- model token usage,
- ingestion volume,
- assessment generation volume.

Actual limits will be selected after measuring the chosen API/model usage. No cost claim will be invented before measurement.

## Failure Behavior

- API unavailable → show service-unavailable state; do not fabricate output.
- Retrieval failure → report insufficient evidence.
- Citation mapping failure → do not present a grounded answer.
- Question verification failure → do not present the question.
- Quota exceeded → clearly report the limit.

## Privacy

Only the minimum learner data required for the demo should be stored. Demo data should be synthetic or user-provided for the session.
