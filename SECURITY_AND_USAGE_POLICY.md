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
