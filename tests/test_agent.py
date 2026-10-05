from edupad.agent import tools
from edupad.processing import index

CATALOG = [
    {"course_id": "38408", "matkul": "Pemrograman Visual", "kode": "TIF 3 031",
     "alias": ["pemrograman visual", "pv", "tif 3 031", "tif3031"], "pertemuan": {"5": {}}},
    {"course_id": "38415", "matkul": "Praktikum Pemrograman Visual", "kode": "TIF 3 031 P",
     "alias": ["prak pemrograman visual", "prak pv", "praktikum pemrograman visual", "praktikum pv"],
     "pertemuan": {}},
]


def test_resolve_course_prefers_theory_class(monkeypatch):
    monkeypatch.setattr(tools, "_catalog", lambda: CATALOG)
    assert tools.resolve_course("PV")["course_id"] == "38408"
    assert tools.resolve_course("pemrograman visual")["course_id"] == "38408"
    assert tools.resolve_course("Praktikum PV")["course_id"] == "38415"
    assert tools.resolve_course("prak pemrograman")["course_id"] == "38415"
    assert tools.resolve_course("38415")["course_id"] == "38415"
    assert tools.resolve_course("basis data") is None


def test_keyword_query_drops_stopwords():
    assert tools._keyword_query("Apa itu materi percabangan If-Else di VB?") == "percabangan | if | else | vb"


def test_content_hash_changes_with_text():
    chunk = {"teks_embedding": "a"}
    assert index.content_hash(chunk) == index.content_hash({"teks_embedding": "a"})
    assert index.content_hash(chunk) != index.content_hash({"teks_embedding": "b"})
