import { useEffect } from "react";
import { Icon } from "../components/Icon";
import { MonitoringKpis } from "../components/KpiRow";
import { PageHeader } from "../components/PageHeader";
import { fullDate } from "../lib/format";
import { MONITOR_SECTIONS } from "../lib/nav";
import { go } from "../lib/router";
import { ActivityPanel } from "../panels/ActivityPanel";
import { AgentPanel } from "../panels/AgentPanel";
import { ApiPanel } from "../panels/ApiPanel";
import { CostPanel } from "../panels/CostPanel";
import { DevicesPanel } from "../panels/DevicesPanel";
import { ErrorsPanel } from "../panels/ErrorsPanel";
import { KnowledgePanel } from "../panels/KnowledgePanel";
import { ResourcesPanel } from "../panels/ResourcesPanel";
import { ServicesPanel } from "../panels/ServicesPanel";

/** Endpoint saat ini hanya melayani 24 jam terakhir; rentang lain menunggu dukungan server. */
const RANGES = [
  { id: "24h", label: "24 jam", ready: true },
  { id: "7d", label: "7 hari", ready: false },
  { id: "30d", label: "30 hari", ready: false },
];

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

  return (
    <>
      <PageHeader
        title="Monitoring sistem"
        subtitle="perangkat, server & AI agent"
        actions={
          <>
            <div className="segmented" role="group" aria-label="Rentang waktu">
              {RANGES.map((r) => (
                <button key={r.id} aria-pressed={r.id === "24h"} disabled={!r.ready} title={r.ready ? undefined : "Belum didukung endpoint server"}>
                  {r.label}
                </button>
              ))}
            </div>
            <button className="btn" type="button" title="Pemilih tanggal belum tersedia">
              <Icon name="calendar" size={14} />
              <span className="mono">{fullDate(new Date())}</span>
            </button>
          </>
        }
      />

      <nav className="chip-nav" aria-label="Bagian monitoring">
        {MONITOR_SECTIONS.map((s) => (
          <button key={s.id} className={section === s.id ? "active" : undefined} onClick={() => go("monitoring", s.id)}>
            {s.label}
          </button>
        ))}
      </nav>

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
