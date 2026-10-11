"""Scraper materi kuliah kelas.usu.ac.id memakai Playwright.

Hanya membaca dan mengunduh materi; tidak pernah mengirim atau mengubah apa pun.
Unduhan inkremental berdasarkan URL file (URL Moodle memuat nomor revisi).
"""

from __future__ import annotations

import contextlib
import logging
import re
import time
from html import unescape
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from edupad.config import (
    BROWSER_PROFILE_DIR,
    MATERIALS_DIR,
    MOODLE_SESSION_FILE,
    MOODLE_URL,
    REQUEST_DELAY,
    SCRAPER_LOCK_FILE,
)
from edupad.core.files import (
    NAME_MAXLEN,
    now_iso,
    read_json,
    safe_filename,
    safe_name,
    sha256_bytes,
    write_json,
)
from edupad.core.lock import AlreadyRunning, acquire_lock
from edupad.core.markdown import html_to_markdown
from edupad.core.session import (
    MOODLE,
    load_cookies,
    report_login_expired,
    report_login_ok,
    save_cookies,
)
from edupad.errors import EXIT_ERROR, EXIT_LOGIN_REQUIRED, EXIT_OK, LoginRequired

log = logging.getLogger(__name__)

MANIFEST_FILE = MATERIALS_DIR / "manifest.json"
MY_COURSES_URL = f"{MOODLE_URL}/my/courses.php"

DOWNLOAD_TIMEOUT_MS = 60_000
LOGIN_TIMEOUT_MS = 5 * 60_000
AUTO_SSO_TIMEOUT_MS = 30_000  # mode headless hanya menunggu login SSO otomatis

# assign/quiz/forum dilewati; page/book/label adalah materi HTML yang ditulis di Moodle
MATERIAL_MODULES = ("resource", "folder", "url", "page", "book")
MATERIAL_EXTS = (".pdf", ".ppt", ".pptx", ".doc", ".docx", ".txt", ".md", ".html", ".htm")

# Selektor Moodle 4.x. Sesuaikan bila tema kelas.usu.ac.id berubah.
SEL_COURSE_LINKS = "a[href*='/course/view.php?id=']"
SEL_MAIN = "div[role='main'], #region-main"
SEL_PAGE_CONTENT = "div[role='main'] .generalbox, #region-main .generalbox"
SEL_BOOK_CHAPTER = ".book_chapter"
SEL_HTML = {
    "section": "#region-main [data-for='section'][data-number], #region-main li.section[id^='section-']",
    "summary": ".summarytext, .summary",
    "label": "li.modtype_label",
    "label_content": ".activity-altcontent, .contentwithoutlink, .no-overflow",
}
# Panel course index memuat semua section + aktivitas. Tema USU menampilkan
# section sebagai kartu, sehingga aktivitas tidak ada di konten utama.
SEL_INDEX = {
    "section": ".courseindex-section[data-for='section']",
    "name": "[data-for='section_title']",
    "activity": "li[data-for='cm']",
    "link": "a.courseindex-link",
}
SEL_CONTENT = {
    "section": "li.section, div.course-section",
    "name": "h3.sectionname, .sectionname",
    "activity": "li.activity, div.activity",
    "link": "a.aalink, .activityname a, .activitytitle a",
}

_EXTRACT_SECTIONS_JS = """
([secSel, nameSel, actSel, linkSel]) => {
  const clean = (el) => {
    const c = el.cloneNode(true);
    c.querySelectorAll('.accesshide, .sr-only, .visually-hidden').forEach(e => e.remove());
    return c.textContent.replace(/\\s+/g, ' ').trim();
  };
  return [...document.querySelectorAll(secSel)].map(sec => {
    const nameEl = sec.querySelector(nameSel);
    const items = [...sec.querySelectorAll(actSel)].flatMap(act => {
      const a = act.querySelector(linkSel);
      if (!a) return [];
      return [{title: clean(a.querySelector('.instancename') || a), href: a.href}];
    });
    const number = sec.dataset.number ?? (sec.id.match(/^section-(\\d+)$/) || [])[1] ?? null;
    return {name: nameEl ? clean(nameEl) : '', number, items};
  });
}
"""

