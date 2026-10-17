import json

import pytest

from edupad.processing import convert


def _meta(name: str) -> dict:
    return {
        "course_id": "1",
        "course": "Basis Data",
        "pertemuan": 1,
        "section": "Pertemuan 1",
        "section_index": 1,
        "title": name,
        "type": "resource",
        "activity_url": "https://kelas.usu.ac.id/mod/resource/view.php?id=1",
        "source_file": f"1_Basis Data/01_Pertemuan 1/{name}.pdf",
        "source_url": f"https://kelas.usu.ac.id/{name}.pdf",
        "sha256": name,
    }


@pytest.fixture
def materials(monkeypatch, tmp_path):
    """Tiga materi palsu; kembalikan daftar file yang benar-benar dikonversi."""
    metas = [_meta(n) for n in ("a", "b", "c")]
    for m in metas:
        source = tmp_path / "materials" / m["source_file"]
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"%PDF")
    monkeypatch.setattr(convert, "MATERIALS_DIR", tmp_path / "materials")
    monkeypatch.setattr(convert, "MARKDOWN_DIR", tmp_path / "markdown")
    monkeypatch.setattr(convert, "INDEX_FILE", tmp_path / "markdown" / "index.json")
    monkeypatch.setattr(
        convert, "read_json", lambda p: json.loads(p.read_text()) if p.exists() else {}
    )
    monkeypatch.setattr(convert, "write_json", lambda p, d: p.write_text(json.dumps(d)))
    monkeypatch.setattr(convert, "iter_sources", lambda _: iter(metas))
    monkeypatch.setattr(convert, "MANIFEST_FILE", tmp_path / "manifest.json")
    (tmp_path / "manifest.json").write_text(json.dumps({"courses": {"1": {}}}))
    return []


def test_killed_run_resumes_instead_of_starting_over(materials, monkeypatch):
    """Server mematikan convert (OOM) di file kedua: run berikutnya tidak mengulang file pertama."""

    def killed_on_b(path):
        if path.stem == "b":
            raise SystemExit(-9)  # bukan Exception: tidak ditangkap, seperti proses dibunuh
        materials.append(path.stem)
        return "isi materi", "pymupdf4llm"

    monkeypatch.setattr(convert, "convert_file", killed_on_b)
    with pytest.raises(SystemExit):
        convert.run()
    assert materials == ["a"]

    def works(path):
        materials.append(path.stem)
        return "isi materi", "pymupdf4llm"

    monkeypatch.setattr(convert, "convert_file", works)
    assert convert.run() == 0
    assert materials == ["a", "b", "c"]


def test_pdf_in_child_process_matches_direct_conversion(tmp_path):
    import pymupdf

    path = tmp_path / "materi.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        text = "Normalisasi basis data mengurangi redundansi dan anomali data. " * 6
        page.insert_textbox(pymupdf.Rect(40, 40, 560, 800), text)
        doc.save(path)
    assert convert.pdf_to_markdown_isolated(path) == convert.pdf_to_markdown(path)
    assert "Normalisasi" in convert.pdf_to_markdown_isolated(path)[0]


@pytest.mark.parametrize("target", ["slides/slide1.xml", "/ppt/slides/slide1.xml"])
def test_pptx_slide_targets_relative_or_absolute(tmp_path, target):
    """PowerPoint menulis target relatif; aplikasi lain (mis. ekspor Google Slides) absolut."""
    import zipfile

    p = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
    a = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
    r = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    path = tmp_path / "RPL_Pertemuan_04.pptx"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "ppt/presentation.xml",
            f'<p:presentation {p} {r}><p:sldIdLst><p:sldId id="256" r:id="rId2"/>'
            "</p:sldIdLst></p:presentation>",
        )
        z.writestr(
            "ppt/_rels/presentation.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId2" Type="slide" Target="{target}"/></Relationships>',
        )
        z.writestr(
            "ppt/slides/slide1.xml",
            f"<p:sld {p} {a}><p:cSld><p:spTree><p:sp><p:nvSpPr><p:nvPr>"
            '<p:ph type="title"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>Agile dan Scrum'
            "</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>",
        )
    md, converter = convert.pptx_to_markdown(path)
    assert "## Agile dan Scrum" in md and converter == "pptx-slide"
