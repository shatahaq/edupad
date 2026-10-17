import { useEffect, useRef, useState } from "react";

// Satu suara pada satu waktu: memutar yang lain menghentikan yang sedang berbunyi.
let current: HTMLAudioElement | null = null;

export function PlayIcon({ playing }: { playing: boolean }) {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" className="shrink-0 fill-current">
      {playing ? <rect x="3" y="3" width="10" height="10" rx="1" /> : <path d="M4 2.5v11l9.5-5.5z" />}
    </svg>
  );
}

type Props = {
  src: string;
  label: string;
  stopLabel: string;
  className: string;
};

/** Tombol putar/hentikan untuk satu file audio (dimuat saat pertama ditekan). */
export function AudioButton({ src, label, stopLabel, className }: Props) {
  const audio = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);

  useEffect(() => () => audio.current?.pause(), []);

  const toggle = () => {
    let a = audio.current;
    if (!a) {
      a = new Audio(src);
      a.addEventListener("play", () => setPlaying(true));
      a.addEventListener("pause", () => setPlaying(false));
      a.addEventListener("ended", () => setPlaying(false));
      audio.current = a;
    }
    if (a.paused) {
      if (current && current !== a) current.pause();
      current = a;
      a.currentTime = 0;
      void a.play();
    } else {
      a.pause();
    }
  };

  return (
    <button type="button" onClick={toggle} aria-pressed={playing} className={className}>
      <PlayIcon playing={playing} />
      {playing ? stopLabel : label}
    </button>
  );
}
