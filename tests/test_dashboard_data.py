import json

from edupad.office import dashboard_data


def test_assignments_maps_existing_edupad_shape(tmp_path, monkeypatch):
    folder = tmp_path / "assignments"
    folder.mkdir()
    (folder / "assignments.json").write_text(
        json.dumps(
            {
                "diperbarui": "2026-10-14T10:00:00+07:00",
                "tugas": [
                    {
                        "cmid": "42",
                        "jenis": "tugas",
                        "judul": "Latihan",
                        "matkul": "[TIF 3 031] Pemrograman Visual - Kelas 5/B",
                        "status": {"penilaian": "belum_dinilai", "nilai": None},
                        "sudah_dikumpulkan": False,
                        "lewat_deadline": True,
                        "deskripsi": "Buat aplikasi sederhana.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(dashboard_data, "ASSIGNMENTS_DIR", folder)

    result = dashboard_data.assignments()

    assert result["source"] == "local"
    assert result["tasks"][0]["course"] == "Pemrograman Visual"
    assert result["tasks"][0]["kode"] == "TIF 3 031"
    assert result["tasks"][0]["overdue"] is True


def test_schedule_uses_local_schedule_file(tmp_path, monkeypatch):
    folder = tmp_path / "schedule"
    folder.mkdir()
    (folder / "schedule.json").write_text(
        json.dumps(
            {
                "diperbarui": "2026-10-14T10:00:00+07:00",
                "kelas": [
                    {
                        "hari": "senin",
                        "mulai": "08:00",
                        "selesai": "09:40",
                        "kode": "TIF 3 031",
                        "matkul": "Pemrograman Visual",
                        "jenis": "teori",
                        "kelas": "5/B",
                        "sks": 2,
                        "ruang": "I01",
                        "nama_ruang": "Kelas",
                        "dosen": ["Dosen"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(dashboard_data, "SCHEDULE_DIR", folder)

    result = dashboard_data.schedule()

    assert result["classes"][0]["course"] == "Pemrograman Visual"
    assert result["classes"][0]["hari"] == "senin"


def test_unknown_dashboard_panel_is_rejected():
    try:
        dashboard_data.panel("tidak-ada")
    except KeyError as exc:
        assert "tidak dikenal" in str(exc)
    else:
        raise AssertionError("panel yang tidak dikenal seharusnya ditolak")