_EXTRACT_HTML_JS = """
([secSel, sumSel, labelSel, labelContentSel]) => {
  const html = (el) => {
    const c = el.cloneNode(true);
    c.querySelectorAll('script, style, noscript, .accesshide, .sr-only, .visually-hidden')
     .forEach(e => e.remove());
    return c.textContent.trim() ? c.innerHTML : '';
  };
  const out = {};
  document.querySelectorAll(secSel).forEach(sec => {
    const n = sec.dataset.number ?? (sec.id.match(/^section-(\\d+)$/) || [])[1];
    if (n === undefined || n in out) return;
    const own = (el) => el.closest(secSel) === sec;  // abaikan subsection bersarang
    const sum = [...sec.querySelectorAll(sumSel)].find(own);
    const labels = [...sec.querySelectorAll(labelSel)].filter(own).flatMap(l => {
      const c = l.querySelector(labelContentSel);
      const h = c ? html(c) : '';
      return h ? [{id: l.dataset.id || l.id.replace('module-', ''), html: h}] : [];
    });
    out[n] = {summary: sum ? html(sum) : '', labels};
  });
  return out;
}
"""


# ------------------------------ helpers --------------------------------------
def is_login_page(url: str) -> bool:
    return not url.startswith(MOODLE_URL) or "/login/" in url or "jwtsso" in url


def is_browser_closed(error: Exception) -> bool:
    msg = str(error)
    return isinstance(error, PlaywrightError) and ("has been closed" in msg or "disposed" in msg)


def module_type(href: str) -> str | None:
    m = re.search(r"/mod/([a-z]+)/", href)
    return m.group(1) if m else None


def file_key(url: str) -> str:
    """URL file tanpa nomor revisi: key sama + URL beda berarti file diperbarui dosen."""
    return re.sub(r"/content/\d+/", "/content/0/", urlparse(url).path)


def filename_from_url(url: str) -> str:
    return unquote(urlparse(url).path.rsplit("/", 1)[-1]) or "file"


def relative(path: Path) -> str:
    return path.relative_to(MATERIALS_DIR).as_posix()


def goto(page, url: str, wait_until: str = "domcontentloaded") -> None:
    page.goto(url, wait_until=wait_until)
    time.sleep(REQUEST_DELAY)
    if is_login_page(page.url):
        raise LoginRequired(f"diarahkan ke halaman login saat membuka {url}")


# ------------------------------ manifest -------------------------------------
def load_manifest() -> dict:
    data = read_json(MANIFEST_FILE)
    return data if "courses" in data else {"generated_at": None, "courses": {}}


def save_manifest(manifest: dict) -> None:
    manifest["generated_at"] = now_iso()
    write_json(MANIFEST_FILE, manifest)


def known_files(manifest: dict) -> dict[str, dict]:
    """file_key -> record file hasil run sebelumnya."""
    known = {}
    for course in manifest["courses"].values():
        for section in course.get("sections", []):
            files = list(section.get("summary_files", []))
            for item in section.get("items", []):
                files.extend(item.get("files", []))
            for f in files:
                if "pluginfile.php" in f.get("source_url", ""):
                    known[file_key(f["source_url"])] = f
    return known


# ------------------------------ login ----------------------------------------
def ensure_logged_in(page, interactive: bool) -> None:
    page.goto(MY_COURSES_URL, wait_until="domcontentloaded")
    if not is_login_page(page.url):
        return
    if interactive:
        log.info(
            "[..] Menunggu login SSO USU di jendela browser (maks. %d menit).",
            LOGIN_TIMEOUT_MS // 60_000,
        )
    try:
        page.wait_for_url(
            lambda u: not is_login_page(u),
            timeout=LOGIN_TIMEOUT_MS if interactive else AUTO_SSO_TIMEOUT_MS,
        )
    except PlaywrightTimeoutError:
        raise LoginRequired(
            "login tidak selesai" if interactive else "sesi habis dan SSO tidak login otomatis"
        ) from None
    page.goto(MY_COURSES_URL, wait_until="domcontentloaded")
    if is_login_page(page.url):
        raise LoginRequired("masih di halaman login")


