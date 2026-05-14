from __future__ import annotations

import unittest

from quantagent_api.config.settings import Settings
from quantagent_api.main import create_app
from fastapi.testclient import TestClient


class ApiAppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)

    def test_health_uses_envelope_and_request_id(self) -> None:
        response = self.client.get("/api/v1/health", headers={"X-Request-ID": "req-123"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], "req-123")
        self.assertEqual(response.json(), {"code": 0, "data": {"status": "ok"}, "msg": "ok", "error": None})

    def test_debug_error_uses_envelope(self) -> None:
        response = self.client.get("/api/v1/debug/error")
        body = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.headers["X-Request-ID"], body["error"]["request_id"])
        self.assertEqual(body["code"], 40000)
        self.assertEqual(body["error"]["code"], "BAD_REQUEST")
        self.assertIsNone(body["error"]["trace_id"])
        self.assertEqual(body["msg"], "参数错误")

    def test_validation_error_sanitizes_fields(self) -> None:
        response = self.client.post("/api/v1/debug/validation", json={})
        body = response.json()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(body["code"], 42200)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertIn("fields", body["error"]["details"])
        self.assertTrue(body["error"]["details"]["fields"])
        self.assertTrue({"loc", "msg", "type"}.issubset(body["error"]["details"]["fields"][0].keys()))

    def test_not_found_uses_envelope(self) -> None:
        response = self.client.get("/api/v1/missing")
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body["code"], 40400)
        self.assertEqual(body["error"]["code"], "NOT_FOUND")
        self.assertEqual(response.headers["X-Request-ID"], body["error"]["request_id"])

    def test_method_not_allowed_uses_envelope(self) -> None:
        response = self.client.post("/api/v1/health")
        body = response.json()
        self.assertEqual(response.status_code, 405)
        self.assertEqual(body["code"], 40500)
        self.assertEqual(body["error"]["code"], "METHOD_NOT_ALLOWED")
        self.assertEqual(response.headers["X-Request-ID"], body["error"]["request_id"])

    def test_invalid_request_id_is_replaced(self) -> None:
        response = self.client.get("/api/v1/health", headers={"X-Request-ID": "bad id"})
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.headers["X-Request-ID"], "bad id")
        self.assertRegex(response.headers["X-Request-ID"], r"^[0-9a-f]{32}$")

    def test_debug_routes_disabled_in_production(self) -> None:
        production_app = create_app(Settings(APP_ENV="production"))
        with TestClient(production_app) as client:
            response = client.get("/api/v1/debug/success")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
