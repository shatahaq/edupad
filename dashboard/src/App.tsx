import { useEffect, useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { Topbar } from "./components/Topbar";
import { NAV_ITEMS, pageLabel, type NavId } from "./lib/nav";
import { go, useRoute, type Page } from "./lib/router";
import { AttendancePage } from "./pages/AttendancePage";
import { ConversationsPage } from "./pages/ConversationsPage";
import { HomePage } from "./pages/HomePage";
import { LearningPage } from "./pages/LearningPage";
import { MonitoringPage } from "./pages/MonitoringPage";
import { SchedulePage } from "./pages/SchedulePage";
import { TasksPage } from "./pages/TasksPage";

export function App() {
  const { page, section } = useRoute();
  const [drawer, setDrawer] = useState(false);

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

        <main className="content">
          {page === "beranda" && <HomePage />}
          {page === "presensi" && <AttendancePage />}
          {page === "tugas" && <TasksPage />}
          {page === "jadwal" && <SchedulePage />}
          {page === "percakapan" && <ConversationsPage />}
          {page === "belajar" && <LearningPage />}
          {page === "monitoring" && <MonitoringPage section={section} />}
        </main>
      </div>
    </div>
  );
}
