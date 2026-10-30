import { useMemo } from "react";

import { assetUrl } from "../../../ai-office/src/game/assetUrl";
import { useOfficeData } from "../../../ai-office/src/hooks/useOfficeData";
import type { AgentState, OfficeAgent } from "../../../ai-office/src/types";
import "./neo-office.css";

// AI Office versi neo-brutalism: denah kantor sebagai blok, bukan permainan Phaser.
// Datanya sama dengan versi pertama (useOfficeData -> /api/office/snapshot), jadi yang
// ditampilkan tetap pekerjaan agent yang sebenarnya.

const OWL_BY_AGENT: Record<string, { owl: string; color: string }> = {
  coordinator: { owl: "nova", color: "#30B8E8" },
  researcher: { owl: "pixel", color: "#3F97EA" },
  tutor: { owl: "sora", color: "#EFB81A" },
  planner: { owl: "tempo", color: "#A77EF0" },
  analyst: { owl: "metric", color: "#2FD3A3" },
  finance: { owl: "koin", color: "#3DB368" },
  keeper: { owl: "nexus", color: "#EF5F6F" },
};

const ROOM_NAME: Record<string, string> = {
  "command-center": "Command Center",
  "research-lab": "Research Lab",
  "tutor-room": "Tutor Room",
  "planning-hub": "Planning Hub",
  "analytics-room": "Analytics Room",
  "finance-office": "Finance Office",
  "knowledge-server": "Knowledge Server",
};

const STATE_LABEL: Record<AgentState, string> = {
  offline: "Tidak terhubung",
  idle: "Siaga",
  queued: "Menunggu giliran",
  running: "Sedang bekerja",
  waiting: "Menunggu data",
  succeeded: "Pekerjaan selesai",
  failed: "Perlu diperiksa",
  cancelled: "Dibatalkan",
};

/** Warna label status: hanya tiga tingkat, selebihnya netral. */
const STATE_TAG: Partial<Record<AgentState, string>> = {
  running: "good",
  succeeded: "good",
  waiting: "warn",
  queued: "warn",
  failed: "bad",
  offline: "bad",
};

const ORDER = ["coordinator", "researcher", "tutor", "planner", "analyst", "finance", "keeper"];

function readableTime(value?: string | null) {
  if (!value) return "belum ada pembaruan";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "waktu tidak tersedia";
  return new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(date);
}

function RoomCard({ agent }: { agent: OfficeAgent }) {
  const owl = OWL_BY_AGENT[agent.id] ?? { owl: "nova", color: "#30B8E8" };
  const titleId = `kamar-${agent.id}`;
  const running = agent.state === "running";

  return (
    <article className="no-room card" aria-labelledby={titleId}>
      <header className="no-room-head" style={{ background: owl.color }}>
        <h3 id={titleId}>{ROOM_NAME[agent.room] ?? agent.room}</h3>
        <span className="no-room-agent">{agent.name}</span>
      </header>

      <div className="no-room-body">
        <img className="no-room-owl" src={assetUrl(`assets/agents/owls/avatar/${owl.owl}-idle.png`)} alt="" width={72} height={72} />
        <div className="no-room-text">
          <p className="no-room-role">{agent.role}</p>
          <p className="no-room-task">{agent.task || "Belum ada pekerjaan"}</p>
          <p className="no-room-meta">
            <span className={`tag ${STATE_TAG[agent.state] ?? ""}`}>{STATE_LABEL[agent.state]}</span>
            <span className="no-room-time">Diperbarui {readableTime(agent.updated_at)}</span>
          </p>
        </div>
      </div>

      {running && (
        <div className="no-room-progress" role="progressbar" aria-valuenow={agent.progress} aria-valuemin={0} aria-valuemax={100} aria-label={`Kemajuan ${agent.name}`}>
          <span style={{ width: `${Math.max(0, Math.min(100, agent.progress))}%` }} />
        </div>
      )}
    </article>
  );
}

export function NeoOffice() {
  const { snapshot, apiAvailable } = useOfficeData();

  const agents = useMemo(
    () => [...snapshot.agents].sort((a, b) => ORDER.indexOf(a.id) - ORDER.indexOf(b.id)),
    [snapshot.agents],
  );
  const tasks = apiAvailable ? snapshot.tasks : [];
  const events = apiAvailable ? snapshot.recent_events.slice(0, 8) : [];

  return (
    <section className="no-office" aria-label="Kantor AI EduPad">
      {!apiAvailable && (
        <p className="no-offline" role="status">
          <b>Kantor belum terhubung ke server EduPad.</b> Yang tampil di bawah ini contoh tampilan, bukan pekerjaan yang sedang berjalan.
        </p>
      )}

      <div className="no-metrics">
        <Metric label="Owl bekerja" value={snapshot.metrics.active_agents} />
        <Metric label="Antrean tugas" value={snapshot.metrics.queued_tasks} />
        <Metric label="Tugas selesai" value={snapshot.metrics.completed_tasks} />
        <Metric label="Kesehatan pengetahuan" value={`${snapshot.metrics.knowledge_health}%`} />
      </div>

      <div className="no-floor">
        {agents.map((agent) => (
          <RoomCard key={agent.id} agent={agent} />
        ))}
      </div>

      <div className="no-lists">
        <div className="card no-list">
          <div className="panel-head">
            <h2 className="card-title">Tugas kantor</h2>
          </div>
          {tasks.length === 0 ? (
            <p className="empty">Belum ada tugas yang tercatat.</p>
          ) : (
            <ul>
              {tasks.slice(0, 6).map((task) => (
                <li key={task.id}>
                  <span className="no-list-main">{task.title}</span>
                  <span className="tag">{task.status}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card no-list">
          <div className="panel-head">
            <h2 className="card-title">Kabar terakhir</h2>
          </div>
          {events.length === 0 ? (
            <p className="empty">Belum ada kabar dari kantor.</p>
          ) : (
            <ul>
              {events.map((event) => (
                <li key={event.id}>
                  <span className="no-list-main">{event.message || event.job_type}</span>
                  <span className="no-room-time">{readableTime(event.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="card no-metric">
      <p className="no-metric-label">{label}</p>
      <p className="no-metric-value">{value}</p>
    </div>
  );
}
