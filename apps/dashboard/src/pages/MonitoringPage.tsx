import { useEffect } from "react";
import { usePanel } from "../api/usePanel";
import { MonitoringKpis } from "../components/KpiRow";
import { PageIntro } from "../components/PageIntro";
import { ActivityPanel } from "../panels/ActivityPanel";
import { AgentPanel } from "../panels/AgentPanel";
import { ApiPanel } from "../panels/ApiPanel";
import { CostPanel } from "../panels/CostPanel";
import { DevicesPanel } from "../panels/DevicesPanel";
import { ErrorsPanel } from "../panels/ErrorsPanel";
import { KnowledgePanel } from "../panels/KnowledgePanel";
import { ResourcesPanel } from "../panels/ResourcesPanel";
import { ServicesPanel } from "../panels/ServicesPanel";

/** Kesehatan sistem: perangkat, API, agent, biaya, layanan luar. `section` = kartu tujuan. */
export function MonitoringPage({ section }: { section: string | null }) {
  // Scroll ke kartu tujuan lalu tandai sebentar; berguna saat kartu bersebelahan.
  useEffect(() => {
    if (!section) return;
    // Tunggu satu frame agar kartu sudah ter-render saat datang dari halaman lain.
    const id = requestAnimationFrame(() => {
      const el = document.getElementById(section);
      if (!el) return;
      const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      el.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
      el.classList.remove("flash");
      void el.offsetWidth;
      el.classList.add("flash");
    });
    return () => cancelAnimationFrame(id);
  }, [section]);

  const devices = usePanel("devices").data?.devices;
  const online = devices?.filter((d) => d.online).length ?? 0;
  const api = usePanel("api").data;
  const failed = api ? api.by_status.server_error + api.by_status.client_error : 0;

  return (
    <>
      <PageIntro owl="nova" title="Monitoring" mood={devices?.length && online && !failed ? "happy" : "idle"}>
        {!devices ? (
          "Memeriksa perangkat dan server…"
        ) : !devices.length ? (
          "Belum ada perangkat EduPad yang terhubung ke server."
        ) : (
          <>
            {online ? <b>{online} perangkat online</b> : <b>Perangkat offline</b>}
            {api && (
              <>
                {" "}· {api.requests} pertanyaan dalam 24 jam
                {failed ? <>, <b>{failed} gagal</b></> : ", semuanya berhasil"}
              </>
            )}
            .
          </>
        )}
      </PageIntro>

      <MonitoringKpis />

      <div className="row row-2-1">
        <ApiPanel />
        <DevicesPanel />
      </div>

      <div className="row row-3">
        <AgentPanel />
        <CostPanel />
        <ServicesPanel />
      </div>

      <div className="row row-3">
        <KnowledgePanel />
        <ErrorsPanel />
        <ResourcesPanel />
      </div>

      <ActivityPanel />
    </>
  );
}
