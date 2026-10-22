import { type CSSProperties, type ReactNode, useEffect, useState } from "react";

import { AudioButton, PlayIcon } from "../../../web/src/landing/AudioButton";
import { COPY, type CueName, type Lang, type OwlName, type Phrase } from "../../../web/src/landing/copy";
import { playCue } from "../../../web/src/landing/cues";
import { useLang } from "../../../web/src/landing/useLang";
import { LOGIN_URL, fetchMe } from "../../../web/src/lib/api";
import { Eyebrow, EnrolmentBars, GraduationLine, LangSwitch, Marquee, SHELL, SectionTitle, Source, StatCard } from "../components/neo";

// Halaman depan edupad.ai.id versi kedua (tema neo-brutalism). Isi teksnya sama persis dengan
// versi pertama di web/ — yang berbeda hanya rupa dan susunannya.

const OWL_COLOR: Record<OwlName, string> = {
  nova: "#30B8E8",
  pixel: "#3F97EA",
  sora: "#EFB81A",
  tempo: "#A77EF0",
  metric: "#2FD3A3",
  koin: "#3DB368",
  nexus: "#EF5F6F",
};
const TEAM: OwlName[] = ["pixel", "sora", "tempo", "metric", "koin", "nexus"];
const CUES: CueName[] = ["listen", "sent", "thinking", "alert", "error"];

// Aset yang digambar untuk versi ini (web-neo/art-src -> public/art). Selama null, tempatnya
// tetap ada sebagai bingkai kosong yang jujur — bukan gambar contoh yang tidak nyambung.
const DEVICE_ART: string | null = "/art/device.png";
const OFFICE_ART: string | null = "/art/office-neo.png";
const BEHIND_ART: string | null = "/art/behind-";

/** Teks yang tidak ada di copy.ts: keterangan gambar khusus versi ini. */
const LOCAL: Record<Lang, { office: string; deviceAlt: string }> = {
  id: {
    office: "Tangkapan layar dashboard versi ini menyusul.",
    deviceAlt: "Ilustrasi perangkat EduPad di meja belajar: layar kecil, satu tombol besar, dan lubang speaker.",
  },
  en: {
    office: "A screenshot of this version's dashboard is coming.",
    deviceAlt: "Illustration of the EduPad device on a desk: a small screen, one big button, and speaker holes.",
  },
};

const BTN = {
  primary: "neo-btn bg-pop-yellow text-ink",
  plain: "neo-btn bg-paper text-ink",
  onDark: "neo-btn border-paper bg-paper text-ink shadow-neo-light-sm hover:shadow-neo-light",
  small:
    "inline-flex h-10 items-center border-3 border-ink bg-pop-yellow px-3 font-display text-xs uppercase tracking-wide shadow-neo-sm transition-[transform,box-shadow] duration-100 hover:-translate-x-[2px] hover:-translate-y-[2px] hover:shadow-neo active:translate-x-[2px] active:translate-y-[2px] active:shadow-neo-press",
};

/** Ucapan berbahasa Indonesia; di versi Inggris diberi terjemahan di bawahnya. */
function Said({ phrase, className = "", muted = "text-ink-2" }: { phrase: Phrase; className?: string; muted?: string }) {
  return (
    <>
      <q lang="id" className={className}>
        {phrase.said}
      </q>
      {phrase.meaning && <span className={`mt-1 block text-[15px] ${muted}`}>{phrase.meaning}</span>}
    </>
  );
}

