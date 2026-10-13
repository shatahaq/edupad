import http.client
import json
import threading
from concurrent.futures import Future
from dataclasses import replace

import pytest

from edupad import cli
from edupad import server as srv
from edupad.agent.assistant import LLMError
from edupad.agent.formatting import fit_screen
from edupad.config import get_settings

TOKEN = "rahasia-perangkat"
PCM = b"\x01\x00" * 1600


class FakeAgent:
    def __init__(self):
        self.asked, self.prepared = [], []

    def prepare(self, new_session):
        self.prepared.append(new_session)
        future = Future()
        future.set_result(new_session)
        return future

    def answer(self, question, prepared):
        self.asked.append((question, prepared.result()))
        if question == "llm mati":
            raise LLMError("HTTP 503: sibuk")
        if question == "bug":
            raise KeyError("choices")
        return {
            "speech": "" if question == "diam" else f"Jawaban: {question}",
            "screen": fit_screen("PV", ["If-Else"]),
        }

    def close(self):
        pass


@pytest.fixture
def server():
    agent = FakeAgent()
    server = srv.EduPadServer(("127.0.0.1", 0), TOKEN, agent=agent)
    server.asked = agent.asked
    threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
    ).start()
    yield server
    server.shutdown()
    server.server_close()


def connect(server):
    return http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)


def request(server, method, path, body=None, headers=None, token=TOKEN, conn=None):
    own = conn is None
    conn = conn or connect(server)
    conn.request(
        method,
        path,
        body=body,
        headers={**({"Authorization": f"Bearer {token}"} if token else {}), **(headers or {})},
    )
    response = conn.getresponse()
    data = response.read()
    if own:
        conn.close()
    return response, data


def ask_json(server, text, path="/v1/ask", **kw):
    response, data = request(
        server, "POST", path, json.dumps({"text": text}), {"Content-Type": "application/json"}, **kw
    )
    return response.status, json.loads(data)


@pytest.fixture
def fake_stt(monkeypatch):
    received = []

    def transcribe_pcm(pcm):
        received.append(("pcm", pcm))
        return "" if set(pcm) <= {0} else "PV pertemuan 5"

    monkeypatch.setattr(srv.stt, "transcribe_pcm", transcribe_pcm)
    monkeypatch.setattr(
        srv.stt, "transcribe_file", lambda audio, name: received.append((name, audio)) or "dari wav"
    )
    return received


@pytest.fixture
def fake_tts(monkeypatch):
    calls = []

    def stream(text):
        calls.append(text)
        yield from (b"\x01", b"\x02\x03", b"\x04\x05")  # potongan ganjil, total 5 byte

    monkeypatch.setattr(srv.tts, "stream", stream)
    return calls


def test_health_needs_no_token(server):
    response, data = request(server, "GET", "/v1/health", token=None)
    assert response.status == 200 and json.loads(data) == {"status": "ok"}


def test_requests_without_valid_token_are_rejected(server, fake_tts):
    for token in (None, "salah"):
        status, body = ask_json(server, "halo", token=token)
        assert status == 401 and body["status"] == "error" and body["screen"]["lines"]
        response, _ = request(server, "GET", "/v1/audio/apa", token=token)
        assert response.status == 401
    assert server.asked == [] and fake_tts == []


def test_text_question_answers_with_screen_and_audio_url(server):
    status, body = ask_json(server, " PV pertemuan 5? ")
    assert status == 200 and body["status"] == "ok"
    assert body["question"] == "PV pertemuan 5?" and body["speech"] == "Jawaban: PV pertemuan 5?"
    assert body["screen"] == fit_screen("PV", ["If-Else"])
    assert body["audio_url"].startswith("/v1/audio/") and "agent" in body["timing"]
    ask_json(server, "lagi", path="/v1/ask?new=1")
    assert server.asked == [("PV pertemuan 5?", False), ("lagi", True)]


def test_empty_speech_has_no_audio(server):
    assert ask_json(server, "diam")[1]["audio_url"] is None


