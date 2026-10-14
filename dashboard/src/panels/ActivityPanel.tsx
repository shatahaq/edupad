import { Panel, SectionLabel } from "../components/Panel";
import { num } from "../lib/format";

const DAYS = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"];

/** Abu → hitam: alfa tinta di atas kartu putih. Nol tetap terlihat sebagai kotak pucat. */
const shade = (v: number, max: number) => (v === 0 ? 0.05 : 0.12 + (v / max) * 0.88);

export function ActivityPanel() {
  return (
    <Panel panel="activity" title="Aktivitas pengguna" subtitle="Pertanyaan per jam, 7 hari terakhir (WIB)">
      {(d) => {
        const max = Math.max(1, ...d.matrix.flat());
        return (
          <div className="activity">
            <div className="heatmap-col">
              <div className="heatmap-wrap">
                <div className="heatmap" role="img" aria-label="Peta panas pertanyaan per hari dan jam">
                  <span />
                  {Array.from({ length: 24 }, (_, h) => (
                    <span key={h} className="hm-hour">
                      {h % 3 === 0 ? String(h).padStart(2, "0") : ""}
                    </span>
                  ))}
                  {d.matrix.map((row, day) => (
                    <Row key={day} label={DAYS[day]} row={row} max={max} />
                  ))}
                </div>
              </div>
              <div className="hm-scale">
                sedikit
                {[0.05, 0.3, 0.55, 0.8, 1].map((a) => (
                  <i key={a} style={{ background: `rgba(24, 24, 27, ${a})` }} />
                ))}
                banyak
              </div>
            </div>

            <div className="top-questions">
              <SectionLabel>Pertanyaan terbanyak</SectionLabel>
              <ol className="ranked">
                {d.top_questions.map((q, i) => (
                  <li key={q.text}>
                    <span className="rank mono">{String(i + 1).padStart(2, "0")}</span>
                    <span className="ranked-text">{q.text}</span>
                    <span className="mono num">{num(q.count)}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        );
      }}
    </Panel>
  );
}

function Row({ label, row, max }: { label: string; row: number[]; max: number }) {
  return (
    <>
      <span className="hm-day">{label}</span>
      {row.map((v, h) => (
        <span
          key={h}
          className="hm-cell"
          style={{ background: `rgba(24, 24, 27, ${shade(v, max)})` }}
          title={`${label} ${String(h).padStart(2, "0")}.00 — ${v} pertanyaan`}
        />
      ))}
    </>
  );
}
