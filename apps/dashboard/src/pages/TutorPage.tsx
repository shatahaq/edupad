import { useState, type ReactNode } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { HelpStatus, LearningCurve, QuizCheck, TutorData, TutorHelp } from "../api/types";
import { usePanel } from "../api/usePanel";
import { ChartTooltip } from "../components/ChartTooltip";
import { PageIntro } from "../components/PageIntro";
import { Bar, Figure, Section } from "../components/Section";
import { axisProps } from "../lib/chart";
import { ago, dayLabel } from "../lib/format";

const HELP_STATUS: Record<HelpStatus, { label: string; tone: string }> = {
  siap: { label: "Siap dimulai", tone: "warn" },
  berjalan: { label: "Sedang belajar", tone: "" },
  kuis: { label: "Kuis terarah", tone: "" },
  selesai: { label: "Selesai", tone: "good" },
  ditolak: { label: "Ditunda", tone: "" },
  kedaluwarsa: { label: "Kedaluwarsa", tone: "" },
};

const VERDICT: Record<QuizCheck["penilaian"], { label: string; tone: string }> = {
  benar: { label: "Benar", tone: "good" },
  sebagian: { label: "Sebagian", tone: "warn" },
  salah: { label: "Belum tepat", tone: "bad" },
};

const GOOD = "#1f7a45";
const TEAL = "#1d727a";

const tone = (value: number) => (value >= 80 ? "good" : value < 60 ? "warn" : undefined);

/** Pesan utama SORA: satu hal yang paling berguna dilakukan sekarang. */
function mainMessage(data: TutorData | null): { text: ReactNode; say?: string; happy?: boolean } {
  if (!data) return { text: "Memuat progres belajarmu…" };
  if (!data.available) return { text: "Tutor belum aktif di server." };
  const help = data.help?.find((h) => h.status === "siap" || h.status === "berjalan");
  if (help)
    return {
      text: (
        <>
          Aku sudah menyiapkan pelajaran singkat tentang <b>{help.judul}</b> karena {help.alasan.join(" dan ")}.
        </>
      ),
      say: "mulai",
    };
  const due = data.topics.find((t) => t.jatuh_tempo);
  if (due)
    return {
      text: (
        <>
          Waktunya mengulang <b>{due.judul || due.matkul}</b>. Penguasaanmu {due.penguasaan}%.
        </>
      ),
      say: "uji aku lagi",
    };
  if (!data.topics.length) return { text: "Belum ada kuis. Coba satu kuis lisan dari materi kuliahmu.", say: "uji aku Basis Data pertemuan dua" };
  const weakest = data.topics[0];
  if (weakest.penguasaan >= 80) return { text: "Semua topik yang sudah diuji kamu kuasai. Mantap!", happy: true };
  return {
    text: (
      <>
        Topik yang paling perlu diperkuat: <b>{weakest.judul || weakest.matkul}</b> ({weakest.penguasaan}%).
      </>
    ),
    say: `uji aku ${weakest.matkul}${weakest.pertemuan != null ? ` pertemuan ${weakest.pertemuan}` : ""}`,
  };
}

