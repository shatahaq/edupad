import type { ReactNode } from "react";
import { REFRESH_SECONDS } from "../api/client";
import { reloadAll, useSummary } from "../api/usePanel";
import { hourLabel } from "../lib/format";
import { Icon } from "./Icon";

/** Header halaman; mode statis dipakai halaman yang datanya berasal dari input pengguna. */
export function PageHeader({
  title,
  subtitle,
  actions,
  live = true,
}: {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  live?: boolean;
}) {
  const { updatedAt, loading } = useSummary();
  return (
    <div className="page-head" id="top">
      <div>
        <h1>{title}</h1>
        <p className="page-sub">
          {subtitle}
          {live && (
            <>
              {subtitle && " · "}diperbarui <span className="mono">{updatedAt ? hourLabel(updatedAt.toISOString()) : "—"}</span> WIB
            </>
          )}
        </p>
      </div>

      <div className="page-actions">
        {live && (
          <span className="live-pill">
            <i aria-hidden />
            Live · refresh {REFRESH_SECONDS} dtk
          </span>
        )}
        {actions}
        {live && (
          <button className="btn btn-dark" onClick={reloadAll}>
            <Icon name="refresh" size={14} className={loading ? "spin" : undefined} />
            Muat ulang semua
          </button>
        )}
      </div>
    </div>
  );
}
