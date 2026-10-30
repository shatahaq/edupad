import { useEffect, useState } from "react";

import type { Lang } from "./copy";

const KEY = "edupad-lang";
const TITLES: Record<Lang, string> = {
  id: "EduPad: asisten belajar berbasis suara",
  en: "EduPad: a voice-first study assistant",
};

function initial(): Lang {
  const param = new URLSearchParams(window.location.search).get("lang");
  if (param === "id" || param === "en") return param;
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "id" || saved === "en") return saved;
  } catch {
    // penyimpanan diblokir: pakai bahasa browser
  }
  return navigator.language.toLowerCase().startsWith("id") ? "id" : "en";
}

/** Bahasa halaman: ?lang=, lalu pilihan terakhir, lalu bahasa browser. */
export function useLang(): [Lang, (lang: Lang) => void] {
  const [lang, setLang] = useState<Lang>(initial);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.title = TITLES[lang];
    try {
      localStorage.setItem(KEY, lang);
    } catch {
      // tidak apa-apa: pilihan hanya tidak diingat
    }
  }, [lang]);

  return [lang, setLang];
}
