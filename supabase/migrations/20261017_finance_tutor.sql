-- Keuangan mahasiswa & Tutor belajar EduPad (additive; tabel lama tidak diubah).
-- Diakses hanya oleh backend dengan secret key: RLS aktif tanpa policy, seperti tabel agent_*.

-- ------------------------------- keuangan ---------------------------------
create table if not exists public.finance_transactions (
    id uuid primary key default gen_random_uuid(),
    user_id text not null,
    kind text not null check (kind in ('income', 'expense')),
    amount bigint not null check (amount > 0 and amount <= 1000000000),
    category text not null check (char_length(category) between 1 and 40),
    note text not null default '' check (char_length(note) <= 200),
    occurred_on date not null default ((now() at time zone 'Asia/Jakarta')::date),
    source text not null default 'dashboard' check (source in ('suara', 'dashboard', 'impor')),
    created_at timestamptz not null default now()
);
comment on table public.finance_transactions is
    'Transaksi keuangan mahasiswa; source suara = dicatat AI agent dari perangkat EduPad.';
create index if not exists finance_transactions_user_date_idx
    on public.finance_transactions (user_id, occurred_on desc, created_at desc);

create table if not exists public.finance_budgets (
    user_id text not null,
    category text not null check (char_length(category) between 1 and 40),
    amount bigint not null check (amount >= 0 and amount <= 1000000000),
    updated_at timestamptz not null default now(),
    primary key (user_id, category)
);
comment on table public.finance_budgets is 'Anggaran bulanan per kategori pengeluaran.';

-- -------------------------------- tutor -----------------------------------
create table if not exists public.tutor_quizzes (
    id uuid primary key default gen_random_uuid(),
    user_id text not null,
    course text not null,
    course_id text,
    meeting integer,
    title text not null default '',
    questions jsonb not null,
    current integer not null default 0,
    status text not null default 'active' check (status in ('active', 'done', 'stopped')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
comment on table public.tutor_quizzes is
    'Kuis lisan Tutor (SORA): soal + kunci dibuat dari materi pertemuan; current = soal berjalan.';
create index if not exists tutor_quizzes_user_status_idx
    on public.tutor_quizzes (user_id, status, created_at desc);

create table if not exists public.learning_checks (
    id bigint generated always as identity primary key,
    user_id text not null,
    quiz_id uuid references public.tutor_quizzes (id) on delete cascade,
    topic_key text not null,
    course text not null,
    course_id text,
    meeting integer,
    question text not null,
    expected text not null default '',
    answer text not null default '',
    verdict text not null check (verdict in ('benar', 'sebagian', 'salah')),
    score real not null check (score between 0 and 1),
    feedback text not null default '',
    misconception text,
    created_at timestamptz not null default now()
);
comment on table public.learning_checks is
    'Satu jawaban kuis lisan beserta penilaian agent; dasar penguasaan topik & Equity Radar.';
create index if not exists learning_checks_user_created_idx
    on public.learning_checks (user_id, created_at desc);
create index if not exists learning_checks_quiz_idx on public.learning_checks (quiz_id);

create table if not exists public.topic_mastery (
    user_id text not null,
    topic_key text not null,
    course text not null,
    course_id text,
    meeting integer,
    title text not null default '',
    mastery real not null check (mastery between 0 and 1),
    attempts integer not null default 0,
    last_score real,
    last_checked_at timestamptz,
    next_review_at timestamptz,
    interval_days integer,
    primary key (user_id, topic_key)
);
comment on table public.topic_mastery is
    'Penguasaan per topik (mata kuliah + pertemuan) dan jadwal pengulangan berjarak.';

alter table public.finance_transactions enable row level security;
alter table public.finance_budgets enable row level security;
alter table public.tutor_quizzes enable row level security;
alter table public.learning_checks enable row level security;
alter table public.topic_mastery enable row level security;
