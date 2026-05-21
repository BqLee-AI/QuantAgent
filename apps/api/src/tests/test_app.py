from __future__ import annotations

import os
import tempfile
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError

from quantagent.api.auth import (
    ALL_CAPABILITIES,
    CurrentActor,
    RUNTIME_INSPECT_CAPABILITY,
    build_actor_audit_context,
    issue_session,
    require_capability,
    require_csrf,
)
from quantagent.api.config.settings import Settings
from quantagent.api.db import get_db_session
from quantagent.api.errors import ServiceUnavailableError
from quantagent.api.main import create_app
from quantagent.api.responses import ApiResponse
from quantagent.api.routers.register import (
    API_V1_PUBLIC_ROUTE_ALLOWLIST,
    STANDARD_API_V1_ROUTER_REGISTRATIONS,
    build_api_v1_public_route_allowlist,
    register_api_v1_protected_router,
)
from fastapi.routing import APIRoute


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
        self.settings = self._settings()
        self.client = TestClient(create_app(self.settings))
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
        self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
        response = self.client.get("/api/v1/debug/error")
        body = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.headers["X-Request-ID"], body["error"]["request_id"])
        self.assertEqual(body["code"], 40000)
        self.assertEqual(body["error"]["code"], "BAD_REQUEST")
        self.assertIsNone(body["error"]["trace_id"])
        self.assertEqual(body["msg"], "参数错误")

    def test_validation_error_sanitizes_fields(self) -> None:
        self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
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

    def test_debug_routes_require_session_when_not_production(self) -> None:
        response = self.client.get("/api/v1/debug/success")
        body = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")
        self.assertEqual(response.headers["X-Request-ID"], body["error"]["request_id"])

    def test_production_rejects_disabled_auth(self) -> None:
        with self.assertRaisesRegex(ValueError, "AUTH_ENABLED=false"):
            self._settings(
                APP_ENV="production",
                AUTH_ENABLED=False,
                AUTH_ADMIN_PASSWORD="prod-password",
                AUTH_SESSION_SECRET="prod-secret",
            )

    def test_production_login_uses_secure_cookie(self) -> None:
        production_app = create_app(
            self._settings(
                APP_ENV="production",
                AUTH_ADMIN_PASSWORD="prod-password",
                AUTH_SESSION_SECRET="prod-secret",
            )
        )
        with TestClient(production_app) as client:
            response = client.post("/api/v1/auth/login", json={"password": "prod-password"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("Secure", response.headers["set-cookie"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])

    def test_non_development_env_requires_explicit_auth_credentials(self) -> None:
        with self.assertRaisesRegex(ValueError, "AUTH_SESSION_SECRET is required when APP_ENV is not development/test/local"):
            Settings(APP_ENV="staging", AUTH_ADMIN_PASSWORD="local-password")

    def test_production_rejects_whitespace_only_auth_credentials(self) -> None:
        with self.assertRaisesRegex(ValueError, "AUTH_ADMIN_PASSWORD is required in production"):
            Settings(
                APP_ENV="production",
                AUTH_ADMIN_PASSWORD="   ",
                AUTH_SESSION_SECRET="prod-secret",
            )

        with self.assertRaisesRegex(ValueError, "AUTH_SESSION_SECRET is required in production"):
            Settings(
                APP_ENV="production",
                AUTH_ADMIN_PASSWORD="prod-password",
                AUTH_SESSION_SECRET="   ",
            )

    def test_test_env_still_receives_weak_auth_defaults(self) -> None:
        settings = Settings(APP_ENV="test")
        self.assertEqual(settings.AUTH_ADMIN_PASSWORD, "12345678")
        self.assertEqual(settings.AUTH_SESSION_SECRET, "dev-session-secret-change-me")

    def test_same_site_none_requires_secure_cookie(self) -> None:
        with self.assertRaisesRegex(ValueError, "AUTH_COOKIE_SAME_SITE=none requires AUTH_COOKIE_SECURE=true"):
            Settings(
                APP_ENV="development",
                AUTH_ADMIN_PASSWORD="test-admin-password",
                AUTH_SESSION_SECRET="test-session-secret",
                AUTH_COOKIE_SAME_SITE="none",
                AUTH_COOKIE_SECURE=False,
            )

    def test_login_success_sets_cookie_and_returns_csrf_token(self) -> None:
        response = self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(body["error"])
        self.assertEqual(body["data"]["actor_id"], "local_admin")
        self.assertEqual(body["data"]["actor_type"], "local_single_user")
        self.assertEqual(set(body["data"]["capabilities"]), ALL_CAPABILITIES)
        self.assertTrue(body["data"]["csrf_token"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertNotIn(self.settings.AUTH_ADMIN_PASSWORD or "", str(body))
        self.assertNotIn(self.settings.AUTH_SESSION_SECRET or "", str(body))

    def test_public_allowlist_matches_expected_routes(self) -> None:
        self.assertEqual(
            API_V1_PUBLIC_ROUTE_ALLOWLIST,
            frozenset(
                {
                    ("GET", "/health"),
                    ("GET", "/ready"),
                    ("GET", "/version"),
                    ("POST", "/auth/login"),
                }
            ),
        )

    def test_standard_public_registrations_match_allowlist(self) -> None:
        public_routes = frozenset(
            (method, route.path)
            for registration in STANDARD_API_V1_ROUTER_REGISTRATIONS
            if registration.access == "public"
            for route in registration.router.routes
            if isinstance(route, APIRoute)
            for method in (route.methods or ())
            if method in {"DELETE", "GET", "PATCH", "POST", "PUT"}
        )
        self.assertEqual(
            public_routes,
            frozenset(
                {
                    ("GET", "/health"),
                    ("GET", "/ready"),
                    ("GET", "/version"),
                    ("POST", "/auth/login"),
                }
            ),
        )

    def test_public_allowlist_builds_prefixed_routes_from_settings(self) -> None:
        custom_prefix = "/internal/v9"
        self.assertEqual(
            build_api_v1_public_route_allowlist(custom_prefix),
            frozenset(
                {
                    ("GET", f"{custom_prefix}/health"),
                    ("GET", f"{custom_prefix}/ready"),
                    ("GET", f"{custom_prefix}/version"),
                    ("POST", f"{custom_prefix}/auth/login"),
                }
            ),
        )

    def test_login_failure_uses_unauthorized_envelope(self) -> None:
        response = self.client.post("/api/v1/auth/login", json={"password": "wrong-password"})
        body = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(body["code"], 40100)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")
        self.assertEqual(response.headers["X-Request-ID"], body["error"]["request_id"])
        self.assertNotIn("wrong-password", str(body))
        self.assertNotIn(self.settings.AUTH_ADMIN_PASSWORD or "", str(body))
        self.assertNotIn(self.settings.AUTH_SESSION_SECRET or "", str(body))
        self.assertNotIn("set-cookie", {key.lower() for key in response.headers.keys()})

    def test_login_with_non_ascii_password_uses_unauthorized_envelope_instead_of_500(self) -> None:
        app = create_app(
            self._settings(
                AUTH_ADMIN_PASSWORD="密碼",
                AUTH_SESSION_SECRET="测试-secret",
            )
        )
        with TestClient(app) as client:
            response = client.post("/api/v1/auth/login", json={"password": "错误密码"})

        body = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")
        self.assertEqual(response.headers["X-Request-ID"], body["error"]["request_id"])

    def test_issue_session_rejects_unsupported_actor_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported actor_id for session issuance: local_other"):
            issue_session("local_other", self.settings)

    def test_me_rejects_missing_session(self) -> None:
        response = self.client.get("/api/v1/me")
        body = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")
        self.assertEqual(response.headers["X-Request-ID"], body["error"]["request_id"])

    def test_me_rejects_invalid_session_without_leaking_cookie(self) -> None:
        self.client.cookies.set(self.settings.AUTH_COOKIE_NAME, "invalid.session")
        response = self.client.get("/api/v1/me")
        body = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")
        self.assertNotIn("invalid.session", str(body))
        self.assertNotIn(self.settings.AUTH_SESSION_SECRET or "", str(body))

    def test_me_rejects_expired_session(self) -> None:
        session_value, _csrf_token = issue_session("local_admin", self.settings, expires_at=1)
        self.client.cookies.set(self.settings.AUTH_COOKIE_NAME, session_value)

        response = self.client.get("/api/v1/me")
        body = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")

    def test_me_rejects_session_expiring_at_now(self) -> None:
        session_value, _csrf_token = issue_session(
            "local_admin",
            self.settings,
            expires_at=int(datetime.now(UTC).timestamp()),
        )
        self.client.cookies.set(self.settings.AUTH_COOKIE_NAME, session_value)

        response = self.client.get("/api/v1/me")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    def test_me_returns_actor_capabilities_and_csrf(self) -> None:
        login_response = self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
        login_body = login_response.json()

        response = self.client.get("/api/v1/me")
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["data"]["actor_id"], "local_admin")
        self.assertEqual(body["data"]["actor_type"], "local_single_user")
        self.assertEqual(set(body["data"]["capabilities"]), ALL_CAPABILITIES)
        self.assertNotEqual(body["data"]["csrf_token"], login_body["data"]["csrf_token"])
        self.assertNotIn(self.settings.AUTH_SESSION_SECRET or "", str(body))
        self.assertNotIn(self.settings.AUTH_COOKIE_NAME, str(body))
        self.assertIn("HttpOnly", response.headers["set-cookie"])

    def test_me_refreshes_session_cookie_and_csrf_token(self) -> None:
        login_response = self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
        initial_csrf_token = login_response.json()["data"]["csrf_token"]
        initial_cookie = login_response.headers["set-cookie"]

        response = self.client.get("/api/v1/me")
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertNotEqual(response.headers["set-cookie"], initial_cookie)
        self.assertNotEqual(body["data"]["csrf_token"], initial_csrf_token)

    def test_development_can_disable_auth_and_keep_actor_context(self) -> None:
        app = create_app(self._settings(AUTH_ENABLED=False))
        with TestClient(app) as client:
            response = client.get("/api/v1/me")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["data"]["actor_id"], "local_dev")
        self.assertEqual(body["data"]["actor_type"], "local_single_user")
        self.assertTrue(body["data"]["capabilities"])
        self.assertTrue(body["data"]["csrf_token"])

    def test_disabled_auth_login_returns_development_actor_without_session_cookie(self) -> None:
        app = create_app(self._settings(AUTH_ENABLED=False))
        with TestClient(app) as client:
            response = client.post("/api/v1/auth/login", json={"password": "ignored-in-development-bypass"})
            me_response = client.get("/api/v1/me")

        body = response.json()
        me_body = me_response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["data"]["actor_id"], "local_dev")
        self.assertEqual(body["data"]["actor_type"], "local_single_user")
        self.assertEqual(body["data"]["csrf_token"], me_body["data"]["csrf_token"])
        self.assertIn("Max-Age=0", response.headers["set-cookie"])

    def test_disabled_auth_logout_uses_development_csrf_token(self) -> None:
        app = create_app(self._settings(AUTH_ENABLED=False))
        with TestClient(app) as client:
            login_response = client.post("/api/v1/auth/login", json={"password": "ignored"})
            csrf_token = login_response.json()["data"]["csrf_token"]
            response = client.post("/api/v1/auth/logout", headers={self.settings.AUTH_CSRF_HEADER_NAME: csrf_token})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], {"cleared": True})

    def test_logout_without_session_is_unauthorized(self) -> None:
        response = self.client.post("/api/v1/auth/logout")
        body = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")
        self.assertEqual(response.headers["X-Request-ID"], body["error"]["request_id"])

    def test_logout_requires_csrf_token(self) -> None:
        self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
        response = self.client.post("/api/v1/auth/logout")
        body = response.json()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(body["error"]["code"], "FORBIDDEN")

    def test_logout_rejects_invalid_csrf_token_without_echoing_it(self) -> None:
        self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
        response = self.client.post("/api/v1/auth/logout", headers={self.settings.AUTH_CSRF_HEADER_NAME: "bad-token"})
        body = response.json()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(body["error"]["code"], "FORBIDDEN")
        self.assertNotIn("bad-token", str(body))

    def test_logout_clears_cookie_with_valid_csrf_token(self) -> None:
        login_response = self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
        csrf_token = login_response.json()["data"]["csrf_token"]

        response = self.client.post("/api/v1/auth/logout", headers={self.settings.AUTH_CSRF_HEADER_NAME: csrf_token})
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["data"], {"cleared": True})
        self.assertIn("Max-Age=0", response.headers["set-cookie"])

    def test_protected_write_requires_session(self) -> None:
        with TestClient(self._protected_write_test_app()) as client:
            response = client.post("/test/protected-write")
        body = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")

    def test_protected_write_requires_csrf_token(self) -> None:
        with TestClient(self._protected_write_test_app()) as client:
            client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
            response = client.post("/test/protected-write")
        body = response.json()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(body["error"]["code"], "FORBIDDEN")

    def test_protected_write_rejects_invalid_csrf_token(self) -> None:
        with TestClient(self._protected_write_test_app()) as client:
            client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
            response = client.post(
                "/test/protected-write",
                headers={self.settings.AUTH_CSRF_HEADER_NAME: "bad-token"},
            )
        body = response.json()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(body["error"]["code"], "FORBIDDEN")
        self.assertNotIn("bad-token", str(body))

    def test_protected_write_returns_actor_audit_context_fields(self) -> None:
        with TestClient(self._protected_write_test_app()) as client:
            login_response = client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
            csrf_token = login_response.json()["data"]["csrf_token"]

            response = client.post(
                "/test/protected-write",
                headers={
                    self.settings.AUTH_CSRF_HEADER_NAME: csrf_token,
                    "X-Request-ID": "req-runtime-write",
                },
            )
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["data"]["actor_id"], "local_admin")
        self.assertEqual(body["data"]["request_id"], "req-runtime-write")

    def test_registered_protected_router_requires_session_without_route_level_dependency(self) -> None:
        with TestClient(self._registered_protected_api_v1_test_app()) as client:
            response = client.get("/api/v1/test-actions/runtime-inspect")

        body = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")
        self.assertEqual(response.headers["X-Request-ID"], body["error"]["request_id"])

    def test_registered_protected_router_allows_authenticated_request_without_route_level_dependency(self) -> None:
        with TestClient(self._registered_protected_api_v1_test_app()) as client:
            client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
            response = client.get("/api/v1/test-actions/runtime-inspect")

        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["data"], {"status": "protected"})

    def test_missing_capability_is_forbidden(self) -> None:
        reduced_capabilities = frozenset({"plugin.configure"})
        session_value, csrf_token = issue_session("local_admin", self.settings, capabilities=reduced_capabilities)
        with TestClient(self._protected_write_test_app()) as client:
            client.cookies.set(self.settings.AUTH_COOKIE_NAME, session_value)
            response = client.post(
                "/test/protected-write",
                headers={self.settings.AUTH_CSRF_HEADER_NAME: csrf_token},
            )

        body = response.json()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(body["code"], 40300)
        self.assertEqual(body["error"]["code"], "FORBIDDEN")
        self.assertEqual(response.headers["X-Request-ID"], body["error"]["request_id"])

    def test_unknown_required_capability_fails_fast(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown capability: runtime.typo"):
            require_capability("runtime.typo")

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

        self.assertIn("auth", schema["paths"]["/api/v1/auth/login"]["post"]["tags"])
        self.assertIn("auth", schema["paths"]["/api/v1/auth/logout"]["post"]["tags"])
        self.assertIn("auth", schema["paths"]["/api/v1/me"]["get"]["tags"])
        self.assertNotIn("/api/v1/auth/test-actions/runtime-inspect", schema["paths"])

        login_schema = self._resolve_response_schema(schema, "/api/v1/auth/login", method="post")
        self.assertTrue({"code", "data", "msg", "error"}.issubset(login_schema["properties"].keys()))

        logout_schema = self._resolve_response_schema(schema, "/api/v1/auth/logout", method="post")
        self.assertTrue({"code", "data", "msg", "error"}.issubset(logout_schema["properties"].keys()))

        me_schema = self._resolve_response_schema(schema, "/api/v1/me")
        me_data_schema = self._resolve_schema_ref(schema, me_schema["properties"]["data"])
        self.assertTrue({"actor_id", "actor_type", "capabilities", "csrf_token"}.issubset(me_data_schema["properties"]))

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
        self.assertNotIn("/api/v1/auth/test-actions/runtime-inspect", schema["paths"])

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

    def _protected_write_test_app(self) -> FastAPI:
        app = create_app(self.settings)

        class ProtectedWriteResponse(BaseModel):
            model_config = ConfigDict(extra="forbid")

            actor_id: str = Field(min_length=1)
            request_id: str = Field(min_length=1)

        @app.post("/test/protected-write", response_model=ApiResponse[ProtectedWriteResponse])
        def protected_write(
            request: Request,
            actor: CurrentActor = Depends(require_csrf),
            _capability_actor: CurrentActor = Depends(require_capability(RUNTIME_INSPECT_CAPABILITY)),
        ) -> ApiResponse[ProtectedWriteResponse]:
            context = build_actor_audit_context(request, actor)
            return ApiResponse.success(
                ProtectedWriteResponse(
                    actor_id=context.actor_id,
                    request_id=context.request_id,
                )
            )

        return app

    def _registered_protected_api_v1_test_app(self) -> FastAPI:
        app = create_app(self.settings)

        class RuntimeInspectResponse(BaseModel):
            model_config = ConfigDict(extra="forbid")

            status: str = Field(min_length=1)

        router = APIRouter(prefix="/test-actions", tags=["test"])

        @router.get("/runtime-inspect", response_model=ApiResponse[RuntimeInspectResponse])
        def runtime_inspect() -> ApiResponse[RuntimeInspectResponse]:
            return ApiResponse.success(RuntimeInspectResponse(status="protected"))

        register_api_v1_protected_router(app, self.settings, router)
        return app

    def _resolve_response_schema(self, openapi_schema: dict, path: str, *, method: str = "get") -> dict:
        response_schema = openapi_schema["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"]
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
            "AUTH_ENABLED": True,
            "AUTH_ADMIN_PASSWORD": "test-admin-password",
            "AUTH_SESSION_SECRET": "test-session-secret",
        }
        baseline.update(overrides)
        return Settings(**baseline)


if __name__ == "__main__":
    unittest.main()
