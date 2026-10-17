import { useCallback, useSyncExternalStore } from "react";
import { fetchPanel, REFRESH_SECONDS } from "./client";
import type { DashboardData, PanelKey } from "./types";

export interface PanelSnapshot<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  updatedAt: Date | null;
}

export interface PanelState<T> extends PanelSnapshot<T> {
  reload: () => void;
}

/**
 * Store bersama per panel: komponen yang memakai panel yang sama (kartu panel, KPI, badge
 * sidebar) berbagi satu fetch dan satu timer refresh. Data terakhir tetap ditampilkan saat
 * refresh gagal, sehingga satu endpoint yang error tidak mengosongkan panel atau panel lain.
 */
interface Entry {
  snap: PanelSnapshot<unknown>;
  listeners: Set<() => void>;
  timer?: number;
  ctrl?: AbortController;
}

const entries = new Map<PanelKey, Entry>();

function entry(panel: PanelKey): Entry {
  let e = entries.get(panel);
  if (!e) {
    e = { snap: { data: null, error: null, loading: true, updatedAt: null }, listeners: new Set() };
    entries.set(panel, e);
  }
  return e;
}

function update(panel: PanelKey, patch: Partial<PanelSnapshot<unknown>>) {
  const e = entry(panel);
  e.snap = { ...e.snap, ...patch };
  e.listeners.forEach((l) => l());
}

function load(panel: PanelKey) {
  const e = entry(panel);
  e.ctrl?.abort();
  const ctrl = new AbortController();
  e.ctrl = ctrl;
  update(panel, { loading: true });
  fetchPanel(panel, ctrl.signal)
    .then((data) => {
      if (!ctrl.signal.aborted) update(panel, { data, error: null, loading: false, updatedAt: new Date() });
    })
    .catch((err: unknown) => {
      if (!ctrl.signal.aborted) update(panel, { error: err instanceof Error ? err.message : String(err), loading: false });
    });
}

function subscribe(panel: PanelKey, listener: () => void) {
  const e = entry(panel);
  e.listeners.add(listener);
  if (e.listeners.size === 1) {
    load(panel);
    e.timer = window.setInterval(() => load(panel), REFRESH_SECONDS * 1000);
  }
  return () => {
    e.listeners.delete(listener);
    if (!e.listeners.size) {
      window.clearInterval(e.timer);
      e.ctrl?.abort();
    }
  };
}

/** Ambil satu panel dan refresh berkala (dibagi dengan pemakai lain panel yang sama). */
export function usePanel<K extends PanelKey>(panel: K): PanelState<DashboardData[K]> {
  const sub = useCallback((l: () => void) => subscribe(panel, l), [panel]);
  const snap = useSyncExternalStore(sub, () => entry(panel).snap) as PanelSnapshot<DashboardData[K]>;
  const reload = useCallback(() => load(panel), [panel]);
  return { ...snap, reload };
}
