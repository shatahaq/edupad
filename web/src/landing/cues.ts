// Bunyi penanda Mode Suara, dibuat ulang di browser dengan nada & durasi yang sama dengan
// firmware (firmware/edupad/voice.cpp & speaker.cpp), supaya pengunjung mendengar yang asli.
import type { CueName } from "./copy";

let context: AudioContext | null = null;

function audio(): AudioContext {
  context ??= new AudioContext();
  if (context.state === "suspended") void context.resume();
  return context;
}

/** Nada sinus dengan naik/turun 5 ms (speaker::tone). */
function tone(ctx: AudioContext, at: number, freq: number, ms: number, amplitude = 0.3): number {
  const end = at + ms / 1000;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.frequency.value = freq;
  gain.gain.setValueAtTime(0, at);
  gain.gain.linearRampToValueAtTime(amplitude * 0.6, at + 0.005);
  gain.gain.setValueAtTime(amplitude * 0.6, end - 0.005);
  gain.gain.linearRampToValueAtTime(0, end);
  osc.connect(gain).connect(ctx.destination);
  osc.start(at);
  osc.stop(end);
  return end;
}

/** "Ding-dong" pemberitahuan: E6 lalu C6 dengan harmoni oktaf yang meluruh (speaker::chime). */
const CHIME = [
  { freq: 1318.5, seconds: 0.32, offset: 0 },
  { freq: 1046.5, seconds: 0.6, offset: 0.32 },
];
const HARMONICS = [
  { multiple: 1, level: 0.27 },
  { multiple: 2, level: 0.08 },
];

function chime(ctx: AudioContext, at: number): void {
  for (const { freq, seconds, offset } of CHIME) {
    const start = at + offset;
    for (const { multiple, level } of HARMONICS) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = freq * multiple;
      gain.gain.setValueAtTime(0, start);
      gain.gain.linearRampToValueAtTime(level, start + 0.0025);
      gain.gain.setTargetAtTime(0, start + 0.0025, 1 / 5.5);
      osc.connect(gain).connect(ctx.destination);
      osc.start(start);
      osc.stop(start + seconds);
    }
  }
}

export function playCue(name: CueName): void {
  const ctx = audio();
  const now = ctx.currentTime + 0.02;
  switch (name) {
    case "listen":
      tone(ctx, tone(ctx, now, 880, 70), 1320, 90);
      break;
    case "sent":
      tone(ctx, tone(ctx, now, 1320, 70), 880, 90);
      break;
    case "thinking": // di perangkat tiap dua detik; di sini dirapatkan supaya terdengar polanya
      for (const offset of [0, 0.7, 1.4]) tone(ctx, now + offset, 660, 40, 0.12);
      break;
    case "error":
      tone(ctx, tone(ctx, now, 392, 130) + 0.04, 262, 200);
      break;
    case "alert":
      chime(ctx, now);
      break;
  }
}
