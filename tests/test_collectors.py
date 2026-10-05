from bs4 import BeautifulSoup

from edupad.collectors.assignments import parse_assign, parse_moodle_date, summarize
from edupad.collectors.materials import file_key, filename_from_url, is_login_page


def test_file_key_ignores_revision_number():
    old = "https://kelas.usu.ac.id/pluginfile.php/123/mod_resource/content/3/a.pdf"
    new = "https://kelas.usu.ac.id/pluginfile.php/123/mod_resource/content/7/a.pdf?forcedownload=1"
    assert file_key(old) == file_key(new)


def test_filename_from_url_decodes():
    url = "https://kelas.usu.ac.id/pluginfile.php/1/mod_resource/content/1/Materi%20Pertemuan%201.pdf"
    assert filename_from_url(url) == "Materi Pertemuan 1.pdf"


def test_login_page_detection():
    assert is_login_page("https://sso.usu.ac.id/login")
    assert not is_login_page("https://kelas.usu.ac.id/my/courses.php")


SUBMITTED = """
<table class="generaltable">
 <tr><th>Submission status</th><td class="submissionstatussubmitted">Submitted for grading</td></tr>
 <tr><th>Grading status</th><td class="submissionnotgraded">Not graded</td></tr>
 <tr><th>Time remaining</th><td class="earlysubmission">submitted 1 hour early</td></tr>
 <tr><th>File submissions</th><td><a href="x/assignsubmission_file/1/tugas.pdf">tugas.pdf</a></td></tr>
</table>"""

NOT_SUBMITTED = """
<table class="generaltable">
 <tr><th>Submission status</th><td>No submissions have been made yet</td></tr>
 <tr><th>Time remaining</th><td class="overdue">Assignment is overdue by: 2 days</td></tr>
</table>"""


def test_parse_submitted_assignment():
    status = parse_assign(BeautifulSoup(SUBMITTED, "html.parser"))
    assert status["pengumpulan"] == "submitted"
    assert status["penilaian"] == "belum_dinilai"
    assert status["waktu"] == "tepat_waktu"
    assert status["file_dikumpulkan"] == ["tugas.pdf"]


def test_unsubmitted_overdue_assignment_summary():
    task = {"module": "assign", "deadline_ts": 100,
            "status": parse_assign(BeautifulSoup(NOT_SUBMITTED, "html.parser"))}
    summarize(task, now=200)
    assert task["sudah_dikumpulkan"] is False
    assert task["status_ringkas"] == "BELUM dikumpulkan — LEWAT DEADLINE"


def test_parse_moodle_date():
    assert parse_moodle_date("Tuesday, 15 September 2026, 11:30 AM") is not None
    assert parse_moodle_date("bukan tanggal") is None
