"""Тесты HTTP-интерфейса serve.py (используется на Stage 4 Deploy)."""
import json
import threading
import urllib.request
from contextlib import contextmanager

from FileManager.serve import Handler
from http.server import ThreadingHTTPServer


@contextmanager
def _server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        thread.join()


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=3) as resp:
        assert resp.status == 200
        return json.loads(resp.read().decode())


def test_health_endpoint():
    with _server() as base:
        assert _get(base + "/health") == {"status": "ok"}


def test_root_shows_secret_flag_without_leaking(monkeypatch):
    monkeypatch.setattr("FileManager.serve.APP_SECRET", "super-secret")
    with _server() as base:
        payload = _get(base + "/")
    assert payload["secret_configured"] is True
    assert "super-secret" not in json.dumps(payload)


def test_unknown_path_404():
    with _server() as base:
        try:
            urllib.request.urlopen(base + "/nope", timeout=3)
            raised = False
        except urllib.error.HTTPError as e:
            raised = e.code == 404
        assert raised
