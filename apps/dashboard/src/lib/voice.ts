import type { VoiceSpeed } from "../api/types";

/** Label kecepatan bicara Mode Suara (server: src/edupad/voice/mode.py SPEEDS). */
export const SPEED_LABEL: Record<VoiceSpeed, string> = {
  lambat: "Lambat",
  normal: "Normal",
  cepat: "Cepat",
  sangat_cepat: "Sangat cepat",
};
