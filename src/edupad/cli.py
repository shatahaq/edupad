"""Perintah: python -m edupad <perintah> [opsi]."""

from __future__ import annotations

import argparse

from edupad.core.logs import setup_logging


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="edupad", description="Data perkuliahan USU untuk AI agent EduPad")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("login", help="login SSO kelas.usu.ac.id lewat browser, lalu simpan sesi")

    scrape = sub.add_parser("scrape", help="unduh materi dari kelas.usu.ac.id")
    scrape.add_argument("--course", nargs="+", metavar="ID", help="hanya mata kuliah ini")
    scrape.add_argument("--list", action="store_true", help="tampilkan daftar mata kuliah saja")
    scrape.add_argument("--headless", action="store_true", help="tanpa jendela (untuk cron)")

    assignments = sub.add_parser("assignments", help="ambil tugas, kuis, deadline & status")
    assignments.add_argument("--course", nargs="+", metavar="ID", help="hanya mata kuliah ini")

    schedule = sub.add_parser("schedule", help="ambil jadwal kuliah & presensi dari portal SATU")
    schedule.add_argument("--login", action="store_true", help="login portal SATU lewat browser dulu")

    att = sub.add_parser("attendance", help="cek presensi yang sedang dibuka & kirim notifikasi")
    att.add_argument("--fill", action="store_true", help="isi presensi mandiri otomatis (EKSPERIMENTAL)")
    att.add_argument("--dry-run", action="store_true", help="simulasi tanpa benar-benar mengisi")

    convert = sub.add_parser("convert", help="konversi materi ke Markdown")
    convert.add_argument("--force", action="store_true", help="konversi ulang semua file")

    sub.add_parser("corpus", help="bersihkan & potong materi untuk AI agent")

    summarize = sub.add_parser("summarize", help="buat ringkasan per pertemuan untuk AI agent")
    summarize.add_argument("--force", action="store_true", help="buat ulang semua ringkasan")

    index = sub.add_parser("index", help="embed chunk & sinkronkan ke vector database Supabase")
    index.add_argument("--force", action="store_true", help="embed ulang semua chunk")

    ask = sub.add_parser("ask", help="tanya AI agent")
    ask.add_argument("question", help="pertanyaan, dalam tanda kutip")
    ask.add_argument("--trace", action="store_true", help="tampilkan tool yang dipanggil")
    ask.add_argument("--detail", action="store_true", help="tampilkan jawaban lengkap (Markdown)")
    ask.add_argument("--new", action="store_true", help="mulai sesi percakapan baru")
    ask.add_argument("--speak", action="store_true", help="suarakan jawaban (TTS), simpan & putar WAV")
    ask.add_argument("--no-memory", action="store_true", help="tanpa memory percakapan")

    chat = sub.add_parser("chat", help="percakapan berlanjut dengan AI agent")
    chat.add_argument("--trace", action="store_true", help="tampilkan tool yang dipanggil")
    chat.add_argument("--detail", action="store_true", help="tampilkan jawaban lengkap (Markdown)")
    chat.add_argument("--new", action="store_true", help="mulai sesi percakapan baru")
    chat.add_argument("--speak", action="store_true", help="suarakan setiap jawaban (TTS)")

    mem = sub.add_parser("memory", help="lihat atau hapus memory AI agent")
    mem.add_argument("--clear", action="store_true", help="hapus semua percakapan & fakta tersimpan")

    ev = sub.add_parser("eval", help="ukur token & kualitas AI agent pada set uji")
    ev.add_argument("--label", default="run", help="nama hasil di evals/results/")
    ev.add_argument("--case", nargs="+", metavar="ID", help="hanya kasus ini")
    ev.add_argument("--repeat", type=int, default=1, help="ulangi set uji (jawaban LLM bervariasi)")
    ev.add_argument("--no-judge", action="store_true", help="tanpa penilaian LLM")
    ev.add_argument("--compare", nargs="+", metavar="LABEL", help="bandingkan hasil yang sudah ada")
    ev.add_argument("--no-memory", action="store_true", help="riwayat di RAM, tanpa memory Supabase")
    ev.add_argument("--detail", action="store_true", help="dengan jawaban detail (default mode perangkat)")
    ev.add_argument("--no-summaries", action="store_true", help="get_meeting tanpa ringkasan")
    ev.add_argument("--rejudge", metavar="LABEL", help="nilai ulang hasil tersimpan")

    sub.add_parser("keepalive", help="perpanjang sesi kelas.usu.ac.id")
    sub.add_parser("pipeline", help="scrape -> assignments -> convert -> corpus -> summarize -> index")
    return parser


def _print_answer(result: dict, trace: bool, show_detail: bool) -> None:
    from edupad.agent.formatting import SCREEN_COLS

    if trace:
        for step in result["tools"]:
            print(f"[tool] {step['tool']}({step['args']}) {step['ms']} ms{' ERROR' if step['error'] else ''}")
        print(f"[info] {result['tokens']} token ({result['cached_tokens']} dari cache), "
              f"{result['seconds']} detik\n")
    print(f"[SUARA] {result['speech']}\n")
    screen = result["screen"]
    border = "+" + "-" * SCREEN_COLS + "+"
    print("[LCD]\n" + border)
    title = screen["title"].upper() if screen["title_size"] == "large" else screen["title"]
    print(f"|{title:^{SCREEN_COLS}}|")
    print("|" + " " * SCREEN_COLS + "|")
    for line in screen["lines"]:
        print(f"|{line:<{SCREEN_COLS}}|")
    print(border)
    if show_detail:
        print(f"\n[DETAIL]\n{result['detail']}")


