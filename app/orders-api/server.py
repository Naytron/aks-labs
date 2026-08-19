#!/usr/bin/env python3
import hashlib
import json
import logging
import os
import signal
import sqlite3
import threading
import time
import uuid
from contextlib import closing
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PORT = int(os.getenv("PORT", "8080"))
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
DATABASE_PATH = DATA_DIR / "orders.db"
APP_MESSAGE = os.getenv("APP_MESSAGE", "orders-api")
SECRET_PATH = Path(os.getenv("SECRET_PATH", "/mnt/secrets-store/course-api-key"))
FAIL_READINESS = os.getenv("FAIL_READINESS", "false").lower() == "true"
STARTUP_DELAY_SECONDS = max(0, int(os.getenv("STARTUP_DELAY_SECONDS", "0")))
MAX_BODY_BYTES = 1024 * 1024

started_at = time.time()
ready_at = started_at + STARTUP_DELAY_SECONDS
metrics_lock = threading.Lock()
metrics = {
    "requests_total": 0,
    "orders_created_total": 0,
    "errors_total": 0,
}

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")
logger = logging.getLogger("orders-api")


def log_event(event: str, **fields: object) -> None:
    logger.info(json.dumps({"service": "orders-api", "event": event, **fields}, sort_keys=True))


def initialize_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    item TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )


def increment(metric: str) -> None:
    with metrics_lock:
        metrics[metric] += 1


def read_secret_state() -> dict[str, object]:
    if not SECRET_PATH.is_file():
        return {"mounted": False}
    digest = hashlib.sha256(SECRET_PATH.read_bytes()).hexdigest()[:12]
    return {"mounted": True, "sha256Prefix": digest}


class OrdersHandler(BaseHTTPRequestHandler):
    server_version = "aks-labs-orders-api"

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, status: HTTPStatus, payload: object) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, object]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0 or content_length > MAX_BODY_BYTES:
            raise ValueError("request body must be between 1 byte and 1 MiB")
        payload = json.loads(self.rfile.read(content_length))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def do_GET(self) -> None:
        increment("requests_total")
        path = urlparse(self.path).path
        if path == "/healthz":
            self._send_json(HTTPStatus.OK, {"status": "alive"})
            return
        if path == "/readyz":
            ready = not FAIL_READINESS and time.time() >= ready_at and DATABASE_PATH.is_file()
            status = HTTPStatus.OK if ready else HTTPStatus.SERVICE_UNAVAILABLE
            self._send_json(status, {"status": "ready" if ready else "not-ready"})
            return
        if path == "/metrics":
            self._send_metrics()
            return
        if path == "/api/config":
            self._send_json(
                HTTPStatus.OK,
                {
                    "message": APP_MESSAGE,
                    "database": str(DATABASE_PATH),
                    "secret": read_secret_state(),
                    "uptimeSeconds": round(time.time() - started_at, 3),
                },
            )
            return
        if path == "/api/orders":
            with closing(sqlite3.connect(DATABASE_PATH)) as connection:
                rows = connection.execute(
                    "SELECT id, item, quantity, created_at FROM orders ORDER BY created_at DESC LIMIT 100"
                ).fetchall()
            self._send_json(
                HTTPStatus.OK,
                [
                    {"id": row[0], "item": row[1], "quantity": row[2], "createdAt": row[3]}
                    for row in rows
                ],
            )
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        increment("requests_total")
        if urlparse(self.path).path != "/api/orders":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            payload = self._read_json()
            item = str(payload.get("item", "")).strip()
            quantity = int(payload.get("quantity", 0))
            if not item or len(item) > 100:
                raise ValueError("item must be 1-100 characters")
            if quantity < 1 or quantity > 100:
                raise ValueError("quantity must be 1-100")
            order = {
                "id": str(uuid.uuid4()),
                "item": item,
                "quantity": quantity,
                "createdAt": int(time.time()),
            }
            with closing(sqlite3.connect(DATABASE_PATH)) as connection:
                with connection:
                    connection.execute(
                        "INSERT INTO orders (id, item, quantity, created_at) VALUES (?, ?, ?, ?)",
                        (order["id"], order["item"], order["quantity"], order["createdAt"]),
                    )
            increment("orders_created_total")
            log_event("order_created", order_id=order["id"], quantity=quantity)
            self._send_json(HTTPStatus.CREATED, order)
        except (ValueError, json.JSONDecodeError) as error:
            increment("errors_total")
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except sqlite3.Error:
            increment("errors_total")
            log_event("database_error")
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "database operation failed"})

    def _send_metrics(self) -> None:
        with metrics_lock:
            snapshot = dict(metrics)
        lines = [
            "# HELP orders_api_requests_total HTTP requests received.",
            "# TYPE orders_api_requests_total counter",
            f"orders_api_requests_total {snapshot['requests_total']}",
            "# HELP orders_api_orders_created_total Orders accepted.",
            "# TYPE orders_api_orders_created_total counter",
            f"orders_api_orders_created_total {snapshot['orders_created_total']}",
            "# HELP orders_api_errors_total Request or storage errors.",
            "# TYPE orders_api_errors_total counter",
            f"orders_api_errors_total {snapshot['errors_total']}",
            "# HELP orders_api_uptime_seconds Process uptime.",
            "# TYPE orders_api_uptime_seconds gauge",
            f"orders_api_uptime_seconds {time.time() - started_at:.3f}",
            "",
        ]
        body = "\n".join(lines).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    initialize_database()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), OrdersHandler)

    def shutdown(signum: int, _frame: object) -> None:
        log_event("shutdown", signal=signum)
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    log_event("started", port=PORT, database=str(DATABASE_PATH))
    server.serve_forever(poll_interval=0.25)
    server.server_close()


if __name__ == "__main__":
    main()