def restore_session(context) -> None:
    """Chromium membuang cookie sesi setiap ditutup; pasang lagi dari file."""
    cookies = load_cookies(MOODLE_SESSION_FILE).get("cookies") or []
    if cookies:
        try:
            context.add_cookies(cookies)
        except PlaywrightError as e:
            log.warning("[!] Cookie tersimpan tidak bisa dipakai: %s", e)


def persist_session(context, page) -> None:
    save_cookies(MOODLE_SESSION_FILE, context.cookies(), page.evaluate("navigator.userAgent"))


# ------------------------------ courses --------------------------------------
def enrolled_courses(page) -> list[dict]:
    """Lewat AJAX Moodle (tidak terpengaruh pagination/filter tampilan); fallback: DOM."""
    goto(page, MY_COURSES_URL, wait_until="networkidle")
    try:
        sesskey = page.evaluate("M.cfg.sesskey")
        resp = page.request.post(
            f"{MOODLE_URL}/lib/ajax/service.php?sesskey={sesskey}",
            data=[
                {
                    "index": 0,
                    "methodname": "core_course_get_enrolled_courses_by_timeline_classification",
                    "args": {"offset": 0, "limit": 0, "classification": "all", "sort": "fullname"},
                }
            ],
        )
        result = resp.json()[0]
        if result.get("error"):
            raise RuntimeError(result.get("exception"))
        return [
            {"id": str(c["id"]), "name": unescape(c["fullname"]).strip(), "url": c["viewurl"]}
            for c in result["data"]["courses"]
        ]
    except (PlaywrightError, RuntimeError, KeyError, IndexError, ValueError) as e:
        if is_browser_closed(e):
            raise
        log.warning("[!] AJAX daftar mata kuliah gagal (%s), pakai DOM.", e)
        return _enrolled_courses_from_dom(page)


def _enrolled_courses_from_dom(page) -> list[dict]:
    names: dict[str, str] = {}
    for a in page.query_selector_all(SEL_COURSE_LINKS):
        m = re.search(r"id=(\d+)", a.get_attribute("href") or "")
        if not m:
            continue
        # satu kartu punya link gambar & judul: ambil teks terpanjang
        text = re.sub(r"^(Course name|Nama mata kuliah)\s*", "", a.inner_text().strip())
        if len(text) > len(names.get(m.group(1), "")):
            names[m.group(1)] = text
        names.setdefault(m.group(1), "")
    return [
        {
            "id": cid,
            "name": name or f"course_{cid}",
            "url": f"{MOODLE_URL}/course/view.php?id={cid}",
        }
        for cid, name in names.items()
    ]


# ------------------------------ sections -------------------------------------
def _extract_sections(page, sel: dict) -> list[dict]:
    return page.evaluate(
        _EXTRACT_SECTIONS_JS, [sel["section"], sel["name"], sel["activity"], sel["link"]]
    )


def _extract_html_blocks(page) -> dict[str, dict]:
    """nomor section -> {summary: html, labels: [{id, html}]}"""
    return page.evaluate(
        _EXTRACT_HTML_JS,
        [SEL_HTML["section"], SEL_HTML["summary"], SEL_HTML["label"], SEL_HTML["label_content"]],
    )


def label_title(html: str) -> str:
    first = next(
        (ln.strip("#*_ -") for ln in html_to_markdown(html).splitlines() if ln.strip("#*_ -")), ""
    )
    return first[:NAME_MAXLEN] or "label"