def test_pcm_upload_plain_and_chunked_reach_stt_unchanged(server, fake_stt):
    response, data = request(
        server, "POST", "/v1/ask", PCM, {"Content-Type": "application/octet-stream"}
    )
    assert response.status == 200 and json.loads(data)["question"] == "PV pertemuan 5"
    chunks = [PCM[:1000], PCM[1000:1001], PCM[1001:]]  # dikirim sambil merekam
    response, data = request(server, "POST", "/v1/ask", iter(chunks))
    assert response.status == 200 and "stt" in json.loads(data)["timing"]
    assert fake_stt == [("pcm", PCM), ("pcm", PCM)]
    assert server.asked == [("PV pertemuan 5", False)] * 2


def test_wav_upload_uses_file_transcription(server, fake_stt):
    response, data = request(server, "POST", "/v1/ask", b"RIFF...", {"Content-Type": "audio/wav"})
    assert json.loads(data)["question"] == "dari wav" and fake_stt == [("audio.wav", b"RIFF...")]


def test_silence_returns_no_speech_without_calling_agent(server, fake_stt):
    response, data = request(server, "POST", "/v1/ask", b"\x00\x00" * 1600)
    body = json.loads(data)
    assert response.status == 200 and body["status"] == "no_speech"
    assert body["audio_url"] is None and body["screen"] == srv.NO_SPEECH_SCREEN
    assert server.asked == []


def test_failures_still_return_error_screen(server, monkeypatch):
    def broken_stt(pcm):
        raise srv.stt.STTError("Groq HTTP 401: Invalid API Key")

    monkeypatch.setattr(srv.stt, "transcribe_pcm", broken_stt)
    response, data = request(server, "POST", "/v1/ask", PCM)
    assert response.status == 502 and "Invalid API Key" in json.loads(data)["error"]
    for text, status, error in (("llm mati", 502, "agent: HTTP 503"), ("bug", 500, "KeyError")):
        code, body = ask_json(server, text)
        assert code == status and error in body["error"] and body["screen"] == srv.ERROR_SCREEN


def test_bad_requests(server, monkeypatch):
    headers = {"Content-Type": "application/json"}
    for body in ("bukan json", "[1, 2]", '{"text": "  "}'):
        response, data = request(server, "POST", "/v1/ask", body, headers)
        assert response.status == 400 and json.loads(data)["status"] == "error"
    assert request(server, "POST", "/v1/lain", "{}", headers)[0].status == 404
    assert request(server, "GET", "/v1/lain")[0].status == 404
    for raw in (
        b"Content-Length: -5\r\n\r\n",
        b"Transfer-Encoding: chunked\r\n\r\n-5\r\n",
        b"Transfer-Encoding: chunked\r\n\r\nzz\r\n",
    ):
        conn = connect(server)
        conn.connect()
        conn.sock.sendall(
            b"POST /v1/ask HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer "
            + TOKEN.encode()
            + b"\r\n"
            + raw
        )
        response = http.client.HTTPResponse(conn.sock)
        response.begin()
        assert response.status == 400  # langsung ditolak, tidak menunggu timeout
        conn.close()
    monkeypatch.setattr(srv, "MAX_BODY_BYTES", 100)
    assert request(server, "POST", "/v1/ask", PCM)[0].status == 413
    assert request(server, "POST", "/v1/ask", iter([PCM[:60], PCM[60:120]]))[0].status == 413
    assert server.asked == []


def test_audio_streams_whole_samples_then_replays_from_cache(server, fake_tts):
    audio_url = ask_json(server, "PV")[1]["audio_url"]
    response, data = request(server, "GET", audio_url)
    assert response.status == 200 and response.getheader("Transfer-Encoding") == "chunked"
    assert response.getheader("X-Audio-Format") == "pcm_s16le;rate=16000;channels=1"
    assert data == b"\x01\x02\x03\x04"  # byte ganjil terakhir dibuang
    response, again = request(server, "GET", audio_url)
    assert again == data and response.getheader("Content-Length") == "4"
    assert fake_tts == ["Jawaban: PV"]


def test_ask_and_audio_share_one_keep_alive_connection(server, fake_tts):
    conn = connect(server)
    response, data = request(
        server,
        "POST",
        "/v1/ask",
        json.dumps({"text": "PV"}),
        {"Content-Type": "application/json"},
        conn=conn,
    )
    _, audio = request(server, "GET", json.loads(data)["audio_url"], conn=conn)
    conn.close()
    assert audio == b"\x01\x02\x03\x04"


