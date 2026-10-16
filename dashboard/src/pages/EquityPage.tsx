import { PageHeader } from "../components/PageHeader";
import { Icon } from "../components/Icon";
import { usePanel } from "../api/usePanel";
import type { KnowledgeData, LearningData } from "../api/types";
import { num } from "../lib/format";

type Coverage = KnowledgeData["per_course"][number] & { discussed: boolean };

function courseKey(value: string) {
  return value
    .toLocaleLowerCase("id-ID")
    .replace(/\bprak\./g, "praktikum")
    .replace(/\b(kelas|mata kuliah)\b/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function sumQuestions(days: LearningData["daily"]) {
  return days.reduce((total, day) => total + day.questions, 0);
}

function supportLevel(value: number, max: number) {
  const ratio = value / Math.max(1, max);
  if (ratio >= 0.7) return "Tinggi";
  if (ratio >= 0.4) return "Sedang";
  return "Awal";
}

export function EquityPage() {
  const learning = usePanel("learning");
  const knowledge = usePanel("knowledge");
  const schedule = usePanel("schedule");
  const data = learning.data;

  const discussedKeys = new Set((data?.courses ?? []).map((course) => courseKey(course.course)));
  const coverage: Coverage[] = (knowledge.data?.per_course ?? []).map((course) => ({
    ...course,
    discussed: discussedKeys.has(courseKey(course.course)),
  }));
  const knownKeys = new Set(coverage.map((course) => courseKey(course.course)));
  const scheduledCourses = Array.from(new Set((schedule.data?.classes ?? []).map((item) => item.course)));
  const unavailable = scheduledCourses.filter((course) => !knownKeys.has(courseKey(course)));
  const topics = data?.sources_top ?? [];
  const maxTopicCount = Math.max(1, ...topics.map((topic) => topic.count));
  const highSupport = topics.filter((topic) => topic.count / maxTopicCount >= 0.7).length;
  const sourceUses = topics.reduce((total, topic) => total + topic.count, 0);
  const recent = data?.daily.slice(-7) ?? [];
  const previous = data?.daily.slice(-14, -7) ?? [];
  const recentTotal = sumQuestions(recent);
  const previousTotal = sumQuestions(previous);
  const supportTrend = previousTotal ? Math.round(((recentTotal - previousTotal) / previousTotal) * 100) : null;
  const loading = learning.loading || knowledge.loading || schedule.loading;
  const error = learning.error || knowledge.error || schedule.error;

  const interventions = [
    ...unavailable.slice(0, 2).map((course) => ({
      title: course,
      reason: "Belum ditemukan di basis pengetahuan.",
      action: "Prioritaskan materi yang mudah diakses, ringkasan, dan format alternatif.",
    })),
    ...topics.slice(0, 3).map((topic) => ({
      title: topic.judul ?? `Pertemuan ${topic.pertemuan}`,
      reason: `${topic.course} | dirujuk ${topic.count} kali dalam jawaban EduPad.`,
      action: "Tinjau penjelasan, contoh, dan latihan singkat untuk topik ini.",
    })),
  ].slice(0, 4);

  return (
    <div className="equity-page">
      <PageHeader title="Learning Equity Radar" subtitle="Dashboard kesenjangan akses dan pemahaman belajar | data agregat 30 hari terakhir" />

      <section className="card equity-privacy" aria-label="Prinsip privasi Equity Radar">
        <Icon name="users" size={18} />
        <div>
          <strong>Agregat, anonim, dan tidak memberi label mahasiswa</strong>
          <p>
            Frekuensi pertanyaan menunjukkan kebutuhan dukungan, bukan kemampuan, kondisi ekonomi, tingkat ketekunan, atau risiko individu.
          </p>
        </div>
        <span className="equity-sdgs">SDGs 1 / 4 / 17</span>
      </section>

      {error && <div className="panel-error" role="alert">Sebagian data belum tersedia: {error}</div>}

      <section className="equity-kpis" aria-busy={loading}>
        <EquityMetric label="Topik terpantau" value={data ? num(topics.length) : "\u2014"} note="berdasarkan sumber jawaban" />
        <EquityMetric label="Butuh dukungan tinggi" value={data ? num(highSupport) : "\u2014"} note="sinyal relatif, bukan label" />
        <EquityMetric label="Pemakaian sumber" value={data ? num(sourceUses) : "\u2014"} note="rujukan teratas dalam 30 hari" />
        <EquityMetric label="Pemahaman" value="Belum terukur" note="perlu kuis atau umpan balik" compact />
      </section>

      <div className="equity-grid">
        <section className="card equity-card">
          <header>
            <div>
              <h2>Sinyal kebutuhan dukungan</h2>
              <p>Topik yang paling sering dirujuk saat menjawab pertanyaan</p>
            </div>
            <span className="equity-trend">
              7 hari {supportTrend === null ? "\u2014" : `${supportTrend >= 0 ? "+" : ""}${supportTrend}%`}
            </span>
          </header>
          {topics.length ? (
            <ol className="equity-topic-list">
              {topics.slice(0, 8).map((topic, index) => (
                <li key={`${topic.course}-${topic.pertemuan}`}>
                  <span className="rank mono">{String(index + 1).padStart(2, "0")}</span>
                  <span>
                    <strong>{topic.judul ?? `Pertemuan ${topic.pertemuan}`}</strong>
                    <small>{topic.course} | pertemuan {topic.pertemuan}</small>
                  </span>
                  <span className="equity-signal">
                    <b>{supportLevel(topic.count, maxTopicCount)}</b>
                    <small>{topic.count} rujukan</small>
                  </span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="empty">Belum ada sumber belajar yang cukup untuk membentuk sinyal.</p>
          )}
          <p className="equity-method-note">Sinyal tinggi berarti relatif lebih sering ditanyakan, bukan bukti bahwa mahasiswa gagal memahami materi.</p>
        </section>

        <section className="card equity-card">
          <header>
            <div>
              <h2>Ketersediaan materi</h2>
              <p>Cakupan basis pengetahuan untuk mata kuliah aktif</p>
            </div>
          </header>
          <div className="equity-coverage-summary">
            <span><b>{knowledge.data?.courses_total ?? "\u2014"}</b> mata kuliah tersedia</span>
            <span><b>{unavailable.length}</b> belum ditemukan</span>
          </div>
          <ul className="equity-coverage-list">
            {coverage.slice(0, 8).map((course) => (
              <li key={course.course}>
                <span>
                  <strong>{course.course}</strong>
                  <small>{course.meetings} pertemuan | {num(course.chunks)} potongan materi</small>
                </span>
                <b>{course.discussed ? "Digunakan" : "Tersedia"}</b>
              </li>
            ))}
            {unavailable.slice(0, 4).map((course) => (
              <li key={course} className="is-missing">
                <span><strong>{course}</strong><small>Belum ada materi terindeks</small></span>
                <b>Lengkapi</b>
              </li>
            ))}
          </ul>
          <p className="equity-method-note">Ketersediaan format aksesibel belum diaudit; radar saat ini baru memeriksa materi yang terindeks.</p>
        </section>
      </div>

      <section className="card equity-card equity-actions">
        <header>
          <div>
            <h2>Prioritas intervensi pembelajaran</h2>
            <p>Saran berbasis pola agregat yang dapat ditinjau dosen atau mitra</p>
          </div>
        </header>
        {interventions.length ? (
          <div className="equity-action-grid">
            {interventions.map((item, index) => (
              <article key={`${item.title}-${index}`}>
                <span className="mono">{String(index + 1).padStart(2, "0")}</span>
                <div><strong>{item.title}</strong><p>{item.reason}</p><small>{item.action}</small></div>
              </article>
            ))}
          </div>
        ) : (
          <p className="empty">Belum ada data yang cukup untuk menyusun prioritas intervensi.</p>
        )}
      </section>
    </div>
  );
}

function EquityMetric({ label, value, note, compact = false }: { label: string; value: string; note: string; compact?: boolean }) {
  return (
    <article className="card equity-metric">
      <span>{label}</span>
      <strong className={compact ? "is-compact" : undefined}>{value}</strong>
      <small>{note}</small>
    </article>
  );
}