def course_sections(page, course: dict) -> list[dict]:
    goto(page, course["url"], wait_until="networkidle")
    raw = _extract_sections(page, SEL_INDEX)
    if not any(s["items"] for s in raw):
        raw = _extract_sections(page, SEL_CONTENT)
    html_blocks = _extract_html_blocks(page)

    if not any(s["items"] for s in raw):
        # format satu-section-per-halaman (Tiles/Grid/OneTopic)
        section_urls = sorted(
            set(
                page.eval_on_selector_all(
                    f"a[href*='course/view.php?id={course['id']}'][href*='section=']",
                    "els => els.map(e => e.href)",
                )
            )
        )
        for url in section_urls:
            goto(page, url, wait_until="networkidle")
            raw.extend(_extract_sections(page, SEL_CONTENT))
            for n, block in _extract_html_blocks(page).items():
                html_blocks.setdefault(n, block)

    sections, seen_urls, seen_numbers = [], set(), set()
    for idx, sec in enumerate(raw):
        number = sec["number"] if sec["number"] is not None else str(idx)
        index = int(number) if number.isdigit() else idx
        block = html_blocks.get(number, {}) if number not in seen_numbers else {}
        seen_numbers.add(number)
        items = [
            {
                "title": label_title(label["html"]),
                "type": "label",
                "url": f"{course['url']}#module-{label['id']}",
                "html": label["html"],
            }
            for label in block.get("labels", [])
        ]
        for it in sec["items"]:
            href, mtype = it["href"], module_type(it["href"])
            if mtype not in MATERIAL_MODULES or href in seen_urls:
                continue
            seen_urls.add(href)
            items.append({"title": it["title"] or mtype, "url": href, "type": mtype})
        summary = block.get("summary", "")
        if items or summary:
            sections.append(
                {
                    "index": index,
                    "section": sec["name"] or f"pertemuan_{index:02d}",
                    "items": items,
                    "summary_html": summary,
                    "url": f"{MOODLE_URL}/course/view.php?id={course['id']}&section={number}",
                }
            )
    return sections


# ------------------------------ downloads ------------------------------------
class Downloader:
    """Unduhan & penyimpanan materi satu run, inkremental terhadap manifest lama."""

    def __init__(self, page, context, known: dict[str, dict]):
        self.page = page
        self.context = context
        self.known = known
        self.used_paths: set[Path] = set()

    def new_course(self) -> None:
        self.used_paths = set()

    def redirect_target(self, item_url: str) -> str:
        """Baca header Location dari ?redirect=1 tanpa mengikuti atau mengunduh file."""
        sep = "&" if "?" in item_url else "?"
        resp = self.context.request.get(
            f"{item_url}{sep}redirect=1", max_redirects=0, timeout=DOWNLOAD_TIMEOUT_MS
        )
        time.sleep(REQUEST_DELAY)
        location = resp.headers.get("location", "")
        return urljoin(MOODLE_URL, location) if location else ""

    def pluginfile_links(self, item_url: str) -> list[str]:
        try:
            goto(self.page, item_url)
        except PlaywrightError as e:
            if is_browser_closed(e):
                raise
            # resource "force download" memicu unduhan saat dibuka
            log.warning(
                "      [skip] tidak bisa membuka %s: %s", item_url, e.message.splitlines()[0]
            )
            return []
        urls = self.page.eval_on_selector_all(
            "a[href*='pluginfile.php'], object[data*='pluginfile.php'], iframe[src*='pluginfile.php']",
            "els => els.map(e => e.href || e.data || e.src)",
        )
        if not urls and "pluginfile.php" in self.page.url:
            urls = [self.page.url]
        return list(dict.fromkeys(urljoin(MOODLE_URL, u) for u in urls if u))

    def download(self, url: str, dest_dir: Path) -> dict | None:
        filename = safe_filename(filename_from_url(url))
        if not filename.lower().endswith(MATERIAL_EXTS):
            log.info("      [lewat] bukan tipe materi: %s", filename)
            return None

        key = file_key(url)
        previous = self.known.get(key)
        if previous:
            previous_path = MATERIALS_DIR / previous["path"]
            if previous["source_url"] == url and previous_path.exists():
                self.used_paths.add(previous_path)
                log.info("      [ada] %s", previous["path"])
                return previous
            dest = previous_path  # revisi baru dari dosen: timpa di tempat yang sama
        else:
            owned = {MATERIALS_DIR / f["path"] for f in self.known.values()}
            dest = dest_dir / filename
            n = 2
            while dest in self.used_paths or dest in owned:
                dest = dest_dir / f"{Path(filename).stem} ({n}){Path(filename).suffix}"
                n += 1

        resp = self.context.request.get(url, timeout=DOWNLOAD_TIMEOUT_MS)
        time.sleep(REQUEST_DELAY)
        if not resp.ok:
            log.warning("      [skip] HTTP %s %s", resp.status, filename)
            return None
        got_html = "text/html" in resp.headers.get("content-type", "")
        if is_login_page(resp.url) or (
            got_html and not filename.lower().endswith((".html", ".htm"))
        ):
            raise LoginRequired(f"unduhan {filename} diarahkan ke halaman login")

        body = resp.body()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        self.used_paths.add(dest)
        log.info("      [%s] %s", "update" if previous else "dl", relative(dest))
        record = {
            "path": relative(dest),
            "source_url": url,
            "size": len(body),
            "sha256": sha256_bytes(body),
            "downloaded_at": now_iso(),
        }
        self.known[key] = record
        return record

    def save_html(
        self, html: str, title: str, source_url: str, dest_dir: Path, filename: str | None = None
    ) -> dict | None:
        """Materi HTML (page, book, label, deskripsi section) disimpan sebagai Markdown."""
        md = html_to_markdown(html)
        if not md:
            return None
        body = f"# {title}\n\nSumber: {source_url}\n\n{md}\n".encode()
        base = filename or safe_name(title)
        dest = dest_dir / f"{base}.md"
        n = 2
        while dest in self.used_paths:
            dest = dest_dir / f"{base} ({n}).md"
            n += 1
        self.used_paths.add(dest)
        if dest.exists() and dest.read_bytes() == body:
            log.info("      [ada] %s", relative(dest))
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
            log.info("      [html] %s", relative(dest))
        return {
            "path": relative(dest),
            "source_url": source_url,
            "size": len(body),
            "sha256": sha256_bytes(body),
            "downloaded_at": now_iso(),
        }

    def html_content(self, item: dict) -> str:
        if item["type"] == "book":
            cmid = re.search(r"id=(\d+)", item["url"]).group(1)
            goto(self.page, f"{MOODLE_URL}/mod/book/tool/print/index.php?id={cmid}")
            chapters = self.page.query_selector_all(SEL_BOOK_CHAPTER)
            if chapters:
                return "\n".join(c.inner_html() for c in chapters)
        else:
            goto(self.page, item["url"])
            el = self.page.query_selector(SEL_PAGE_CONTENT)
            if el:
                return el.inner_html()
        el = self.page.query_selector(SEL_MAIN)
        return el.inner_html() if el else ""


