import { useState } from "react";
import type { AccessCourse, AttendanceRisk, EarlyWarning, EquityData } from "../api/types";
import { usePanel } from "../api/usePanel";
import { Icon } from "../components/Icon";
import { PageHeader } from "../components/PageHeader";
import { dayLabel, num } from "../lib/format";
import { loadPreferences } from "../lib/preferences";

const ACCESS_STATUS: Record<AccessCourse["status"], { label: string; tone: string }> = {
  lengkap: { label: "Lengkap", tone: "good" },
  ada_kekosongan: { label: "Ada kekosongan", tone: "warn" },
  belum_ada_materi: { label: "Belum ada materi", tone: "bad" },
};

const ATTENDANCE_STATUS: Record<AttendanceRisk["status"], { label: string; tone: string }> = {
  aman: { label: "Aman", tone: "good" },
  waspada: { label: "Waspada", tone: "warn" },
  melewati: { label: "Melewati batas", tone: "bad" },
};

const WARNING_LABEL: Record<EarlyWarning["jenis"], string> = {
  kehadiran: "Kehadiran",
  tugas_terlewat: "Tugas",
  anggaran: "Anggaran",
};

function meetingList(numbers: number[]) {
  if (numbers.length <= 6) return numbers.join(", ");
  return `${numbers.slice(0, 5).join(", ")} … ${numbers[numbers.length - 1]}`;
}

/** Pesan sopan untuk dosen: materi pertemuan yang sudah berlangsung tetapi belum tersedia. */
function lecturerMessage(course: AccessCourse) {
  const name = loadPreferences().studentName;
  const meetings = course.tanpa_materi.map((m) => m.pertemuan);
  const who = name && name !== "Mahasiswa" ? `Saya ${name}, mahasiswa ${course.matkul}. ` : "";
  return (
    `Selamat siang, Bapak/Ibu. ${who}Mohon izin, materi ${course.matkul} pertemuan ${meetingList(meetings)} ` +
    "belum tersedia di kelas.usu maupun Google Classroom. Bila berkenan, mohon materinya dapat diunggah " +
    "agar bisa kami pelajari ulang. Terima kasih banyak, Bapak/Ibu."
  );
}

interface Action {
  key: string;
  title: string;
  reason: string;
  action: string;
  copy?: string;
}

function nextActions(data: EquityData): Action[] {
  const actions: Action[] = [];
  for (const topic of data.mastery.topics.filter((t) => t.jatuh_tempo || t.penguasaan < 60).slice(0, 2)) {
    actions.push({
      key: `topic-${topic.course_id}-${topic.pertemuan}`,
      title: topic.judul || topic.matkul,
      reason: `Penguasaan ${topic.penguasaan}% (${topic.matkul}${topic.pertemuan != null ? ` pertemuan ${topic.pertemuan}` : ""}).`,
      action: `Ulangi lewat suara: “uji aku ${topic.matkul} pertemuan ${topic.pertemuan ?? ""}”.`,
    });
  }
  for (const course of data.access.mata_kuliah.filter((c) => c.tanpa_materi.length).slice(0, 2)) {
    actions.push({
      key: `access-${course.course_id}`,
      title: course.matkul,
      reason: `${course.tanpa_materi.length} pertemuan berlangsung tanpa materi (pertemuan ${meetingList(course.tanpa_materi.map((m) => m.pertemuan))}).`,
      action: "Minta dosen mengunggah materi; pesan siap disalin.",
      copy: lecturerMessage(course),
    });
  }
  for (const row of data.attendance.filter((r) => r.status !== "aman").slice(0, 1)) {
    actions.push({
      key: `att-${row.course_id}`,
      title: row.matkul,
      reason: `${row.tidak_hadir} dari ${row.berlangsung} pertemuan belum tercatat hadir di SATU (batas ${row.jatah_tidak_hadir}).`,
      action: row.status === "melewati" ? "Konfirmasi ke dosen bila ada yang keliru tercatat." : "Prioritaskan hadir di pertemuan berikutnya.",
    });
  }
  if (!data.mastery.topics.length) {
    actions.push({
      key: "first-quiz",
      title: "Mulai ukur pemahaman",
      reason: "Radar belum punya data pemahaman.",
      action: "Ucapkan ke EduPad: “uji aku [mata kuliah] pertemuan [nomor]”.",
    });
  }
  return actions.slice(0, 6);
}

