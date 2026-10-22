import { useEffect, useState } from "react";

import { Sidebar } from "../../dashboard/src/components/Sidebar";
import { Topbar } from "../../dashboard/src/components/Topbar";
import { pageLabel } from "../../dashboard/src/lib/nav";
import { go, useRoute } from "../../dashboard/src/lib/router";
import { applyPreferences, loadPreferences } from "../../dashboard/src/lib/preferences";
import { CONSENT_URL, useViewer } from "../../dashboard/src/lib/session";
import { AttendancePage } from "../../dashboard/src/pages/AttendancePage";
import { ConversationsPage } from "../../dashboard/src/pages/ConversationsPage";
import { EquityPage } from "../../dashboard/src/pages/EquityPage";
import { FinancePage } from "../../dashboard/src/pages/FinancePage";
import { HelpPage } from "../../dashboard/src/pages/HelpPage";
import { HomePage } from "../../dashboard/src/pages/HomePage";
import { LearningPage } from "../../dashboard/src/pages/LearningPage";
import { MonitoringPage } from "../../dashboard/src/pages/MonitoringPage";
import { SchedulePage } from "../../dashboard/src/pages/SchedulePage";
import { SettingsPage } from "../../dashboard/src/pages/SettingsPage";
import { TasksPage } from "../../dashboard/src/pages/TasksPage";
import { TutorPage } from "../../dashboard/src/pages/TutorPage";
import { NeoOffice } from "./office/NeoOffice";

// Salinan kerangka dashboard versi pertama dengan satu perbedaan: halaman AI Office memakai
// denah neo-brutalism (NeoOffice) dan bukan kantor Phaser. Halaman lain diambil apa adanya
// dari dashboard/src, jadi isinya tidak pernah berbeda antara dua versi.
export function App() {
  const { page, section } = useRoute();
  const [drawer, setDrawer] = useState(false);
  const viewer = useViewer();
  const needsClassroom = viewer && (!viewer.classroom.granted || viewer.classroom.reauth_required);

  useEffect(() => {
    applyPreferences(loadPreferences());
  }, []);

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
    // Isi di belakang menu tidak ikut tergulir selama menu terbuka.
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [drawer]);

  return (
    <div className="app">
      <Sidebar active={page} open={drawer} onNavigate={go} onClose={() => setDrawer(false)} />

      <div className="main">
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

        <main className="content">
          {page === "office" && <NeoOffice />}
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