def linked_files(html: str) -> list[str]:
    hrefs = re.findall(r'href="([^"]*pluginfile\.php[^"]*)"', html)
    return list(dict.fromkeys(urljoin(MOODLE_URL, unescape(h)) for h in hrefs))


def process_item(dl: Downloader, item: dict, dest_dir: Path) -> dict:
    record = {
        "title": item["title"],
        "type": item["type"],
        "activity_url": item["url"],
        "files": [],
    }
    kind = item["type"]

    if kind == "url":  # link eksternal: dicatat, tidak dibuka
        record["external_url"] = dl.redirect_target(item["url"]) or None
        log.info("      [link] %s -> %s", item["title"], record["external_url"])
        return record

    if kind in ("page", "book", "label"):
        html = item["html"] if kind == "label" else dl.html_content(item)
        saved = dl.save_html(html, item["title"], item["url"], dest_dir)
        record["files"] = [saved] if saved else []
        record["files"] += [f for url in linked_files(html) if (f := dl.download(url, dest_dir))]
        return record

    urls: list[str] = []
    if kind == "resource":
        target = dl.redirect_target(item["url"])
        if "pluginfile.php" in target:
            urls = [target]
        elif is_login_page(target):
            raise LoginRequired(f"diarahkan ke login saat membuka {item['url']}")
    if not urls:  # folder, atau resource dengan tampilan embed
        urls = dl.pluginfile_links(item["url"])
    record["files"] = [f for url in urls if (f := dl.download(url, dest_dir))]
    return record


def _guard(stats: dict, label: str, fn, *args):
    """Satu item gagal tidak menghentikan run, kecuali sesi habis / browser tertutup."""
    try:
        return fn(*args)
    except LoginRequired:
        raise
    except Exception as e:
        if is_browser_closed(e):
            raise
        log.error("      [error] %s: %s", label, e)
        stats["errors"] += 1
        return None


