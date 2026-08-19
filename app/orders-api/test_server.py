import importlib.util
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path


class OrdersApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DATA_DIR"] = cls.temp_dir.name
        os.environ["PORT"] = "0"
        module_path = Path(__file__).with_name("server.py")
        spec = importlib.util.spec_from_file_location("orders_server", module_path)
        assert spec and spec.loader
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.module.initialize_database()
        cls.server = cls.module.ThreadingHTTPServer(("127.0.0.1", 0), cls.module.OrdersHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp_dir.cleanup()

    def request(self, path: str, method: str = "GET", payload: dict | None = None):
        body = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        return urllib.request.urlopen(request, timeout=2)

    def test_health_and_readiness(self) -> None:
        self.assertEqual(self.request("/healthz").status, 200)
        self.assertEqual(self.request("/readyz").status, 200)

    def test_order_round_trip(self) -> None:
        created = self.request("/api/orders", "POST", {"item": "book", "quantity": 2})
        self.assertEqual(created.status, 201)
        orders = json.loads(self.request("/api/orders").read())
        self.assertTrue(any(order["item"] == "book" for order in orders))

    def test_rejects_invalid_order(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as context:
            self.request("/api/orders", "POST", {"item": "", "quantity": 0})
        self.assertEqual(context.exception.code, 400)
        context.exception.close()

    def test_metrics_are_prometheus_text(self) -> None:
        response = self.request("/metrics")
        self.assertIn(b"orders_api_requests_total", response.read())


if __name__ == "__main__":
    unittest.main()
