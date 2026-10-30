import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { LearningData } from "../api/types";
import { ChartTooltip } from "../components/ChartTooltip";
import { Panel, Stat } from "../components/Panel";
import { axisProps, C, cursorProps } from "../lib/chart";
import { dayLabel, dec, num } from "../lib/format";

type Day = LearningData["daily"][number];

export function LearningActivityPanel() {
  return (
    <Panel panel="learning" id="learning-activity" title="Aktivitas belajar" subtitle="Pertanyaan ke EduPad per hari">
      {(d) => {
        const active = d.daily.filter((x) => x.questions > 0).length;
        return (
          <>
            <div className="stats">
              <Stat label="Pertanyaan" value={num(d.questions_total)} hint={`${d.window_days} hari`} />
              <Stat label="Hari aktif" value={active} unit={`/${d.window_days}`} hint="hari bertanya" />
              <Stat label="Mata kuliah" value={d.courses.length} hint="dibahas" />
              <Stat label="Rata-rata" value={active ? dec(d.questions_total / active) : "0"} hint="per hari aktif" />
            </div>
            <div className="chart" style={{ height: 150 }}>
              <ResponsiveContainer>
                <BarChart data={d.daily} margin={{ top: 4, right: 0, left: -28, bottom: 0 }} barCategoryGap="25%">
                  <CartesianGrid vertical={false} stroke={C.grid} />
                  <XAxis dataKey="date" tickFormatter={dayLabel} interval="preserveStartEnd" minTickGap={28} {...axisProps} />
                  <YAxis allowDecimals={false} {...axisProps} />
                  <Tooltip
                    cursor={cursorProps}
                    content={<ChartTooltip<Day> title={(p) => dayLabel(p.date)} rows={(p) => [{ label: "Pertanyaan", value: num(p.questions), color: C.ink }]} />}
                  />
                  <Bar dataKey="questions" fill={C.ink} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        );
      }}
    </Panel>
  );
}

export function MemoryPanel() {
  return (
    <Panel panel="learning" id="learning-memory" title="Yang diingat EduPad" subtitle="Dipakai agar jawaban menyesuaikan dirimu">
      {(d) =>
        d.facts.length ? (
          <ul className="facts">
            {d.facts.map((f) => (
              <li key={f}>
                <i className="fact-dot" aria-hidden />
                <span>{f}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="empty">Belum ada yang diingat.</p>
        )
      }
    </Panel>
  );
}

export function CoursesLearnedPanel() {
  return (
    <Panel panel="learning" id="learning-courses" title="Mata kuliah yang dibahas" subtitle="Jumlah pertanyaan & pertemuan yang ditanyakan">
      {(d) => {
        const max = Math.max(1, ...d.courses.map((c) => c.questions));
        return (
          <ol className="bars tall">
            {d.courses.map((c) => (
              <li key={c.course}>
                <span className="bars-label">
                  {c.course}
                  <span className="cell-sub mono">{c.meetings.length ? `p${c.meetings.join(", p")}` : "—"}</span>
                </span>
                <span className="bars-track">
                  <span style={{ width: `${(c.questions / max) * 100}%` }} />
                </span>
                <span className="mono num">{num(c.questions)}</span>
              </li>
            ))}
          </ol>
        );
      }}
    </Panel>
  );
}

export function SourcesPanel() {
  return (
    <Panel panel="learning" id="learning-sources" title="Materi paling sering dirujuk" subtitle="Sumber jawaban agent">
      {(d) => (
        <ol className="ranked">
          {d.sources_top.map((s, i) => (
            <li key={`${s.course}-${s.pertemuan}`}>
              <span className="rank mono">{String(i + 1).padStart(2, "0")}</span>
              <span className="ranked-text">
                {s.judul ?? `Pertemuan ${s.pertemuan}`}
                <span className="cell-sub">
                  {s.course} · p{s.pertemuan}
                </span>
              </span>
              <span className="mono num">{num(s.count)}×</span>
            </li>
          ))}
        </ol>
      )}
    </Panel>
  );
}
