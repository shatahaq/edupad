import requests

from edupad.core.session import load_cookies, persist_cookie_updates, save_cookies


def _cookie(name: str, value: str) -> dict:
    return {"name": name, "value": value, "domain": "satu.usu.ac.id", "path": "/",
            "expires": -1, "httpOnly": True, "secure": True, "sameSite": "Lax"}


def test_persist_cookie_updates_tracks_changed_added_and_removed(tmp_path):
    path = tmp_path / "session.json"
    save_cookies(path, [_cookie("token.0", "a"), _cookie("token.1", "b")], "UA")

    http = requests.Session()
    for c in load_cookies(path)["cookies"]:
        http.cookies.set(c["name"], c["value"], domain=c["domain"], path=c["path"])
    # server memperbarui token: chunk 0 berubah, chunk 1 dihapus, chunk 2 baru
    http.cookies.set("token.0", "a2", domain="satu.usu.ac.id", path="/")
    http.cookies.clear("satu.usu.ac.id", "/", "token.1")
    http.cookies.set("token.2", "c", domain="satu.usu.ac.id", path="/")

    persist_cookie_updates(path, http)
    saved = {c["name"]: c["value"] for c in load_cookies(path)["cookies"]}
    assert saved == {"token.0": "a2", "token.2": "c"}
    assert load_cookies(path)["user_agent"] == "UA"
