import { BarList, Panel, SectionLabel, Stat } from "../components/Panel";
import { C } from "../lib/chart";
import { dec, num, secs } from "../lib/format";

export function AgentPanel() {
  return (
    <Panel panel="agent" title="AI Agent" subtitle="Kualitas & kecepatan jawaban">
      {(d) => {
        const stages = [
          { key: "STT", value: d.stage_avg_s.stt, color: C.inkFaint },
          { key: "Agent", value: d.stage_avg_s.agent, color: C.ink },
          { key: "TTS", value: d.stage_avg_s.tts_first_audio, color: C.inkSoft },
        ];
        const total = stages.reduce((s, x) => s + (x.value ?? 0), 0);

        return (
          <>
            <div className="stats">
              <Stat label="Jawaban" value={num(d.answers)} hint={`${d.window_hours} jam`} />
              <Stat
                label="Pakai sumber"
                value={d.with_source_pct ?? "—"}
                unit={d.with_source_pct == null ? undefined : "%"}
                hint={d.with_source_pct == null ? "belum tercatat" : d.with_source_pct >= 85 ? "baik" : "rendah"}
                tone={d.with_source_pct == null ? undefined : d.with_source_pct >= 85 ? "good" : "warn"}
              />
              <Stat label="Token/jawaban" value={num(d.tokens_avg)} hint={`${dec(d.llm_calls_avg)} panggilan LLM`} />
            </div>

            <div className="block">
              <SectionLabel>
                Waktu per tahap <span className="section-aside mono">{secs(total)} s.d. suara</span>
              </SectionLabel>
              <div className="stack" role="img" aria-label={`Waktu per tahap, total ${secs(total)}`}>
                {stages.map((s) => (
                  <div key={s.key} style={{ flex: s.value ?? 0, background: s.color }} title={`${s.key}: ${s.value == null ? "belum tercatat" : secs(s.value)}`} />
                ))}
              </div>
              <ul className="legend">
                {stages.map((s) => (
                  <li key={s.key}>
                    <i style={{ background: s.color }} />
                    {s.key} <span className="mono">{s.value == null ? "—" : secs(s.value)}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="block">
              <SectionLabel>Mata kuliah paling ditanya</SectionLabel>
              <BarList items={d.top_courses.map((c) => ({ label: c.course, value: c.questions }))} />
            </div>

            <div className="block">
              <SectionLabel>Tool dipanggil</SectionLabel>
              <div className="pills">
                {d.tools.map((t) => (
                  <span key={t.tool} className="pill chip mono">
                    {t.tool} <b>{num(t.count)}</b>
                  </span>
                ))}
              </div>
            </div>

            {d.eval && (
              <p className="footnote">
                Eval terakhir <code>{d.eval.label}</code>: skor{" "}
                <span className="mono">
                  {d.eval.score.toFixed(2).replace(".", ",")}/{d.eval.max_score}
                </span>
                , {d.eval.hallucinations} halusinasi dari {d.eval.cases} kasus.
              </p>
            )}
          </>
        );
      }}
    </Panel>
  );
}
