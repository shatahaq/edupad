from edupad.agent import formatting as fmt


def test_clean_speech_removes_markdown_code_and_urls():
    text = ("## WBS\n**WBS** adalah *pemecahan* proyek 🎯.\n\n```vb\nDim x As Integer\n```\n"
            "- poin satu\n- poin dua\nLihat [slide](https://kelas.usu.ac.id/x) — selesai.")
    speech = fmt.clean_speech(text)
    for bad in ("#", "*", "`", "Dim x", "http", "🎯", "—"):
        assert bad not in speech
    assert "WBS adalah pemecahan proyek" in speech
    assert "poin satu. poin dua" in speech


def test_clean_speech_cuts_at_sentence_end():
    speech = fmt.clean_speech("Kalimat pertama cukup panjang. " * 30)
    assert len(speech) <= fmt.MAX_SPEECH_CHARS
    assert speech.endswith(".")


def test_fit_screen_wraps_and_limits_lines():
    screen = fmt.fit_screen("Work Breakdown Structure (WBS) lengkap",
                            ["**100% rule**: semua pekerjaan tercakup tanpa kurang atau lebih", "≥ 5 porsi → diskon"]
                            + [f"poin {i}" for i in range(20)])
    assert screen["title"] == "Work Breakdown Structure (WBS) lengkap"
    assert screen["title_size"] == "normal"
    assert fmt.fit_screen("WBS", [])["title_size"] == "large"
    long_title = fmt.fit_screen("Validasi input angka menggunakan TryParse di Visual Basic", [])["title"]
    assert len(long_title) <= fmt.SCREEN_COLS and long_title.endswith("...")
    assert len(screen["lines"]) == fmt.SCREEN_MAX_LINES
    assert all(len(line) <= fmt.SCREEN_COLS for line in screen["lines"])
    assert all(line.isascii() for line in [screen["title"], *screen["lines"]])
    assert screen["lines"][0].startswith("- 100% rule: semua")
    assert ">= 5 porsi -> diskon" in " ".join(screen["lines"])


def test_fallback_answer_builds_all_forms():
    answer = fmt.fallback_answer("# Percabangan\nIf Then Else dipakai untuk memilih aksi.")
    assert answer["screen"]["title"] == "Percabangan"
    assert answer["speech"].startswith("Percabangan")
    assert answer["detail"].startswith("# Percabangan")