export function TutorPage() {
  const tutor = usePanel("tutor");
  const data = tutor.data;
  const topics = data?.topics ?? [];
  const helps = data?.help ?? [];
  const measured = helps.filter((h) => h.sebelum != null && h.sesudah != null);
  const effect = measured.length ? Math.round(measured.reduce((total, h) => total + (h.sesudah! - h.sebelum!), 0) / measured.length) : null;
  const message = mainMessage(data);

  return (
    <>
      <PageIntro owl="sora" title="Tutor Belajar" say={message.say} mood={message.happy ? "happy" : "idle"}>
        {message.text}
      </PageIntro>

      {tutor.error && <div className="panel-error" role="alert">Data tutor belum bisa dimuat: {tutor.error}</div>}

      {topics.length > 0 && (
        <div className="figures">
          <Figure value={data?.rata_rata != null ? `${data.rata_rata}%` : "–"} label="Rata-rata penguasaan" note={`${topics.length} topik sudah diuji`} />
          <Figure value={`${data?.dikuasai ?? 0}/${topics.length}`} label="Topik dikuasai" note="penguasaan 80% ke atas" />
          <Figure value={data?.soal_7_hari ?? 0} label="Soal dijawab minggu ini" note={data?.skor_7_hari != null ? `rata-rata ${data.skor_7_hari}%` : undefined} />
          {effect != null && (
            <Figure value={`${effect >= 0 ? "+" : ""}${effect}`} tone={effect > 0 ? "good" : undefined} label="Poin naik setelah bantuan SORA" note={`dari ${measured.length} bantuan`} />
          )}
        </div>
      )}

      <div className="grid-3-2">
        <div className="column">
          {helps.length > 0 && <HelpSection helps={helps} />}
          {data && <CurveSection curves={data.history ?? []} />}
        </div>
        <div className="column">
          <Section title="Penguasaan per topik">
            {topics.length ? (
              <ul className="list">
                {topics.map((t) => (
                  <li key={`${t.course_id ?? t.matkul}-${t.pertemuan}`} className="topic-row">
                    <div className="item-main">
                      <strong>{t.judul || t.matkul}</strong>
                      <span>
                        {t.matkul}
                        {t.pertemuan != null ? ` · P${t.pertemuan}` : ""}
                        {t.jatuh_tempo ? " · waktunya diulang" : t.ulang_pada ? ` · ulang ${dayLabel(t.ulang_pada)}` : ""}
                      </span>
                      <Bar value={t.penguasaan} tone={tone(t.penguasaan)} label={`Penguasaan ${t.penguasaan}%`} />
                    </div>
                    <b className="topic-pct">{t.penguasaan}%</b>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty-line">{data ? "Topik muncul di sini setelah kuis pertama." : "Memuat…"}</p>
            )}
          </Section>

          {(data?.miskonsepsi?.length ?? 0) > 0 && (
            <Section title="Yang sering keliru">
              <ul className="list">
                {data!.miskonsepsi!.map((m) => (
                  <li key={m.teks}>
                    <span className="item-text">{m.teks}</span>
                    {m.jumlah > 1 && <span className="tag">{m.jumlah}×</span>}
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </div>
      </div>

      {(data?.checks.length ?? 0) > 0 && <AnswerHistory checks={data!.checks} />}
    </>
  );
}

function HelpSection({ helps }: { helps: TutorHelp[] }) {
  return (
    <Section title="Bantuan dari SORA" note="Disiapkan otomatis saat sebuah topik terlihat sulit">
      <ul className="list">
        {helps.slice(0, 4).map((h) => {
          const status = HELP_STATUS[h.status] ?? { label: h.status, tone: "" };
          return (
            <li key={h.id} className="help-row">
              <div className="item-main">
                <strong>{h.judul}</strong>
                <span>
                  {h.matkul}
                  {h.pertemuan != null ? ` · P${h.pertemuan}` : ""} · {h.dibuat ? ago(h.dibuat) : ""}
                </span>
                {h.masalah && <p className="help-problem">{h.masalah}</p>}
                <span className="help-why">Karena: {h.alasan.join(", ")}</span>
                {h.pelajaran.length > 0 && (
                  <details className="help-lesson">
                    <summary>Lihat isi pelajaran</summary>
                    <ol>
                      {h.pelajaran.map((text, index) => (
                        <li key={index}>{text}</li>
                      ))}
                    </ol>
                  </details>
                )}
              </div>
              <div className="item-side">
                <span className={`tag ${status.tone}`}>{status.label}</span>
                {h.sebelum != null && (
                  <span className="help-score">
                    {h.sebelum}%{h.sesudah != null && <> → <b className={h.sesudah >= h.sebelum ? "good-text" : "warn-text"}>{h.sesudah}%</b></>}
                  </span>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </Section>
  );
}

type CurvePoint = LearningCurve["titik"][number] & { label: string };

function CurveDot(props: { cx?: number; cy?: number; payload?: CurvePoint; index?: number }) {
  const { cx, cy, payload, index } = props;
  if (cx == null || cy == null) return null;
  const size = payload?.bantuan ? 12 : 9;
  return <rect key={index} x={cx - size / 2} y={cy - size / 2} width={size} height={size} fill={payload?.bantuan ? GOOD : TEAL} stroke="#fffdf8" strokeWidth={2} />;
}

function CurveSection({ curves }: { curves: LearningCurve[] }) {
  const [selected, setSelected] = useState<string | null>(null);
  const curve = curves.find((c) => c.topic_key === selected) ?? curves[0];
  const points: CurvePoint[] = (curve?.titik ?? []).map((p, i) => ({ ...p, label: `Kuis ${i + 1}` }));
  return (
    <Section
      title="Perkembangan skor"
      note={points.length ? "Kotak hijau: kuis sesudah bantuan SORA" : undefined}
      action={
        curves.length > 1 ? (
          <select className="curve-select" value={curve?.topic_key} onChange={(e) => setSelected(e.target.value)} aria-label="Pilih topik">
            {curves.map((c) => (
              <option key={c.topic_key} value={c.topic_key}>
                {c.judul || c.matkul}
              </option>
            ))}
          </select>
        ) : undefined
      }
    >
      {points.length > 1 ? (
        <div className="chart" style={{ height: 220 }}>
          <ResponsiveContainer>
            <LineChart data={points} margin={{ top: 10, right: 12, left: -20, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke="#ebe2d3" />
              <XAxis dataKey="label" {...axisProps} />
              <YAxis domain={[0, 100]} ticks={[0, 50, 80, 100]} {...axisProps} />
              <ReferenceLine y={80} stroke={GOOD} strokeDasharray="4 4" />
              <Tooltip
                content={
                  <ChartTooltip<CurvePoint>
                    title={(p) => `${p.label} · ${dayLabel(p.waktu)}`}
                    rows={(p) => [
                      { label: "Skor", value: `${p.skor}%`, color: p.bantuan ? GOOD : TEAL },
                      { label: "Jenis", value: p.bantuan ? "kuis terarah SORA" : "kuis lisan" },
                    ]}
                  />
                }
              />
              <Line type="linear" dataKey="skor" stroke={TEAL} strokeWidth={3} dot={<CurveDot />} activeDot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="empty-line">Grafik muncul setelah topik yang sama diuji lebih dari sekali.</p>
      )}
      {curve && points.length > 1 && <span className="item-meta">{curve.judul || curve.matkul} · garis putus-putus = target 80%</span>}
    </Section>
  );
}

function AnswerHistory({ checks }: { checks: QuizCheck[] }) {
  return (
    <Section title="Jawaban terakhir">
      <ul className="list">
        {checks.slice(0, 8).map((c, i) => {
          const verdict = VERDICT[c.penilaian];
          return (
            <li key={`${c.waktu}-${i}`} className="answer-row">
              <span className={`tag ${verdict.tone}`}>{verdict.label}</span>
              <div className="item-main">
                <strong>{c.soal}</strong>
                <span className="answer-text">Jawabanmu: “{c.jawaban || "-"}”</span>
                {c.umpan_balik && <span>{c.umpan_balik}</span>}
              </div>
              <span className="item-meta">{ago(c.waktu)}</span>
            </li>
          );
        })}
      </ul>
    </Section>
  );
}
