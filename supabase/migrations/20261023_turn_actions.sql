-- Jejak aksi per giliran percakapan (additive; data lama tetap, default daftar kosong).
--
-- Riwayat yang dikirim ke LLM hanya memuat pertanyaan + jawaban (agent/memory.py
-- turn_messages), bukan tool yang sudah dijalankan. Akibatnya agent bisa "menyusul"
-- menjalankan lagi perubahan data dari giliran sebelumnya -- mis. mencatat ulang transaksi
-- lama saat mahasiswa menyebut transaksi baru. Kolom ini menyimpan apa yang sudah terjadi
-- ("catat pengeluaran Makan Rp20.000 (2026-10-22)") supaya ikut terbaca di giliran berikutnya.
alter table public.agent_turns
    add column if not exists actions jsonb not null default '[]'::jsonb;

comment on column public.agent_turns.actions is
    'Perubahan data yang dijalankan pada giliran ini; dibaca lagi sebagai konteks LLM.';
