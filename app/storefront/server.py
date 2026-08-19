#!/usr/bin/env python3
import json
import logging
import os
import signal
import threading
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PORT = int(os.getenv("PORT", "8080"))
ORDERS_API_URL = os.getenv("ORDERS_API_URL", "http://orders-api:8080").rstrip("/")
CPU_BURN_MS = max(0, min(250, int(os.getenv("CPU_BURN_MS", "0"))))
INDEX_PATH = Path(__file__).with_name("index.html")
MAX_BODY_BYTES = 1024 * 1024
started_at = time.time()
request_count = 0
request_lock = threading.Lock()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")
logger = logging.getLogger("storefront")


def increment_requests() -> None:
    global request_count
    with request_lock:
        request_count += 1


def burn_cpu() -> None:
    if CPU_BURN_MS == 0:
        return
    deadline = time.perf_counter() + (CPU_BURN_MS / 1000)
    value = 1
    while time.perf_counter() < deadline:
        value = (value * 48271) % 2147483647


class StorefrontHandler(BaseHTTPRequestHandler):
    server_version = "aks-labs-storefront"

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        increment_requests()
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send(HTTPStatus.OK, INDEX_PATH.read_bytes(), "text/html; charset=utf-8")
            return
        if path == "/healthz":
            self._send(HTTPStatus.OK, b'{"status":"alive"}', "application/json")
            return
        if path == "/readyz":
            try:
                with urllib.request.urlopen(f"{ORDERS_API_URL}/readyz", timeout=2) as response:
                    ready = response.status == 200
            except (urllib.error.URLError, TimeoutError):
                ready = False
            status = HTTPStatus.OK if ready else HTTPStatus.SERVICE_UNAVAILABLE
            body = b'{"status":"ready"}' if ready else b'{"status":"dependency-unavailable"}'
            self._send(status, body, "application/json")
            return
        if path == "/metrics":
            with request_lock:
                count = request_count
            body = (
                "# HELP storefront_requests_total HTTP requests received.\n"
                "# TYPE storefront_requests_total counter\n"
                f"storefront_requests_total {count}\n"
                "# HELP storefront_uptime_seconds Process uptime.\n"
                "# TYPE storefront_uptime_seconds gauge\n"
                f"storefront_uptime_seconds {time.time() - started_at:.3f}\n"
            ).encode()
            self._send(HTTPStatus.OK, body, "text/plain; version=0.0.4")
            return
        if path.startswith("/api/"):
            self._proxy("GET")
            return
        self._send(HTTPStatus.NOT_FOUND, b'{"error":"not found"}', "application/json")

    def do_POST(self) -> None:
        increment_requests()
        if not urlparse(self.path).path.startswith("/api/"):
            self._send(HTTPStatus.NOT_FOUND, b'{"error":"not found"}', "application/json")
            return
        self._proxy("POST")

    def _proxy(self, method: str) -> None:
        burn_cpu()
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY_BYTES:
            self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, b'{"error":"body too large"}', "application/json")
            return
        body = self.rfile.read(length) if length else None
        request = urllib.request.Request(
            f"{ORDERS_API_URL}{self.path}",
            data=body,
            method=method,
            headers={"Content-Type": self.headers.get("Content-Type", "application/json")},
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                self._send(HTTPStatus(response.status), response.read(), response.headers.get_content_type())
        except urllib.error.HTTPError as error:
            self._send(HTTPStatus(error.code), error.read(), "application/json")
        except (urllib.error.URLError, TimeoutError) as error:
            logger.error(json.dumps({"service": "storefront", "event": "proxy_error", "error": str(error)}))
            self._send(HTTPStatus.BAD_GATEWAY, b'{"error":"orders api unavailable"}', "application/json")


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), StorefrontHandler)

    def shutdown(_signum: int, _frame: object) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    logger.info(json.dumps({"service": "storefront", "event": "started", "port": PORT}))
    server.serve_forever(poll_interval=0.25)
    server.server_close()


if __name__ == "__main__":
    main()