export function EquityPage() {
  const equity = usePanel("equity");
  const data = equity.data;
  const access = data?.access;
  const mastery = data?.mastery;
  const [copied, setCopied] = useState<string | null>(null);
  const high = data?.warnings.filter((w) => w.tingkat === "tinggi").length ?? 0;
  const gaps = access?.mata_kuliah.filter((c) => c.status !== "lengkap") ?? [];

  const copy = async (key: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      window.setTimeout(() => setCopied(null), 2000);
    } catch {
      window.prompt("Salin pesan ini:", text);
    }
  };

  return (
    <div className="equity-page">
      <PageHeader title="Learning Equity Radar" subtitle="Radar pribadi: akses materi, kehadiran, dan pemahaman agar tidak ada yang tertinggal" />

      <section className="card equity-privacy" aria-label="Prinsip Equity Radar">
        <Icon name="users" size={18} />
        <div>
          <strong>Hanya datamu sendiri, untuk ditindaklanjuti, bukan untuk memberi label</strong>
          <p>
            Dihitung dari jadwal & presensi SATU, materi kelas.usu dan Google Classroom, serta kuis lisan Tutor. Kesenjangan akses
            materi adalah masalah ketersediaan, bukan kemampuanmu; sinyal pemahaman berasal dari jawaban kuis, bukan dari seberapa
            sering kamu bertanya.
          </p>
        </div>
        <span className="equity-sdgs">SDG 4.1 · 4.5 · 4.a · 10</span>
      </section>

      {equity.error && <div className="panel-error" role="alert">Sebagian data belum tersedia: {equity.error}</div>}

      <section className="equity-kpis" aria-busy={equity.loading}>
        <Metric
          label="Cakupan materi"
          value={access?.cakupan_persen != null ? `${access.cakupan_persen}%` : "—"}
          note={access ? `${access.pertemuan_berlangsung - access.pertemuan_tanpa_materi} dari ${access.pertemuan_berlangsung} pertemuan berlangsung bermateri` : "pertemuan berlangsung yang bermateri"}
        />
        <Metric
          label="Pemahaman"
          value={mastery?.rata_rata != null ? `${mastery.rata_rata}%` : "Belum diuji"}
          note={mastery?.topics.length ? `${mastery.topics.length} topik dari kuis lisan` : "mulai kuis lewat suara"}
          compact={mastery?.rata_rata == null}
        />
        <Metric label="Peringatan dini" value={data ? num(data.warnings.length) : "—"} note={high ? `${high} prioritas tinggi` : "kehadiran, tugas, anggaran"} />
        <Metric
          label="Akses lewat suara"
          value={data ? num(data.voice.questions_30d) : "—"}
          note={data ? `pertanyaan dijawab di perangkat (30 hari) · ${data.voice.listenable_meetings} pertemuan bisa didengar` : "pertanyaan dijawab di perangkat"}
        />
      </section>

      <div className="equity-grid">
        <section className="card equity-card">
          <header>
            <div>
              <h2>Kesenjangan akses materi</h2>
              <p>Pertemuan yang sudah berlangsung dibanding materi yang tersedia</p>
            </div>
            {access && (
              <span className="equity-trend">
                {access.tanpa_materi_sama_sekali}/{access.jumlah_mata_kuliah} tanpa materi
              </span>
            )}
          </header>
          {access ? (
            <ul className="equity-coverage-list access-list">
              {(gaps.length ? gaps : access.mata_kuliah).slice(0, 10).map((course) => {
                const status = ACCESS_STATUS[course.status];
                return (
                  <li key={course.course_id} className={course.status === "belum_ada_materi" ? "is-missing" : undefined}>
                    <span>
                      <strong>{course.matkul}</strong>
                      <small>
                        {course.pertemuan_bermateri} bermateri dari {course.pertemuan_berlangsung} berlangsung
                        {course.tanpa_materi.length ? ` · kosong: ${meetingList(course.tanpa_materi.map((m) => m.pertemuan))}` : ""}
                        {course.ocr.length ? ` · ${course.ocr.length} hasil scan (OCR)` : ""}
                        {course.materi_classroom ? ` · ${course.materi_classroom} materi Classroom` : ""}
                      </small>
                    </span>
                    <span className="access-actions">
                      <span className={`pill ${status.tone}`}>{status.label}</span>
                      {course.tanpa_materi.length > 0 && (
                        <button className="text-button" onClick={() => copy(course.course_id, lecturerMessage(course))}>
                          {copied === course.course_id ? "Tersalin" : "Salin pesan ke dosen"}
                        </button>
                      )}
                    </span>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="empty">Memuat audit materi…</p>
          )}
          <p className="equity-method-note">
            Pertemuan berlangsung = sudah dimulai menurut presensi SATU. Bermateri = ada materi kelas.usu atau Classroom untuk nomor
            pertemuan itu. Materi hasil scan dibaca dengan OCR dan bisa salah baca; ringkasannya tetap bisa dibacakan EduPad.
          </p>
        </section>

        <div className="tutor-side">
          <section className="card equity-card">
            <header>
              <div>
                <h2>Peringatan dini</h2>
                <p>Juga muncul sebagai kartu di layar EduPad</p>
              </div>
            </header>
            {data?.warnings.length ? (
              <ul className="warning-list">
                {data.warnings.slice(0, 6).map((warning) => (
                  <li key={warning.kunci}>
                    <span className={`pill ${warning.tingkat === "tinggi" ? "bad" : "warn"}`}>{WARNING_LABEL[warning.jenis]}</span>
                    <p>{warning.pesan}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty">Tidak ada peringatan. Pertahankan!</p>
            )}
          </section>

          <section className="card equity-card">
            <header>
              <div>
                <h2>Kehadiran vs syarat ujian</h2>
                <p>
                  Minimal {Math.round((data?.rules.min_attendance ?? 0.75) * 100)}% dari {data?.rules.semester_meetings ?? 16} pertemuan
                  {data?.attendance[0]?.diperbarui ? ` · data SATU ${dayLabel(data.attendance[0].diperbarui)}` : ""}
                </p>
              </div>
            </header>
            {data?.attendance.length ? (
              <ul className="equity-coverage-list">
                {data.attendance.slice(0, 8).map((row) => {
                  const status = ATTENDANCE_STATUS[row.status];
                  return (
                    <li key={row.course_id ?? row.matkul}>
                      <span>
                        <strong>{row.matkul}</strong>
                        <small>
                          hadir {row.hadir}/{row.berlangsung} · sisa jatah absen {Math.max(0, row.sisa_jatah)}
                        </small>
                      </span>
                      <span className={`pill ${status.tone}`}>{status.label}</span>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="empty">Data presensi belum ada.</p>
            )}
          </section>
        </div>
      </div>

      <section className="card equity-card equity-actions">
        <header>
          <div>
            <h2>Langkah berikutnya</h2>
            <p>Disusun dari sinyal di atas; bisa langsung dikerjakan lewat EduPad</p>
          </div>
        </header>
        {data ? (
          <div className="equity-action-grid">
            {nextActions(data).map((item, index) => (
              <article key={item.key}>
                <span className="mono">{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.reason}</p>
                  <small>{item.action}</small>
                  {item.copy && (
                    <button className="text-button" onClick={() => copy(item.key, item.copy!)}>
                      {copied === item.key ? "Tersalin" : "Salin pesan"}
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="empty">Memuat…</p>
        )}
      </section>
    </div>
  );
}

function Metric({ label, value, note, compact = false }: { label: string; value: string; note: string; compact?: boolean }) {
  return (
    <article className="card equity-metric">
      <span>{label}</span>
      <strong className={compact ? "is-compact" : undefined}>{value}</strong>
      <small>{note}</small>
    </article>
  );
}