def scrape_course(dl: Downloader, course: dict, stats: dict) -> dict | None:
    log.info("\n=== %s (id=%s) ===", course["name"], course["id"])
    sections = _guard(stats, "gagal membaca mata kuliah", course_sections, dl.page, course)
    if sections is None:
        return None
    dl.new_course()
    course_dir = MATERIALS_DIR / f"{course['id']}_{safe_name(course['name'])}"
    entry = {
        "id": course["id"],
        "course": course["name"],
        "url": course["url"],
        "scraped_at": now_iso(),
        "sections": [],
    }
    for sec in sections:
        log.info("  - %s (%d item)", sec["section"], len(sec["items"]))
        sec_dir = course_dir / f"{sec['index']:02d}_{safe_name(sec['section'])}"
        sec_entry = {
            "section": sec["section"],
            "index": sec["index"],
            "url": sec["url"],
            "summary": None,
            "items": [],
        }
        if sec["summary_html"]:
            sec_entry["summary"] = dl.save_html(
                sec["summary_html"],
                sec["section"],
                sec["url"],
                sec_dir,
                filename="00_Deskripsi pertemuan",
            )
            stats["files"] += bool(sec_entry["summary"])
            for url in linked_files(sec["summary_html"]):
                saved = _guard(stats, url, dl.download, url, sec_dir)
                if saved:
                    sec_entry.setdefault("summary_files", []).append(saved)
                    stats["files"] += 1
        for item in sec["items"]:
            stats["items"] += 1
            record = _guard(stats, item["title"], process_item, dl, item, sec_dir)
            if record:
                stats["files"] += len(record["files"])
                sec_entry["items"].append(record)
        entry["sections"].append(sec_entry)
    return entry


# ------------------------------ entry point ----------------------------------
def run(
    course_ids: list[str] | None = None,
    list_only: bool = False,
    headless: bool = False,
    login_only: bool = False,
) -> int:
    try:
        lock = acquire_lock(SCRAPER_LOCK_FILE)  # noqa: F841 - dipegang sampai proses selesai
    except AlreadyRunning:
        log.error("[x] Scraper lain sedang berjalan (profil browser sedang dipakai).")
        return EXIT_ERROR

    MATERIALS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    stats = {"items": 0, "files": 0, "errors": 0}
    headless = headless and not login_only
    exit_code = EXIT_OK

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(BROWSER_PROFILE_DIR), headless=headless, accept_downloads=True
        )
        restore_session(context)
        page = context.pages[0] if context.pages else context.new_page()
        try:
            ensure_logged_in(page, interactive=not headless)
            log.info("[ok] Login terverifikasi.")
            persist_session(context, page)
            report_login_ok(MOODLE)
            if login_only:
                log.info("[ok] Sesi tersimpan di %s", MOODLE_SESSION_FILE)
                return EXIT_OK

            courses = enrolled_courses(page)
            log.info("[ok] Ditemukan %d mata kuliah.", len(courses))
            if list_only:
                for c in courses:
                    log.info("  %-8s %s", c["id"], c["name"])
                return EXIT_OK
            if course_ids:
                courses = [c for c in courses if c["id"] in set(course_ids)]

            dl = Downloader(page, context, known_files(manifest))
            for course in courses:
                entry = scrape_course(dl, course, stats)
                if entry:
                    manifest["courses"][course["id"]] = entry
                    save_manifest(manifest)  # per mata kuliah: aman bila proses terhenti
            persist_session(context, page)
        except LoginRequired as e:
            log.error("\n[!] Sesi login habis: %s. Login ulang: python -m edupad login", e)
            report_login_expired(MOODLE, "scraper materi")
            exit_code = EXIT_LOGIN_REQUIRED
        except PlaywrightError as e:
            if not is_browser_closed(e):
                raise
            log.error("\n[!] Jendela browser tertutup, proses dihentikan.")
            exit_code = EXIT_ERROR
        finally:
            with contextlib.suppress(PlaywrightError):  # browser mungkin sudah tertutup
                context.close()

    log.info(
        "\n[selesai] %d aktivitas, %d file tercatat, %d error. Manifest: %s",
        stats["items"],
        stats["files"],
        stats["errors"],
        MANIFEST_FILE,
    )
    if exit_code == EXIT_OK and stats["errors"]:
        return EXIT_ERROR
    return exit_code
