import { useState } from "react";
import type { AccessCourse, AccessibilityData, AttendanceRisk, EarlyWarning } from "../api/types";
import { usePanel } from "../api/usePanel";
import { PageIntro } from "../components/PageIntro";
import { Bar, Figure, Section } from "../components/Section";
import { dayLabel } from "../lib/format";
import { go } from "../lib/router";
import { loadPreferences } from "../lib/preferences";
import { SPEED_LABEL } from "../lib/voice";

const ACCESS: Record<AccessCourse["status"], { label: string; tone: string }> = {
  lengkap: { label: "Lengkap", tone: "good" },
  ada_kekosongan: { label: "Sebagian", tone: "warn" },
  belum_ada_materi: { label: "Belum ada", tone: "bad" },
};

const PRESENCE: Record<AttendanceRisk["status"], { label: string; tone: string }> = {
  aman: { label: "Aman", tone: "good" },
  waspada: { label: "Waspada", tone: "warn" },
  melewati: { label: "Lewat batas", tone: "bad" },
};

const WARNING: Record<EarlyWarning["jenis"], string> = { kehadiran: "Hadir", tugas_terlewat: "Tugas", anggaran: "Uang" };

/** "1, 2, 3, 5" -> "P1–P3, P5" */
function meetings(numbers: number[]) {
  const sorted = [...numbers].sort((a, b) => a - b);
  const parts: string[] = [];
  for (let i = 0; i < sorted.length; i++) {
    let j = i;
    while (j + 1 < sorted.length && sorted[j + 1] === sorted[j] + 1) j++;
    parts.push(j > i ? `P${sorted[i]}–P${sorted[j]}` : `P${sorted[i]}`);
    i = j;
  }
  return parts.join(", ");
}

/** Pesan sopan untuk dosen: materi pertemuan yang sudah berlangsung tetapi belum tersedia. */
function lecturerMessage(course: AccessCourse) {
  const name = loadPreferences().studentName;
  const who = name && name !== "Mahasiswa" ? `Saya ${name}, mahasiswa ${course.matkul}. ` : "";
  const list = meetings(course.tanpa_materi.map((m) => m.pertemuan)).replace(/P/g, "");
  return (
    `Selamat siang, Bapak/Ibu. ${who}Mohon izin, materi ${course.matkul} pertemuan ${list} ` +
    "belum tersedia di kelas.usu maupun Google Classroom. Bila berkenan, mohon materinya dapat diunggah " +
    "agar bisa kami pelajari ulang. Terima kasih banyak, Bapak/Ibu."
  );
}