def test_audio_as_wav_and_unknown_id(server, fake_tts):
    audio_url = ask_json(server, "PV")[1]["audio_url"]
    response, data = request(server, "GET", audio_url + "?format=wav")
    assert response.getheader("Content-Type") == "audio/wav" and data[:4] == b"RIFF"
    assert request(server, "GET", "/v1/audio/tidak-ada")[0].status == 404


def test_tts_error_before_and_during_audio(server, monkeypatch):
    def quota(text):
        raise srv.tts.TTSError("ElevenLabs HTTP 401: quota_exceeded")
        yield

    def cut(text):
        yield b"\x01\x00" * 10
        raise srv.tts.TTSError("stream ElevenLabs terputus")

    audio_url = ask_json(server, "PV")[1]["audio_url"]
    monkeypatch.setattr(srv.tts, "stream", quota)
    response, data = request(server, "GET", audio_url)
    assert response.status == 502 and "quota_exceeded" in json.loads(data)["error"]
    monkeypatch.setattr(srv.tts, "stream", cut)
    with pytest.raises(http.client.IncompleteRead):
        request(server, "GET", audio_url)
    assert (
        server.audio.get(audio_url.rsplit("/", 1)[1])["pcm"] is None
    )  # audio rusak tidak di-cache


def test_new_answer_replaces_audio_and_latest_replays_without_tts(server, fake_tts):
    assert request(server, "GET", "/v1/audio/latest")[0].status == 404
    first = ask_json(server, "PV")[1]["audio_url"]
    second = ask_json(server, "MSBD")[1]["audio_url"]
    assert request(server, "GET", first)[0].status == 404  # suara lama ditimpa
    _, data = request(server, "GET", "/v1/audio/latest")
    _, again = request(server, "GET", second)
    assert data == again == b"\x01\x02\x03\x04"
    assert fake_tts == ["Jawaban: MSBD"]  # putar ulang tidak memanggil TTS lagi


def test_audio_is_kept_when_device_stops_playback(server, monkeypatch):
    calls, sent_first = [], threading.Event()

    def stream(text):
        calls.append(text)
        yield b"\x01\x00" * 4
        sent_first.wait(5)
        for _ in range(200):  # cukup besar agar penulisan ke soket yang ditutup gagal
            yield b"\x02\x00" * 4096

    monkeypatch.setattr(srv.tts, "stream", stream)
    audio_url = ask_json(server, "PV")[1]["audio_url"]
    conn = connect(server)
    conn.request("GET", audio_url, headers={"Authorization": f"Bearer {TOKEN}"})
    conn.getresponse().read(8)
    conn.close()  # perangkat menghentikan pemutaran
    sent_first.set()
    item = server.audio.get("latest")
    for _ in range(100):
        if item["pcm"] is not None:
            break
        threading.Event().wait(0.05)
    assert len(item["pcm"]) == 8 + 200 * 8192
    _, data = request(server, "GET", "/v1/audio/latest")
    assert data == item["pcm"] and calls == ["Jawaban: PV"]


def test_run_refuses_public_proxy_without_token(monkeypatch):
    settings = replace(get_settings(), device_token=None, public_url="https://shata.id")
    monkeypatch.setattr(srv, "get_settings", lambda: settings)
    assert srv.run("127.0.0.1", 0) == 1  # di belakang Caddy/Cloudflare tetap wajib token
    assert srv.publicly_reachable("127.0.0.1", settings)
    assert not srv.publicly_reachable(
        "127.0.0.1", replace(settings, public_url="http://localhost:5173")
    )


def test_run_refuses_network_access_without_token(monkeypatch):
    monkeypatch.setattr(srv, "get_settings", lambda: replace(get_settings(), device_token=None))
    assert srv.run("0.0.0.0", 0) == 1


def test_cli_serve_routes_host_and_port(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "setup_logging", lambda _: None)
    monkeypatch.setattr(srv, "run", lambda host, port: calls.append((host, port)) or 0)
    assert (
        cli.main(["serve"]) == 0 and cli.main(["serve", "--host", "0.0.0.0", "--port", "9000"]) == 0
    )
    assert calls == [("127.0.0.1", 8000), ("0.0.0.0", 9000)]
