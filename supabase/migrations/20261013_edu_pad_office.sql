-- Migration additive untuk EduPad AI Office.
-- File ini TIDAK diterapkan otomatis. Review dan jalankan terpisah setelah disetujui.

create table if not exists public.office_tasks (
    id uuid primary key,
    user_id text not null,
    title text not null check (char_length(title) between 1 and 160),
    description text not null default '',
    status text not null default 'queued'
        check (status in ('queued', 'in_progress', 'completed', 'failed', 'cancelled')),
    priority text not null default 'medium'
        check (priority in ('low', 'medium', 'high')),
    assigned_agent text not null default 'coordinator',
    job_type text not null default 'manual' check (job_type in ('manual', 'index')),
    claimed_by text,
    claimed_at timestamptz,
    started_at timestamptz,
    finished_at timestamptz,
    error text,
    result jsonb,
    due_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists office_tasks_user_status_idx
    on public.office_tasks (user_id, status, created_at desc);

create table if not exists public.office_agent_events (
    id bigint generated always as identity primary key,
    user_id text not null,
    run_id text,
    agent_id text not null,
    state text not null
        check (state in ('offline', 'idle', 'queued', 'running', 'waiting', 'succeeded', 'failed', 'cancelled')),
    room text not null,
    job_type text not null,
    message text not null default '',
    progress smallint not null default 0 check (progress between 0 and 100),
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists office_agent_events_user_id_idx
    on public.office_agent_events (user_id, id desc);
create index if not exists office_agent_events_run_id_idx
    on public.office_agent_events (run_id) where run_id is not null;

alter table public.office_tasks enable row level security;
alter table public.office_agent_events enable row level security;

-- Tidak ada policy anon/authenticated pada tahap awal.
-- Akses dilakukan oleh backend memakai secret/service role yang sudah ada.
