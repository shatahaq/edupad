export const PREFERENCES_KEY = "edupad-dashboard-preferences-v1";
export const PREFERENCES_UPDATED = "edupad:preferences-updated";

export interface DashboardPreferences {
  studentName: string;
  studentId: string;
  compactMode: boolean;
  reduceMotion: boolean;
}

export const DEFAULT_PREFERENCES: DashboardPreferences = {
  studentName: "Mahasiswa",
  studentId: "",
  compactMode: false,
  reduceMotion: false,
};

export function loadPreferences(): DashboardPreferences {
  try {
    const saved = JSON.parse(localStorage.getItem(PREFERENCES_KEY) ?? "{}") as Partial<DashboardPreferences>;
    return { ...DEFAULT_PREFERENCES, ...saved };
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

export function applyPreferences(preferences: DashboardPreferences) {
  document.documentElement.dataset.compact = String(preferences.compactMode);
  document.documentElement.dataset.reduceMotion = String(preferences.reduceMotion);
}

export function savePreferences(preferences: DashboardPreferences) {
  localStorage.setItem(PREFERENCES_KEY, JSON.stringify(preferences));
  applyPreferences(preferences);
  window.dispatchEvent(new CustomEvent<DashboardPreferences>(PREFERENCES_UPDATED, { detail: preferences }));
}

export function initials(name: string) {
  const letters = name.trim().split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join("");
  return letters || "MH";
}
