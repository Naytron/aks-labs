import importlib.util
import os
import threading
import unittest
import urllib.request
from pathlib import Path


class StorefrontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["PORT"] = "0"
        module_path = Path(__file__).with_name("server.py")
        spec = importlib.util.spec_from_file_location("storefront_server", module_path)
        assert spec and spec.loader
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.server = cls.module.ThreadingHTTPServer(("127.0.0.1", 0), cls.module.StorefrontHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def test_index_and_health(self) -> None:
        with urllib.request.urlopen(f"{self.base_url}/", timeout=2) as response:
            self.assertIn(b"AKS Orders Lab", response.read())
        with urllib.request.urlopen(f"{self.base_url}/healthz", timeout=2) as response:
            self.assertEqual(response.status, 200)

    def test_metrics(self) -> None:
        with urllib.request.urlopen(f"{self.base_url}/metrics", timeout=2) as response:
            self.assertIn(b"storefront_requests_total", response.read())


if __name__ == "__main__":
    unittest.main()
