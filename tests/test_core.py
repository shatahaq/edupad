from edupad.core.academic import course_class, meeting_number
from edupad.core.files import safe_filename, safe_name
from edupad.core.markdown import clean_markdown


def test_safe_name_windows_rules():
    assert safe_name("  Pertemuan 1:  Pengantar...  ") == "Pertemuan 1_ Pengantar"
    assert safe_name("CON") == "_CON"
    assert safe_name("") == "untitled"


def test_safe_filename_keeps_extension():
    name = safe_filename("Materi Kuliah Yang Sangat Panjang Sekali Sampai Melebihi Batas Enam Puluh.PDF")
    assert name.endswith(".pdf")
    assert len(name) <= 60


def test_meeting_number():
    assert meeting_number("Pertemuan 5-Percabangan If-Else", 7) == 5
    assert meeting_number("03 - Monitoring Kapasitas", 3) == 3
    assert meeting_number("Database Engine and Architecture", 2) == 2
    assert meeting_number("General", 0) is None


def test_course_class():
    assert course_class("[TIF 3 031 P] Praktikum Pemrograman Visual - Kelas 5/B1") == "B"
    assert course_class("Praktek Kerja Lapangan") is None


def test_clean_markdown_removes_ocr_noise():
    raw = "# **Judul**\n\n回興<sup>国</sup>\n\n×\n\nIsi<br>baris dua\n\n\n\n~~O~~"
    assert clean_markdown(raw) == "# Judul\n\nIsi\nbaris dua"


def test_wait_for_lock_waits_then_times_out(tmp_path):
    import pytest

    from edupad.core.lock import AlreadyRunning, acquire_lock, release_lock, wait_for_lock

    path = tmp_path / "satu.lock"
    fd = acquire_lock(path)
    with pytest.raises(AlreadyRunning), wait_for_lock(path, timeout=0.3, poll=0.1):
        pass
    release_lock(fd)
    with wait_for_lock(path, timeout=0.3, poll=0.1):
        pass
    with wait_for_lock(path, timeout=0.3, poll=0.1):  # dilepas setelah blok sebelumnya
        pass