export function EquityPage() {
  const equity = usePanel("equity");
  const data = equity.data;
  const access = data?.access;
  const [copied, setCopied] = useState<string | null>(null);
  const gaps = access?.mata_kuliah.filter((c) => c.tanpa_materi.length > 0) ?? [];
  const complete = access?.mata_kuliah.filter((c) => c.status === "lengkap") ?? [];
  const risky = data?.attendance.filter((r) => r.berlangsung > 0) ?? [];
  const warnings = data?.warnings ?? [];

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
    <>
      <PageIntro owl="nexus" title="Equity Radar" mood={access && !gaps.length ? "happy" : "idle"}>
        {!access ? (
          "Memeriksa ketersediaan materi…"
        ) : gaps.length ? (
          <>
            Baru <b>{access.cakupan_persen ?? 0}%</b> pertemuan yang sudah berlangsung punya materi.{" "}
            {access.tanpa_materi_sama_sekali > 0 && (
              <>
                <b>{access.tanpa_materi_sama_sekali} mata kuliah</b> belum ada materi sama sekali.
              </>
            )}
          </>
        ) : (
          "Semua pertemuan yang sudah berlangsung punya materi."
        )}
      </PageIntro>

      {equity.error && <div className="panel-error" role="alert">Sebagian data belum tersedia: {equity.error}</div>}

      {access && (
        <div className="figures">
          <Figure
            value={`${access.pertemuan_berlangsung - access.pertemuan_tanpa_materi}/${access.pertemuan_berlangsung}`}
            label="Pertemuan punya materi"
            tone={(access.cakupan_persen ?? 0) < 60 ? "bad" : undefined}
          />
          <Figure value={access.tanpa_materi_sama_sekali} label="Mata kuliah tanpa materi" tone={access.tanpa_materi_sama_sekali ? "bad" : "good"} />
          <Figure value={access.bisa_didengar} label="Pertemuan bisa didengar" note="ringkasannya bisa dibacakan EduPad" />
          <Figure value={warnings.length} label="Peringatan" tone={warnings.some((w) => w.tingkat === "tinggi") ? "bad" : warnings.length ? "warn" : "good"} />
        </div>
      )}

      <div className="grid-3-2">
        <div className="column">
          <Section title="Materi yang belum tersedia" note="Pertemuan yang sudah berlangsung menurut SATU, tapi belum ada materinya">
            {gaps.length ? (
              <ul className="list">
                {gaps.map((course) => {
                  const status = ACCESS[course.status];
                  return (
                    <li key={course.course_id} className="gap-row">
                      <div className="item-main">
                        <strong>{course.matkul}</strong>
                        <span>
                          Kosong: {meetings(course.tanpa_materi.map((m) => m.pertemuan))}
                          {course.pertemuan_bermateri > 0 ? ` · ${course.pertemuan_bermateri} pertemuan sudah ada` : ""}
                        </span>
                      </div>
                      <div className="item-side">
                        <span className={`tag ${status.tone}`}>{status.label}</span>
                        <button className="section-link" onClick={() => copy(course.course_id, lecturerMessage(course))}>
                          {copied === course.course_id ? "Tersalin" : "Salin pesan ke dosen"}
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="empty-line">{access ? "Tidak ada yang kosong." : "Memuat…"}</p>
            )}
          </Section>

          {complete.length > 0 && (
            <Section title="Materi lengkap">
              <div className="chips">
                {complete.map((c) => (
                  <span key={c.course_id} className="tag good">
                    {c.matkul}
                  </span>
                ))}
              </div>
            </Section>
          )}
        </div>

        <div className="column">
          {data?.accessibility && <AccessibilitySection a={data.accessibility} />}

          {warnings.length > 0 && (
            <Section title="Perlu perhatian">
              <ul className="list">
                {warnings.slice(0, 5).map((w) => (
                  <li key={w.kunci}>
                    <span className={`tag ${w.tingkat === "tinggi" ? "bad" : "warn"}`}>{WARNING[w.jenis]}</span>
                    <span className="item-text">{w.pesan}</span>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          <Section
            title="Kehadiran"
            note={
              data
                ? `Syarat ujian minimal ${Math.round(data.rules.min_attendance * 100)}%${data.attendance[0]?.diperbarui ? ` · data SATU ${dayLabel(data.attendance[0].diperbarui)}` : ""}`
                : undefined
            }
          >
            {risky.length ? (
              <ul className="list">
                {risky.map((row) => {
                  const status = PRESENCE[row.status];
                  const rate = row.berlangsung ? (row.hadir / row.berlangsung) * 100 : 0;
                  return (
                    <li key={row.course_id ?? row.matkul} className="topic-row">
                      <div className="item-main">
                        <strong>{row.matkul}</strong>
                        <span>
                          Hadir {row.hadir} dari {row.berlangsung} · sisa jatah absen {Math.max(0, row.sisa_jatah)}
                        </span>
                        <Bar value={rate} tone={row.status === "aman" ? "good" : row.status === "waspada" ? "warn" : "bad"} label={`Hadir ${Math.round(rate)}%`} />
                      </div>
                      <span className={`tag ${status.tone}`}>{status.label}</span>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="empty-line">{data ? "Data presensi belum ada." : "Memuat…"}</p>
            )}
          </Section>

          <Section
            title="Pemahaman"
            action={
              <button className="section-link" onClick={() => go("tutor")}>
                Tutor
              </button>
            }
          >
            {data?.mastery.courses.length ? (
              <ul className="list">
                {data.mastery.courses.map((c) => (
                  <li key={c.matkul} className="topic-row">
                    <div className="item-main">
                      <strong>{c.matkul}</strong>
                      <Bar value={c.penguasaan} tone={c.penguasaan >= 80 ? "good" : c.penguasaan < 60 ? "warn" : undefined} />
                    </div>
                    <b className="topic-pct">{c.penguasaan}%</b>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty-line">Diukur dari kuis lisan Tutor.</p>
            )}
          </Section>
        </div>
      </div>
    </>
  );
}

/** Bukti EduPad bisa dipakai tanpa melihat layar (Mode Suara untuk mahasiswa tunanetra). */
function AccessibilitySection({ a }: { a: AccessibilityData }) {
  const listenable = a.meetings_with_material ? (a.listenable_meetings / a.meetings_with_material) * 100 : 0;
  return (
    <Section
      title="Aksesibilitas"
      note="EduPad bisa dipakai tanpa melihat layar"
      action={
        <button className="section-link" onClick={() => go("pengaturan")}>
          Atur
        </button>
      }
    >
      <ul className="list">
        <li className="topic-row">
          <div className="item-main">
            <strong>Mode Suara</strong>
            <span>
              {a.voice_mode
                ? `Semua jawaban & pemberitahuan dibacakan · bicara ${SPEED_LABEL[a.speed].toLowerCase()}`
                : "Mati · nyalakan di Pengaturan atau lewat suara"}
            </span>
          </div>
          <span className={`tag ${a.voice_mode ? "good" : ""}`}>{a.voice_mode ? "Aktif" : "Mati"}</span>
        </li>
        <li className="topic-row">
          <div className="item-main">
            <strong>Pertemuan yang bisa didengar</strong>
            <span>Ringkasan materinya bisa dibacakan EduPad</span>
            <Bar value={listenable} tone={listenable >= 80 ? "good" : "warn"} label={`${Math.round(listenable)}% pertemuan bermateri`} />
          </div>
          <b className="topic-pct">
            {a.listenable_meetings}/{a.meetings_with_material}
          </b>
        </li>
        <li className="topic-row">
          <div className="item-main">
            <strong>Halaman gambar jadi teks</strong>
            <span>Slide berupa gambar dibaca dengan OCR, sehingga isinya ikut bisa didengar</span>
          </div>
          <b className="topic-pct">{a.ocr_pages}</b>
        </li>
        <li className="topic-row">
          <div className="item-main">
            <strong>Dibacakan 30 hari terakhir</strong>
            <span>
              {a.answers_spoken_30d} jawaban dan {a.alerts_spoken_30d} pemberitahuan dalam Mode Suara · {a.questions_30d} pertanyaan lewat suara
            </span>
          </div>
          <b className="topic-pct">{a.answers_spoken_30d + a.alerts_spoken_30d}</b>
        </li>
      </ul>
      <p className="say-hint">
        Ucapkan ke EduPad: <q>{a.voice_mode ? "bicara lebih cepat" : "aktifkan mode suara"}</q>
      </p>
    </Section>
  );
}
