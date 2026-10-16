import { useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { HelpStatus, LearningCurve, MasteryTopic, QuizCheck, TutorHelp } from "../api/types";
import { usePanel } from "../api/usePanel";
import { ChartTooltip } from "../components/ChartTooltip";
import { Icon } from "../components/Icon";
import { PageHeader } from "../components/PageHeader";
import { axisProps, C } from "../lib/chart";
import { ago, dayLabel, num } from "../lib/format";

const VOICE_EXAMPLES = [
  "Uji aku Basis Data pertemuan dua",
  "Kuis dong tentang normalisasi, tiga soal",
  "Aku belum paham rekursi",
  "Mulai (saat SORA menawarkan bantuan)",
  "Hari ini aku sebaiknya belajar apa?",
  "Berhenti kuisnya",
];

const VERDICT: Record<QuizCheck["penilaian"], { label: string; tone: string }> = {
  benar: { label: "Benar", tone: "good" },
  sebagian: { label: "Sebagian", tone: "warn" },
  salah: { label: "Belum tepat", tone: "bad" },
};

const HELP_STATUS: Record<HelpStatus, { label: string; tone: string }> = {
  siap: { label: "Siap ditawarkan", tone: "warn" },
  berjalan: { label: "Sedang belajar", tone: "" },
  kuis: { label: "Kuis terarah", tone: "" },
  selesai: { label: "Selesai", tone: "good" },
  ditolak: { label: "Ditunda", tone: "" },
  kedaluwarsa: { label: "Kedaluwarsa", tone: "" },
};

const GOOD = "#15803d";

function level(value: number) {
  if (value >= 80) return { label: "Dikuasai", tone: "good" };
  if (value >= 60) return { label: "Berkembang", tone: "" };
  return { label: "Perlu diperkuat", tone: "warn" };
}

function topicName(topic: MasteryTopic) {
  return `${topic.matkul}${topic.pertemuan != null ? ` · pertemuan ${topic.pertemuan}` : ""}`;
}

export function TutorPage() {
  const tutor = usePanel("tutor");
  const data = tutor.data;
  const topics = data?.topics ?? [];
  const checks = data?.checks ?? [];
  const due = topics.filter((topic) => topic.jatuh_tempo);
  const helps = data?.help ?? [];
  const measured = helps.filter((h) => h.sebelum != null && h.sesudah != null);
  const effect = measured.length
    ? Math.round(measured.reduce((total, h) => total + (h.sesudah! - h.sebelum!), 0) / measured.length)
    : null;

  return (
    <div className="equity-page tutor-page">
      <PageHeader title="Tutor Belajar" subtitle="SORA menguji pemahaman lewat kuis lisan dari materi kuliah asli, lalu menjadwalkan pengulangan" />

      {tutor.error && <div className="panel-error" role="alert">Data tutor belum bisa dimuat: {tutor.error}</div>}
      {data && !data.available && <div className="panel-error" role="alert">Tutor belum aktif di server: {data.reason}</div>}

      <section className="card equity-privacy" aria-label="Cara memakai Tutor di perangkat">
        <Icon name="mic" size={18} />
        <div>
          <strong>Belajar cukup dengan bicara ke EduPad</strong>
          <p>
            Soal dibuat dari materi pertemuan yang benar-benar diunggah dosen, dinilai AI dari jawaban lisanmu, lalu topik yang
            belum dikuasai dijadwalkan diulang (1, 3, 7, 14, 30 hari). Soal tugas dijawab bertahap: konsep dan petunjuk dulu,
            penjelasan lengkap saat kamu minta.
          </p>
          <div className="voice-examples">
            {VOICE_EXAMPLES.map((text) => (
              <span key={text} className="pill chip">
                “{text}”
              </span>
            ))}
          </div>
        </div>
        <span className="equity-sdgs">SDG 4.1 · 4.4</span>
      </section>

      <section className="equity-kpis" aria-busy={tutor.loading}>
        <Metric label="Rata-rata penguasaan" value={data?.rata_rata != null ? `${data.rata_rata}%` : "—"} note={topics.length ? `${topics.length} topik sudah diuji` : "mulai kuis pertama lewat suara"} />
        <Metric label="Topik dikuasai" value={data ? `${data.dikuasai ?? 0}/${topics.length}` : "—"} note="penguasaan ≥ 80%" />
        <Metric label="Soal 7 hari" value={data ? num(data.soal_7_hari ?? 0) : "—"} note={data?.skor_7_hari != null ? `skor rata-rata ${data.skor_7_hari}%` : due.length ? `${due.length} topik jatuh tempo diulang` : "belum ada jawaban minggu ini"} />
        <Metric
          label="Efek bantuan SORA"
          value={effect != null ? `${effect >= 0 ? "+" : ""}${effect} poin` : "—"}
          note={measured.length ? `rata-rata kenaikan penguasaan, ${measured.length} bantuan` : "terukur setelah bantuan pertama selesai"}
        />
      </section>

      <HelpSection helps={helps} />
      <CurveSection curves={data?.history ?? []} />

      <div className="equity-grid">
        <section className="card equity-card">
          <header>
            <div>
              <h2>Peta penguasaan topik</h2>
              <p>Dari kuis lisan; urut dari yang paling perlu diperkuat</p>
            </div>
          </header>
          {topics.length ? (
            <ul className="mastery-list">
              {topics.map((topic) => {
                const lv = level(topic.penguasaan);
                return (
                  <li key={`${topic.course_id ?? topic.matkul}-${topic.pertemuan}`}>
                    <div className="mastery-head">
                      <span>
                        <strong>{topic.judul || topicName(topic)}</strong>
                        <small>
                          {topicName(topic)} · {topic.kuis}× kuis · terakhir {topic.terakhir ? ago(topic.terakhir) : "—"}
                        </small>
                      </span>
                      <span className={`pill ${lv.tone}`}>{lv.label}</span>
                    </div>
                    <div className="meter" aria-label={`Penguasaan ${topic.penguasaan}%`}>
                      <div className={`meter-fill ${lv.tone}`} style={{ width: `${Math.max(4, topic.penguasaan)}%` }} />
                    </div>
                    <small className={topic.jatuh_tempo ? "warn-text" : "muted"}>
                      {topic.penguasaan}% ·{" "}
                      {topic.jatuh_tempo ? "waktunya mengulang: ucapkan “uji aku lagi”" : topic.ulang_pada ? `diulang ${dayLabel(topic.ulang_pada)}` : "—"}
                    </small>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="empty">Belum ada topik yang diuji. Tekan tombol di EduPad dan ucapkan “uji aku [mata kuliah] pertemuan [nomor]”.</p>
          )}
        </section>

        <div className="tutor-side">
          <section className="card equity-card">
            <header>
              <div>
                <h2>Per mata kuliah</h2>
                <p>Rata-rata penguasaan topik yang sudah diuji</p>
              </div>
            </header>
            {data?.courses.length ? (
              <ul className="equity-coverage-list">
                {data.courses.map((course) => (
                  <li key={course.matkul}>
                    <span>
                      <strong>{course.matkul}</strong>
                      <small>{course.topik} topik</small>
                    </span>
                    <b className={course.penguasaan >= 80 ? "good-text" : course.penguasaan < 60 ? "warn-text" : undefined}>{course.penguasaan}%</b>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty">Belum ada data.</p>
            )}
          </section>

          <section className="card equity-card">
            <header>
              <div>
                <h2>Salah paham yang muncul</h2>
                <p>Dicatat AI saat menilai jawaban (30 hari)</p>
              </div>
            </header>
            {data?.miskonsepsi?.length ? (
              <ul className="equity-coverage-list">
                {data.miskonsepsi.map((item) => (
                  <li key={item.teks}>
                    <span>
                      <strong>{item.teks}</strong>
                    </span>
                    <b>{item.jumlah}×</b>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty">Belum ada salah paham yang tercatat.</p>
            )}
          </section>
        </div>
      </div>

      <section className="card equity-card">
        <header>
          <div>
            <h2>Riwayat jawaban kuis</h2>
            <p>Jawaban lisan terakhir beserta umpan balik SORA</p>
          </div>
        </header>
        {checks.length ? (
          <ol className="quiz-history">
            {checks.map((check, index) => {
              const verdict = VERDICT[check.penilaian];
              return (
                <li key={`${check.waktu}-${index}`}>
                  <span className={`pill ${verdict.tone}`}>{verdict.label}</span>
                  <div>
                    <strong>{check.soal}</strong>
                    <p>
                      <b>Jawabanmu:</b> {check.jawaban || "—"}
                    </p>
                    {check.umpan_balik && <p className="muted">{check.umpan_balik}</p>}
                    <small className="muted">
                      {check.matkul}
                      {check.pertemuan != null ? ` · pertemuan ${check.pertemuan}` : ""} · {ago(check.waktu)}
                    </small>
                  </div>
                </li>
              );
            })}
          </ol>
        ) : (
          <p className="empty">Riwayat kuis akan muncul setelah kuis lisan pertama.</p>
        )}
      </section>
    </div>
  );
}

function HelpSection({ helps }: { helps: TutorHelp[] }) {
  return (
    <section className="card equity-card">
      <header>
        <div>
          <h2>Bantuan dari SORA</h2>
          <p>Disiapkan sendiri oleh AI saat muncul minimal dua tanda kesulitan pada satu topik</p>
        </div>
      </header>
      {helps.length ? (
        <ul className="help-list">
          {helps.map((h) => {
            const status = HELP_STATUS[h.status] ?? { label: h.status, tone: "" };
            return (
              <li key={h.id}>
                <div className="mastery-head">
                  <span>
                    <strong>{h.judul}</strong>
                    <small>
                      {h.matkul}
                      {h.pertemuan != null ? ` · pertemuan ${h.pertemuan}` : ""} · {h.dibuat ? ago(h.dibuat) : "—"}
                    </small>
                  </span>
                  <span className={`pill ${status.tone}`}>{status.label}</span>
                </div>
                {h.masalah && <p className="help-problem">{h.masalah}</p>}
                <div className="voice-examples help-reasons">
                  {h.alasan.map((reason) => (
                    <span key={reason} className="pill chip">
                      {reason}
                    </span>
                  ))}
                </div>
                {h.sebelum != null && (
                  <p className="help-effect">
                    Penguasaan {h.sebelum}%
                    {h.sesudah != null ? (
                      <>
                        {" → "}
                        <b className={h.sesudah >= h.sebelum ? "good-text" : "warn-text"}>{h.sesudah}%</b>
                        {` (${h.sesudah >= h.sebelum ? "+" : ""}${h.sesudah - h.sebelum} poin)`}
                      </>
                    ) : (
                      " sebelum bantuan"
                    )}
                  </p>
                )}
                {h.status === "siap" && <small className="warn-text">Tahan tombol di EduPad lalu ucapkan “mulai”.</small>}
                {h.pelajaran.length > 0 && (
                  <details>
                    <summary>
                      Isi pelajaran mini ({h.pelajaran.length} bagian) + {h.soal} soal terarah
                    </summary>
                    <ol>
                      {h.pelajaran.map((text, index) => (
                        <li key={index}>{text}</li>
                      ))}
                    </ol>
                  </details>
                )}
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="empty">
          Belum ada. Setiap sore SORA menganalisis jawaban kuis, penguasaan, pertanyaan berulang, dan ucapan “belum paham”; bila
          ada topik yang sulit, bantuan muncul di sini dan di layar EduPad.
        </p>
      )}
    </section>
  );
}

type CurvePoint = LearningCurve["titik"][number] & { label: string };

function CurveDot(props: { cx?: number; cy?: number; payload?: CurvePoint; index?: number }) {
  const { cx, cy, payload, index } = props;
  if (cx == null || cy == null) return null;
  return payload?.bantuan ? (
    <circle key={index} cx={cx} cy={cy} r={6} fill={GOOD} stroke="#fff" strokeWidth={2} />
  ) : (
    <circle key={index} cx={cx} cy={cy} r={4} fill={C.accent} stroke="#fff" strokeWidth={2} />
  );
}

function CurveSection({ curves }: { curves: LearningCurve[] }) {
  const [selected, setSelected] = useState<string | null>(null);
  const curve = curves.find((c) => c.topic_key === selected) ?? curves[0];
  const points: CurvePoint[] = (curve?.titik ?? []).map((p, i) => ({ ...p, label: `Kuis ${i + 1}` }));
  return (
    <section className="card equity-card">
      <header>
        <div>
          <h2>Kurva belajar</h2>
          <p>Skor tiap kuis lisan per topik; titik hijau = kuis setelah bantuan SORA</p>
        </div>
        {curves.length > 1 && (
          <select className="curve-select" value={curve?.topic_key} onChange={(e) => setSelected(e.target.value)} aria-label="Pilih topik">
            {curves.map((c) => (
              <option key={c.topic_key} value={c.topic_key}>
                {c.judul || c.matkul} {c.pertemuan != null ? `(P${c.pertemuan})` : ""}
              </option>
            ))}
          </select>
        )}
      </header>
      {points.length ? (
        <div className="chart" style={{ height: 220 }}>
          <ResponsiveContainer>
            <LineChart data={points} margin={{ top: 10, right: 16, left: -20, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke={C.grid} />
              <XAxis dataKey="label" {...axisProps} />
              <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} {...axisProps} />
              <ReferenceLine y={80} stroke={GOOD} strokeDasharray="4 4" label={{ value: "dikuasai", position: "insideTopRight", fill: GOOD, fontSize: 11 }} />
              <Tooltip
                content={
                  <ChartTooltip<CurvePoint>
                    title={(p) => `${p.label} · ${dayLabel(p.waktu)}`}
                    rows={(p) => [
                      { label: "Skor", value: `${p.skor}%`, color: p.bantuan ? GOOD : C.accent },
                      { label: "Jenis", value: p.bantuan ? "kuis terarah SORA" : "kuis lisan" },
                    ]}
                  />
                }
              />
              <Line type="monotone" dataKey="skor" stroke={C.accent} strokeWidth={2} dot={<CurveDot />} activeDot={{ r: 6 }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="empty">Kurva muncul setelah topik yang sama diuji lebih dari sekali.</p>
      )}
    </section>
  );
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <article className="card equity-metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  );
}
