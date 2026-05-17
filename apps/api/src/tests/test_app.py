from __future__ import annotations

import os
import tempfile
import unittest
from types import SimpleNamespace

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from quantagent.api.config.settings import Settings
from quantagent.api.db import get_db_session
from quantagent.api.errors import ServiceUnavailableError
from quantagent.api.main import create_app


class FakeSession:
    """用于测试数据库依赖的轻量 Session 替身。"""

    def __init__(self, *, execute_error: Exception | None = None) -> None:
        self.execute_error = execute_error
        self.rollback_calls = 0
        self.close_calls = 0
        self.commit_calls = 0
        self.execute_calls = 0

    def execute(self, *_args, **_kwargs) -> None:
        self.execute_calls += 1
        if self.execute_error is not None:
            raise self.execute_error

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.close_calls += 1

    def commit(self) -> None:
        self.commit_calls += 1


class FailingSessionFactory:
    """模拟 session factory 初始化失败的场景。"""

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    def __call__(self) -> FakeSession:
        self.calls += 1
        raise self.error


class ApiAppTestCase(unittest.TestCase):
    """覆盖应用装配、错误响应和数据库依赖行为的集成测试。"""

    def setUp(self) -> None:
        self.client = TestClient(create_app(self._settings()))
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)

    def test_health_uses_envelope_and_request_id(self) -> None:
        response = self.client.get("/api/v1/health", headers={"X-Request-ID": "req-123"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], "req-123")
        self.assertEqual(response.json(), {"code": 0, "data": {"status": "ok"}, "msg": "ok", "error": None})

    def test_version_uses_explicit_envelope_contract(self) -> None:
        response = self.client.get("/api/v1/version")
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["msg"], "ok")
        self.assertIsNone(body["error"])
        self.assertEqual(set(body["data"].keys()), {"service", "api_version", "version"})
        self.assertEqual(body["data"]["service"], "quantagent-api")
        self.assertEqual(body["data"]["api_version"], "v1")
        self.assertTrue(body["data"]["version"])

    def test_health_stays_live_when_database_session_factory_is_broken(self) -> None:
        failing_factory = FailingSessionFactory(SQLAlchemyError("password=secret connect failed"))
        app = create_app(self._settings())
        with TestClient(app) as client:
            client.app.state.db_session_factory = failing_factory
            response = client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"code": 0, "data": {"status": "ok"}, "msg": "ok", "error": None})
        self.assertEqual(failing_factory.calls, 0)

    def test_ready_returns_service_unavailable_when_database_is_not_configured(self) -> None:
        response = self.client.get("/api/v1/ready")
        body = response.json()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(body["code"], 50300)
        self.assertEqual(body["msg"], "Database not configured")
        self.assertEqual(body["error"]["code"], "SERVICE_UNAVAILABLE")
        self.assertTrue(body["error"]["retryable"])
        self.assertEqual(response.headers["X-Request-ID"], body["error"]["request_id"])
        self.assertNotIn("DATABASE_URL", str(body))
        self.assertNotIn("postgresql+psycopg://", str(body))
        self.assertNotIn("traceback", str(body).lower())

    def test_ready_uses_database_lifecycle_when_configured(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))

        # 使用临时 sqlite 文件验证应用生命周期内的数据库初始化和清理逻辑。
        app = create_app(self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}"))
        with TestClient(app) as client:
            response = client.get("/api/v1/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"code": 0, "data": {"status": "ready"}, "msg": "ok", "error": None})
        self.assertIsNone(app.state.db_engine)
        self.assertIsNone(app.state.db_session_factory)

    def test_ready_returns_service_unavailable_when_database_query_fails(self) -> None:
        app = create_app(self._settings())
        with TestClient(app) as client:
            client.app.state.db_session_factory = (
                lambda: FakeSession(
                    execute_error=SQLAlchemyError(
                        "db down password=hunter2 token=abc123 traceback line 42 "
                        "postgresql+psycopg://quantagent:quantagent@localhost:15432/quantagent"
                    )
                )
            )
            response = client.get("/api/v1/ready")

        body = response.json()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(body["code"], 50300)
        self.assertEqual(body["msg"], "Database not ready")
        self.assertEqual(body["error"]["code"], "SERVICE_UNAVAILABLE")
        self.assertTrue(body["error"]["retryable"])
        self.assertNotIn("hunter2", str(body))
        self.assertNotIn("abc123", str(body))
        self.assertNotIn("postgresql+psycopg://", str(body))
        self.assertNotIn("traceback", str(body).lower())

    def test_invalid_database_url_fails_app_startup(self) -> None:
        app = create_app(self._settings(DATABASE_URL="not-a-valid-database-url"))

        with self.assertRaisesRegex(Exception, "Could not parse SQLAlchemy URL"):
            with TestClient(app):
                pass

        self.assertIsNone(getattr(app.state, "db_engine", None))
        self.assertIsNone(getattr(app.state, "db_session_factory", None))

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
        production_app = create_app(self._settings(APP_ENV="production"))
        with TestClient(production_app) as client:
            response = client.get("/api/v1/debug/success")
        self.assertEqual(response.status_code, 404)

    def test_openapi_exposes_system_routes_with_tags_and_envelope_schema(self) -> None:
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()

        self.assertIn("system", schema["paths"]["/api/v1/version"]["get"]["tags"])
        self.assertIn("system", schema["paths"]["/api/v1/health"]["get"]["tags"])
        self.assertIn("system", schema["paths"]["/api/v1/ready"]["get"]["tags"])

        version_schema = self._resolve_response_schema(schema, "/api/v1/version")
        self.assertTrue({"code", "data", "msg", "error"}.issubset(version_schema["properties"].keys()))

        version_data_schema = self._resolve_schema_ref(schema, version_schema["properties"]["data"])
        self.assertEqual(set(version_data_schema["properties"].keys()), {"service", "api_version", "version"})
        self.assertFalse(version_data_schema.get("additionalProperties", True))
        self.assertEqual(version_data_schema["properties"]["service"]["minLength"], 1)
        self.assertEqual(version_data_schema["properties"]["api_version"]["minLength"], 1)
        self.assertEqual(version_data_schema["properties"]["version"]["minLength"], 1)

        health_schema = self._resolve_response_schema(schema, "/api/v1/health")
        self.assertTrue({"code", "data", "msg", "error"}.issubset(health_schema["properties"].keys()))

        ready_schema = self._resolve_response_schema(schema, "/api/v1/ready")
        self.assertTrue({"code", "data", "msg", "error"}.issubset(ready_schema["properties"].keys()))

    def test_production_openapi_excludes_debug_routes(self) -> None:
        production_app = create_app(self._settings(APP_ENV="production"))
        with TestClient(production_app) as client:
            response = client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertIn("/api/v1/version", schema["paths"])
        self.assertIn("/api/v1/health", schema["paths"])
        self.assertIn("/api/v1/ready", schema["paths"])
        self.assertNotIn("/api/v1/debug/error", schema["paths"])
        self.assertNotIn("/api/v1/debug/success", schema["paths"])

    def test_db_session_dependency_closes_session_without_auto_commit(self) -> None:
        session = FakeSession()
        request = self._build_request(lambda: session)

        dependency = get_db_session(request)
        resolved_session = next(dependency)
        self.assertIs(resolved_session, session)

        with self.assertRaises(StopIteration):
            next(dependency)

        self.assertEqual(session.rollback_calls, 0)
        self.assertEqual(session.close_calls, 1)
        self.assertEqual(session.commit_calls, 0)

    def test_db_session_dependency_rolls_back_on_error(self) -> None:
        session = FakeSession()
        app = FastAPI()
        app.state.db_session_factory = lambda: session

        def dependency(request: Request):
            # 显式透传原依赖，便于验证生成器在异常路径下的回滚逻辑。
            yield from get_db_session(request)

        @app.get("/test-db-rollback")
        def test_db_rollback_route(_session=Depends(dependency)) -> None:
            raise HTTPException(status_code=400, detail="boom")

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/test-db-rollback")

        body = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["detail"], "boom")
        self.assertEqual(session.rollback_calls, 1)
        self.assertEqual(session.close_calls, 1)
        self.assertEqual(session.commit_calls, 0)

    def test_db_session_dependency_raises_service_unavailable_without_factory(self) -> None:
        request = self._build_request(None)

        with self.assertRaises(ServiceUnavailableError) as context:
            next(get_db_session(request))

        self.assertEqual(context.exception.status_code, 503)
        self.assertEqual(context.exception.error_code, 50300)
        self.assertEqual(context.exception.error_key, "SERVICE_UNAVAILABLE")

    def test_db_session_dependency_raises_service_unavailable_when_factory_is_not_ready(self) -> None:
        failing_factory = FailingSessionFactory(SQLAlchemyError("connect failed"))
        request = self._build_request(failing_factory)

        with self.assertRaises(ServiceUnavailableError) as context:
            next(get_db_session(request))

        self.assertEqual(failing_factory.calls, 1)
        self.assertEqual(context.exception.status_code, 503)
        self.assertEqual(context.exception.error_code, 50300)
        self.assertEqual(context.exception.error_key, "SERVICE_UNAVAILABLE")
        self.assertEqual(context.exception.message, "Database not ready")

    def _build_request(self, session_factory):
        """构造带 app.state 的最小 Request 对象，供依赖函数直接测试。"""
        scope = {"type": "http", "app": SimpleNamespace(state=SimpleNamespace(db_session_factory=session_factory))}
        return Request(scope)

    def _resolve_response_schema(self, openapi_schema: dict, path: str) -> dict:
        response_schema = openapi_schema["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        return self._resolve_schema_ref(openapi_schema, response_schema)

    def _resolve_schema_ref(self, openapi_schema: dict, schema_node: dict) -> dict:
        if "$ref" not in schema_node:
            for keyword in ("anyOf", "allOf", "oneOf"):
                variants = schema_node.get(keyword)
                if not variants:
                    continue
                for variant in variants:
                    if "$ref" in variant:
                        return self._resolve_schema_ref(openapi_schema, variant)
            return schema_node

        ref_path = schema_node["$ref"].removeprefix("#/")
        resolved: dict = openapi_schema
        for part in ref_path.split("/"):
            resolved = resolved[part]
        return resolved

    def _settings(self, **overrides) -> Settings:
        """生成测试默认配置，并允许按场景覆盖个别字段。"""
        baseline = {
            "APP_ENV": "development",
            "DATABASE_URL": None,
            "RUNTIME_DIR": "runtime",
            "LOG_LEVEL": "INFO",
            "API_V1_PREFIX": "/api/v1",
            "HOST": "127.0.0.1",
            "PORT": 8000,
        }
        baseline.update(overrides)
        return Settings(**baseline)


if __name__ == "__main__":
    unittest.main()
