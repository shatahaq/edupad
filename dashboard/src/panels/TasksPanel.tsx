import { useState } from "react";
import type { Task } from "../api/types";
import { Icon } from "../components/Icon";
import { Panel } from "../components/Panel";
import { countdown, dayLabel, hourLabel } from "../lib/format";
import { go } from "../lib/router";

const DAY_MS = 86_400_000;

type Filter = "pending" | "overdue" | "done" | "all";

const FILTERS: { id: Filter; label: string; match: (t: Task) => boolean }[] = [
  { id: "pending", label: "Belum dikumpulkan", match: (t) => !t.submitted && !t.overdue },
  { id: "overdue", label: "Lewat deadline", match: (t) => !t.submitted && t.overdue },
  { id: "done", label: "Selesai", match: (t) => t.submitted },
  { id: "all", label: "Semua", match: () => true },
];

/** Waktu deadline; tanpa deadline dianggap paling jauh. */
const dueMs = (t: Task) => (t.deadline ? new Date(t.deadline).getTime() : Number.MAX_SAFE_INTEGER);

/** Belum dikumpulkan: deadline terdekat dulu; lainnya: deadline terbaru dulu. Tanpa deadline selalu di akhir. */
function sortTasks(tasks: Task[], filter: Filter) {
  const latestFirst = (t: Task) => (t.deadline ? -new Date(t.deadline).getTime() : Number.MAX_SAFE_INTEGER);
  const key = filter === "pending" ? dueMs : latestFirst;
  return [...tasks].sort((a, b) => key(a) - key(b));
}

function status(t: Task): { label: string; tone?: "good" | "warn" | "bad" } {
  if (t.submitted) {
    if (t.graded) return { label: t.nilai ? `Dinilai ${t.nilai.split("/")[0].trim()}` : "Dinilai", tone: "good" };
    return t.late_submission ? { label: "Dikumpulkan terlambat", tone: "warn" } : { label: "Dikumpulkan", tone: "good" };
  }
  if (t.overdue) return { label: "Lewat deadline", tone: "bad" };
  return { label: t.jenis === "kuis" ? "Belum dikerjakan" : "Belum dikumpulkan" };
}

export function TaskRow({ t }: { t: Task }) {
  const s = status(t);
  const urgent = !t.submitted && !t.overdue && dueMs(t) - Date.now() < DAY_MS;
  return (
    <li>
      <details className="task">
        <summary>
          <div className="task-due mono">
            <b>{t.deadline ? dayLabel(t.deadline) : "—"}</b>
            <span>{t.deadline ? hourLabel(t.deadline) : "tanpa batas"}</span>
          </div>
          <div className="row-main">
            <div className="cell-strong wrap">{t.judul}</div>
            <div className="cell-sub wrap">
              {t.course} · {t.jenis}
              {t.pertemuan != null && ` · p${t.pertemuan}`}
            </div>
          </div>
          <div className="row-side">
            <span className={`pill ${s.tone ?? ""}`}>{s.label}</span>
            {t.deadline && !t.submitted && <div className={`cell-sub mono ${urgent || t.overdue ? "bad-text" : ""}`}>{countdown(t.deadline)}</div>}
          </div>
          <Icon name="chevron" size={14} className="task-chev" />
        </summary>
        <div className="task-body">
          <p>{t.soal || "Tidak ada deskripsi soal."}</p>
          <a className="link" href={t.url} target="_blank" rel="noreferrer">
            Buka di kelas.usu.ac.id <Icon name="external" size={12} />
          </a>
        </div>
      </details>
    </li>
  );
}

/** Semua tugas dengan filter (halaman Tugas). */
export function TasksPanel() {
  const [filter, setFilter] = useState<Filter>("pending");
  return (
    <Panel panel="assignments" title="Tugas & kuis" subtitle="kelas.usu.ac.id · klik untuk melihat soal">
      {(d) => {
        const f = FILTERS.find((x) => x.id === filter)!;
        const list = sortTasks(d.tasks.filter(f.match), filter);
        return (
          <>
            <div className="segmented tabs" role="group" aria-label="Filter tugas">
              {FILTERS.map((x) => (
                <button key={x.id} aria-pressed={filter === x.id} onClick={() => setFilter(x.id)}>
                  {x.label} <span className="mono">{d.tasks.filter(x.match).length}</span>
                </button>
              ))}
            </div>
            {list.length ? (
              <ul className="rows tasks">
                {list.map((t) => (
                  <TaskRow key={t.id} t={t} />
                ))}
              </ul>
            ) : (
              <p className="empty">Tidak ada tugas di kategori ini.</p>
            )}
          </>
        );
      }}
    </Panel>
  );
}

/** Tugas yang belum dikumpulkan, deadline terdekat dulu (Beranda). */
export function UpcomingTasksPanel({ limit = 4 }: { limit?: number }) {
  return (
    <Panel
      panel="assignments"
      title="Tugas mendekati deadline"
      subtitle="Belum dikumpulkan"
      action={
        <button className="link-btn" onClick={() => go("tugas")}>
          Semua
        </button>
      }
    >
      {(d) => {
        const pending = sortTasks(d.tasks.filter(FILTERS[0].match), "pending");
        const overdue = d.tasks.filter(FILTERS[1].match).length;
        return (
          <>
            {pending.length ? (
              <ul className="rows tasks">
                {pending.slice(0, limit).map((t) => (
                  <TaskRow key={t.id} t={t} />
                ))}
              </ul>
            ) : (
              <p className="empty">Semua tugas sudah dikumpulkan.</p>
            )}
            {(overdue > 0 || pending.length > limit) && (
              <p className="footnote">
                {pending.length > limit && <>{pending.length - limit} tugas lain belum dikumpulkan. </>}
                {overdue > 0 && <span className="bad-text">{overdue} tugas lewat deadline belum dikumpulkan.</span>}
              </p>
            )}
          </>
        );
      }}
    </Panel>
  );
}
