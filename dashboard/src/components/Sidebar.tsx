import { useEffect, useState, type CSSProperties } from "react";
import { usePanel } from "../api/usePanel";
import { NAV, type NavId } from "../lib/nav";
import { OWL_COLOR, owlSrc } from "../lib/owls";
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

/** Angka kecil di menu hanya untuk hal yang perlu segera ditindaklanjuti. */
function useBadges(): Partial<Record<NavId, Badge>> {
  const meetings = usePanel("attendance").data?.today ?? [];
  const tasks = usePanel("assignments").data?.tasks ?? [];

  const open = meetings.filter((m) => m.window === "dibuka").length;
  const pending = tasks.filter((t) => !t.submitted && !t.overdue && t.deadline);
  const urgent = pending.some((t) => new Date(t.deadline!).getTime() - Date.now() < DAY_MS);

  const badges: Partial<Record<NavId, Badge>> = {};
  if (open) badges.presensi = { text: String(open), tone: "good", title: `${open} presensi sedang dibuka` };
  if (pending.length)
    badges.tugas = { text: String(pending.length), tone: urgent ? "bad" : undefined, title: `${pending.length} tugas belum dikumpulkan` };
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
        <div className="brand">
          <img className="brand-owl" src={owlSrc("nova")} alt="" width={44} height={44} />
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
                const color = item.owl ? OWL_COLOR[item.owl] : "var(--slate-muted)";
                return (
                  <button
                    key={item.id}
                    className={`nav-item ${active === item.id ? "active" : ""}`}
                    style={{ "--owl": color } as CSSProperties}
                    aria-current={active === item.id ? "page" : undefined}
                    title={badge?.title}
                    onClick={() => onNavigate(item.id)}
                  >
                    <i className="nav-dot" aria-hidden />
                    <span>{item.label}</span>
                    {badge && <span className={`nav-badge ${badge.tone ?? ""}`}>{badge.text}</span>}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="profile">
          <span className="avatar" aria-hidden>
            {viewer?.picture ? <img src={viewer.picture} alt="" referrerPolicy="no-referrer" /> : initials(displayName)}
          </span>
          <div className="profile-text">
            <strong>{displayName}</strong>
            {(preferences.studentId || viewer?.email) && <span>{preferences.studentId || viewer?.email}</span>}
          </div>
          {viewer && (
            <button className="logout-btn" onClick={logout}>
              Keluar
            </button>
          )}
        </div>
      </aside>
      <div className={`scrim ${open ? "open" : ""}`} onClick={onClose} aria-hidden />
    </>
  );
}
