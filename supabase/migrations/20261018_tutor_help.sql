-- Tutor mandiri (SORA): rencana bantuan yang disiapkan AI untuk topik yang sulit bagi mahasiswa.
-- Additive: tabel baru + kolom opsional di tutor_quizzes. RLS aktif tanpa policy (akses backend).

create table if not exists public.tutor_help (
    id uuid primary key default gen_random_uuid(),
    user_id text not null,
    topic_key text not null,
    course text not null,
    course_id text,
    meeting integer,
    title text not null default '',
    problem text not null default '',
    reasons jsonb not null default '[]'::jsonb,
    lesson jsonb not null default '[]'::jsonb,
    questions jsonb not null default '[]'::jsonb,
    status text not null default 'siap'
        check (status in ('siap', 'berjalan', 'kuis', 'selesai', 'ditolak', 'kedaluwarsa')),
    part integer not null default 0,
    mastery_before real,
    mastery_after real,
    created_at timestamptz not null default now(),
    started_at timestamptz,
    finished_at timestamptz,
    declined_at timestamptz
);
comment on table public.tutor_help is
    'Bantuan belajar yang disiapkan SORA: alasan (sinyal kesulitan), pelajaran mini, kuis terarah, skor sebelum/sesudah.';
create index if not exists tutor_help_user_status_idx
    on public.tutor_help (user_id, status, created_at desc);

alter table public.tutor_quizzes
    add column if not exists help_id uuid references public.tutor_help (id) on delete set null;

alter table public.tutor_help enable row level security;
