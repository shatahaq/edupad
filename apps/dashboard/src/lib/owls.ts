import { assetUrl } from "../../../ai-office/src/game/assetUrl";

/** Tujuh owl AI Office; tiap halaman dashboard dipandu satu owl dengan warnanya. */
export type OwlName = "nova" | "pixel" | "sora" | "tempo" | "metric" | "koin" | "nexus";

export const OWL_COLOR: Record<OwlName, string> = {
  nova: "var(--nova)",
  pixel: "var(--pixel)",
  sora: "var(--sora)",
  tempo: "var(--tempo)",
  metric: "var(--metric)",
  koin: "var(--koin)",
  nexus: "var(--nexus)",
};

export const owlSrc = (owl: OwlName, mood: "idle" | "happy" = "idle") =>
  assetUrl(`assets/agents/owls/avatar/${owl}-${mood}.png`);
