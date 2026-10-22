import { type CSSProperties, type ReactNode, useEffect, useState } from "react";

import { LOGIN_URL, fetchMe } from "../lib/api";
import { AudioButton, PlayIcon } from "../landing/AudioButton";
import { COPY, type CueName, type Lang, type OwlName, type Phrase } from "../landing/copy";
import { playCue } from "../landing/cues";
import { useLang } from "../landing/useLang";

// Halaman depan edupad.ai.id untuk juri & pengunjung: apa itu EduPad dan cara kerjanya.
// Tanpa data pribadi pemilik; pemilik masuk lewat tombol di pojok kanan atas.

const OWL_COLOR: Record<OwlName, string> = {
  nova: "#30b8e8",
  pixel: "#3f97ea",
  sora: "#efb81a",
  tempo: "#a77ef0",
  metric: "#2fd3a3",
  koin: "#3db368",
  nexus: "#ef5f6f",
};
const TEAM: OwlName[] = ["pixel", "sora", "tempo", "metric", "koin", "nexus"];
const CUES: CueName[] = ["listen", "sent", "thinking", "alert", "error"];
const SECTION = "mx-auto max-w-6xl px-4 sm:px-6";
// Foto perangkat untuk bagian pembuka. Simpan fotonya di web/public/media/, lalu isi alamatnya,
// mis. "/media/edupad-device.webp" (potret 4:5). Selama null, tampil bingkai kosong.
const DEVICE_PHOTO: string | null = null;

const button = {
  dark: "inline-flex h-12 items-center gap-2 rounded-lg bg-slate px-5 text-[15px] font-semibold text-white shadow-hard-dark transition hover:bg-slate-2",
  light:
    "inline-flex h-12 items-center gap-2 rounded-lg border-2 border-edge bg-paper px-5 text-[15px] font-semibold text-ink shadow-hard transition hover:bg-paper-2",
  small:
    "inline-flex h-10 items-center rounded-lg border-2 border-edge bg-paper px-4 text-sm font-semibold text-ink transition hover:bg-paper-2",
  onSlate:
    "inline-flex h-10 shrink-0 items-center gap-2 rounded-lg border-2 border-slate-3 bg-slate-2 px-3.5 text-sm font-semibold text-white transition hover:bg-slate-3",
};

/** Ucapan berbahasa Indonesia; di versi Inggris diberi terjemahan. */
function Said({ phrase, className = "" }: { phrase: Phrase; className?: string }) {
  return (
    <>
      <q lang="id" className={className}>
        {phrase.said}
      </q>
      {phrase.meaning && <span className="mt-1 block text-[15px] text-ink-3">{phrase.meaning}</span>}
    </>
  );
}

function Heading({ eyebrow, title, id, light }: { eyebrow?: string; title: string; id: string; light?: boolean }) {
  return (
    <>
      {eyebrow && <p className={`font-display text-lg ${light ? "text-teal" : "text-teal-ink"}`}>{eyebrow}</p>}
      <h2 id={id} className="mt-2 font-display text-3xl leading-tight sm:text-4xl">
        {title}
      </h2>
    </>
  );
}

