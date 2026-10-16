import { useEffect, useState } from "react";
import { DATA_SOURCE, REFRESH_SECONDS } from "../api/client";
import { usePanel } from "../api/usePanel";
import { NAV, type NavId } from "../lib/nav";
import { DEFAULT_PREFERENCES, initials, loadPreferences, PREFERENCES_UPDATED, type DashboardPreferences } from "../lib/preferences";
import { logout, useViewer } from "../lib/session";
import { Icon } from "./Icon";

interface Props {
  active: NavId;
  open: boolean;
  onNavigate: (id: NavId) => void;
  onClose: () => void;
}

type Badge = { text: string; tone?: "good" | "bad"; title: string };

const DAY_MS = 86_400_000;

/** Badge menu dihitung dari data panel (fetch dibagi dengan kartunya). */
function useBadges(): Partial<Record<NavId, Badge>> {
  const meetings = usePanel("attendance").data?.today ?? [];
  const tasks = usePanel("assignments").data?.tasks ?? [];
  const services = usePanel("services").data?.services ?? [];
  const devices = usePanel("devices").data?.devices ?? [];

  const open = meetings.filter((m) => m.window === "dibuka").length;
  const pending = tasks.filter((t) => !t.submitted && t.deadline);
  const urgent = pending.some((t) => new Date(t.deadline!).getTime() - Date.now() < DAY_MS);
  const issues = services.filter((s) => s.state === "down").length + devices.filter((d) => !d.online).length;

  const badges: Partial<Record<NavId, Badge>> = {};
  if (open) badges.presensi = { text: String(open), tone: "good", title: `${open} presensi sedang dibuka` };
  if (pending.length)
    badges.tugas = { text: String(pending.length), tone: urgent ? "bad" : undefined, title: `${pending.length} tugas belum dikumpulkan` };
  if (issues) badges.monitoring = { text: String(issues), tone: "bad", title: `${issues} layanan/perangkat bermasalah` };
  return badges;
}

export function Sidebar({ active, open, onNavigate, onClose }: Props) {
  const badges = useBadges();
  const viewer = useViewer();
  const [preferences, setPreferences] = useState<DashboardPreferences>(() => loadPreferences());

  useEffect(() => {
    const update = (event: Event) => setPreferences((event as CustomEvent<DashboardPreferences>).detail);
    window.addEventListener(PREFERENCES_UPDATED, update);
    return () => window.removeEventListener(PREFERENCES_UPDATED, update);
  }, []);

  const custom = preferences.studentName !== DEFAULT_PREFERENCES.studentName;
  const displayName = (custom ? preferences.studentName : viewer?.name) || preferences.studentName;

  return (
    <>
      <aside className={`sidebar ${open ? "open" : ""}`} aria-label="Navigasi">
        <div className="brand card">
          <span className="brand-mark" aria-hidden>
            E
          </span>
          <div className="brand-text">
            <strong>EduPad</strong>
            <span>Asisten belajar</span>
          </div>
          <button className="icon-btn drawer-close" onClick={onClose} aria-label="Tutup menu">
            <Icon name="close" size={14} />
          </button>
        </div>

        <nav className="nav">
          {NAV.map((g) => (
            <div key={g.group} className="nav-group">
              <div className="nav-label">{g.group}</div>
              {g.items.map((item) => {
                const badge = badges[item.id];
                return (
                  <button
                    key={item.id}
                    className={`nav-item ${active === item.id ? "active" : ""}`}
                    aria-current={active === item.id ? "page" : undefined}
                    title={item.target === false ? "Belum tersedia" : badge?.title}
                    onClick={() => onNavigate(item.id)}
                  >
                    <Icon name={item.icon} />
                    <span>{item.label}</span>
                    {badge && <span className={`nav-badge ${badge.tone ?? ""}`}>{badge.text}</span>}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-foot">
          <div className="source card">
            <div className="source-row">
              <span className="muted">Sumber data</span>
              <span className={`pill ${DATA_SOURCE === "mock" ? "warn" : "good"}`}>
                {DATA_SOURCE === "mock" ? "Data dummy" : "Server live"}
              </span>
            </div>
            <div className="source-row muted">
              <Icon name="refresh" size={12} />
              Refresh otomatis {REFRESH_SECONDS} dtk
            </div>
          </div>

          <div className="profile card">
            <span className="avatar" aria-hidden>
              {viewer?.picture ? <img src={viewer.picture} alt="" referrerPolicy="no-referrer" /> : initials(displayName)}
              <i className="online" />
            </span>
            <div className="profile-text">
              <strong>{displayName}</strong>
              <span>{preferences.studentId || viewer?.email || "EduPad terhubung"}</span>
            </div>
            {viewer && (
              <button className="icon-btn profile-logout" onClick={logout} aria-label="Keluar" title="Keluar">
                <Icon name="external" size={13} />
              </button>
            )}
          </div>
        </div>
      </aside>
      <div className={`scrim ${open ? "open" : ""}`} onClick={onClose} aria-hidden />
    </>
  );
}
