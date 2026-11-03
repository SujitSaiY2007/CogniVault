-- CogniVault durable account and private learning-material store.
-- Apply in Supabase SQL Editor before deploying the backend.
create extension if not exists pgcrypto;

create table if not exists public.cognivault_users (
  username text primary key check (username ~ '^[a-z0-9_.-]{3,32}$'),
  password_hash text not null,
  learner_id text not null unique,
  created_at timestamptz not null default now()
);

create table if not exists public.cognivault_sessions (
  token_hash text primary key,
  username text not null references public.cognivault_users(username) on delete cascade,
  expires_at timestamptz not null,
  created_at timestamptz not null default now()
);
create index if not exists cognivault_sessions_username_idx on public.cognivault_sessions(username);
create index if not exists cognivault_sessions_expiry_idx on public.cognivault_sessions(expires_at);

create table if not exists public.user_sources (
  source_id text primary key,
  owner_id text not null references public.cognivault_users(learner_id) on delete cascade,
  filename text not null,
  title text not null,
  modality text not null,
  sha256 text not null,
  storage_path text not null unique,
  evidence_count integer not null default 0 check (evidence_count >= 0),
  file_size_bytes bigint not null default 0 check (file_size_bytes >= 0),
  created_at timestamptz not null default now(),
  unique (source_id, owner_id)
);
alter table public.user_sources add column if not exists file_size_bytes bigint not null default 0 check (file_size_bytes >= 0);

create index if not exists user_sources_owner_idx on public.user_sources(owner_id, created_at desc);

create table if not exists public.user_evidence (
  evidence_id text primary key,
  owner_id text not null references public.cognivault_users(learner_id) on delete cascade,
  source_id text not null,
  modality text not null,
  evidence_text text not null,
  location jsonb not null default '{}'::jsonb,
  evidence_type text not null default 'text',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  foreign key (source_id, owner_id) references public.user_sources(source_id, owner_id) on delete cascade
);
create index if not exists user_evidence_owner_source_idx on public.user_evidence(owner_id, source_id);
create index if not exists user_evidence_owner_created_idx on public.user_evidence(owner_id, created_at desc);

-- Backend service-role access is server-only. Browser anon/authenticated roles receive no table grants.
alter table public.cognivault_users enable row level security;
alter table public.cognivault_sessions enable row level security;
alter table public.user_sources enable row level security;
alter table public.user_evidence enable row level security;
revoke all on public.cognivault_users, public.cognivault_sessions, public.user_sources, public.user_evidence from anon, authenticated;

-- Private bucket. Service-role operations only; object paths are server-generated owner/source prefixes.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('user-materials', 'user-materials', false, 26214400,
  array['application/pdf','application/vnd.openxmlformats-officedocument.presentationml.presentation','text/plain','text/vtt','application/x-subrip'])
on conflict (id) do update set public=false, file_size_limit=26214400, allowed_mime_types=EXCLUDED.allowed_mime_types;

create table if not exists public.learner_state_snapshots (
  owner_id text primary key references public.cognivault_users(learner_id) on delete cascade,
  snapshot_json jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
alter table public.learner_state_snapshots enable row level security;
revoke all on public.learner_state_snapshots from anon, authenticated;

-- The backend service role is the only runtime database principal used by the API.
grant usage on schema public to service_role;
grant all privileges on table public.cognivault_users, public.cognivault_sessions,
  public.user_sources, public.user_evidence, public.learner_state_snapshots to service_role;

-- Aggregate quota checks run as one database query (not repeated row pagination).
create or replace function public.cognivault_global_storage_usage_bytes()
returns bigint
language sql
security definer
set search_path = public
as $$ select coalesce(sum(file_size_bytes), 0)::bigint from public.user_sources; $$;

create or replace function public.cognivault_global_evidence_count()
returns bigint
language sql
security definer
set search_path = public
as $$ select count(*)::bigint from public.user_evidence; $$;

revoke all on function public.cognivault_global_storage_usage_bytes() from public, anon, authenticated;
revoke all on function public.cognivault_global_evidence_count() from public, anon, authenticated;
grant execute on function public.cognivault_global_storage_usage_bytes() to service_role;
grant execute on function public.cognivault_global_evidence_count() to service_role;
