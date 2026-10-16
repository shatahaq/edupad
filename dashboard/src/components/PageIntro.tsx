import type { CSSProperties, ReactNode } from "react";
import { OWL_COLOR, owlSrc, type OwlName } from "../lib/owls";

interface Props {
  owl: OwlName;
  title: string;
  /** Satu pesan utama halaman, dibacakan owl di balon bicara. */
  children?: ReactNode;
  /** Contoh ucapan ke perangkat EduPad untuk menindaklanjuti pesan. */
  say?: string;
  mood?: "idle" | "happy";
  actions?: ReactNode;
}

/** Pembuka halaman: owl pemandu + judul + satu pesan utama. */
export function PageIntro({ owl, title, children, say, mood = "idle", actions }: Props) {
  return (
    <header className="intro" style={{ "--owl": OWL_COLOR[owl] } as CSSProperties}>
      <div className="intro-owl" aria-hidden>
        <img src={owlSrc(owl, mood)} alt="" width={76} height={76} />
      </div>
      <div className="intro-body">
        <h1>{title}</h1>
        {children && <div className="say">{children}</div>}
        {say && (
          <p className="say-hint">
            Ucapkan ke EduPad: <q>{say}</q>
          </p>
        )}
      </div>
      {actions && <div className="intro-actions">{actions}</div>}
    </header>
  );
}
