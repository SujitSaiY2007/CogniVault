# Supabase Free setup for CogniVault

This PR introduces durable username/password accounts, private uploaded materials, and account-scoped learner progress snapshots. Apply the schema and configure the backend before deployment.

## Supabase project preparation

1. Create a Supabase project on the Free plan.
2. Open **SQL Editor** and run the complete file [001_cognivault_tenant_storage.sql](../supabase/migrations/001_cognivault_tenant_storage.sql).
3. In **Project Settings → API**, copy the project URL and the server-side service-role key. Do not place the service-role key in the frontend, GitHub, a public environment variable, or a browser bundle.
4. Set these Render backend environment variables:
   - `SUPABASE_URL` — project URL
   - `SUPABASE_SERVICE_ROLE_KEY` — server-only service role key
5. Confirm the Supabase project has the private `user-materials` bucket created by the SQL migration.
6. Check Supabase usage metrics after initial test upload and learner progress.

## Free-plan guardrails

- 25 MB maximum upload per file (API enforced).
- 10 uploaded files per username.
- 100 MB private file storage quota per username.
- 2,000 evidence chunks per uploaded file and 10,000 chunks per username.
- 800 MB project-wide object-storage soft ceiling (leaves headroom under Supabase Free 1 GB).
- Evidence insertion uses batches of 100 records.
- Search results are capped at 10 and simple lexical retrieval is bounded to 5,000 stored chunks per user per search. Source evidence listing uses bounded 1,000-row pages.
- The Free plan is a finite quota, not a guarantee of unlimited usage or continuous uptime. Supabase may pause projects for inactivity; Render Free may sleep. AI provider usage also has its own quota.

These limits are deliberately conservative. They are app-side ceilings; overall project quotas remain shared by all accounts and must be monitored.

## Tenant model

- Account and session records are held in Supabase Postgres.
- Passwords are PBKDF2-HMAC-SHA256 hashes with a per-user random salt; plaintext passwords are never persisted.
- Sessions store SHA-256 hashes of opaque bearer tokens and expire after 30 days.
- User source and evidence rows are keyed by the validated learner/account owner.
- Original uploads live in the private Storage bucket under server-generated owner/source paths.
- Learner progress snapshots are owner-specific; the backend hydrates only that learner's rows into its working SQLite service and saves them back after state-changing learner operations.
- Tables enable RLS and revoke direct browser roles. All Supabase service-role usage is server-side only.

## Local development

Without Supabase environment variables, the app retains its local SQLite auth behavior for development/tests. Private durable upload APIs intentionally return 503 until Supabase is configured. Production must set both Supabase variables.

## Deployment gate

Before deploying, verify:
- signup/login/logout persists across backend restart;
- account A cannot list/read/search account B's source IDs or evidence;
- uploaded original bytes survive Render restart;
- learner mastery and misconception state survives restart;
- SQL migration applied successfully;
- Render environment variables are set securely.

Legacy users created in the former Render-local SQLite auth store are not automatically migrated by this schema. They may need to recreate their username account unless a deliberate one-time migration of the old database is available.