def _speak(text: str) -> None:
    """Suarakan jawaban: simpan ke data/voice/jawaban.wav dan putar (Windows)."""
    import sys
    import time

    from edupad.config import VOICE_DIR
    from edupad.voice import tts

    started, first, chunks = time.time(), None, []
    try:
        for chunk in tts.stream(text):
            first = first if first is not None else time.time() - started
            chunks.append(chunk)
    except tts.TTSError as e:
        print(f"[x] TTS: {e}")
        return
    pcm = b"".join(chunks)
    path = VOICE_DIR / "jawaban.wav"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(tts.to_wav(pcm))
    print(f"[TTS] audio pertama {first or 0:.2f} s, selesai {time.time() - started:.2f} s, "
          f"{tts.duration_seconds(pcm):.1f} s audio -> {path}")
    if sys.platform == "win32":
        import winsound

        winsound.PlaySound(str(path), winsound.SND_FILENAME)


def _ask(question: str, trace: bool, show_detail: bool, new: bool, use_memory: bool,
         speak: bool = False) -> int:
    from edupad.agent.assistant import LLMError, ask, open_memory

    try:
        result = ask(question, memory=open_memory(new_session=new) if use_memory else None,
                     with_detail=show_detail)
    except LLMError as e:
        print(f"[x] {e}")
        return 1
    _print_answer(result, trace, show_detail)
    if speak:
        _speak(result["speech"])
    return 0


def _chat(trace: bool, show_detail: bool, new: bool, speak: bool = False) -> int:
    from edupad.agent.assistant import LLMError, ask, open_memory

    memory = open_memory(new_session=new)
    history: list[dict] = []  # dipakai hanya bila memory Supabase tidak tersedia
    print("EduPad chat. Ketik pertanyaan, atau 'keluar'.")
    while True:
        try:
            question = input("\nKamu: ").strip()
        except (EOFError, KeyboardInterrupt):
            return 0
        if question.lower() in {"keluar", "exit", "quit"}:
            return 0
        if not question:
            continue
        try:
            result = ask(question, history, memory=memory, with_detail=show_detail)
        except LLMError as e:
            print(f"[x] {e}")
            continue
        history = result["history"]
        _print_answer(result, trace, show_detail)
        if speak:
            _speak(result["speech"])


def _memory(clear: bool) -> int:
    from edupad.agent.assistant import open_memory

    memory = open_memory()
    if not memory:
        return 1
    if clear:
        memory.delete_user()
        print("[ok] Memory dihapus.")
        return 0
    print("Fakta tersimpan:")
    print("\n".join(f"- {f}" for f in memory.facts()) or "-")
    print(f"\nSesi aktif sejak {memory.session['started_at']}")
    print(f"Ringkasan: {memory.session.get('summary') or '-'}")
    for m in memory.history():
        if m["role"] == "user":
            print(f"\nKamu: {m['content']}")
        elif m["role"] == "assistant":
            print(f"EduPad: {m['content'].splitlines()[0]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    setup_logging(args.command)

    # Impor per perintah: keepalive tidak perlu memuat Playwright/PyMuPDF.
    if args.command == "login":
        from edupad.collectors import materials
        return materials.run(login_only=True)
    if args.command == "scrape":
        from edupad.collectors import materials
        return materials.run(course_ids=args.course, list_only=args.list, headless=args.headless)
    if args.command == "assignments":
        from edupad.collectors import assignments
        return assignments.run(course_ids=args.course)
    if args.command == "schedule":
        from edupad.collectors import schedule
        return schedule.run(login=args.login)
    if args.command == "attendance":
        from edupad.collectors import attendance
        return attendance.run(fill=args.fill or args.dry_run, dry_run=args.dry_run)
    if args.command == "convert":
        from edupad.processing import convert
        return convert.run(force=args.force)
    if args.command == "corpus":
        from edupad.processing import corpus
        return corpus.run()
    if args.command == "summarize":
        from edupad.processing import summaries
        return summaries.run(force=args.force)
    if args.command == "index":
        from edupad.processing import index
        return index.run(force=args.force)
    if args.command == "ask":
        return _ask(args.question, args.trace, args.detail, args.new, not args.no_memory, args.speak)
    if args.command == "chat":
        return _chat(args.trace, args.detail, args.new, args.speak)
    if args.command == "memory":
        return _memory(args.clear)
    if args.command == "eval":
        from edupad.agent import evaluate
        if args.rejudge:
            evaluate.rejudge(args.rejudge)
            return 0
        if args.compare:
            print(evaluate.compare(args.compare))
            return 0
        evaluate.run(args.label, args.case, args.repeat, use_judge=not args.no_judge,
                     use_memory=not args.no_memory, with_detail=args.detail,
                     summaries=not args.no_summaries)
        return 0
    if args.command == "keepalive":
        from edupad.jobs import keepalive
        return keepalive.run()
    from edupad.jobs import pipeline
    return pipeline.run()
