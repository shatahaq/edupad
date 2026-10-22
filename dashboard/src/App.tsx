import { lazy, Suspense, useEffect, useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { Topbar } from "./components/Topbar";
import { pageLabel } from "./lib/nav";
import { go, useRoute } from "./lib/router";
import { applyPreferences, loadPreferences } from "./lib/preferences";
import { CONSENT_URL, useViewer } from "./lib/session";
import { AttendancePage } from "./pages/AttendancePage";
import { ConversationsPage } from "./pages/ConversationsPage";
import { EquityPage } from "./pages/EquityPage";
import { FinancePage } from "./pages/FinancePage";
import { HelpPage } from "./pages/HelpPage";
import { HomePage } from "./pages/HomePage";
import { LearningPage } from "./pages/LearningPage";
import { MonitoringPage } from "./pages/MonitoringPage";
import { SchedulePage } from "./pages/SchedulePage";
import { SettingsPage } from "./pages/SettingsPage";
import { TasksPage } from "./pages/TasksPage";
import { TutorPage } from "./pages/TutorPage";

// Kantor virtual memakai Phaser (~1 MB); dimuat terpisah agar halaman lain tetap cepat dibuka.
const OfficePage = lazy(() => import("./pages/OfficePage").then((m) => ({ default: m.OfficePage })));

export function App() {
  const { page, section } = useRoute();
  const [drawer, setDrawer] = useState(false);
  const viewer = useViewer();
  const needsClassroom = viewer && (!viewer.classroom.granted || viewer.classroom.reauth_required);

  useEffect(() => {
    applyPreferences(loadPreferences());
  }, []);

  // Halaman baru mulai dari atas (kecuali menuju kartu tertentu di Monitoring).
  useEffect(() => {
    if (!section) window.scrollTo({ top: 0 });
    setDrawer(false);
  }, [page, section]);

  useEffect(() => {
    if (!drawer) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDrawer(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawer]);

  return (
    <div className="app">
      <Sidebar active={page} open={drawer} onNavigate={go} onClose={() => setDrawer(false)} />

      <div className={`main ${page === "office" ? "main-office" : ""}`}>
        <Topbar page={pageLabel(page)} onMenu={() => setDrawer(true)} />

        {needsClassroom && (
          <div className="consent-banner" role="status">
            <span>
              {viewer.classroom.reauth_required
                ? "Izin Google Classroom perlu diperbarui agar tugas & materi Classroom tetap terbaca EduPad."
                : "Izin Google Classroom belum diberikan, jadi tugas & materi Classroom belum bisa dibaca EduPad."}
            </span>
            <a className="btn" href={CONSENT_URL}>
              Beri izin Classroom
            </a>
          </div>
        )}

        <main className={`content ${page === "office" ? "content-office" : ""}`}>
          {page === "office" && (
            <Suspense fallback={<p className="empty-line">Membuka AI Office…</p>}>
              <OfficePage />
            </Suspense>
          )}
          {page === "beranda" && <HomePage />}
          {page === "presensi" && <AttendancePage />}
          {page === "tugas" && <TasksPage />}
          {page === "jadwal" && <SchedulePage />}
          {page === "keuangan" && <FinancePage />}
          {page === "percakapan" && <ConversationsPage />}
          {page === "belajar" && <LearningPage />}
          {page === "tutor" && <TutorPage />}
          {page === "equity" && <EquityPage />}
          {page === "monitoring" && <MonitoringPage section={section} />}
          {page === "pengaturan" && <SettingsPage />}
          {page === "bantuan" && <HelpPage />}
        </main>
      </div>
    </div>
  );
}
