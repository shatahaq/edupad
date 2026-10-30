import type { ReactNode } from "react";
import type { OwlName } from "../lib/owls";
import { PageIntro } from "./PageIntro";

/** Kompatibel dengan halaman lama: judul + pesan singkat, dipandu owl. */
export function PageHeader({
  title,
  subtitle,
  actions,
  owl = "nova",
}: {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  /** Diabaikan: data diperbarui otomatis tanpa indikator. */
  live?: boolean;
  owl?: OwlName;
}) {
  return (
    <PageIntro owl={owl} title={title} actions={actions}>
      {subtitle}
    </PageIntro>
  );
}
