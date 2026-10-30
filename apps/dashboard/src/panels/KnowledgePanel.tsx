import { BarList, Panel, SectionLabel, Stat } from "../components/Panel";
import { ago, num } from "../lib/format";

export function KnowledgePanel() {
  return (
    <Panel panel="knowledge" title="Basis pengetahuan" subtitle="Materi kuliah & indeks vektor">
      {(d) => (
        <>
          <div className="stats">
            <Stat label="Chunk terindeks" value={num(d.chunks_total)} hint={`${d.courses_total} mata kuliah`} />
            <Stat
              label="Pipeline terakhir"
              value={<span className="stat-text">{ago(d.last_pipeline_at)}</span>}
              hint={d.last_pipeline_ok == null ? undefined : d.last_pipeline_ok ? "berhasil" : "gagal"}
              tone={d.last_pipeline_ok == null ? undefined : d.last_pipeline_ok ? "good" : "bad"}
            />
            <Stat
              label="Belum di-embed"
              value={num(d.pending_index)}
              hint={`${d.new_materials_24h} materi baru 24 jam`}
              tone={d.pending_index > 0 ? "warn" : "good"}
            />
          </div>

          <div className="block">
            <SectionLabel>Chunk per mata kuliah</SectionLabel>
            <BarList
              items={d.per_course.map((c) => ({ label: c.course, value: c.chunks, title: `${c.course}: ${num(c.chunks)} chunk, ${c.meetings} pertemuan` }))}
            />
          </div>
        </>
      )}
    </Panel>
  );
}
