"""Минимальный HTTP-интерфейс приложения для запуска в Docker.

Отвечает на:
  /health — health-check для конвейера деплоя (CI/CD, Stage 4)
  /disks  — реальный функционал приложения (список дисков)
  /       — статус, включая признак того, что секрет задан через окружение
            (сам секрет никогда не раскрывается)
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __doc__ as DESCRIPTION
from .disks import list_disks

# Секрет приходит только через переменные окружения (Docker env / CI secrets).
APP_SECRET = os.environ.get("APP_SECRET", "")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {"status": "ok"})
        elif self.path == "/":
            self._json(200, {"app": "secfm", "description": DESCRIPTION,
                             "secret_configured": bool(APP_SECRET)})
        elif self.path == "/disks":
            self._json(200, list_disks())
        else:
            self._json(404, {"error": "not found"})

    def log_message(self, fmt: str, *args) -> None:
        print(f"[serve] {self.address_string()} {fmt % args}")


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    with ThreadingHTTPServer(("0.0.0.0", port), Handler) as httpd:
        print(f"[serve] secfm HTTP-сервер: http://0.0.0.0:{port} (/health, /disks)")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
