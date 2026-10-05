from edupad.processing.corpus import (
    clean_text,
    course_aliases,
    detect_meetings,
    find_boilerplate,
    make_chunks,
    split_segments,
)


def test_meeting_range_in_content_overrides_section_order():
    meta = {"section": "Konsep Dasar & Siklus Hidup", "section_index": 1, "source_file": "a/MPIT1.pptx"}
    assert detect_meetings(meta, "MANAJEMEN PROYEK TI\nPertemuan 1–2 • Sub-CPMK 1") == [1, 2]


def test_meeting_range_from_filename():
    meta = {"section": "Metode dalam SPK", "section_index": 6, "source_file": "x/6-7 Praktik Metode.pdf"}
    assert detect_meetings(meta, "") == [6, 7]


def test_meeting_explicit_section_wins_over_unrelated_numbers():
    meta = {"section": "Pertemuan 5-Percabangan", "section_index": 5, "source_file": "x/p5.pdf"}
    assert detect_meetings(meta, "tahun 2024-2025") == [5]


def test_aliases_do_not_collide_between_theory_and_lab():
    theory = course_aliases("Manajemen Sistem Basis Data", "TIF 3 030")
    lab = course_aliases("Praktikum Manajemen Sistem Basis Data", "TIF 3 030 P")
    assert "msbd" in theory
    assert "prak msbd" in lab
    assert not set(theory) & set(lab)


def test_aliases_keep_uppercase_abbreviation():
    assert "mpit" in course_aliases("Manajemen Proyek IT", "TIF 3 035")


def _slides(n: int) -> str:
    return "".join(f"<!-- slide {i} -->\nLangkah {i}: isi berbeda\nTIK2111 • Pertemuan 1 • {i}/27\n"
                   for i in range(1, n + 1))


def test_footer_with_page_counter_is_removed_but_numbered_content_kept():
    segments = split_segments(_slides(5))
    boilerplate = find_boilerplate(segments)
    cleaned = clean_text(segments[0]["text"], boilerplate)
    assert "TIK2111" not in cleaned
    assert "Langkah 1: isi berbeda" in cleaned


def test_standalone_numbers_merge_into_list():
    assert clean_text("**1**\n\nApa itu proyek\n2\nTriple constraint", set()) == \
        "1. Apa itu proyek\n2. Triple constraint"


def test_chunks_respect_size_and_carry_context():
    segments = [{"kind": "halaman", "number": i, "ocr": i == 2, "text": "kata " * 200}
                for i in range(1, 5)]
    doc = {"course_id": "1", "matkul": "PV", "kode": "TIF", "section": "S", "judul": "J",
           "jenis": "resource", "pertemuan": [5], "source_file": "f", "source_url": "u",
           "sha256": "abc", "juga_di": [], "segments": segments}
    chunks = make_chunks(doc)
    assert len(chunks) == 4
    assert all(c["kata"] <= 550 for c in chunks)
    assert chunks[1]["ocr"] and chunks[1]["lokasi"] == "halaman 2"
    assert chunks[0]["teks_embedding"].startswith("PV | Pertemuan 5 | S")
