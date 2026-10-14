import type { ReactNode } from "react";
import { REFRESH_SECONDS } from "../api/client";
import { reloadAll, useSummary } from "../api/usePanel";
import { hourLabel } from "../lib/format";
import { Icon } from "./Icon";

/** Judul halaman + waktu data terbaru + pill Live + aksi halaman + "Muat ulang semua". */
export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  const { updatedAt, loading } = useSummary();
  return (
    <div className="page-head" id="top">
      <div>
        <h1>{title}</h1>
        <p className="page-sub">
          {subtitle && <>{subtitle} · </>}
          diperbarui <span className="mono">{updatedAt ? hourLabel(updatedAt.toISOString()) : "—"}</span> WIB
        </p>
      </div>

      <div className="page-actions">
        <span className="live-pill">
          <i aria-hidden />
          Live · refresh {REFRESH_SECONDS} dtk
        </span>
        {actions}
        <button className="btn btn-dark" onClick={reloadAll}>
          <Icon name="refresh" size={14} className={loading ? "spin" : undefined} />
          Muat ulang semua
        </button>
      </div>
    </div>
  );
}