export default function Landing() {
  const [lang, setLang] = useLang();
  const t = COPY[lang];
  const [signedIn, setSignedIn] = useState(false);
  const [errorCode] = useState(() => new URLSearchParams(window.location.search).get("error"));
  const loginError = errorCode ? (t.loginErrors[errorCode] ?? t.loginErrors.google_error) : null;

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has("error")) {
      params.delete("error");
      const rest = params.toString();
      window.history.replaceState(null, "", `/${rest ? `?${rest}` : ""}`);
    }
    const controller = new AbortController();
    fetchMe(controller.signal)
      .then(() => setSignedIn(true))
      .catch(() => {});
    return () => controller.abort();
  }, []);

  const account = (
    <a href={signedIn ? "/dashboard/" : LOGIN_URL} className={BTN.small}>
      {signedIn ? t.openDashboard : t.signIn}
    </a>
  );

  return (
    <div className="min-h-dvh text-[17px] leading-relaxed">
      <a href="#isi" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:border-3 focus:border-ink focus:bg-pop-yellow focus:px-4 focus:py-2">
        {t.skip}
      </a>

      <header className="sticky top-0 z-30 border-b-3 border-ink bg-paper">
        <div className={`${SHELL} flex h-16 items-center gap-5`}>
          <a href="#isi" className="flex items-center gap-2.5">
            {/* Tanda huruf, bukan owl kecil: pada 36 px gambar owl kehilangan detailnya. */}
            <span aria-hidden="true" className="grid h-9 w-9 place-items-center border-3 border-ink bg-pop-yellow font-display text-lg leading-none">
              E
            </span>
            <span className="font-display text-xl">EduPad</span>
          </a>
          <nav aria-label={t.nav.label} className="hidden items-center gap-5 font-display text-xs uppercase tracking-wide lg:flex">
            <a href="#cara-kerja" className="border-b-3 border-transparent py-1 hover:border-ink">
              {t.nav.how}
            </a>
            <a href="#fitur" className="border-b-3 border-transparent py-1 hover:border-ink">
              {t.nav.owls}
            </a>
            <a href="#mode-suara" className="border-b-3 border-transparent py-1 hover:border-ink">
              {t.nav.voice}
            </a>
            <a href="#equity-radar" className="border-b-3 border-transparent py-1 hover:border-ink">
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
        <p role="alert" className="border-b-3 border-ink bg-pop-red px-4 py-3 text-center font-semibold text-ink">
          {loginError}
        </p>
      )}

      <main id="isi">
        {/* ------------------------------------------------------------ pembuka */}
        <section aria-labelledby="judul" className="border-b-3 border-ink bg-bone">
          <div className={`${SHELL} grid items-center gap-10 py-14 md:grid-cols-[1.15fr_0.85fr] md:py-20`}>
            <div>
              <Eyebrow>{t.hero.eyebrow}</Eyebrow>
              <h1 id="judul" className="mt-5 font-display text-[clamp(2.5rem,6.2vw,4.5rem)] leading-[0.98]">
                {t.hero.title}
              </h1>
              <p className="mt-6 max-w-xl text-lg text-ink-2">{t.hero.lead}</p>
              <div className="mt-8 flex flex-wrap gap-3">
                <AudioButton src="/media/edupad-intro.mp3" label={t.hero.listen} stopLabel={t.hero.stop} className={BTN.primary} />
                <a href="#cara-kerja" className={BTN.plain}>
                  {t.hero.how}
                </a>
              </div>
            </div>
            <DeviceFrame alt={LOCAL[lang].deviceAlt} pending={t.hero.photoPending} note={t.hero.photoPendingNote} />
          </div>
        </section>

        <Marquee items={t.how.steps.map((step) => step.title)} />

        {/* ------------------------------------------------- SDG: kenapa penting */}
        <section aria-labelledby="sdg-judul" className="border-b-3 border-ink py-16 sm:py-20">
          <div className={SHELL}>
            <div className="max-w-3xl">
              <Eyebrow>{t.sdg.eyebrow}</Eyebrow>
              <SectionTitle id="sdg-judul" className="mt-5">
                {t.sdg.title}
              </SectionTitle>
              <p className="mt-4 text-lg text-ink-2">{t.sdg.lead}</p>
            </div>

            <div className="mt-10 grid gap-6 lg:grid-cols-2">
              <StatCard data={t.sdg.enrolment} accent="#35C8F3">
                <EnrolmentBars before={t.sdg.enrolment.before} after={t.sdg.enrolment.after} growth={t.sdg.enrolment.growth} label={t.sdg.enrolment.chart} />
              </StatCard>
              <StatCard data={t.sdg.graduation} accent="#FFD400">
                <GraduationLine from={t.sdg.graduation.from} to={t.sdg.graduation.to} label={t.sdg.graduation.chart} />
              </StatCard>
            </div>

            <h3 className="mt-14 font-display text-2xl">{t.sdg.disabilityTitle}</h3>
            <p className="mt-1 text-[15px] text-ink-2">{t.sdg.disabilityNote}</p>
            <ul className="mt-5 grid gap-6 md:grid-cols-2">
              {t.sdg.stats.map((stat) => (
                <li key={stat.value} className="flex flex-col border-3 border-ink bg-paper p-5 shadow-neo">
                  <p className="nums text-4xl font-bold leading-none tracking-tight text-pop-red">{stat.value}</p>
                  <p className="mt-3 text-[16px] text-ink-2">{stat.body}</p>
                  <Source href={stat.url}>{stat.source}</Source>
                </li>
              ))}
            </ul>

            <h3 className="mt-14 font-display text-2xl">{t.sdg.fitTitle}</h3>
            <div className="mt-5 grid gap-6 md:grid-cols-2">
              {t.sdg.items.map((item) => (
                <div key={item.code} className="border-3 border-ink bg-bone p-5">
                  <p className="nums border-3 border-ink bg-ink px-2 py-1 font-display text-sm uppercase tracking-wide text-paper inline-block">{item.code}</p>
                  <h4 className="mt-3 text-lg font-bold">{item.title}</h4>
                  <p className="mt-1 text-ink-2">{item.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------- cara kerja */}
        <section id="cara-kerja" aria-labelledby="cara-kerja-judul" className="scroll-mt-16 border-b-3 border-ink bg-pop-yellow py-16 sm:py-20">
          <div className={SHELL}>
            <SectionTitle id="cara-kerja-judul">{t.how.title}</SectionTitle>
            <ol className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {t.how.steps.map((step, index) => (
                <li key={step.title} className="border-3 border-ink bg-paper p-5 shadow-neo">
                  <span aria-hidden="true" className="nums inline-flex h-9 w-9 items-center justify-center border-3 border-ink bg-ink font-bold text-paper">
                    {index + 1}
                  </span>
                  <h3 className="mt-3 text-lg font-bold">{step.title}</h3>
                  <p className="mt-1 text-ink-2">{step.body}</p>
                </li>
              ))}
            </ol>

            <div className="mt-12 border-3 border-ink bg-paper p-5 shadow-neo sm:p-8">
              <p className="font-display text-sm uppercase tracking-wide">{t.how.exampleLabel}</p>
              <div className="mt-6 grid gap-8 lg:grid-cols-[1fr_auto]">
                <div className="space-y-6">
                  <div className="border-l-5 border-ink pl-4">
                    <p className="font-display text-xs uppercase tracking-wide text-ink-2">{t.how.you}</p>
                    <p className="mt-1 text-lg font-semibold">
                      <Said phrase={t.how.question} />
                    </p>
                  </div>
                  <div className="flex gap-4">
                    <img src="/owls/nova.png" width={48} height={48} alt="" className="h-12 w-12 shrink-0 border-3 border-ink bg-pop-cyan object-contain p-0.5" />
                    <div>
                      <p className="font-display text-xs uppercase tracking-wide text-ink-2">{t.how.answerLabel}</p>
                      <p className="mt-1">
                        <Said phrase={t.how.answer} />
                      </p>
                    </div>
                  </div>
                </div>
                <div>
                  <p className="font-display text-xs uppercase tracking-wide text-ink-2">{t.how.screenLabel}</p>
                  <div lang="id" className="mt-2 w-full border-3 border-ink bg-ink p-4 font-mono text-[13px] leading-6 text-paper sm:w-72">
                    <p className="font-display text-lg text-pop-cyan">{t.how.screen.title}</p>
                    {t.how.screen.lines.map((line) => (
                      <p key={line} className="whitespace-pre">
                        {line}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
              <p className="mt-6 text-sm text-ink-2">{t.how.exampleNote}</p>
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- owl */}
        <section id="fitur" aria-labelledby="fitur-judul" className="scroll-mt-16 border-b-3 border-ink py-16 sm:py-20">
          <div className={SHELL}>
            <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
              <img src="/owls/nova.png" width={96} height={96} alt="" className="h-24 w-24 shrink-0 border-3 border-ink bg-pop-cyan object-contain p-1 shadow-neo" />
              <div>
                <SectionTitle id="fitur-judul">{t.owls.title}</SectionTitle>
                <p className="mt-4 max-w-2xl text-ink-2">
                  <b className="font-display text-ink">NOVA</b> · {t.owls.list.nova.role}: {t.owls.list.nova.body} {t.owls.lead}
                </p>
              </div>
            </div>

            <ul className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {TEAM.map((owl) => {
                const item = t.owls.list[owl];
                return (
                  <li key={owl} style={{ "--owl": OWL_COLOR[owl] } as CSSProperties} className="flex flex-col border-3 border-ink bg-paper shadow-neo">
                    <div className="flex items-center gap-3 border-b-3 border-ink p-4" style={{ backgroundColor: OWL_COLOR[owl] }}>
                      <img src={`/owls/${owl}.png`} width={56} height={56} alt="" className="h-14 w-14 shrink-0 border-3 border-ink bg-paper object-contain p-0.5" />
                      <div>
                        <h3 className="font-display text-lg">{owl.toUpperCase()}</h3>
                        <p className="text-[15px] font-semibold">{item.role}</p>
                      </div>
                    </div>
                    <div className="flex flex-1 flex-col p-4">
                      <p className="text-ink-2">{item.body}</p>
                      {item.say && (
                        <p className="mt-auto pt-4 text-[16px]">
                          <span className="block font-display text-xs uppercase tracking-wide text-ink-2">{t.owls.say}</span>
                          <Said phrase={item.say} className="font-semibold" />
                        </p>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        </section>

        {/* --------------------------------------------------------- Mode Suara */}
        <section id="mode-suara" aria-labelledby="mode-suara-judul" className="scroll-mt-16 border-b-3 border-ink bg-ink py-16 text-paper sm:py-20">
          <div className={`${SHELL} grid gap-12 lg:grid-cols-2`}>
            <div>
              <Eyebrow tone="light">{t.voice.eyebrow}</Eyebrow>
              <SectionTitle id="mode-suara-judul" className="mt-5">
                {t.voice.title}
              </SectionTitle>
              <p className="mt-4 text-lg text-paper/80">{t.voice.lead}</p>
              <p className="mt-8 border-3 border-paper bg-pop-yellow p-4 font-display text-xl text-ink">
                <q lang="id">{t.voice.turnOn.said}</q>
              </p>
              {t.voice.turnOn.meaning && <p className="mt-2 text-paper/70">{t.voice.turnOn.meaning}</p>}
              <ul className="mt-8 space-y-3">
                {t.voice.more.map((line) => (
                  <li key={line} className="border-l-5 border-pop-yellow pl-4 text-paper/80">
                    {line}
                  </li>
                ))}
              </ul>
            </div>

            <div className="space-y-6">
              <div className="border-3 border-paper p-5 shadow-neo-light sm:p-6">
                <h3 className="font-display text-xl">{t.voice.cuesTitle}</h3>
                <ul className="mt-4">
                  {CUES.map((cue) => (
                    <li key={cue} className="flex items-center gap-4 border-b-3 border-paper/25 py-3 last:border-b-0">
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold">{t.voice.cues[cue].label}</p>
                        <p className="text-[15px] text-paper/70">{t.voice.cues[cue].body}</p>
                      </div>
                      <button type="button" onClick={() => playCue(cue)} aria-label={`${t.voice.listenLabel}: ${t.voice.cues[cue].label}`} className={BTN.onDark}>
                        <PlayIcon playing={false} />
                        {t.voice.listenLabel}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="border-3 border-paper p-5 shadow-neo-light sm:p-6">
                <h3 className="font-display text-xl">{t.voice.offlineTitle}</h3>
                <p className="mt-2 text-[15px] text-paper/70">{t.voice.offlineBody}</p>
                <div className="mt-4 flex flex-wrap items-start gap-4">
                  <AudioButton src="/media/mode-suara-wifi.mp3" label={t.voice.listenLabel} stopLabel={t.hero.stop} className={BTN.onDark} />
                  <p className="flex-1">
                    <Said phrase={t.voice.offlineClip} muted="text-paper/70" />
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------- Equity Radar */}
        <section id="equity-radar" aria-labelledby="equity-judul" className="scroll-mt-16 border-b-3 border-ink bg-bone py-16 sm:py-20">
          <div className={`${SHELL} grid gap-12 lg:grid-cols-2`}>
            <div>
              <Eyebrow>{t.equity.eyebrow}</Eyebrow>
              <SectionTitle id="equity-judul" className="mt-5">
                {t.equity.title}
              </SectionTitle>
              <p className="mt-4 text-lg text-ink-2">{t.equity.lead}</p>
              <dl className="mt-8 space-y-6">
                {t.equity.points.map((point) => (
                  <div key={point.title} className="border-l-5 border-pop-red pl-4">
                    <dt className="text-lg font-bold">{point.title}</dt>
                    <dd className="mt-1 text-ink-2">{point.body}</dd>
                  </div>
                ))}
              </dl>
            </div>

            <figure className="self-start border-3 border-ink bg-paper p-5 shadow-neo sm:p-6">
              <figcaption className="flex items-center gap-3 border-b-3 border-ink pb-4">
                <img src="/owls/nexus.png" width={44} height={44} alt="" className="h-11 w-11 border-3 border-ink object-contain p-0.5" style={{ backgroundColor: OWL_COLOR.nexus }} />
                <span className="font-display text-lg">{t.equity.messageLabel}</span>
              </figcaption>
              <blockquote lang="id" className="mt-4 border-3 border-ink bg-bone p-4 text-[16px] text-ink-2">
                {t.equity.message}
              </blockquote>
              <p className="mt-3 text-sm text-ink-2">{t.equity.messageNote}</p>
            </figure>
          </div>
        </section>

        {/* ---------------------------------------------------------- dashboard */}
        <section aria-labelledby="office-judul" className="border-b-3 border-ink py-16 sm:py-20">
          <div className={SHELL}>
            <div className="max-w-2xl">
              <Eyebrow>{t.office.eyebrow}</Eyebrow>
              <SectionTitle id="office-judul" className="mt-5">
                {t.office.title}
              </SectionTitle>
              <p className="mt-4 text-lg text-ink-2">{t.office.lead}</p>
            </div>
            <figure className="mt-10">
              {OFFICE_ART ? (
                <img src={OFFICE_ART} width={1280} height={800} loading="lazy" decoding="async" alt={t.office.alt} className="w-full border-5 border-ink shadow-neo-lg" />
              ) : (
                <div className="flex aspect-[16/9] w-full items-center justify-center border-5 border-dashed border-ink bg-bone p-8 text-center">
                  <p className="font-display text-lg uppercase tracking-wide text-ink-2">{LOCAL[lang].office}</p>
                </div>
              )}
              <figcaption className="mt-3 text-sm text-ink-2">{t.office.caption}</figcaption>
            </figure>
          </div>
        </section>

        {/* ------------------------------------------------------- di balik layar */}
        <section aria-labelledby="behind-judul" className="bg-bone py-16 sm:py-20">
          <div className={SHELL}>
            <SectionTitle id="behind-judul">{t.behind.title}</SectionTitle>
            <p className="mt-3 max-w-2xl text-lg text-ink-2">{t.behind.lead}</p>

            <ol className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {t.behind.parts.map((part, index) => (
                <li key={part.title} className="border-3 border-ink bg-paper shadow-neo">
                  {BEHIND_ART && (
                    <div className="border-b-3 border-ink" aria-hidden="true">
                      <img src={`${BEHIND_ART}${index + 1}.png`} alt="" width={768} height={512} loading="lazy" decoding="async" className="aspect-[3/2] w-full object-cover" />
                    </div>
                  )}
                  <div className="p-5">
                    <div className="flex items-center gap-2.5">
                      <span aria-hidden="true" className="nums inline-flex h-8 w-8 items-center justify-center border-3 border-ink bg-pop-cyan font-bold">
                        {index + 1}
                      </span>
                      <h3 className="font-display text-lg">{part.title}</h3>
                    </div>
                    <p className="mt-3 text-[15px] text-ink-2">{part.summary}</p>
                  </div>
                </li>
              ))}
            </ol>

            <details className="mt-6 border-3 border-ink bg-paper px-5 py-4">
              <summary className="cursor-pointer font-display text-sm uppercase tracking-wide">{t.behind.details}</summary>
              <div className="mt-5 grid gap-6 pb-2 sm:grid-cols-2 lg:grid-cols-4">
                {t.behind.parts.map((part) => (
                  <div key={part.title}>
                    <h3 className="font-display text-lg">{part.title}</h3>
                    <p className="mt-2 text-[15px] text-ink-2">{part.body}</p>
                  </div>
                ))}
              </div>
            </details>

            <div className="mt-12 grid gap-10 md:grid-cols-2">
              <List title={t.behind.privacyTitle} items={t.behind.privacy} />
              <List title={t.behind.limitsTitle} items={t.behind.limits} />
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t-3 border-ink bg-ink py-10 text-paper">
        <div className={`${SHELL} flex flex-wrap items-center gap-4`}>
          <span aria-hidden="true" className="grid h-10 w-10 place-items-center border-3 border-paper bg-pop-yellow font-display text-lg leading-none text-ink">
            E
          </span>
          <p>
            <span className="font-display text-xl">EduPad</span>
            <span className="ml-2 text-paper/70">{t.footer.tagline}</span>
          </p>
          <div className="ml-auto flex items-center gap-2">
            <LangSwitch lang={lang} setLang={setLang} label={t.langLabel} tone="light" />
            <a href={signedIn ? "/dashboard/" : LOGIN_URL} className="inline-flex h-10 items-center border-3 border-paper bg-pop-yellow px-3 font-display text-xs uppercase tracking-wide text-ink">
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
            <span aria-hidden="true" className="mt-2.5 h-3 w-3 shrink-0 border-3 border-ink bg-pop-yellow" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Tempat foto perangkat. Selama fotonya belum ada, bingkainya dibiarkan kosong dan diberi
 *  keterangan apa adanya — sama seperti versi pertama. */
function DeviceFrame({ alt, pending, note }: { alt: string; pending: string; note: string }) {
  if (DEVICE_ART) {
    return <img src={DEVICE_ART} alt={alt} width={900} height={1125} className="aspect-[4/5] w-full border-5 border-ink bg-paper object-cover shadow-neo-lg" />;
  }
  return (
    <div className="flex aspect-[4/3] w-full flex-col items-center justify-center gap-1 border-5 border-dashed border-ink bg-paper p-6 text-center shadow-neo md:aspect-[4/5]">
      <p className="font-display text-base uppercase tracking-wide">{pending}</p>
      <p className="text-[15px] text-ink-2">{note}</p>
    </div>
  );
}