function LangSwitch({ lang, setLang, label, dark }: { lang: Lang; setLang: (l: Lang) => void; label: string; dark?: boolean }) {
  return (
    <div role="group" aria-label={label} className={`flex rounded-lg border-2 p-0.5 ${dark ? "border-slate-3" : "border-edge bg-paper"}`}>
      {(["id", "en"] as const).map((code) => (
        <button
          key={code}
          type="button"
          lang={code}
          aria-pressed={lang === code}
          onClick={() => setLang(code)}
          className={`h-8 w-10 rounded-md text-sm font-semibold transition ${
            lang === code ? (dark ? "bg-slate-text text-slate" : "bg-slate text-white") : dark ? "text-slate-text hover:bg-slate-2" : "text-ink-2 hover:bg-paper-2"
          }`}
        >
          {code.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

export default function Landing() {
  const [lang, setLang] = useLang();
  const t = COPY[lang];
  const [signedIn, setSignedIn] = useState(false);
  // Kode `?error=` dari server saat login gagal: dibaca sekali, lalu dihapus dari URL.
  const [errorCode] = useState(() => new URLSearchParams(window.location.search).get("error"));
  const loginError = errorCode ? (t.loginErrors[errorCode] ?? t.loginErrors.google_error) : null;

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has("error")) {
      params.delete("error");
      const rest = params.toString();
      window.history.replaceState(null, "", `/${rest ? `?${rest}` : ""}`);
    }
    // Sudah login: tampilkan jalan ke dashboard, tanpa mengalihkan (halaman ini juga untuk demo).
    const controller = new AbortController();
    fetchMe(controller.signal)
      .then(() => setSignedIn(true))
      .catch(() => {});
    return () => controller.abort();
  }, []);

  const account = signedIn ? (
    <a href="/dashboard/" className={button.small}>
      {t.openDashboard}
    </a>
  ) : (
    <a href={LOGIN_URL} className={button.small}>
      {t.signIn}
    </a>
  );

  return (
    <div className="min-h-dvh text-[17px] leading-relaxed">
      <a href="#isi" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-paper focus:px-4 focus:py-2">
        {t.skip}
      </a>

      <header className="sticky top-0 z-20 border-b-2 border-edge bg-floor">
        <div className={`${SECTION} flex h-16 items-center gap-6`}>
          <a href="#isi" className="flex items-center gap-2">
            <img src="/owls/nova-idle.webp" width={36} height={36} alt="" className="pixelated" />
            <span className="font-display text-2xl font-semibold">EduPad</span>
          </a>
          <nav aria-label={t.nav.label} className="hidden items-center gap-6 text-[15px] font-medium text-ink-2 lg:flex">
            <a href="#cara-kerja" className="hover:text-ink">
              {t.nav.how}
            </a>
            <a href="#fitur" className="hover:text-ink">
              {t.nav.owls}
            </a>
            <a href="#mode-suara" className="hover:text-ink">
              {t.nav.voice}
            </a>
            <a href="#equity-radar" className="hover:text-ink">
              {t.nav.equity}
            </a>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <LangSwitch lang={lang} setLang={setLang} label={t.langLabel} />
            {account}
          </div>
        </div>
      </header>

      {loginError && (
        <p role="alert" className="border-b-2 border-[#e9b8b8] bg-[#fbe4e4] px-4 py-3 text-center text-[15px] text-[#8f1d27]">
          {loginError}
        </p>
      )}

      <main id="isi">
        {/* ------------------------------------------------------------ pembuka */}
        <section aria-labelledby="judul" className={`${SECTION} grid gap-10 pb-20 pt-12 md:grid-cols-[1.2fr_0.8fr] md:items-center md:pt-20`}>
          <div>
            <p className="font-display text-lg text-teal-ink">{t.hero.eyebrow}</p>
            <h1 id="judul" className="mt-3 font-display text-[2.6rem] leading-[1.05] sm:text-6xl">
              {t.hero.title}
            </h1>
            <p className="mt-6 max-w-xl text-lg text-ink-2">{t.hero.lead}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <AudioButton src="/media/edupad-intro.mp3" label={t.hero.listen} stopLabel={t.hero.stop} className={button.dark} />
              <a href="#cara-kerja" className={button.light}>
                {t.hero.how}
              </a>
            </div>
          </div>
          <DevicePhoto alt={t.hero.photoAlt} pending={t.hero.photoPending} note={t.hero.photoPendingNote} />
        </section>

        {/* ------------------------------------------------- SDG: kenapa penting */}
        <section aria-labelledby="sdg-judul" className="border-t-2 border-edge py-20">
          <div className={SECTION}>
            <div className="max-w-3xl">
              <Heading id="sdg-judul" eyebrow={t.sdg.eyebrow} title={t.sdg.title} />
              <p className="mt-4 text-lg text-ink-2">{t.sdg.lead}</p>
            </div>
            <div className="mt-10 grid gap-5 lg:grid-cols-2">
              <ChartCard data={t.sdg.enrolment}>
                <EnrolmentBars before={t.sdg.enrolment.before} after={t.sdg.enrolment.after} growth={t.sdg.enrolment.growth} label={t.sdg.enrolment.chart} />
              </ChartCard>
              <ChartCard data={t.sdg.graduation}>
                <GraduationLine from={t.sdg.graduation.from} to={t.sdg.graduation.to} label={t.sdg.graduation.chart} />
              </ChartCard>
            </div>

            <h3 className="mt-14 font-display text-2xl">{t.sdg.disabilityTitle}</h3>
            <p className="mt-1 text-[15px] text-ink-3">{t.sdg.disabilityNote}</p>
            <ul className="mt-5 grid gap-5 md:grid-cols-2">
              {t.sdg.stats.map((stat) => (
                <li key={stat.value} className="flex flex-col rounded-xl border-2 border-edge bg-paper p-5 shadow-hard">
                  {/* Angka statistik memakai huruf biasa: "5" di Pixelify Sans mirip "S"/"8". */}
                  <p className="text-4xl font-extrabold tracking-tight text-owl-nexus">{stat.value}</p>
                  <p className="mt-3 text-[16px] text-ink-2">{stat.body}</p>
                  <Source href={stat.url}>{stat.source}</Source>
                </li>
              ))}
            </ul>

            <h3 className="mt-14 font-display text-2xl">{t.sdg.fitTitle}</h3>
            <div className="mt-5 grid gap-5 md:grid-cols-2">
              {t.sdg.items.map((item) => (
                <div key={item.code} className="rounded-xl border-2 border-edge bg-paper p-5">
                  <p className="font-display text-2xl text-teal-ink">{item.code}</p>
                  <h4 className="mt-1 text-lg font-bold">{item.title}</h4>
                  <p className="mt-1 text-ink-2">{item.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------- cara kerja */}
        <section id="cara-kerja" aria-labelledby="cara-kerja-judul" className="scroll-mt-16 border-y-2 border-edge bg-paper py-20">
          <div className={SECTION}>
            <Heading id="cara-kerja-judul" title={t.how.title} />
            <ol className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
              {t.how.steps.map((step, index) => (
                <li key={step.title}>
                  <span aria-hidden="true" className="font-display text-4xl text-teal-ink">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <h3 className="mt-2 text-lg font-bold">{step.title}</h3>
                  <p className="mt-1 text-ink-2">{step.body}</p>
                </li>
              ))}
            </ol>

            <div className="mt-14 rounded-xl border-2 border-edge bg-floor p-5 sm:p-8">
              <p className="font-display text-lg">{t.how.exampleLabel}</p>
              <div className="mt-5 grid gap-6 lg:grid-cols-[1fr_auto]">
                <div className="space-y-5">
                  <div>
                    <p className="text-sm font-semibold text-ink-3">{t.how.you}</p>
                    <p className="mt-1 text-lg font-semibold">
                      <Said phrase={t.how.question} />
                    </p>
                  </div>
                  <div className="flex gap-3">
                    <img src="/owls/nova-idle.webp" width={44} height={44} alt="" className="pixelated h-11 w-11 shrink-0" />
                    <div>
                      <p className="text-sm font-semibold text-ink-3">{t.how.answerLabel}</p>
                      <p className="mt-1">
                        <Said phrase={t.how.answer} />
                      </p>
                    </div>
                  </div>
                </div>
                <div>
                  <p className="text-sm font-semibold text-ink-3">{t.how.screenLabel}</p>
                  <div lang="id" className="mt-1 w-full rounded-lg border-4 border-slate-2 bg-slate p-4 font-mono text-[13px] leading-6 text-slate-text sm:w-72">
                    <p className="font-display text-xl text-teal">{t.how.screen.title}</p>
                    {t.how.screen.lines.map((line) => (
                      <p key={line} className="whitespace-pre">
                        {line}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
              <p className="mt-6 text-sm text-ink-3">{t.how.exampleNote}</p>
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- owl */}
        <section id="fitur" aria-labelledby="fitur-judul" className={`${SECTION} scroll-mt-16 py-20`}>
          <div className="flex items-start gap-4">
            <img src="/owls/nova-idle.webp" width={64} height={64} alt="" className="pixelated hidden h-16 w-16 sm:block" />
            <div>
              <Heading id="fitur-judul" title={t.owls.title} />
              <p className="mt-3 max-w-2xl text-ink-2">
                <b className="font-display font-semibold text-ink">NOVA</b> · {t.owls.list.nova.role}: {t.owls.list.nova.body} {t.owls.lead}
              </p>
            </div>
          </div>
          <ul className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {TEAM.map((owl) => {
              const item = t.owls.list[owl];
              return (
                <li
                  key={owl}
                  style={{ "--owl": OWL_COLOR[owl] } as CSSProperties}
                  className="flex flex-col rounded-xl border-2 border-t-[6px] border-edge border-t-[var(--owl)] bg-paper p-5 shadow-hard"
                >
                  <div className="flex items-center gap-3">
                    <img src={`/owls/${owl}-idle.webp`} width={56} height={56} alt="" className="pixelated h-14 w-14" />
                    <div>
                      <h3 className="font-display text-xl font-semibold">{owl.toUpperCase()}</h3>
                      <p className="text-[15px] font-semibold text-ink-3">{item.role}</p>
                    </div>
                  </div>
                  <p className="mt-3 text-ink-2">{item.body}</p>
                  {item.say && (
                    <p className="mt-auto pt-4 text-[16px]">
                      <span className="block text-sm font-semibold text-ink-3">{t.owls.say}</span>
                      <Said phrase={item.say} className="font-semibold" />
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </section>

        {/* --------------------------------------------------------- Mode Suara */}
        <section id="mode-suara" aria-labelledby="mode-suara-judul" className="scroll-mt-16 bg-slate py-20 text-slate-text">
          <div className={`${SECTION} grid gap-12 lg:grid-cols-2`}>
            <div>
              <Heading id="mode-suara-judul" eyebrow={t.voice.eyebrow} title={t.voice.title} light />
              <p className="mt-4 text-lg text-slate-muted">{t.voice.lead}</p>
              <p className="mt-8 font-display text-2xl text-white">
                <q lang="id">{t.voice.turnOn.said}</q>
              </p>
              {t.voice.turnOn.meaning && <p className="mt-1 text-slate-muted">{t.voice.turnOn.meaning}</p>}
              <ul className="mt-8 space-y-3 text-slate-muted">
                {t.voice.more.map((line) => (
                  <li key={line} className="border-l-4 border-slate-3 pl-4">
                    {line}
                  </li>
                ))}
              </ul>
            </div>
            <div className="space-y-6">
              <div className="rounded-xl border-2 border-slate-3 bg-slate-2 p-5 sm:p-6">
                <h3 className="font-display text-xl text-white">{t.voice.cuesTitle}</h3>
                <ul className="mt-4 divide-y-2 divide-slate-3">
                  {CUES.map((cue) => (
                    <li key={cue} className="flex items-center gap-4 py-3">
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold text-white">{t.voice.cues[cue].label}</p>
                        <p className="text-[15px] text-slate-muted">{t.voice.cues[cue].body}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => playCue(cue)}
                        aria-label={`${t.voice.listenLabel}: ${t.voice.cues[cue].label}`}
                        className={button.onSlate}
                      >
                        <PlayIcon playing={false} />
                        {t.voice.listenLabel}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-xl border-2 border-slate-3 bg-slate-2 p-5 sm:p-6">
                <h3 className="font-display text-xl text-white">{t.voice.offlineTitle}</h3>
                <p className="mt-2 text-[15px] text-slate-muted">{t.voice.offlineBody}</p>
                <div className="mt-4 flex items-start gap-4">
                  <AudioButton src="/media/mode-suara-wifi.mp3" label={t.voice.listenLabel} stopLabel={t.hero.stop} className={button.onSlate} />
                  <p className="text-white">
                    <q lang="id">{t.voice.offlineClip.said}</q>
                    {t.voice.offlineClip.meaning && <span className="mt-1 block text-[15px] text-slate-muted">{t.voice.offlineClip.meaning}</span>}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------- Equity Radar */}
        <section id="equity-radar" aria-labelledby="equity-judul" className={`${SECTION} scroll-mt-16 grid gap-12 py-20 lg:grid-cols-2`}>
          <div>
            <Heading id="equity-judul" eyebrow={t.equity.eyebrow} title={t.equity.title} />
            <p className="mt-4 text-lg text-ink-2">{t.equity.lead}</p>
            <dl className="mt-8 space-y-6">
              {t.equity.points.map((point) => (
                <div key={point.title} className="border-l-4 border-owl-nexus pl-4">
                  <dt className="text-lg font-bold">{point.title}</dt>
                  <dd className="mt-1 text-ink-2">{point.body}</dd>
                </div>
              ))}
            </dl>
          </div>
          <figure className="self-start rounded-xl border-2 border-edge bg-paper p-6 shadow-hard">
            <figcaption className="flex items-center gap-3">
              <img src="/owls/nexus-idle.webp" width={44} height={44} alt="" className="pixelated h-11 w-11" />
              <span className="font-display text-lg">{t.equity.messageLabel}</span>
            </figcaption>
            <blockquote lang="id" className="mt-4 rounded-lg bg-floor p-4 text-[16px] text-ink-2">
              {t.equity.message}
            </blockquote>
            <p className="mt-3 text-sm text-ink-3">{t.equity.messageNote}</p>
          </figure>
        </section>

        {/* ---------------------------------------------------------- dashboard */}
        <section aria-labelledby="office-judul" className="border-y-2 border-edge bg-paper py-20">
          <div className={SECTION}>
            <div className="max-w-2xl">
              <Heading id="office-judul" eyebrow={t.office.eyebrow} title={t.office.title} />
              <p className="mt-4 text-lg text-ink-2">{t.office.lead}</p>
            </div>
            <figure className="mt-10">
              <img
                src="/media/ai-office.webp"
                width={1104}
                height={878}
                loading="lazy"
                decoding="async"
                alt={t.office.alt}
                className="w-full rounded-xl border-4 border-slate shadow-hard-dark"
              />
              <figcaption className="mt-3 text-sm text-ink-3">{t.office.caption}</figcaption>
            </figure>
          </div>
        </section>

        {/* ------------------------------------------------------- di balik layar */}
        <section aria-labelledby="behind-judul" className={`${SECTION} py-20`}>
          <Heading id="behind-judul" title={t.behind.title} />
          <p className="mt-3 max-w-2xl text-lg text-ink-2">{t.behind.lead}</p>
          <ol className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {t.behind.parts.map((part, index) => (
              <li key={index} className="relative rounded-xl border-2 border-edge bg-paper shadow-hard">
                <div className="relative m-2 aspect-[3/2] overflow-hidden rounded-lg" aria-hidden="true">
                  <img
                    src="/media/behind-the-scenes.webp"
                    alt=""
                    width={1536}
                    height={1024}
                    loading="lazy"
                    decoding="async"
                    className="absolute h-[200%] w-[200%] max-w-none"
                    style={{ left: index % 2 === 0 ? "0" : "-100%", top: index < 2 ? "0" : "-100%" }}
                  />
                </div>
                <div className="px-5 pb-6 pt-2">
                  <div className="flex items-center gap-2.5">
                    <span aria-hidden="true" className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-slate font-display text-sm text-white">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <h3 className="font-display text-xl">{part.title}</h3>
                  </div>
                  <p className="mt-3 text-[15px] leading-relaxed text-ink-2">{part.summary}</p>
                </div>
                {index < t.behind.parts.length - 1 && (
                  <span aria-hidden="true" className="absolute -right-5 top-1/3 z-10 hidden h-8 w-8 items-center justify-center rounded-full border-2 border-edge bg-paper font-display text-xl text-teal-ink lg:flex">
                    →
                  </span>
                )}
              </li>
            ))}
          </ol>
          <details className="mt-6 rounded-xl border-2 border-edge bg-paper px-5 py-4">
            <summary className="cursor-pointer font-semibold text-teal-ink">{t.behind.details}</summary>
            <div className="mt-5 grid gap-6 pb-2 sm:grid-cols-2 lg:grid-cols-4">
              {t.behind.parts.map((part) => (
                <div key={part.title}>
                  <h3 className="font-display text-xl">{part.title}</h3>
                  <p className="mt-2 text-[15px] leading-relaxed text-ink-2">{part.body}</p>
                </div>
              ))}
            </div>
          </details>
          <div className="mt-12 grid gap-10 md:grid-cols-2">
            <List title={t.behind.privacyTitle} items={t.behind.privacy} />
            <List title={t.behind.limitsTitle} items={t.behind.limits} />
          </div>
        </section>

      </main>

      <footer className="bg-slate py-10 text-slate-text">
        <div className={`${SECTION} flex flex-wrap items-center gap-4`}>
          <img src="/owls/nova-idle.webp" width={40} height={40} alt="" className="pixelated" />
          <p>
            <span className="font-display text-xl text-white">EduPad</span>
            <span className="ml-2 text-slate-muted">{t.footer.tagline}</span>
          </p>
          <div className="ml-auto flex items-center gap-2">
            <LangSwitch lang={lang} setLang={setLang} label={t.langLabel} dark />
            <a href={signedIn ? "/dashboard/" : LOGIN_URL} className={button.onSlate}>
              {signedIn ? t.openDashboard : t.signIn}
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function List({ title, items }: { title: string; items: string[] }): ReactNode {
  return (
    <div>
      <h3 className="font-display text-2xl">{title}</h3>
      <ul className="mt-4 space-y-3">
        {items.map((item) => (
          <li key={item} className="flex gap-3 text-ink-2">
            <span aria-hidden="true" className="mt-2.5 h-2 w-2 shrink-0 bg-teal-ink" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Source({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="mt-auto pt-4 text-sm font-semibold text-ink-3 underline decoration-edge underline-offset-4 hover:text-ink"
    >
      {children}
    </a>
  );
}

type ChartData = { value: string; label: string; note: string; source: string; url: string };

/** Statistik utama + grafiknya; angka memakai huruf biasa agar tidak salah baca. */
function ChartCard({ data, children }: { data: ChartData; children: ReactNode }) {
  return (
    <figure className="flex flex-col rounded-xl border-2 border-edge bg-paper p-5 shadow-hard sm:p-6">
      <p className="text-5xl font-extrabold tracking-tight text-teal-ink">{data.value}</p>
      <p className="mt-1 text-lg font-semibold">{data.label}</p>
      <div className="mt-5 max-w-md">{children}</div>
      <figcaption className="mt-4 text-[16px] text-ink-2">{data.note}</figcaption>
      <Source href={data.url}>{data.source}</Source>
    </figure>
  );
}

const INK = "#1e2731";
const TEAL = "#1d727a";
const GREEN = "#2f8f5b";
const AXIS = "#ddd1bd";

/** Dua batang: dua dekade lalu (kurang dari separuh) vs 2024. Sumber hanya menyebut "lebih dari
 *  dua kali lipat", jadi batang kiri tidak diberi angka. */
function EnrolmentBars({ before, after, growth, label }: { before: string; after: string; growth: string; label: string }) {
  return (
    <svg viewBox="0 0 320 170" role="img" aria-label={label} className="h-auto w-full" shapeRendering="crispEdges">
      <line x1="20" y1="140" x2="300" y2="140" stroke={AXIS} strokeWidth="3" />
      <rect x="70" y="86" width="56" height="54" fill={INK} opacity="0.35" />
      <rect x="194" y="20" width="56" height="120" fill={TEAL} />
      <rect x="254" y="4" width="56" height="26" rx="3" fill={GREEN} />
      <text x="282" y="22" textAnchor="middle" fontSize="15" fontWeight="800" fill="#fff">
        {growth}
      </text>
      <text x="98" y="162" textAnchor="middle" fontSize="13" fontWeight="600" fill="#5f6b78">
        {before}
      </text>
      <text x="222" y="162" textAnchor="middle" fontSize="13" fontWeight="700" fill={INK}>
        {after}
      </text>
    </svg>
  );
}

/** Rasio kelulusan 22% (2013) -> 27% (2024) pada skala 0-40%. Hanya dua titik ini yang ada di
 *  sumber; garis putus-putus menandai tidak ada data tahunan di antaranya. */
function GraduationLine({ from, to, label }: { from: string; to: string; label: string }) {
  const y = (percent: number) => 140 - (percent / 40) * 120;
  return (
    <svg viewBox="0 0 320 170" role="img" aria-label={label} className="h-auto w-full" shapeRendering="crispEdges">
      <line x1="44" y1="20" x2="44" y2="140" stroke={AXIS} strokeWidth="3" />
      <line x1="44" y1="140" x2="304" y2="140" stroke={AXIS} strokeWidth="3" />
      <text x="36" y="25" textAnchor="end" fontSize="12" fill="#5f6b78">
        40%
      </text>
      <text x="36" y="144" textAnchor="end" fontSize="12" fill="#5f6b78">
        0%
      </text>
      <line x1="66" y1={y(22)} x2="282" y2={y(27)} stroke={INK} strokeWidth="4" strokeDasharray="10 7" />
      <rect x="58" y={y(22) - 8} width="16" height="16" fill={INK} />
      <rect x="274" y={y(27) - 8} width="16" height="16" fill={GREEN} />
      <text x="66" y={y(22) - 16} textAnchor="middle" fontSize="18" fontWeight="800" fill={INK}>
        22%
      </text>
      <text x="282" y={y(27) - 16} textAnchor="middle" fontSize="18" fontWeight="800" fill={GREEN}>
        27%
      </text>
      <text x="66" y="162" textAnchor="middle" fontSize="13" fontWeight="600" fill="#5f6b78">
        {from}
      </text>
      <text x="282" y="162" textAnchor="middle" fontSize="13" fontWeight="700" fill={INK}>
        {to}
      </text>
    </svg>
  );
}

/** Foto perangkat di pembuka; bingkai kosong yang jujur selama perangkat belum selesai dirakit. */
function DevicePhoto({ alt, pending, note }: { alt: string; pending: string; note: string }) {
  const frame = "aspect-[4/3] w-full rounded-xl md:aspect-[4/5]";
  if (DEVICE_PHOTO) {
    return <img src={DEVICE_PHOTO} alt={alt} className={`${frame} border-2 border-edge object-cover shadow-hard`} />;
  }
  return (
    <div className={`${frame} flex flex-col items-center justify-center gap-1 border-2 border-dashed border-edge bg-paper-2 p-6 text-center`}>
      <p className="font-semibold text-ink-2">{pending}</p>
      <p className="text-[15px] text-ink-3">{note}</p>
    </div>
  );
}
