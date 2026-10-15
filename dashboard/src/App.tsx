import { useEffect, useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { Topbar } from "./components/Topbar";
import { NAV_ITEMS, pageLabel, type NavId } from "./lib/nav";
import { go, useRoute, type Page } from "./lib/router";
import { applyPreferences, loadPreferences } from "./lib/preferences";
import { AttendancePage } from "./pages/AttendancePage";
import { ConversationsPage } from "./pages/ConversationsPage";
import { FinancePage } from "./pages/FinancePage";
import { HelpPage } from "./pages/HelpPage";
import { HomePage } from "./pages/HomePage";
import { LearningPage } from "./pages/LearningPage";
import { MonitoringPage } from "./pages/MonitoringPage";
import { OfficePage } from "./pages/OfficePage";
import { SchedulePage } from "./pages/SchedulePage";
import { SettingsPage } from "./pages/SettingsPage";
import { TasksPage } from "./pages/TasksPage";

export function App() {
  const { page, section } = useRoute();
  const [drawer, setDrawer] = useState(false);

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

  const navigate = (id: NavId) => {
    if (NAV_ITEMS.find((i) => i.id === id)?.target === false) return;
    go(id as Page);
  };

  return (
    <div className="app">
      <Sidebar active={page} open={drawer} onNavigate={navigate} onClose={() => setDrawer(false)} />

      <div className="main">
        <Topbar page={pageLabel(page)} onMenu={() => setDrawer(true)} />

        <main className={`content ${page === "office" ? "content-office" : ""}`}>
          {page === "office" && <OfficePage />}
          {page === "beranda" && <HomePage />}
          {page === "presensi" && <AttendancePage />}
          {page === "tugas" && <TasksPage />}
          {page === "jadwal" && <SchedulePage />}
          {page === "keuangan" && <FinancePage />}
          {page === "percakapan" && <ConversationsPage />}
          {page === "belajar" && <LearningPage />}
          {page === "monitoring" && <MonitoringPage section={section} />}
          {page === "pengaturan" && <SettingsPage />}
          {page === "bantuan" && <HelpPage />}
        </main>
      </div>
    </div>
  );
}
