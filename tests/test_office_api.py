import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from tests.test_tutor_finance import Db  # noqa: E402

from edupad.agent import finance  # noqa: E402
from edupad.google.accounts import AccountStore, SessionStore  # noqa: E402
from edupad.office import api, auth  # noqa: E402
from edupad.voice import mode as voice_mode  # noqa: E402

OWNER = "pemilik@usu.ac.id"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EDUPAD_OWNER_EMAILS", OWNER)
    monkeypatch.setenv("EDUPAD_PUBLIC_URL", "https://edupad.ai.id")
    monkeypatch.delenv("EDUPAD_OFFICE_AUTH", raising=False)
    accounts = AccountStore(tmp_path / "accounts.json", tmp_path / "accounts.lock")
    sessions = SessionStore(tmp_path / "sessions.json", tmp_path / "accounts.lock")
    monkeypatch.setattr(auth, "AccountStore", lambda: accounts)
    monkeypatch.setattr(auth, "SessionStore", lambda: sessions)
    fake = Db()
    real_init = finance.FinanceStore.__init__
    monkeypatch.setattr(
        finance.FinanceStore,
        "__init__",
        lambda self, user_id=None, db=None: real_init(self, user_id or "default", fake),
    )
    test_client = TestClient(api.create_app())
    test_client.accounts, test_client.sessions, test_client.db = accounts, sessions, fake
    return test_client


def _login(client, email: str, sub: str) -> None:
    import json

    path = client.accounts.path
    data = json.loads(path.read_text()) if path.exists() else {}
    data[sub] = {"sub": sub, "email": email, "name": "Mahasiswa"}
    path.write_text(json.dumps(data))
    client.cookies.set(auth.SESSION_COOKIE, client.sessions.create(sub))


def test_health_is_public_but_data_needs_owner_login(client):
    assert client.get("/api/office/health").status_code == 200
    assert client.get("/v1/dashboard/schedule").status_code == 401
    _login(client, "orang.lain@gmail.com", "g2")
    assert client.get("/v1/dashboard/schedule").status_code == 403
    _login(client, OWNER, "g1")
    assert client.get("/v1/dashboard/schedule").status_code == 200
    assert client.get("/v1/dashboard/tidak-ada").status_code == 404


def test_writes_reject_other_origins(client):
    _login(client, OWNER, "g1")
    body = {"kind": "expense", "amount": 15000, "category": "Makan"}
    evil = client.post(
        "/api/office/finance/transactions", json=body, headers={"Origin": "https://evil.example"}
    )
    assert evil.status_code == 403
    ok = client.post(
        "/api/office/finance/transactions", json=body, headers={"Origin": "https://edupad.ai.id"}
    )
    assert ok.status_code == 201 and ok.json()["source"] == "dashboard"


def test_finance_endpoints_share_the_agent_ledger(client):
    _login(client, OWNER, "g1")
    assert (
        client.put("/api/office/finance/budgets/Makan", json={"amount": 300000}).status_code == 200
    )
    imported = client.post(
        "/api/office/finance/import",
        json={
            "transactions": [
                {"kind": "income", "amount": 500000, "category": "Beasiswa", "date": "2026-10-01"}
            ],
            "budgets": {"Transportasi": 100000},
        },
    )
    assert imported.json() == {"transactions": 1, "budgets": 1}
    finance.record_transaction("pengeluaran", 20000, "Makan")  # dari perangkat (suara)
    data = client.get("/v1/dashboard/finance").json()
    assert data["available"] and data["budgets"] == {"Makan": 300000, "Transportasi": 100000}
    assert sorted(t["source"] for t in data["transactions"]) == ["impor", "suara"]
    voice = next(t for t in data["transactions"] if t["source"] == "suara")
    assert client.delete(f"/api/office/finance/transactions/{voice['id']}").status_code == 204
    assert len(client.get("/v1/dashboard/finance").json()["transactions"]) == 1
    bad = client.post(
        "/api/office/finance/transactions",
        json={"kind": "expense", "amount": 0, "category": "Makan"},
    )
    assert bad.status_code == 422


def test_auth_can_be_disabled_for_local_development(client, monkeypatch):
    monkeypatch.setenv("EDUPAD_OFFICE_AUTH", "off")
    assert client.get("/api/office/snapshot").status_code == 200


def test_api_health_and_devices_come_from_real_device_traffic(tmp_path, monkeypatch):
    from datetime import datetime, timedelta

    from edupad import device_status
    from edupad.config import WIB
    from edupad.office import dashboard_data

    now = datetime.now(WIB) - timedelta(minutes=5)
    stamp = now.strftime("%Y-%m-%d %H:%M:%S,000")
    (tmp_path / "serve.log").write_text(
        "\n".join(
            [
                f"{stamp} INFO [device] 'Apa itu SQL?' -> 'SQL adalah' {{'stt': 0.5, 'agent': 3.0}}",
                f'{stamp} INFO 127.0.0.1 "POST /v1/ask HTTP/1.1" 200 -',
                f"{stamp} INFO [device] tidak ada ucapan (64000 byte)",
                f'{stamp} INFO 127.0.0.1 "POST /v1/ask HTTP/1.1" 200 -',
                f'{stamp} INFO 127.0.0.1 "POST /v1/ask?new=1 HTTP/1.1" 502 -',
                f'{stamp} INFO 127.0.0.1 "GET /v1/updates HTTP/1.1" 200 -',
            ]
        )
    )
    monkeypatch.setattr(dashboard_data, "LOG_DIR", tmp_path)
    health = dashboard_data.api_health()
    assert health["requests"] == 3
    assert health["by_status"] == {"ok": 1, "no_speech": 1, "client_error": 0, "server_error": 1}
    assert health["latency_avg_s"] == 3.5

    headers = {"X-Device-Id": "AA:BB:CC:DD:EE:FF", "X-Device-RSSI": "-61", "X-Firmware": "1.2"}
    device_status.record(headers, "/v1/updates")
    device_status.record(headers, "/v1/ask", latency_s=4.0)
    [device] = dashboard_data.devices()["devices"]
    assert device["online"] and device["rssi_dbm"] == -61 and device["avg_latency_s"] == 4.0
    assert device["firmware"] == "1.2"


def test_dashboard_switches_voice_mode_for_owner_only(client):
    body = {"enabled": True, "speed": "cepat"}
    assert client.put("/api/office/voice-mode", json=body).status_code == 401
    _login(client, OWNER, "g1")
    response = client.put("/api/office/voice-mode", json=body)
    assert response.status_code == 200 and response.json()["enabled"] is True
    assert voice_mode.load() == {"enabled": True, "speed": "cepat"}
    assert client.put("/api/office/voice-mode", json={"speed": "kilat"}).status_code == 422
    panel = client.get("/v1/dashboard/voice").json()
    assert panel["enabled"] is True and panel["speed"] == "cepat"
