from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
import unittest
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
import json
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from nacl.encoding import HexEncoder
from nacl.signing import SigningKey
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError

from quantagent.api.auth import (
    ALL_CAPABILITIES,
    APPROVAL_APPROVE_CAPABILITY,
    APPROVAL_READ_CAPABILITY,
    CurrentActor,
    RUNTIME_INSPECT_CAPABILITY,
    build_actor_audit_context,
    issue_session,
    require_capability,
    require_csrf,
)
from quantagent.api.auth.session import SESSION_V2, _deserialize_session, _issue_v1_session, _serialize_session
from quantagent.api.config.settings import Settings, _build_env_file_paths
from quantagent.api.db import get_db_session
from quantagent.api.http.errors import ServiceUnavailableError
from quantagent.api.http.responses import ApiResponse
from quantagent.api.main import create_app
from quantagent.api.observability.logging import InMemoryStructuredHandler, shutdown_api_logging
from quantagent.api.routers.v1.register import (
    API_V1_PUBLIC_ROUTE_ALLOWLIST,
    STANDARD_API_V1_ROUTER_REGISTRATIONS,
    build_api_v1_public_route_allowlist,
    register_api_v1_protected_router,
)
from quantagent.core.db.base import Base
from quantagent.core.db.models.scheduler_run import SchedulerRunORM
from quantagent.core.db.models.raw_event import RawEventORM
from quantagent.core.db.models.raw_event_capture import RawEventCaptureORM
from quantagent.core.db.models.source_binding import SourceBindingORM
from quantagent.core.db.models.event_intake import EventIntakeRoutedEventORM
from quantagent.core.db.repositories.approval_repository import SQLAlchemyApprovalRepository
from quantagent.core.approval.models import (
    ActionRequest as ApprovalActionRequestModel,
    ApprovalRequest as ApprovalRequestModel,
    ConfirmationLevel as ApprovalConfirmationLevel,
    ExpirationAction as ApprovalExpirationAction,
)
from quantagent.core.approval import (
    ActionRequestedHandler,
    ApprovalEventPublisher,
    ApprovalOrchestrationService,
)
from quantagent.core.events import EventEnvelope, InMemoryEventBus
from quantagent.core.model_config import FixedModelCallClient, ModelConfigCrypto, ModelTokenUsage
from quantagent.core.model_config.service import ModelCallResult
from quantagent.core.registry import PluginRegistry, PluginStatus, RegistryScanner
from quantagent.core.registry.models import PluginManifest, PluginRecord, PluginSource, PluginType
from quantagent.core.db.repositories.scheduler_run_repository import SchedulerRunRepository
from quantagent.core.scheduling import PluginRunStatus, PluginTriggerType, SchedulerRunService
from quantagent.core.wallet import (
    AccountMode,
    CashBalanceSnapshot,
    OrderSide,
    OrderType,
    PaperExecutionSnapshot,
    PaperOrderSnapshot,
    PaperOrderStatus,
    PositionSide,
    PositionSnapshot,
    TradingAccountSnapshot,
    WalletLedgerEntrySnapshot,
    WalletLedgerEntryType,
    WalletLedgerSourceType,
)


class FakeModelClient(FixedModelCallClient):
    def __init__(self) -> None:
        self.calls: list[dict[str, str | None]] = []

    def run_fixed_smoke(
        self,
        *,
        base_url: str | None,
        model: str,
        api_key: str,
        request_id: str | None,
    ) -> ModelCallResult:
        self.calls.append(
            {
                "base_url": base_url,
                "model": model,
                "api_key": api_key,
                "request_id": request_id,
            }
        )
        return ModelCallResult(token_usage=ModelTokenUsage(prompt_tokens=2, completion_tokens=1, total_tokens=3))


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


class FakeWalletService:
    """用于 wallet route 测试的轻量 service 替身。"""

    def __init__(
        self,
        *,
        account: TradingAccountSnapshot | None = None,
        cash_balances: list[CashBalanceSnapshot] | None = None,
        positions: list[PositionSnapshot] | None = None,
        ledger_entries: list[WalletLedgerEntrySnapshot] | None = None,
        paper_orders: list[PaperOrderSnapshot] | None = None,
        paper_executions: list[PaperExecutionSnapshot] | None = None,
        errors: dict[str, Exception] | None = None,
    ) -> None:
        self.account = account
        self.cash_balances = cash_balances or []
        self.positions = positions or []
        self.ledger_entries = ledger_entries or []
        self.paper_orders = paper_orders or []
        self.paper_executions = paper_executions or []
        self.errors = errors or {}
        self.calls: list[tuple[object, ...]] = []

    def get_trading_account(self, account_id: str) -> TradingAccountSnapshot | None:
        self.calls.append(("get_trading_account", account_id))
        self._maybe_raise("get_trading_account")
        if self.account is None or self.account.account_id != account_id:
            return None
        return self.account

    def list_cash_balances(self, account_id: str) -> list[CashBalanceSnapshot]:
        self.calls.append(("list_cash_balances", account_id))
        self._maybe_raise("list_cash_balances")
        return list(self.cash_balances)

    def list_positions(self, account_id: str) -> list[PositionSnapshot]:
        self.calls.append(("list_positions", account_id))
        self._maybe_raise("list_positions")
        return list(self.positions)

    def list_ledger_entries(self, account_id: str, *, limit: int | None = None) -> list[WalletLedgerEntrySnapshot]:
        self.calls.append(("list_ledger_entries", account_id, limit))
        self._maybe_raise("list_ledger_entries")
        return list(self.ledger_entries)

    def list_paper_orders(self, account_id: str) -> list[PaperOrderSnapshot]:
        self.calls.append(("list_paper_orders", account_id))
        self._maybe_raise("list_paper_orders")
        return list(self.paper_orders)

    def list_paper_executions(self, account_id: str) -> list[PaperExecutionSnapshot]:
        self.calls.append(("list_paper_executions", account_id))
        self._maybe_raise("list_paper_executions")
        return list(self.paper_executions)

    def _maybe_raise(self, method_name: str) -> None:
        error = self.errors.get(method_name)
        if error is not None:
            raise error


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
        self.assertRegex(response.headers["X-Trace-ID"], r"^[0-9a-f]{32}$")
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

    def test_wallet_routes_require_authenticated_session(self) -> None:
        response = self.client.get("/api/v1/wallet/accounts/acct-paper-001")
        body = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")
        self.assertEqual(response.headers["X-Request-ID"], body["error"]["request_id"])

    def test_wallet_routes_return_envelope_and_serialized_snapshots(self) -> None:
        self._login()
        now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
        wallet_service = FakeWalletService(
            account=TradingAccountSnapshot(
                account_id="acct-paper-001",
                name="Primary Paper Wallet",
                mode=AccountMode.PAPER,
                base_currency="USD",
                created_at=now,
            ),
            cash_balances=[
                CashBalanceSnapshot(
                    account_id="acct-paper-001",
                    currency="USD",
                    total=Decimal("1200.50"),
                    available=Decimal("1180.25"),
                    locked=Decimal("20.00"),
                    unsettled=Decimal("0"),
                    updated_at=now,
                )
            ],
            positions=[
                PositionSnapshot(
                    account_id="acct-paper-001",
                    instrument="AAPL",
                    market="NASDAQ",
                    side=PositionSide.LONG,
                    quantity=Decimal("10"),
                    sellable_quantity=Decimal("8"),
                    average_cost=Decimal("180.12"),
                    market_value=Decimal("1900.10"),
                    unrealized_pnl=Decimal("98.90"),
                    currency="USD",
                    updated_at=now,
                )
            ],
            ledger_entries=[
                WalletLedgerEntrySnapshot(
                    entry_id="led-001",
                    account_id="acct-paper-001",
                    entry_type=WalletLedgerEntryType.TRADE,
                    currency="USD",
                    amount=Decimal("-1801.20"),
                    source_type=WalletLedgerSourceType.PAPER_EXECUTION,
                    source_ref="idem-001",
                    occurred_at=now,
                    order_id="ord-001",
                    execution_id="exe-001",
                    metadata={"note": "paper-fill"},
                    created_at=now,
                )
            ],
            paper_orders=[
                PaperOrderSnapshot(
                    order_id="ord-001",
                    account_id="acct-paper-001",
                    client_order_id="client-001",
                    instrument="AAPL",
                    market="NASDAQ",
                    side=OrderSide.BUY,
                    order_type=OrderType.LIMIT,
                    quantity=Decimal("10"),
                    limit_price=Decimal("180.12"),
                    currency="USD",
                    status=PaperOrderStatus.FILLED,
                    requested_at=now,
                    completed_at=now,
                )
            ],
            paper_executions=[
                PaperExecutionSnapshot(
                    execution_id="exe-001",
                    account_id="acct-paper-001",
                    order_id="ord-001",
                    idempotency_key="idem-001",
                    instrument="AAPL",
                    market="NASDAQ",
                    side=OrderSide.BUY,
                    quantity=Decimal("10"),
                    price=Decimal("180.12"),
                    gross_amount=Decimal("1801.20"),
                    currency="USD",
                    fee_amount=Decimal("1.23"),
                    fee_currency="USD",
                    executed_at=now,
                    created_at=now,
                )
            ],
        )
        self.client.app.state.wallet_service = wallet_service

        account_response = self.client.get("/api/v1/wallet/accounts/acct-paper-001")
        cash_response = self.client.get("/api/v1/wallet/accounts/acct-paper-001/cash-balances")
        positions_response = self.client.get("/api/v1/wallet/accounts/acct-paper-001/positions")
        ledger_response = self.client.get("/api/v1/wallet/accounts/acct-paper-001/ledger-entries", params={"limit": 5})
        orders_response = self.client.get("/api/v1/wallet/accounts/acct-paper-001/paper-orders")
        executions_response = self.client.get("/api/v1/wallet/accounts/acct-paper-001/paper-executions")

        self.assertEqual(account_response.status_code, 200)
        self.assertEqual(account_response.json()["data"]["mode"], "paper")
        self.assertEqual(account_response.json()["data"]["created_at"], "2026-01-02T03:04:05Z")

        self.assertEqual(cash_response.status_code, 200)
        self.assertEqual(cash_response.json()["data"][0]["total"], "1200.50")
        self.assertEqual(cash_response.json()["data"][0]["updated_at"], "2026-01-02T03:04:05Z")

        self.assertEqual(positions_response.status_code, 200)
        self.assertEqual(positions_response.json()["data"][0]["side"], "long")
        self.assertEqual(positions_response.json()["data"][0]["average_cost"], "180.12")

        self.assertEqual(ledger_response.status_code, 200)
        self.assertEqual(ledger_response.json()["data"][0]["entry_type"], "trade")
        self.assertEqual(ledger_response.json()["data"][0]["metadata"], {"note": "paper-fill"})
        self.assertNotIn("cookie", str(ledger_response.json()).lower())
        self.assertNotIn("postgresql+psycopg://", str(ledger_response.json()))

        self.assertEqual(orders_response.status_code, 200)
        self.assertEqual(orders_response.json()["data"][0]["status"], "filled")
        self.assertEqual(orders_response.json()["data"][0]["order_type"], "limit")

        self.assertEqual(executions_response.status_code, 200)
        self.assertEqual(executions_response.json()["data"][0]["gross_amount"], "1801.20")
        self.assertEqual(executions_response.json()["data"][0]["executed_at"], "2026-01-02T03:04:05Z")

        self.assertEqual(
            wallet_service.calls,
            [
                ("get_trading_account", "acct-paper-001"),
                ("get_trading_account", "acct-paper-001"),
                ("list_cash_balances", "acct-paper-001"),
                ("get_trading_account", "acct-paper-001"),
                ("list_positions", "acct-paper-001"),
                ("get_trading_account", "acct-paper-001"),
                ("list_ledger_entries", "acct-paper-001", 5),
                ("get_trading_account", "acct-paper-001"),
                ("list_paper_orders", "acct-paper-001"),
                ("get_trading_account", "acct-paper-001"),
                ("list_paper_executions", "acct-paper-001"),
            ],
        )

    def test_wallet_unknown_account_returns_not_found_instead_of_empty_list(self) -> None:
        self._login()
        self.client.app.state.wallet_service = FakeWalletService()

        response = self.client.get("/api/v1/wallet/accounts/acct-paper-missing/positions")
        body = response.json()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(body["msg"], "Wallet account not found")
        self.assertEqual(body["error"]["details"], {"account_id": "acct-paper-missing"})

    def test_wallet_returns_service_unavailable_when_database_not_configured(self) -> None:
        self._login()
        response = self.client.get("/api/v1/wallet/accounts/acct-paper-001")
        body = response.json()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(body["msg"], "Database not configured")
        self.assertEqual(body["error"]["code"], "SERVICE_UNAVAILABLE")
        self.assertNotIn("DATABASE_URL", str(body))

    def test_wallet_query_database_failure_maps_to_service_unavailable(self) -> None:
        self._login()
        self.client.app.state.wallet_service = FakeWalletService(
            errors={"get_trading_account": SQLAlchemyError("db down password=hunter2")}
        )

        response = self.client.get("/api/v1/wallet/accounts/acct-paper-001")
        body = response.json()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(body["msg"], "Database not ready")
        self.assertEqual(body["error"]["code"], "SERVICE_UNAVAILABLE")
        self.assertNotIn("hunter2", str(body))

    def test_wallet_unknown_account_value_error_maps_to_not_found(self) -> None:
        self._login()
        self.client.app.state.wallet_service = FakeWalletService(
            errors={"get_trading_account": ValueError("Unknown trading account: acct-paper-missing")}
        )

        response = self.client.get("/api/v1/wallet/accounts/acct-paper-missing")
        body = response.json()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(body["msg"], "Wallet account not found")
        self.assertEqual(body["error"]["details"], {"account_id": "acct-paper-missing"})

    def test_wallet_paper_only_error_maps_to_bad_request(self) -> None:
        self._login()
        self.client.app.state.wallet_service = FakeWalletService(
            errors={"get_trading_account": ValueError("Portfolio Wallet Core V1 only supports paper accounts.")}
        )

        response = self.client.get("/api/v1/wallet/accounts/acct-live-001")
        body = response.json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["msg"], "Wallet API only supports paper accounts")
        self.assertEqual(body["error"]["code"], "BAD_REQUEST")

    def test_wallet_invalid_ledger_limit_uses_validation_envelope(self) -> None:
        self._login()
        self.client.app.state.wallet_service = FakeWalletService(
            account=TradingAccountSnapshot(
                account_id="acct-paper-001",
                name="Primary Paper Wallet",
                mode=AccountMode.PAPER,
                base_currency="USD",
                created_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
            )
        )

        response = self.client.get("/api/v1/wallet/accounts/acct-paper-001/ledger-entries", params={"limit": 0})
        body = response.json()

        self.assertEqual(response.status_code, 422)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["msg"], "Validation Error")

    def test_wallet_route_builds_service_from_app_session_factory(self) -> None:
        self._login()
        account = TradingAccountSnapshot(
            account_id="acct-paper-001",
            name="Primary Paper Wallet",
            mode=AccountMode.PAPER,
            base_currency="USD",
            created_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
        )
        session_factory = object()
        self.client.app.state.db_session_factory = session_factory

        with patch("quantagent.api.routers.v1.wallet.WalletService") as wallet_service_cls:
            wallet_service_cls.return_value.get_trading_account.return_value = account
            response = self.client.get("/api/v1/wallet/accounts/acct-paper-001")

        self.assertEqual(response.status_code, 200)
        wallet_service_cls.assert_called_once_with(session_factory)
        wallet_service_cls.return_value.get_trading_account.assert_called_once_with("acct-paper-001")

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

    def test_app_lifespan_closes_event_bus_runtime_on_shutdown(self) -> None:
        closed = {"value": False}

        class FakeRuntime:
            async def close(self) -> None:
                closed["value"] = True

        with patch("quantagent.api.main.build_event_bus_runtime", return_value=FakeRuntime()):
            app = create_app(self._settings())
            with TestClient(app):
                self.assertFalse(closed["value"])

        self.assertTrue(closed["value"])

    def test_app_lifespan_still_cleans_up_when_event_bus_close_fails(self) -> None:
        close_attempted = {"value": False}
        shutdown_called = {"value": False}

        class FakeRuntime:
            async def close(self) -> None:
                close_attempted["value"] = True
                raise RuntimeError("close failed")

        def fake_shutdown_database(app) -> None:
            shutdown_called["value"] = True

        with (
            patch("quantagent.api.main.build_event_bus_runtime", return_value=FakeRuntime()),
            patch("quantagent.api.main.shutdown_database", side_effect=fake_shutdown_database),
        ):
            app = create_app(self._settings())
            with self.assertRaisesRegex(RuntimeError, "close failed"):
                with TestClient(app):
                    self.assertIsNotNone(app.state.event_bus_runtime)

        self.assertTrue(close_attempted["value"])
        self.assertTrue(shutdown_called["value"])
        self.assertIsNone(app.state.event_bus_runtime)

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
        self.assertEqual(response.headers["X-Trace-ID"], body["error"]["trace_id"])
        self.assertEqual(body["code"], 40000)
        self.assertEqual(body["error"]["code"], "BAD_REQUEST")
        self.assertRegex(body["error"]["trace_id"], r"^[0-9a-f]{32}$")
        self.assertEqual(body["msg"], "参数错误")

    def test_traceparent_sets_trace_id_for_error_envelope_and_response_header(self) -> None:
        self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
        response = self.client.get(
            "/api/v1/debug/error",
            headers={"traceparent": "00-1234567890abcdef1234567890abcdef-1234567890abcdef-01"},
        )
        body = response.json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.headers["X-Trace-ID"], "1234567890abcdef1234567890abcdef")
        self.assertEqual(body["error"]["trace_id"], "1234567890abcdef1234567890abcdef")

    def test_unhandled_error_response_includes_trace_headers(self) -> None:
        router = APIRouter(prefix="/api/v1/test-unhandled")

        @router.get("/error")
        def unhandled_error() -> None:
            raise RuntimeError("boom")

        app = create_app(self._settings(AUTH_ENABLED=False))
        app.include_router(router)
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/test-unhandled/error", headers={"X-Request-ID": "req-unhandled"})

        body = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.headers["X-Request-ID"], "req-unhandled")
        self.assertEqual(response.headers["X-Request-ID"], body["error"]["request_id"])
        self.assertEqual(response.headers["X-Trace-ID"], body["error"]["trace_id"])

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

    def test_agent_debug_sse_streams_nvda_fixture_events(self) -> None:
        self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})

        with self.client.stream(
            "POST",
            "/api/v1/debug/agent-runs/fixtures/semiconductor-nvda-earnings/stream",
            json={"scenario": "primary"},
            headers={"Accept": "text/event-stream"},
        ) as response:
            body = "".join(response.iter_text())

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        self.assertIn("event: run.started", body)
        self.assertIn("event: todo.updated", body)
        self.assertIn("event: subagent.started", body)
        self.assertIn("event: tool.completed", body)
        self.assertIn("event: artifact.created", body)
        self.assertIn("event: run.completed", body)
        self.assertIn('"trade_decision":"submit_dry_run_open_long"', body)
        self.assertNotIn("sk-", body)
        self.assertNotIn("traceback", body.lower())

    def test_agent_debug_unknown_fixture_uses_envelope(self) -> None:
        self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})

        response = self.client.post("/api/v1/debug/agent-runs/fixtures/missing/stream", json={"scenario": "primary"})
        body = response.json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["error"]["code"], "BAD_REQUEST")
        self.assertEqual(body["msg"], "未知 Agent debug fixture")

    def test_agent_debug_routes_disabled_in_production(self) -> None:
        production_app = create_app(self._settings(APP_ENV="production"))
        with TestClient(production_app) as client:
            response = client.post(
                "/api/v1/debug/agent-runs/fixtures/semiconductor-nvda-earnings/stream",
                json={"scenario": "primary"},
            )

        self.assertEqual(response.status_code, 404)

    def test_production_rejects_disabled_auth(self) -> None:
        with self.assertRaisesRegex(ValueError, "AUTH_ENABLED=false"):
            self._settings(
                APP_ENV="production",
                AUTH_ENABLED=False,
                AUTH_ADMIN_PASSWORD="prod-admin-password",
                AUTH_SESSION_SECRET="production-session-secret-0123456789abcdef",
            )

    def test_production_login_uses_secure_cookie(self) -> None:
        production_app = create_app(
            self._settings(
                APP_ENV="production",
                AUTH_ADMIN_PASSWORD="prod-admin-password",
                AUTH_SESSION_SECRET="production-session-secret-0123456789abcdef",
            )
        )
        with TestClient(production_app) as client:
            response = client.post("/api/v1/auth/login", json={"password": "prod-admin-password"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("Secure", response.headers["set-cookie"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])

    def test_non_development_env_requires_explicit_auth_credentials(self) -> None:
        with self.assertRaisesRegex(ValueError, "AUTH_SESSION_SECRET is required when APP_ENV is not development/test/local"):
            Settings(_env_file=None, APP_ENV="staging", AUTH_ADMIN_PASSWORD="local-password")

    def test_production_rejects_whitespace_only_auth_credentials(self) -> None:
        with self.assertRaisesRegex(ValueError, "AUTH_ADMIN_PASSWORD is required in production"):
            Settings(
                _env_file=None,
                APP_ENV="production",
                AUTH_ADMIN_PASSWORD="   ",
                AUTH_SESSION_SECRET="prod-session-secret-0123456789abcdef",
            )

        with self.assertRaisesRegex(ValueError, "AUTH_SESSION_SECRET is required in production"):
            Settings(
                _env_file=None,
                APP_ENV="production",
                AUTH_ADMIN_PASSWORD="prod-admin-password",
                AUTH_SESSION_SECRET="   ",
            )

    def test_staging_and_production_reject_placeholder_auth_credentials(self) -> None:
        with self.assertRaisesRegex(ValueError, "AUTH_ADMIN_PASSWORD must not use a placeholder"):
            Settings(
                _env_file=None,
                APP_ENV="staging",
                AUTH_ADMIN_PASSWORD="change-me",
                AUTH_SESSION_SECRET="staging-session-secret-0123456789abcdef",
            )

        with self.assertRaisesRegex(ValueError, "AUTH_SESSION_SECRET must not use a placeholder"):
            Settings(
                _env_file=None,
                APP_ENV="production",
                AUTH_ADMIN_PASSWORD="prod-admin-password",
                AUTH_SESSION_SECRET="change-me",
                AUTH_COOKIE_SECURE=True,
            )

        with self.assertRaisesRegex(ValueError, "AUTH_ADMIN_PASSWORD must not use a placeholder"):
            Settings(
                _env_file=None,
                APP_ENV="staging",
                AUTH_ADMIN_PASSWORD="12345678",
                AUTH_SESSION_SECRET="staging-session-secret-0123456789abcdef",
            )

    def test_staging_and_production_reject_weak_auth_credentials(self) -> None:
        with self.assertRaisesRegex(ValueError, "AUTH_ADMIN_PASSWORD must be at least 12 characters"):
            Settings(
                _env_file=None,
                APP_ENV="staging",
                AUTH_ADMIN_PASSWORD="short",
                AUTH_SESSION_SECRET="staging-session-secret-0123456789abcdef",
            )

        with self.assertRaisesRegex(ValueError, "AUTH_ADMIN_PASSWORD must be at least 12 characters"):
            Settings(
                _env_file=None,
                APP_ENV="production",
                AUTH_ADMIN_PASSWORD="short-prod",
                AUTH_SESSION_SECRET="production-session-secret-0123456789abcdef",
                AUTH_COOKIE_SECURE=True,
            )

        with self.assertRaisesRegex(ValueError, "AUTH_SESSION_SECRET must be at least 32 characters"):
            Settings(
                _env_file=None,
                APP_ENV="production",
                AUTH_ADMIN_PASSWORD="prod-admin-password",
                AUTH_SESSION_SECRET="too-short-secret",
                AUTH_COOKIE_SECURE=True,
            )

        with self.assertRaisesRegex(ValueError, "AUTH_SESSION_SECRET must be at least 32 characters"):
            Settings(
                _env_file=None,
                APP_ENV="staging",
                AUTH_ADMIN_PASSWORD="staging-admin-password",
                AUTH_SESSION_SECRET="stage-short-secret",
            )

    def test_non_dev_session_secret_allows_non_placeholder_words(self) -> None:
        settings = Settings(
            _env_file=None,
            APP_ENV="staging",
            AUTH_ADMIN_PASSWORD="staging-admin-password",
            AUTH_SESSION_SECRET="device-session-secret-0123456789abcdef",
        )
        self.assertEqual(settings.AUTH_SESSION_SECRET, "device-session-secret-0123456789abcdef")

    def test_test_env_still_receives_weak_auth_defaults(self) -> None:
        settings = Settings(_env_file=None, APP_ENV="test")
        self.assertEqual(settings.AUTH_ADMIN_PASSWORD, "12345678")
        self.assertEqual(settings.AUTH_SESSION_SECRET, "dev-session-secret-change-me")

    def test_api_host_and_port_use_prefixed_names(self) -> None:
        settings = Settings(
            _env_file=None,
            API_HOST="0.0.0.0",
            API_PORT=9000,
            AUTH_ADMIN_PASSWORD="test-admin-password",
            AUTH_SESSION_SECRET="test-session-secret",
        )
        self.assertEqual(settings.API_HOST, "0.0.0.0")
        self.assertEqual(settings.API_PORT, 9000)

    def test_legacy_host_and_port_env_names_still_work(self) -> None:
        settings = Settings(
            _env_file=None,
            HOST="0.0.0.0",
            PORT=9100,
            AUTH_ADMIN_PASSWORD="test-admin-password",
            AUTH_SESSION_SECRET="test-session-secret",
        )
        self.assertEqual(settings.API_HOST, "0.0.0.0")
        self.assertEqual(settings.API_PORT, 9100)

    def test_api_host_and_port_env_names_are_loaded_from_environment(self) -> None:
        with patch.dict(
            os.environ,
            {"API_HOST": "0.0.0.0", "API_PORT": "9200", "AUTH_ADMIN_PASSWORD": "test-admin-password", "AUTH_SESSION_SECRET": "test-session-secret"},
            clear=False,
        ):
            settings = Settings(_env_file=None)
        self.assertEqual(settings.API_HOST, "0.0.0.0")
        self.assertEqual(settings.API_PORT, 9200)

    def test_legacy_host_and_port_env_names_are_still_loaded_from_environment(self) -> None:
        with patch.dict(
            os.environ,
            {"HOST": "0.0.0.0", "PORT": "9300", "AUTH_ADMIN_PASSWORD": "test-admin-password", "AUTH_SESSION_SECRET": "test-session-secret"},
            clear=False,
        ):
            settings = Settings(_env_file=None)
        self.assertEqual(settings.API_HOST, "0.0.0.0")
        self.assertEqual(settings.API_PORT, 9300)

    def test_api_dotenv_overrides_duplicate_root_variable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            api_dir = workspace / "apps/api"
            api_dir.mkdir(parents=True)
            (workspace / ".env").write_text(
                "DATABASE_URL=postgresql+psycopg://root:root@localhost:15432/rootdb\n",
                encoding="utf-8",
            )
            (api_dir / ".env").write_text(
                "DATABASE_URL=postgresql+psycopg://api:api@localhost:15432/apidb\n",
                encoding="utf-8",
            )

            env_files = _build_env_file_paths(cwd=workspace, source_repo_root=workspace, source_api_app_dir=api_dir)
            with patch.dict(os.environ, {"DATABASE_URL": "", "APP_ENV": ""}, clear=False):
                os.environ.pop("DATABASE_URL", None)
                os.environ.pop("APP_ENV", None)
                settings = Settings(_env_file=tuple(str(path) for path in env_files))

        self.assertEqual(settings.DATABASE_URL, "postgresql+psycopg://api:api@localhost:15432/apidb")

    def test_process_environment_overrides_api_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            api_dir = workspace / "apps/api"
            api_dir.mkdir(parents=True)
            (workspace / ".env").write_text("LOG_LEVEL=INFO\n", encoding="utf-8")
            (api_dir / ".env").write_text("LOG_LEVEL=DEBUG\n", encoding="utf-8")
            env_files = _build_env_file_paths(cwd=workspace, source_repo_root=workspace, source_api_app_dir=api_dir)

            with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}, clear=False):
                settings = Settings(_env_file=tuple(str(path) for path in env_files))

        self.assertEqual(settings.LOG_LEVEL, "ERROR")

    def test_notification_ingress_plugin_config_accepts_json_object_string(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            api_dir = workspace / "apps/api"
            api_dir.mkdir(parents=True)
            (api_dir / ".env").write_text(
                'NOTIFICATION_INGRESS_PLUGIN_CONFIG={"public_key":"abc","guild_allowlist":["guild-1","guild-2"]}\n',
                encoding="utf-8",
            )
            env_files = _build_env_file_paths(cwd=workspace, source_repo_root=workspace, source_api_app_dir=api_dir)

            settings = Settings(_env_file=tuple(str(path) for path in env_files))

        self.assertEqual(settings.NOTIFICATION_INGRESS_PLUGIN_CONFIG["public_key"], "abc")
        self.assertEqual(settings.NOTIFICATION_INGRESS_PLUGIN_CONFIG["guild_allowlist"], ["guild-1", "guild-2"])

    def test_app_env_selects_only_matching_api_environment_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            api_dir = workspace / "apps/api"
            api_dir.mkdir(parents=True)
            (api_dir / ".env").write_text("AUTH_ENABLED=true\n", encoding="utf-8")
            (api_dir / ".env.test").write_text("AUTH_ENABLED=false\n", encoding="utf-8")
            (api_dir / ".env.production").write_text("AUTH_ENABLED=true\nLOG_LEVEL=ERROR\n", encoding="utf-8")
            env_files = _build_env_file_paths(app_env="test", cwd=workspace, source_repo_root=workspace, source_api_app_dir=api_dir)

            settings = Settings(_env_file=tuple(str(path) for path in env_files), APP_ENV="test")

        self.assertFalse(settings.AUTH_ENABLED)
        self.assertEqual(settings.LOG_LEVEL, "INFO")
        self.assertIn(api_dir / ".env.test", env_files)
        self.assertNotIn(api_dir / ".env.production", env_files)

    def test_api_local_dotenv_can_select_environment_specific_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            api_dir = workspace / "apps/api"
            api_dir.mkdir(parents=True)
            (api_dir / ".env.local").write_text("APP_ENV=staging\n", encoding="utf-8")
            (api_dir / ".env.staging").write_text(
                "LOG_LEVEL=WARNING\nAUTH_ADMIN_PASSWORD=staging-admin-password\nAUTH_SESSION_SECRET=staging-session-secret-0123456789abcdef\n",
                encoding="utf-8",
            )

            env_files = _build_env_file_paths(cwd=workspace, source_repo_root=workspace, source_api_app_dir=api_dir)
            settings = Settings(_env_file=tuple(str(path) for path in env_files))

        self.assertEqual(settings.APP_ENV, "staging")
        self.assertEqual(settings.LOG_LEVEL, "WARNING")

    def test_selected_environment_local_dotenv_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            api_dir = workspace / "apps/api"
            api_dir.mkdir(parents=True)
            (api_dir / ".env.staging").write_text(
                "API_HOST=127.0.0.1\nAUTH_ADMIN_PASSWORD=staging-admin-password\nAUTH_SESSION_SECRET=staging-session-secret-0123456789abcdef\n",
                encoding="utf-8",
            )
            (api_dir / ".env.staging.local").write_text("API_HOST=0.0.0.0\n", encoding="utf-8")

            env_files = _build_env_file_paths(app_env="staging", cwd=workspace, source_repo_root=workspace, source_api_app_dir=api_dir)
            settings = Settings(_env_file=tuple(str(path) for path in env_files), APP_ENV="staging")

        self.assertEqual(settings.API_HOST, "0.0.0.0")

    def test_app_env_uses_lowercase_when_selecting_environment_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            api_dir = workspace / "apps/api"
            api_dir.mkdir(parents=True)
            (api_dir / ".env.production").write_text(
                "LOG_LEVEL=ERROR\nAUTH_ADMIN_PASSWORD=prod-admin-password\nAUTH_SESSION_SECRET=production-session-secret-0123456789abcdef\n",
                encoding="utf-8",
            )

            env_files = _build_env_file_paths(app_env="Production", cwd=workspace, source_repo_root=workspace, source_api_app_dir=api_dir)
            settings = Settings(_env_file=tuple(str(path) for path in env_files), APP_ENV="Production")

        self.assertIn(api_dir / ".env.production", env_files)
        self.assertNotIn(api_dir / ".env.Production", env_files)
        self.assertEqual(settings.LOG_LEVEL, "ERROR")
        self.assertEqual(settings.APP_ENV, "Production")

    def test_blank_runtime_dir_uses_default_before_log_dir_resolution(self) -> None:
        settings = Settings(
            _env_file=None,
            APP_ENV="test",
            RUNTIME_DIR="",
            LOG_DIR="",
            AUTH_ENABLED=False,
        )

        self.assertEqual(settings.LOG_DIR, (settings.RUNTIME_DIR / "logs" / "api").resolve())

    def test_env_file_paths_do_not_assume_repo_root_when_source_layout_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            env_files = _build_env_file_paths(
                cwd=workspace,
                source_repo_root=None,
                source_api_app_dir=None,
            )

        self.assertEqual(env_files, (workspace / ".env",))

    def test_env_file_paths_from_apps_api_cwd_include_repo_root_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            api_dir = workspace / "apps/api"
            api_dir.mkdir(parents=True)

            env_files = _build_env_file_paths(
                cwd=api_dir,
                source_repo_root=workspace,
                source_api_app_dir=api_dir,
            )

        self.assertEqual(
            env_files,
            (
                workspace / ".env",
                api_dir / ".env",
                api_dir / ".env.local",
            ),
        )

    def test_same_site_none_requires_secure_cookie(self) -> None:
        with self.assertRaisesRegex(ValueError, "AUTH_COOKIE_SAME_SITE=none requires AUTH_COOKIE_SECURE=true"):
            Settings(
                _env_file=None,
                APP_ENV="development",
                AUTH_ADMIN_PASSWORD="test-admin-password",
                AUTH_SESSION_SECRET="test-session-secret",
                AUTH_COOKIE_SAME_SITE="none",
                AUTH_COOKIE_SECURE=False,
            )

    def test_login_success_sets_cookie_and_returns_csrf_token(self) -> None:
        response = self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
        body = response.json()
        session_payload = self._current_session_payload()

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(body["error"])
        self.assertEqual(body["data"]["actor_id"], "local_admin")
        self.assertEqual(body["data"]["actor_type"], "local_single_user")
        self.assertEqual(set(body["data"]["capabilities"]), ALL_CAPABILITIES)
        self.assertTrue(body["data"]["csrf_token"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertEqual(session_payload["v"], SESSION_V2)
        self.assertEqual(session_payload["sub"], "local_admin")
        self.assertEqual(session_payload["actor_type"], "local_single_user")
        self.assertIn("sid", session_payload)
        self.assertIn("iat", session_payload)
        self.assertIn("exp", session_payload)
        self.assertIn("max_exp", session_payload)
        self.assertIn("capabilities", session_payload)
        self.assertNotIn("csrf", session_payload)
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
                    ("POST", "/integrations/notifications/ingress"),
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
                    ("POST", "/integrations/notifications/ingress"),
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
                    ("POST", f"{custom_prefix}/integrations/notifications/ingress"),
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
        session_value = issue_session("local_admin", self.settings, expires_at=1).value
        self.client.cookies.set(self.settings.AUTH_COOKIE_NAME, session_value)

        response = self.client.get("/api/v1/me")
        body = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")

    def test_me_rejects_session_expiring_at_now(self) -> None:
        session_value = issue_session(
            "local_admin",
            self.settings,
            expires_at=int(datetime.now(UTC).timestamp()),
        ).value
        self.client.cookies.set(self.settings.AUTH_COOKIE_NAME, session_value)

        response = self.client.get("/api/v1/me")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    def test_me_returns_actor_capabilities_and_csrf(self) -> None:
        login_response = self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
        login_csrf_token = login_response.json()["data"]["csrf_token"]

        response = self.client.get("/api/v1/me")
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["data"]["actor_id"], "local_admin")
        self.assertEqual(body["data"]["actor_type"], "local_single_user")
        self.assertEqual(set(body["data"]["capabilities"]), ALL_CAPABILITIES)
        self.assertEqual(body["data"]["csrf_token"], login_csrf_token)
        self.assertNotIn(self.settings.AUTH_SESSION_SECRET or "", str(body))
        self.assertNotIn(self.settings.AUTH_COOKIE_NAME, str(body))
        self.assertNotIn("set-cookie", {key.lower() for key in response.headers.keys()})

    def test_me_upgrades_v1_cookie_to_v2_once(self) -> None:
        legacy_session = _issue_v1_session("local_admin", self.settings)
        self.client.cookies.set(self.settings.AUTH_COOKIE_NAME, legacy_session.value)

        response = self.client.get("/api/v1/me")
        body = response.json()
        upgraded_payload = self._current_session_payload()

        self.assertEqual(response.status_code, 200)
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertEqual(upgraded_payload["v"], SESSION_V2)
        self.assertEqual(upgraded_payload["max_exp"], legacy_session.data.expires_at)
        self.assertNotEqual(body["data"]["csrf_token"], legacy_session.data.csrf_token)

    def test_refresh_sets_cookie_when_idle_time_is_low_and_keeps_csrf_stable(self) -> None:
        now_timestamp = int(datetime.now(UTC).timestamp())
        issued_session = issue_session(
            "local_admin",
            self.settings,
            issued_at=now_timestamp - 60,
            expires_at=now_timestamp + 10,
            max_expires_at=now_timestamp + 600,
        )
        self.client.cookies.set(self.settings.AUTH_COOKIE_NAME, issued_session.value)

        response = self.client.post(
            "/api/v1/auth/refresh",
            headers={self.settings.AUTH_CSRF_HEADER_NAME: issued_session.data.csrf_token},
        )
        body = response.json()
        refreshed_payload = self._current_session_payload()

        self.assertEqual(response.status_code, 200)
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertEqual(body["data"]["csrf_token"], issued_session.data.csrf_token)
        self.assertGreater(body["data"]["expires_at"], issued_session.data.expires_at)
        self.assertEqual(body["data"]["max_expires_at"], issued_session.data.max_expires_at)
        self.assertEqual(refreshed_payload["sid"], issued_session.data.session_id)

    def test_refresh_returns_current_session_without_rewriting_cookie_when_above_threshold(self) -> None:
        now_timestamp = int(datetime.now(UTC).timestamp())
        issued_session = issue_session(
            "local_admin",
            self.settings,
            issued_at=now_timestamp - 60,
            expires_at=now_timestamp + 4000,
            max_expires_at=now_timestamp + 5000,
        )
        self.client.cookies.set(self.settings.AUTH_COOKIE_NAME, issued_session.value)

        response = self.client.post(
            "/api/v1/auth/refresh",
            headers={self.settings.AUTH_CSRF_HEADER_NAME: issued_session.data.csrf_token},
        )
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["data"]["csrf_token"], issued_session.data.csrf_token)
        self.assertEqual(body["data"]["expires_at"], issued_session.data.expires_at)
        self.assertEqual(body["data"]["max_expires_at"], issued_session.data.max_expires_at)
        self.assertNotIn("set-cookie", {key.lower() for key in response.headers.keys()})

    def test_refresh_does_not_extend_beyond_absolute_expiration(self) -> None:
        now_timestamp = int(datetime.now(UTC).timestamp())
        issued_session = issue_session(
            "local_admin",
            self.settings,
            issued_at=now_timestamp - 60,
            expires_at=now_timestamp + 10,
            max_expires_at=now_timestamp + 10,
        )
        self.client.cookies.set(self.settings.AUTH_COOKIE_NAME, issued_session.value)

        response = self.client.post(
            "/api/v1/auth/refresh",
            headers={self.settings.AUTH_CSRF_HEADER_NAME: issued_session.data.csrf_token},
        )
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["data"]["expires_at"], issued_session.data.expires_at)
        self.assertEqual(body["data"]["max_expires_at"], issued_session.data.max_expires_at)
        self.assertNotIn("set-cookie", {key.lower() for key in response.headers.keys()})

    def test_refresh_rejects_missing_csrf_token(self) -> None:
        self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
        response = self.client.post("/api/v1/auth/refresh")
        body = response.json()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(body["error"]["code"], "FORBIDDEN")

    def test_refresh_rejects_invalid_csrf_token_without_echoing_it(self) -> None:
        self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
        response = self.client.post("/api/v1/auth/refresh", headers={self.settings.AUTH_CSRF_HEADER_NAME: "bad-token"})
        body = response.json()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(body["error"]["code"], "FORBIDDEN")
        self.assertNotIn("bad-token", str(body))

    def test_refresh_rejects_session_when_absolute_expiration_is_in_the_past(self) -> None:
        now_timestamp = int(datetime.now(UTC).timestamp())
        invalid_payload = {
            "v": SESSION_V2,
            "sid": "expired-session",
            "sub": "local_admin",
            "actor_type": "local_single_user",
            "iat": now_timestamp - 100,
            "exp": now_timestamp + 100,
            "max_exp": now_timestamp - 1,
            "capabilities": sorted(ALL_CAPABILITIES),
        }
        invalid_session = _serialize_session(invalid_payload, self.settings.AUTH_SESSION_SECRET or "")
        self.client.cookies.set(self.settings.AUTH_COOKIE_NAME, invalid_session)

        response = self.client.post(
            "/api/v1/auth/refresh",
            headers={self.settings.AUTH_CSRF_HEADER_NAME: "irrelevant"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

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

    def test_plugin_list_requires_session(self) -> None:
        response = self.client.get("/api/v1/plugins")
        body = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")

    def test_plugin_list_detail_and_config_schema_use_envelope(self) -> None:
        self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})

        list_response = self.client.get("/api/v1/plugins")
        list_body = list_response.json()
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_body["code"], 0)
        self.assertIsNone(list_body["error"])

        plugins = list_body["data"]
        placeholder = next(
            plugin for plugin in plugins if plugin["id"] == "quantagent.official.source.placeholder"
        )
        self.assertEqual(placeholder["source"], "official")
        self.assertEqual(placeholder["status"], "valid")
        self.assertEqual(placeholder["manifest"]["type"], "source")
        self.assertEqual(placeholder["path"], "plugins/sources/placeholder-source")

        example_industry = next(
            plugin for plugin in plugins if plugin["id"] == "quantagent.official.industry.example"
        )
        self.assertEqual(example_industry["manifest"]["type"], "industry")
        self.assertEqual(example_industry["path"], "plugins/industries/example-industry")
        self.assertEqual(
            example_industry["manifest"]["source_bindings"],
            [
                {
                    "source_plugin_id": "quantagent.official.source.rss",
                    "required": True,
                    "config_template": "templates/source_bindings/rss.default.yaml",
                },
                {
                    "source_plugin_id": "quantagent.official.source.readability",
                    "required": False,
                    "config_template": "templates/source_bindings/readability.fallback.yaml",
                },
            ],
        )

        detail_response = self.client.get("/api/v1/plugins/quantagent.official.source.placeholder")
        detail_body = detail_response.json()
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_body["data"]["overview"]["plugin_id"], "quantagent.official.source.placeholder")
        self.assertEqual(detail_body["data"]["overview"]["type"], "source")
        self.assertEqual(detail_body["data"]["config_summary"]["availability"]["state"], "not_configured")
        self.assertEqual(detail_body["data"]["dependency_summary"]["availability"]["state"], "ready")
        self.assertEqual(detail_body["data"]["health_summary"]["availability"]["state"], "not_collected")
        self.assertEqual(
            {item["action"] for item in detail_body["data"]["allowed_actions"]},
            {"enable", "disable", "reload", "rescan", "uninstall"},
        )
        self.assertNotIn("plugins/sources/placeholder-source", str(detail_body))
        self.assertNotIn("entrypoint", str(detail_body))

        schema_response = self.client.get("/api/v1/plugins/quantagent.official.source.placeholder/config-schema")
        schema_body = schema_response.json()
        self.assertEqual(schema_response.status_code, 200)
        self.assertEqual(schema_body["data"]["title"], "Demo Placeholder Source Plugin Config")

    def test_plugin_detail_config_view_masks_secret_grade_fields(self) -> None:
        self._login()

        response = self.client.get("/api/v1/plugins/quantagent.official.notification.discord/config")
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["data"]["availability"]["state"], "not_configured")
        entries_by_key = {item["key"]: item for item in body["data"]["entries"]}
        self.assertEqual(entries_by_key["webhook_secret_ref"]["display_mode"], "unset")
        self.assertTrue(entries_by_key["webhook_secret_ref"]["is_sensitive"])
        self.assertEqual(entries_by_key["public_key"]["display_mode"], "unset")
        self.assertTrue(entries_by_key["public_key"]["is_sensitive"])
        self.assertNotIn("Discord webhook URL", str(body))

    def test_plugin_detail_section_visibility_uses_forbidden_availability(self) -> None:
        reduced_capabilities = frozenset({"plugin.configure"})
        issued_session = issue_session("local_admin", self.settings, capabilities=reduced_capabilities)
        self.client.cookies.set(self.settings.AUTH_COOKIE_NAME, issued_session.value)

        detail_response = self.client.get("/api/v1/plugins/quantagent.official.source.placeholder")
        detail_body = detail_response.json()
        health_response = self.client.get("/api/v1/plugins/quantagent.official.source.placeholder/health")
        audit_response = self.client.get("/api/v1/plugins/quantagent.official.source.placeholder/audit")

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_body["data"]["overview"]["plugin_id"], "quantagent.official.source.placeholder")
        self.assertEqual(detail_body["data"]["config_summary"]["availability"]["state"], "not_configured")
        self.assertEqual(detail_body["data"]["health_summary"]["availability"]["state"], "forbidden")
        self.assertEqual(detail_body["data"]["audit_summary"]["availability"]["state"], "forbidden")
        self.assertTrue(
            all(item["disabled_reason"] == "permission_denied" for item in detail_body["data"]["allowed_actions"])
        )

        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.json()["data"]["availability"]["state"], "forbidden")
        self.assertEqual(audit_response.status_code, 200)
        self.assertEqual(audit_response.json()["data"]["availability"]["state"], "forbidden")

    def test_approval_list_detail_and_action_use_persistent_source(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        app = create_app(self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}"))

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            csrf_token = self._login_with_client(client, self.settings)
            self._seed_approval(client, "approval-api-1")
            list_response = client.get("/api/v1/approvals")
            detail_response = client.get("/api/v1/approvals/approval-api-1")
            action_response = client.post(
                "/api/v1/approvals/approval-api-1/actions/reject",
                headers={"X-CSRF-Token": csrf_token, "X-Request-ID": "req-approval-action"},
                json={"input_id": "input-api-1", "channel": "web", "reason": "reject from api"},
            )
            with client.app.state.db_session_factory() as session:
                repository = SQLAlchemyApprovalRepository(session)
                audit_records = repository.list_audit_records("approval-api-1")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["data"]["items"][0]["id"], "approval-api-1")
        self.assertIsNotNone(list_response.json()["data"]["items"][0]["created_at"])
        self.assertIsNotNone(list_response.json()["data"]["items"][0]["updated_at"])
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["data"]["action_request_summary"]["id"], "action-api-1")
        self.assertIsNotNone(detail_response.json()["data"]["created_at"])
        self.assertIsNotNone(detail_response.json()["data"]["updated_at"])
        self.assertEqual(action_response.status_code, 200)
        action_body = action_response.json()
        self.assertEqual(action_body["data"]["decision"]["status"], "rejected")
        self.assertEqual(action_body["data"]["approval"]["status"], "completed")

        self.assertEqual(audit_records[-1].action, "decision.rejected")
        self.assertEqual(audit_records[-1].channel, "web")
        self.assertEqual(audit_records[-1].request_id, "req-approval-action")

    def test_approval_full_chain_smoke_from_event_bus_to_routes(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        app = create_app(self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}"))

        class RecordingHandler:
            def __init__(self) -> None:
                self.seen: list[EventEnvelope] = []

            async def handle(self, envelope: EventEnvelope) -> None:
                self.seen.append(envelope)

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            action_bus = InMemoryEventBus()
            approval_requested = RecordingHandler()
            notification_requested = RecordingHandler()
            asyncio.run(
                action_bus.subscribe(
                    topics=("approval.requested",),
                    group_id="approval-smoke",
                    handler=approval_requested,
                )
            )
            asyncio.run(
                action_bus.subscribe(
                    topics=("notification.requested",),
                    group_id="approval-smoke",
                    handler=notification_requested,
                )
            )
            with client.app.state.db_session_factory() as session:
                repository = SQLAlchemyApprovalRepository(session)

                next_id_by_prefix: dict[str, int] = {}

                def smoke_id(prefix: str) -> str:
                    next_id_by_prefix[prefix] = next_id_by_prefix.get(prefix, 0) + 1
                    return f"{prefix}-smoke-{next_id_by_prefix[prefix]}"

                service = ApprovalOrchestrationService(
                    repository=repository,
                    event_publisher=ApprovalEventPublisher(action_bus),
                    id_factory=smoke_id,
                )
                asyncio.run(
                    action_bus.subscribe(
                        topics=("action.requested",),
                        group_id="approval",
                        handler=ActionRequestedHandler(service),
                    )
                )
                for suffix in ("approve", "reject", "reanalysis"):
                    action = ApprovalActionRequestModel(
                        id=f"action-smoke-{suffix}",
                        action_type="adjust_strategy",
                        action_side="increase_risk",
                        target_type="strategy",
                        target_id=f"strategy-smoke-{suffix}",
                        risk_flags=("high_risk",),
                        proposed_payload={"summary": f"smoke masked payload {suffix}"},
                        correlation_id=f"corr-approval-smoke-{suffix}",
                    )
                    asyncio.run(
                        action_bus.publish(
                            EventEnvelope(
                                id=f"event-action-smoke-{suffix}",
                                topic="action.requested",
                                producer="api-test",
                                created_at="2026-06-04T00:00:00+00:00",
                                correlation_id=f"corr-approval-smoke-{suffix}",
                                payload=action.to_mapping(),
                            )
                        )
                    )
                session.commit()

            csrf_token = self._login_with_client(client, self.settings)
            list_before = client.get("/api/v1/approvals")
            approve_detail_before = client.get("/api/v1/approvals/approval-smoke-1")
            reject_detail_before = client.get("/api/v1/approvals/approval-smoke-2")
            reanalysis_detail_before = client.get("/api/v1/approvals/approval-smoke-3")
            route_bus = InMemoryEventBus()
            approval_completed = RecordingHandler()
            asyncio.run(
                route_bus.subscribe(
                    topics=("approval.completed",),
                    group_id="approval-smoke",
                    handler=approval_completed,
                )
            )
            client.app.state.approval_event_bus = route_bus
            client.app.state.approval_event_publisher = ApprovalEventPublisher(route_bus)
            approve_response = client.post(
                "/api/v1/approvals/approval-smoke-1/actions/approve",
                headers={"X-CSRF-Token": csrf_token, "X-Request-ID": "req-approval-smoke-approve"},
                json={"input_id": "input-smoke-approve", "channel": "web", "reason": "approve via smoke"},
            )
            reject_response = client.post(
                "/api/v1/approvals/approval-smoke-2/actions/reject",
                headers={"X-CSRF-Token": csrf_token, "X-Request-ID": "req-approval-smoke"},
                json={"input_id": "input-smoke", "channel": "web", "reason": "reject via smoke"},
            )
            reanalysis_response = client.post(
                "/api/v1/approvals/approval-smoke-3/actions/request-reanalysis",
                headers={"X-CSRF-Token": csrf_token, "X-Request-ID": "req-approval-smoke-reanalysis"},
                json={
                    "input_id": "input-smoke-reanalysis",
                    "channel": "web",
                    "comment": "reanalysis via smoke",
                },
            )
            approve_detail_after = client.get("/api/v1/approvals/approval-smoke-1")
            reject_detail_after = client.get("/api/v1/approvals/approval-smoke-2")
            reanalysis_detail_after = client.get("/api/v1/approvals/approval-smoke-3")
            list_after = client.get("/api/v1/approvals")
            with client.app.state.db_session_factory() as session:
                repository = SQLAlchemyApprovalRepository(session)
                approve_inputs = repository.list_inputs("approval-smoke-1")
                approve_decisions = repository.list_decisions("approval-smoke-1")
                approve_audit_records = repository.list_audit_records("approval-smoke-1")
                reject_inputs = repository.list_inputs("approval-smoke-2")
                reject_evaluations = repository.list_evaluations("approval-smoke-2")
                reject_decisions = repository.list_decisions("approval-smoke-2")
                reject_audit_records = repository.list_audit_records("approval-smoke-2")
                reanalysis_inputs = repository.list_inputs("approval-smoke-3")
                reanalysis_decisions = repository.list_decisions("approval-smoke-3")
                reanalysis_audit_records = repository.list_audit_records("approval-smoke-3")

        self.assertEqual(len(approval_requested.seen), 3)
        self.assertEqual(
            [event.payload["approval_id"] for event in approval_requested.seen],
            ["approval-smoke-1", "approval-smoke-2", "approval-smoke-3"],
        )
        self.assertEqual(
            [event.payload["action_request_id"] for event in approval_requested.seen],
            ["action-smoke-approve", "action-smoke-reject", "action-smoke-reanalysis"],
        )
        self.assertEqual(len(notification_requested.seen), 3)
        self.assertEqual(
            [event.payload["approval_id"] for event in notification_requested.seen],
            ["approval-smoke-1", "approval-smoke-2", "approval-smoke-3"],
        )

        self.assertEqual(list_before.status_code, 200)
        self.assertEqual(
            [item["id"] for item in list_before.json()["data"]["items"]],
            ["approval-smoke-3", "approval-smoke-2", "approval-smoke-1"],
        )
        self.assertEqual({item["status"] for item in list_before.json()["data"]["items"]}, {"pending"})
        self.assertEqual(approve_detail_before.status_code, 200)
        self.assertEqual(approve_detail_before.json()["data"]["action_request_summary"]["id"], "action-smoke-approve")
        self.assertEqual(approve_detail_before.json()["data"]["inputs"], [])
        self.assertEqual(reject_detail_before.status_code, 200)
        self.assertEqual(reject_detail_before.json()["data"]["action_request_summary"]["id"], "action-smoke-reject")
        self.assertEqual(reanalysis_detail_before.status_code, 200)
        self.assertEqual(
            reanalysis_detail_before.json()["data"]["action_request_summary"]["id"],
            "action-smoke-reanalysis",
        )

        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.json()["data"]["evaluation"]["interpreted_intent"], "approve")
        self.assertEqual(approve_response.json()["data"]["decision"]["status"], "policy_gate_failed")
        self.assertEqual(approve_response.json()["data"]["approval"]["status"], "blocked")
        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(reject_response.json()["data"]["evaluation"]["interpreted_intent"], "reject")
        self.assertEqual(reject_response.json()["data"]["decision"]["status"], "rejected")
        self.assertEqual(reject_response.json()["data"]["approval"]["status"], "completed")
        self.assertEqual(reanalysis_response.status_code, 200)
        self.assertEqual(reanalysis_response.json()["data"]["evaluation"]["interpreted_intent"], "request_reanalysis")
        self.assertEqual(reanalysis_response.json()["data"]["decision"]["status"], "reanalysis_requested")
        self.assertEqual(reanalysis_response.json()["data"]["approval"]["status"], "completed")
        self.assertEqual(
            [event.payload["status"] for event in approval_completed.seen],
            ["policy_gate_failed", "rejected", "reanalysis_requested"],
        )

        approve_after_data = approve_detail_after.json()["data"]
        reject_after_data = reject_detail_after.json()["data"]
        reanalysis_after_data = reanalysis_detail_after.json()["data"]
        self.assertEqual(approve_after_data["status"], "blocked")
        self.assertEqual(approve_after_data["latest_decision_summary"]["status"], "policy_gate_failed")
        self.assertEqual(approve_after_data["inputs"][0]["structured_payload"]["intent"], "approve")
        self.assertEqual(approve_after_data["evaluations"][0]["interpreted_intent"], "approve")
        self.assertEqual(approve_after_data["decisions"][0]["status"], "policy_gate_failed")
        self.assertEqual(approve_after_data["decisions"][0]["request_id"], "req-approval-smoke-approve")
        self.assertEqual(approve_after_data["audit_refs"][0]["action"], "decision.policy_gate_failed")
        self.assertEqual(reject_after_data["status"], "completed")
        self.assertEqual(reject_after_data["latest_decision_summary"]["status"], "rejected")
        self.assertEqual(reject_after_data["inputs"][0]["structured_payload"]["intent"], "reject")
        self.assertEqual(reject_after_data["evaluations"][0]["interpreted_intent"], "reject")
        self.assertEqual(reject_after_data["decisions"][0]["status"], "rejected")
        self.assertEqual(reject_after_data["decisions"][0]["request_id"], "req-approval-smoke")
        self.assertEqual(reject_after_data["audit_refs"][0]["action"], "decision.rejected")
        self.assertEqual(reanalysis_after_data["status"], "completed")
        self.assertEqual(reanalysis_after_data["latest_decision_summary"]["status"], "reanalysis_requested")
        self.assertEqual(reanalysis_after_data["inputs"][0]["structured_payload"]["intent"], "request_reanalysis")
        self.assertEqual(reanalysis_after_data["evaluations"][0]["interpreted_intent"], "request_reanalysis")
        self.assertEqual(reanalysis_after_data["decisions"][0]["status"], "reanalysis_requested")
        self.assertEqual(reanalysis_after_data["decisions"][0]["request_id"], "req-approval-smoke-reanalysis")
        self.assertEqual(reanalysis_after_data["audit_refs"][0]["action"], "decision.reanalysis_requested")
        self.assertEqual(
            {item["id"]: item["latest_decision_summary"]["status"] for item in list_after.json()["data"]["items"]},
            {
                "approval-smoke-1": "policy_gate_failed",
                "approval-smoke-2": "rejected",
                "approval-smoke-3": "reanalysis_requested",
            },
        )

        self.assertEqual(approve_inputs[0].id, "input-smoke-approve")
        self.assertEqual(approve_inputs[0].structured_payload["request_id"], "req-approval-smoke-approve")
        self.assertEqual(approve_decisions[-1].status.value, "policy_gate_failed")
        self.assertEqual(approve_decisions[-1].request_id, "req-approval-smoke-approve")
        self.assertEqual(approve_audit_records[-1].request_id, "req-approval-smoke-approve")
        self.assertEqual(reject_inputs[0].id, "input-smoke")
        self.assertEqual(reject_inputs[0].structured_payload["request_id"], "req-approval-smoke")
        self.assertEqual(reject_evaluations[0].interpreted_intent.value, "reject")
        self.assertEqual(reject_decisions[-1].status.value, "rejected")
        self.assertEqual(reject_decisions[-1].request_id, "req-approval-smoke")
        self.assertEqual(reject_audit_records[-1].request_id, "req-approval-smoke")
        self.assertEqual(reanalysis_inputs[0].id, "input-smoke-reanalysis")
        self.assertEqual(reanalysis_inputs[0].structured_payload["request_id"], "req-approval-smoke-reanalysis")
        self.assertEqual(reanalysis_decisions[-1].status.value, "reanalysis_requested")
        self.assertEqual(reanalysis_decisions[-1].request_id, "req-approval-smoke-reanalysis")
        self.assertEqual(reanalysis_audit_records[-1].request_id, "req-approval-smoke-reanalysis")

    def test_approval_routes_enforce_capability_not_found_and_body_intent_conflict(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        app = create_app(self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}"))

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            self._seed_approval(client, "approval-api-1")
            issued_session = issue_session("local_admin", self.settings, capabilities=frozenset({APPROVAL_APPROVE_CAPABILITY}))
            client.cookies.set(self.settings.AUTH_COOKIE_NAME, issued_session.value)
            forbidden_response = client.get("/api/v1/approvals")
            csrf_token = issued_session.data.csrf_token
            conflict_response = client.post(
                "/api/v1/approvals/approval-api-1/actions/approve",
                headers={"X-CSRF-Token": csrf_token},
                json={"input_id": "input-conflict", "channel": "web", "structured_payload": {"intent": "reject"}},
            )
            with client.app.state.db_session_factory() as session:
                repository = SQLAlchemyApprovalRepository(session)
                conflict_inputs = repository.list_inputs("approval-api-1")
            action_missing_response = client.post(
                "/api/v1/approvals/missing-approval/actions/reject",
                headers={"X-CSRF-Token": csrf_token},
                json={"input_id": "input-missing", "channel": "web", "reason": "reject missing approval"},
            )
            read_session = issue_session("local_admin", self.settings, capabilities=frozenset({APPROVAL_READ_CAPABILITY}))
            client.cookies.set(self.settings.AUTH_COOKIE_NAME, read_session.value)
            missing_response = client.get("/api/v1/approvals/missing-approval")

        self.assertEqual(forbidden_response.status_code, 403)
        self.assertEqual(forbidden_response.json()["error"]["request_id"], forbidden_response.headers["X-Request-ID"])
        self.assertEqual(conflict_response.status_code, 400)
        self.assertEqual(conflict_response.json()["error"]["code"], "BAD_REQUEST")
        self.assertEqual(conflict_inputs, ())
        self.assertEqual(missing_response.status_code, 404)
        self.assertEqual(missing_response.json()["error"]["details"]["approval_id"], "missing-approval")
        self.assertEqual(action_missing_response.status_code, 404)
        self.assertEqual(action_missing_response.json()["error"]["details"]["approval_id"], "missing-approval")

    def test_approval_request_reanalysis_records_intent_without_runtime_side_effect(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        app = create_app(self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}"))

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            csrf_token = self._login_with_client(client, self.settings)
            self._seed_approval(client, "approval-api-1")
            response = client.post(
                "/api/v1/approvals/approval-api-1/actions/request-reanalysis",
                headers={"X-CSRF-Token": csrf_token},
                json={"input_id": "input-reanalysis", "channel": "web", "comment": "please re-check"},
            )
            with client.app.state.db_session_factory() as session:
                repository = SQLAlchemyApprovalRepository(session)
                decision = repository.latest_decision("approval-api-1")
                inputs = repository.list_inputs("approval-api-1")

            self.assertFalse(hasattr(client.app.state, "agent_runtime"))
            self.assertFalse(hasattr(client.app.state, "scheduler"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["decision"]["status"], "reanalysis_requested")
        self.assertEqual(decision.status.value, "reanalysis_requested")
        self.assertEqual(inputs[0].structured_payload["intent"], "request_reanalysis")

    def test_plugin_list_uses_repo_root_even_when_api_runtime_directory_exists(self) -> None:
        self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})

        from quantagent.api.services import plugin_registry as plugin_registry_service

        repo_root = next(
            parent
            for parent in Path(__file__).resolve().parents
            if (parent / "pyproject.toml").is_file()
            and (parent / "apps" / "api").is_dir()
            and (parent / "plugins").is_dir()
        )
        api_runtime_dir = repo_root / "apps" / "api" / "runtime"
        api_runtime_dir.mkdir(parents=True, exist_ok=True)

        plugin_registry_service.find_repo_root.cache_clear()
        self.addCleanup(plugin_registry_service.find_repo_root.cache_clear)

        with patch("pathlib.Path.cwd", return_value=api_runtime_dir):
            response = self.client.get("/api/v1/plugins")
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["code"], 0)
        self.assertIn(
            "quantagent.official.source.placeholder",
            {plugin["id"] for plugin in body["data"]},
        )

    def test_plugin_detail_unknown_id_uses_not_found_envelope(self) -> None:
        self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})

        response = self.client.get("/api/v1/plugins/missing.plugin")
        body = response.json()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(body["error"]["code"], "NOT_FOUND")
        self.assertEqual(body["error"]["details"], {"plugin_id": "missing.plugin"})

    def test_plugin_rescan_requires_csrf_and_returns_summary(self) -> None:
        login_response = self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})

        forbidden_response = self.client.post("/api/v1/plugins/actions/rescan")
        self.assertEqual(forbidden_response.status_code, 403)
        self.assertEqual(forbidden_response.json()["error"]["code"], "FORBIDDEN")

        csrf_token = login_response.json()["data"]["csrf_token"]
        response = self.client.post(
            "/api/v1/plugins/actions/rescan",
            headers={self.settings.AUTH_CSRF_HEADER_NAME: csrf_token},
        )
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["code"], 0)
        self.assertGreaterEqual(body["data"]["summary"]["total"], 1)
        self.assertTrue(body["data"]["plugins"])

    def test_plugin_config_schema_for_invalid_plugin_uses_bad_request_envelope(self) -> None:
        app = create_app(self._settings())
        with tempfile.TemporaryDirectory() as tmpdir:
            root = os.path.abspath(tmpdir)
            invalid_plugin = os.path.join(root, "plugins", "invalid")
            os.makedirs(invalid_plugin)
            with open(os.path.join(invalid_plugin, "plugin.yaml"), "w", encoding="utf-8") as manifest_file:
                manifest_file.write(
                    "id: invalid.schema\n"
                    "name: Invalid Schema\n"
                    "type: source\n"
                    "version: 0.1.0\n"
                    "entrypoint: invalid:plugin\n"
                    "capabilities:\n"
                    "  - source.fetch\n"
                    "config_schema: missing.json\n"
                )
            app.state.plugin_registry = PluginRegistry(
                RegistryScanner(
                    official_root=os.path.join(root, "plugins"),
                    runtime_root=os.path.join(root, "runtime", "plugins"),
                )
            )

            with TestClient(app) as client:
                client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
                response = client.get("/api/v1/plugins/invalid.schema/config-schema")

        body = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["error"]["code"], "BAD_REQUEST")
        self.assertEqual(body["error"]["details"]["plugin"]["id"], "invalid.schema")
        self.assertEqual(set(body["error"]["details"]["plugin"]["last_error"]), {"code", "stage", "retryable"})
        self.assertEqual(
            body["error"]["details"]["plugin"]["last_error"]["code"],
            "PLUGIN_CONFIG_SCHEMA_NOT_FOUND",
        )

    def test_model_providers_require_session(self) -> None:
        response = self.client.get("/api/v1/models/providers")
        body = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")

    def test_runtime_health_reports_degraded_when_runtime_read_models_are_partial(self) -> None:
        self._login()

        response = self.client.get("/api/v1/runtime/health")
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["data"]["partial_status"], "degraded")
        self.assertEqual(body["data"]["backend_status"]["api"], "healthy")
        self.assertEqual(body["data"]["backend_status"]["scheduler"], "unavailable")
        self.assertEqual(body["data"]["backend_status"]["worker"], "not_configured")
        reasons = {item["reason"] for item in body["data"]["unavailable_resources"]}
        self.assertIn("agent_runs:agent_runs_read_model_missing", reasons)
        self.assertIn("tool_invocations:tool_invocations_read_model_missing", reasons)
        self.assertIn("runtime_errors:runtime_errors_read_model_missing", reasons)

    def test_runtime_list_resources_require_session(self) -> None:
        response = self.client.get("/api/v1/scheduler-runs")
        body = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")

    def test_runtime_unavailable_resources_return_controlled_unavailable_meta(self) -> None:
        self._login()

        response = self.client.get("/api/v1/agents/runs")
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["data"]["items"], [])
        self.assertEqual(body["data"]["meta"]["state"], "unavailable")
        self.assertEqual(body["data"]["meta"]["unavailable"]["status"], "unavailable")
        self.assertIn("agent_runs_read_model_missing", body["data"]["meta"]["unavailable"]["reason"])

    def test_runtime_unavailable_detail_uses_not_found_envelope(self) -> None:
        self._login()

        response = self.client.get("/api/v1/tools/invocations/invoke-001")
        body = response.json()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(body["error"]["code"], "NOT_FOUND")
        self.assertEqual(body["error"]["details"]["reason"], "tool_invocations_read_model_missing")

    def test_scheduler_runs_list_and_detail_follow_runtime_contract(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        app = create_app(self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}"))

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            seed_session = client.app.state.db_session_factory()
            try:
                repository = SchedulerRunRepository(seed_session)
                service = SchedulerRunService(repository)
                run = service.create_run(
                    run_id="run-runtime-001",
                    binding_id="binding-runtime-001",
                    source_plugin_id="quantagent.official.source.rss",
                    source_plugin_version="1.0.0",
                    trigger_mode=PluginTriggerType.INTERVAL,
                    request_id="req-runtime-001",
                    status=PluginRunStatus.RUNNING,
                    started_at=datetime(2026, 6, 1, 8, 0, 0, tzinfo=UTC),
                    timeout_ms=30000,
                )
                service.finish_run(
                    run_id=run.run_id,
                    status=PluginRunStatus.FAILED,
                    finished_at=datetime(2026, 6, 1, 8, 0, 3, tzinfo=UTC),
                    duration_ms=3000,
                    failure_code="PLUGIN_TIMEOUT",
                    failure_message="token=secret123 /Users/me/project failed",
                    failure_stage="invoke",
                    retryable=True,
                    captured_count=2,
                )
                seed_session.commit()
            finally:
                seed_session.close()
            login_response = client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
            self.assertEqual(login_response.status_code, 200)

            list_response = client.get("/api/v1/scheduler-runs", params={"plugin_id": "quantagent.official.source.rss"})
            detail_response = client.get("/api/v1/scheduler-runs/run-runtime-001")

        list_body = list_response.json()
        detail_body = detail_response.json()
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_body["data"]["meta"]["state"], "ready")
        self.assertEqual(list_body["data"]["meta"]["page"]["returned"], 1)
        self.assertEqual(list_body["data"]["items"][0]["run_id"], "run-runtime-001")
        self.assertEqual(list_body["data"]["items"][0]["plugin_id"], "quantagent.official.source.rss")
        self.assertEqual(list_body["data"]["items"][0]["trigger_type"], "interval")
        self.assertEqual(list_body["data"]["items"][0]["error_summary"]["error_code"], "PLUGIN_TIMEOUT")
        self.assertNotIn("secret123", list_body["data"]["items"][0]["error_summary"]["error_message_summary"])
        self.assertNotIn("/Users/me/project", list_body["data"]["items"][0]["error_summary"]["error_message_summary"])

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_body["data"]["run_id"], "run-runtime-001")
        self.assertEqual(detail_body["data"]["captured_count_summary"], {"captured_count": 2})

    def test_scheduler_runs_detail_returns_not_found_for_unknown_run(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        app = create_app(self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}"))

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
            response = client.get("/api/v1/scheduler-runs/missing-run")

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body["error"]["code"], "NOT_FOUND")
        self.assertEqual(body["error"]["details"]["run_id"], "missing-run")

    def test_scheduler_runs_without_database_return_service_unavailable(self) -> None:
        self._login()

        response = self.client.get("/api/v1/scheduler-runs")
        body = response.json()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(body["error"]["code"], "SERVICE_UNAVAILABLE")
        self.assertEqual(body["error"]["details"]["resource"], "scheduler_runs")

    def test_scheduler_runs_reject_unsupported_trace_filter(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        app = create_app(self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}"))

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
            response = client.get("/api/v1/scheduler-runs", params={"trace_id": "trace-1"})

        body = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["error"]["code"], "BAD_REQUEST")
        self.assertEqual(body["error"]["details"]["filter"], "trace_id")

    def test_raw_events_list_and_detail_split_summary_and_full_content(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        app = create_app(self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}"))

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            seed_session = client.app.state.db_session_factory()
            try:
                seed_session.add(
                    RawEventORM(
                        raw_event_id="rawevt-api-001",
                        source_plugin_id="quantagent.official.source.rss",
                        external_id="rss-entry-001",
                        canonical_url="https://example.com/articles/1",
                        title="HBM market moves",
                        content="full body " * 80,
                        author="Reporter",
                        published_at=datetime(2026, 6, 2, 8, 0, 0, tzinfo=UTC),
                        first_captured_at=datetime(2026, 6, 2, 8, 1, 0, tzinfo=UTC),
                        last_captured_at=datetime(2026, 6, 2, 8, 2, 0, tzinfo=UTC),
                        raw_payload={"body": "very large body", "url": "https://example.com/articles/1"},
                        metadata_json={"source": "rss", "feed": "semiconductor"},
                        canonical_dedupe_key="dedupe-001",
                        dedupe_strategy="external_id",
                        content_hash="hash-001",
                        first_binding_id="binding-api-001",
                        first_run_id="run-api-001",
                        duplicate_capture_count=2,
                    )
                )
                seed_session.commit()
            finally:
                seed_session.close()
            client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})

            list_response = client.get("/api/v1/raw-events", params={"source_plugin_id": "quantagent.official.source.rss"})
            detail_response = client.get("/api/v1/raw-events/rawevt-api-001")

        list_body = list_response.json()
        detail_body = detail_response.json()
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_body["data"]["items"][0]["raw_event_id"], "rawevt-api-001")
        self.assertEqual(list_body["data"]["items"][0]["source_plugin_id"], "quantagent.official.source.rss")
        self.assertIn("content_preview", list_body["data"]["items"][0])
        self.assertNotIn("content", list_body["data"]["items"][0])
        self.assertNotIn("raw_payload", list_body["data"]["items"][0])
        self.assertIsNone(list_body["data"]["next_cursor"])

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_body["data"]["raw_event_id"], "rawevt-api-001")
        self.assertIn("content", detail_body["data"])
        self.assertIn("raw_payload", detail_body["data"])
        self.assertEqual(detail_body["data"]["raw_payload"]["url"], "https://example.com/articles/1")

    def test_runtime_audit_news_returns_sanitized_raw_event_read_model(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        settings = self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}")
        app = create_app(settings)

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            session = client.app.state.db_session_factory()
            try:
                self._seed_runtime_audit_news(session)
                session.commit()
            finally:
                session.close()
            self._login_with_client(client, settings)
            response = client.get("/api/v1/runtime/audit/news", params={"limit": 20})

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["code"], 0)
        items = body["data"]["items"]
        self.assertGreaterEqual(len(items), 2)
        first_item = items[0]
        serialized_item = json.dumps(first_item, ensure_ascii=False)
        self.assertEqual(first_item["raw_event_id"], "rawevt-runtime-002")
        self.assertEqual(first_item["title"], "Advanced packaging capacity expands")
        self.assertEqual(first_item["url_host"], "news.example.com")
        self.assertEqual(first_item["status"], "captured")
        self.assertEqual(first_item["current_stage"], "persisted")
        self.assertEqual(first_item["focus_stage"], "ai_intake_unavailable")
        self.assertIn("content_preview", first_item)
        self.assertNotIn("content", first_item)
        self.assertNotIn("raw_payload", first_item)
        self.assertNotIn("very large full article body", serialized_item)
        self.assertNotIn("secret-token", serialized_item)
        self.assertIn("agent_stages", first_item)
        router_stage = next(stage for stage in first_item["agent_stages"] if stage["stage_id"] == "router_agent")
        self.assertEqual(router_stage["status"], "unavailable")
        self.assertIsNone(router_stage["output_json"])
        self.assertIn("尚未提供 Router Agent", router_stage["unavailable_reason"])
        main_agent_stage = next(stage for stage in first_item["agent_stages"] if stage["stage_id"] == "industry_main_agent")
        self.assertEqual(main_agent_stage["agent_type"], "industry_main_agent")
        self.assertIsNone(main_agent_stage["output_json"])

        timeline_by_step = {step["step_id"]: step for step in first_item["timeline"]}
        self.assertEqual(timeline_by_step["ai_intake_unavailable"]["status"], "unavailable")
        self.assertEqual(timeline_by_step["route_unavailable"]["status"], "unavailable")
        self.assertIn("不展示伪造", timeline_by_step["ai_intake_unavailable"]["summary"])
        self.assertNotIn("review", first_item)
        self.assertNotIn("discard", first_item)

        routed_item = next(item for item in items if item["raw_event_id"] == "rawevt-runtime-001")
        self.assertEqual(routed_item["status"], "routed")
        self.assertEqual(routed_item["current_stage"], "route_decided")
        self.assertEqual(routed_item["focus_stage"], "route_decided")
        router_stage = next(stage for stage in routed_item["agent_stages"] if stage["stage_id"] == "router_agent")
        self.assertEqual(router_stage["status"], "success")
        self.assertEqual(router_stage["key_fields"]["decision"], "route")
        self.assertEqual(router_stage["key_fields"]["short_summary"], "HBM demand is directly relevant.")
        self.assertEqual(router_stage["output_json"]["decision"], "route")
        self.assertNotIn("full article body", json.dumps(router_stage["output_json"], ensure_ascii=False))
        self.assertEqual(router_stage["output_json"]["structured_news"]["reasoning_prompt"], "[REDACTED]")
        self.assertEqual(router_stage["output_json"]["routing"]["provider_raw_response"], "[REDACTED]")
        self.assertEqual(router_stage["output_json"]["routing"]["api_token"], "[REDACTED]")
        routed_timeline = {step["step_id"]: step for step in routed_item["timeline"]}
        self.assertEqual(routed_timeline["ai_intake_routed"]["status"], "success")
        self.assertEqual(routed_timeline["route_decided"]["status"], "success")
        self.assertIn("已路由", routed_timeline["route_decided"]["summary"])

    def test_runtime_audit_news_filters_by_backend_refs_and_time_range(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        settings = self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}")
        app = create_app(settings)

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            session = client.app.state.db_session_factory()
            try:
                self._seed_runtime_audit_news(session)
                session.commit()
            finally:
                session.close()
            self._login_with_client(client, settings)
            binding_response = client.get("/api/v1/runtime/audit/news", params={"binding_id": "binding-runtime-001"})
            plugin_response = client.get(
                "/api/v1/runtime/audit/news",
                params={"source_plugin_id": "quantagent.official.source.rss"},
            )
            trace_response = client.get("/api/v1/runtime/audit/news", params={"trace_id": "trace-runtime-001"})
            request_response = client.get("/api/v1/runtime/audit/news", params={"request_id": "req-capture-001"})
            time_response = client.get(
                "/api/v1/runtime/audit/news",
                params={
                    "time_from": "2026-06-02T00:00:00Z",
                    "time_to": "2026-06-02T23:59:59Z",
                },
            )
            stage_response = client.get("/api/v1/runtime/audit/news", params={"current_stage": "route_decided"})

        self.assertEqual(binding_response.status_code, 200)
        self.assertEqual(
            [item["raw_event_id"] for item in binding_response.json()["data"]["items"]],
            ["rawevt-runtime-001"],
        )
        self.assertEqual(plugin_response.status_code, 200)
        self.assertEqual(len(plugin_response.json()["data"]["items"]), 2)
        self.assertEqual(trace_response.status_code, 200)
        self.assertEqual(trace_response.json()["data"]["items"][0]["trace"]["trace_id"], "trace-runtime-001")
        self.assertEqual(request_response.status_code, 200)
        self.assertEqual(request_response.json()["data"]["items"][0]["trace"]["request_id"], "req-capture-001")
        self.assertEqual(time_response.status_code, 200)
        self.assertEqual(
            [item["raw_event_id"] for item in time_response.json()["data"]["items"]],
            ["rawevt-runtime-002"],
        )
        self.assertEqual(stage_response.status_code, 200)
        self.assertEqual(
            [item["raw_event_id"] for item in stage_response.json()["data"]["items"]],
            ["rawevt-runtime-001"],
        )

    def test_runtime_audit_news_requires_runtime_inspect_session(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        app = create_app(self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}"))

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            response = client.get("/api/v1/runtime/audit/news")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    def test_model_provider_create_masks_key_and_test_connection_records_usage(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        fake_client = FakeModelClient()
        settings = self._settings(
            DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}",
            MODEL_CONFIG_ENCRYPTION_KEY=ModelConfigCrypto.generate_key(),
        )
        app = create_app(settings)
        app.state.model_call_client = fake_client

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            login_response = client.post("/api/v1/auth/login", json={"password": settings.AUTH_ADMIN_PASSWORD})
            csrf_token = login_response.json()["data"]["csrf_token"]

            save_response = client.post(
                "/api/v1/models/providers",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token},
                json={
                    "provider_type": "openai_compatible",
                    "name": "Local Gateway",
                    "base_url": "http://127.0.0.1:11434/v1",
                    "api_key": "sk-api-secret",
                    "enabled": True,
                    "is_default": True,
                },
            )
            provider_id = save_response.json()["data"]["id"]
            create_model_response = client.post(
                f"/api/v1/models/providers/{provider_id}/models",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token},
                json={
                    "model_name": "qwen-test",
                    "enabled": True,
                    "supports_vision": False,
                    "is_global_default": True,
                },
            )
            providers_response = client.get("/api/v1/models/providers")
            detail_response = client.get(f"/api/v1/models/providers/{provider_id}")
            presets_response = client.get("/api/v1/models/presets")
            test_response = client.post(
                f"/api/v1/models/providers/{provider_id}/actions/test-connection",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token, "X-Request-ID": "req-model"},
            )
            invocations_response = client.get(
                f"/api/v1/models/invocations?provider_id={provider_id}&preset_key=global_default"
            )

            session = client.app.state.db_session_factory()
            try:
                encrypted_value = session.execute(
                    Base.metadata.tables["model_providers"].select()
                ).mappings().one()["encrypted_api_key"]
            finally:
                session.close()

        save_body = save_response.json()
        self.assertEqual(save_response.status_code, 200)
        self.assertEqual(save_body["data"]["masked_key"], "********")
        self.assertTrue(save_body["data"]["is_default"])
        self.assertNotIn("sk-api-secret", str(save_body))
        self.assertNotEqual(encrypted_value, "sk-api-secret")
        self.assertEqual(save_body["data"]["model_count"], 0)

        create_model_body = create_model_response.json()
        self.assertEqual(create_model_response.status_code, 200)
        self.assertEqual(create_model_body["data"]["model_name"], "qwen-test")
        self.assertTrue(create_model_body["data"]["is_global_default"])

        providers_body = providers_response.json()
        self.assertEqual(providers_response.status_code, 200)
        self.assertEqual(providers_body["data"]["default_provider_id"], provider_id)
        self.assertEqual(len(providers_body["data"]["providers"]), 1)
        self.assertEqual(providers_body["data"]["providers"][0]["model_count"], 1)

        detail_body = detail_response.json()
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_body["data"]["status"], "configured")
        self.assertEqual(detail_body["data"]["key_status"], "configured")
        self.assertNotIn("sk-api-secret", str(detail_body))
        self.assertEqual(len(detail_body["data"]["models"]), 1)
        self.assertEqual(detail_body["data"]["models"][0]["model_name"], "qwen-test")

        presets_body = presets_response.json()
        self.assertEqual(presets_response.status_code, 200)
        self.assertEqual(len(presets_body["data"]), 5)
        self.assertEqual(
            {item["preset_key"] for item in presets_body["data"]},
            {"global_default", "economy_text", "general_text", "reasoning_text", "multimodal"},
        )

        test_body = test_response.json()
        self.assertEqual(test_response.status_code, 200)
        self.assertTrue(test_body["data"]["success"])
        self.assertEqual(test_body["data"]["invocation"]["provider_id"], provider_id)
        self.assertEqual(test_body["data"]["invocation"]["preset_key"], "global_default")
        self.assertEqual(test_body["data"]["invocation"]["token_usage"]["total_tokens"], 3)
        self.assertEqual(fake_client.calls[0]["api_key"], "sk-api-secret")
        self.assertEqual(fake_client.calls[0]["model"], "qwen-test")
        self.assertNotIn("sk-api-secret", str(test_body))

        invocations_body = invocations_response.json()
        self.assertEqual(invocations_response.status_code, 200)
        self.assertEqual(invocations_body["data"][0]["provider_id"], provider_id)
        self.assertEqual(invocations_body["data"][0]["preset_key"], "global_default")
        self.assertEqual(invocations_body["data"][0]["request_id"], "req-model")
        self.assertEqual(invocations_body["data"][0]["token_usage"]["prompt_tokens"], 2)

    def test_model_provider_save_requires_csrf_and_encryption_key(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        settings = self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}")
        app = create_app(settings)

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            login_response = client.post("/api/v1/auth/login", json={"password": settings.AUTH_ADMIN_PASSWORD})
            forbidden_response = client.post(
                "/api/v1/models/providers",
                json={
                    "name": "OpenAI",
                    "api_key": "sk-should-not-leak",
                    "is_default": True,
                },
            )
            csrf_token = login_response.json()["data"]["csrf_token"]
            missing_key_response = client.post(
                "/api/v1/models/providers",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token},
                json={
                    "name": "OpenAI",
                    "api_key": "sk-should-not-leak",
                    "is_default": True,
                },
            )

        self.assertEqual(forbidden_response.status_code, 403)
        body = missing_key_response.json()
        self.assertEqual(missing_key_response.status_code, 503)
        self.assertEqual(body["error"]["code"], "SERVICE_UNAVAILABLE")
        self.assertEqual(body["error"]["details"]["code"], "MODEL_CONFIG_ENCRYPTION_UNAVAILABLE")
        self.assertNotIn("sk-should-not-leak", str(body))

    def test_model_provider_test_connection_missing_key_records_safe_failure(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        settings = self._settings(
            DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}",
            MODEL_CONFIG_ENCRYPTION_KEY=ModelConfigCrypto.generate_key(),
        )
        app = create_app(settings)

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            login_response = client.post("/api/v1/auth/login", json={"password": settings.AUTH_ADMIN_PASSWORD})
            csrf_token = login_response.json()["data"]["csrf_token"]
            create_response = client.post(
                "/api/v1/models/providers",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token},
                json={
                    "name": "Missing Key Provider",
                    "enabled": True,
                    "is_default": True,
                },
            )
            provider_id = create_response.json()["data"]["id"]
            client.post(
                f"/api/v1/models/providers/{provider_id}/models",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token},
                json={
                    "model_name": "gpt-test",
                    "enabled": True,
                    "supports_vision": False,
                    "is_global_default": True,
                },
            )
            response = client.post(
                f"/api/v1/models/providers/{provider_id}/actions/test-connection",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token},
            )
            invocations_response = client.get(f"/api/v1/models/invocations?provider_id={provider_id}")

        body = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["error"]["details"]["code"], "MODEL_PROVIDER_KEY_MISSING")
        self.assertNotIn("api_key", str(body).lower())
        invocation = invocations_response.json()["data"][0]
        self.assertEqual(invocation["status"], "failed")
        self.assertEqual(invocation["error_summary"], "MODEL_PROVIDER_KEY_MISSING")

    def test_model_provider_models_and_presets_support_binding_and_validation(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        settings = self._settings(
            DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}",
            MODEL_CONFIG_ENCRYPTION_KEY=ModelConfigCrypto.generate_key(),
        )
        app = create_app(settings)

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            login_response = client.post("/api/v1/auth/login", json={"password": settings.AUTH_ADMIN_PASSWORD})
            csrf_token = login_response.json()["data"]["csrf_token"]
            create_provider_response = client.post(
                "/api/v1/models/providers",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token},
                json={
                    "name": "Preset Provider",
                    "base_url": "https://api.example.com/v1",
                    "api_key": "sk-preset",
                    "enabled": True,
                    "is_default": True,
                },
            )
            provider_id = create_provider_response.json()["data"]["id"]
            text_model_response = client.post(
                f"/api/v1/models/providers/{provider_id}/models",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token},
                json={
                    "model_name": "text-model",
                    "enabled": True,
                    "supports_vision": False,
                    "is_global_default": True,
                },
            )
            vision_model_response = client.post(
                f"/api/v1/models/providers/{provider_id}/models",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token},
                json={
                    "model_name": "vision-model",
                    "enabled": True,
                    "supports_vision": True,
                    "is_global_default": False,
                },
            )
            text_model_id = text_model_response.json()["data"]["id"]
            vision_model_id = vision_model_response.json()["data"]["id"]

            invalid_multimodal_response = client.put(
                "/api/v1/models/presets/multimodal",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token},
                json={"primary_model_id": text_model_id, "fallback_model_id": None},
            )
            valid_multimodal_response = client.put(
                "/api/v1/models/presets/multimodal",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token},
                json={"primary_model_id": vision_model_id, "fallback_model_id": None},
            )
            economy_response = client.put(
                "/api/v1/models/presets/economy_text",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token},
                json={"primary_model_id": text_model_id, "fallback_model_id": vision_model_id},
            )
            presets_response = client.get("/api/v1/models/presets")

        invalid_body = invalid_multimodal_response.json()
        self.assertEqual(invalid_multimodal_response.status_code, 400)
        self.assertEqual(invalid_body["error"]["details"]["code"], "MODEL_PRESET_PRIMARY_INVALID")

        valid_multimodal_body = valid_multimodal_response.json()
        self.assertEqual(valid_multimodal_response.status_code, 200)
        self.assertEqual(valid_multimodal_body["data"]["preset_key"], "multimodal")
        self.assertEqual(valid_multimodal_body["data"]["primary_model"]["id"], vision_model_id)

        economy_body = economy_response.json()
        self.assertEqual(economy_response.status_code, 200)
        self.assertEqual(economy_body["data"]["preset_key"], "economy_text")
        self.assertEqual(economy_body["data"]["primary_model"]["id"], text_model_id)
        self.assertEqual(economy_body["data"]["fallback_model"]["id"], vision_model_id)

        presets_body = presets_response.json()
        self.assertEqual(presets_response.status_code, 200)
        by_key = {item["preset_key"]: item for item in presets_body["data"]}
        self.assertEqual(by_key["multimodal"]["primary_model"]["id"], vision_model_id)
        self.assertEqual(by_key["economy_text"]["primary_model"]["id"], text_model_id)
        self.assertEqual(by_key["economy_text"]["fallback_model"]["id"], vision_model_id)

    def test_source_binding_routes_return_envelope_and_mask_sensitive_config(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        settings = self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}")
        app = create_app(settings)

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            session = client.app.state.db_session_factory()
            try:
                session.add(
                    SourceBindingORM(
                        binding_id="binding-api-001",
                        owner_type="industry",
                        owner_id="semiconductor",
                        source_plugin_id="quantagent.official.source.rss",
                        effective_config_snapshot={
                            "feed": "https://example.com/rss",
                            "api_key": "should-not-leak",
                            "keywords": ["chip", "fab"],
                        },
                        schedule_policy={"interval_seconds": 300},
                        retry_policy={"max_attempts": 3},
                        rate_limit_policy={"requests_per_minute": 10},
                        status="active",
                        created_by="issue-226",
                        updated_by="issue-226",
                    )
                )
                session.add(
                    SchedulerRunORM(
                        run_id="run-api-001",
                        binding_id="binding-api-001",
                        source_plugin_id="quantagent.official.source.rss",
                        source_plugin_version=None,
                        trigger_mode="manual",
                        request_id="req-run-api-001",
                        status="failed",
                        failure_code="PLUGIN_FAILED",
                        failure_message="sanitized failure",
                        failure_stage="invoke",
                        retryable=False,
                        metadata_json={"actor": {"actor_id": "local_admin", "actor_type": "local_single_user"}},
                    )
                )
                session.commit()
            finally:
                session.close()

            self._login_with_client(client, settings)
            list_response = client.get("/api/v1/source-bindings")
            detail_response = client.get("/api/v1/source-bindings/binding-api-001")
            binding_runs_response = client.get("/api/v1/source-bindings/binding-api-001/scheduler-runs")

        list_body = list_response.json()
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_body["code"], 0)
        self.assertEqual(list_body["data"]["items"][0]["id"], "binding-api-001")
        self.assertIn("run-now", list_body["data"]["items"][0]["allowed_actions"])

        detail_body = detail_response.json()
        self.assertEqual(detail_response.status_code, 200)
        self.assertNotIn("api_key", detail_body["data"]["effective_config_summary"]["values"])
        self.assertIn("api_key", detail_body["data"]["effective_config_summary"]["secret_fields_masked"])

        binding_runs_body = binding_runs_response.json()
        self.assertEqual(binding_runs_response.status_code, 200)
        self.assertEqual(binding_runs_body["data"]["meta"]["state"], "ready")
        self.assertIsNone(binding_runs_body["data"]["meta"]["page"]["cursor"])
        self.assertIsNone(binding_runs_body["data"]["meta"]["page"]["next_cursor"])
        self.assertEqual(binding_runs_body["data"]["items"][0]["binding_id"], "binding-api-001")
        self.assertEqual(binding_runs_body["data"]["items"][0]["run_id"], "run-api-001")
        self.assertEqual(binding_runs_body["data"]["items"][0]["plugin_id"], "quantagent.official.source.rss")
        self.assertEqual(
            binding_runs_body["data"]["items"][0]["error_summary"]["error_code"],
            "PLUGIN_FAILED",
        )

    def test_source_binding_runs_meta_preserves_cursor_pagination(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        settings = self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}")
        app = create_app(settings)

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            session = client.app.state.db_session_factory()
            try:
                session.add(
                    SourceBindingORM(
                        binding_id="binding-page-001",
                        owner_type="industry",
                        owner_id="semiconductor",
                        source_plugin_id="quantagent.official.source.rss",
                        effective_config_snapshot={"feed": "https://example.com/rss"},
                        schedule_policy={"interval_seconds": 300},
                        retry_policy={"max_attempts": 3},
                        rate_limit_policy={"requests_per_minute": 10},
                        status="active",
                        created_by="issue-226",
                        updated_by="issue-226",
                    )
                )
                session.add(
                    SchedulerRunORM(
                        run_id="run-page-002",
                        binding_id="binding-page-001",
                        source_plugin_id="quantagent.official.source.rss",
                        source_plugin_version=None,
                        trigger_mode="manual",
                        request_id="req-page-002",
                        status="failed",
                        created_at=datetime(2026, 6, 1, 9, 1, tzinfo=UTC),
                        failure_code="PLUGIN_FAILED",
                        failure_message="latest",
                        failure_stage="invoke",
                        retryable=False,
                    )
                )
                session.add(
                    SchedulerRunORM(
                        run_id="run-page-001",
                        binding_id="binding-page-001",
                        source_plugin_id="quantagent.official.source.rss",
                        source_plugin_version=None,
                        trigger_mode="manual",
                        request_id="req-page-001",
                        status="failed",
                        created_at=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
                        failure_code="PLUGIN_FAILED",
                        failure_message="older",
                        failure_stage="invoke",
                        retryable=False,
                    )
                )
                session.commit()
            finally:
                session.close()

            self._login_with_client(client, settings)
            first_response = client.get(
                "/api/v1/source-bindings/binding-page-001/scheduler-runs",
                params={"limit": 1},
            )
            first_body = first_response.json()
            next_cursor = first_body["data"]["meta"]["page"]["next_cursor"]
            second_response = client.get(
                "/api/v1/source-bindings/binding-page-001/scheduler-runs",
                params={"limit": 1, "cursor": next_cursor},
            )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(first_body["data"]["meta"]["page"]["returned"], 1)
        self.assertIsNotNone(next_cursor)
        self.assertEqual(first_body["data"]["items"][0]["run_id"], "run-page-002")

        second_body = second_response.json()
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_body["data"]["meta"]["page"]["cursor"], next_cursor)
        self.assertIsNone(second_body["data"]["meta"]["page"]["next_cursor"])
        self.assertEqual(second_body["data"]["meta"]["page"]["returned"], len(second_body["data"]["items"]))

    def test_source_binding_runs_invalid_cursor_uses_bad_request_envelope(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        settings = self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}")
        app = create_app(settings)

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            session = client.app.state.db_session_factory()
            try:
                session.add(
                    SourceBindingORM(
                        binding_id="binding-bad-cursor-001",
                        owner_type="industry",
                        owner_id="semiconductor",
                        source_plugin_id="quantagent.official.source.rss",
                        effective_config_snapshot={"feed": "https://example.com/rss"},
                        schedule_policy={"interval_seconds": 300},
                        retry_policy={"max_attempts": 3},
                        rate_limit_policy={"requests_per_minute": 10},
                        status="active",
                        created_by="issue-226",
                        updated_by="issue-226",
                    )
                )
                session.commit()
            finally:
                session.close()
            self._login_with_client(client, settings)
            response = client.get(
                "/api/v1/source-bindings/binding-bad-cursor-001/scheduler-runs",
                params={"cursor": "not-base64"},
            )

        body = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["error"]["code"], "BAD_REQUEST")
        self.assertEqual(body["error"]["details"]["reason"], "invalid cursor")

    def test_source_binding_actions_are_idempotent_and_run_now_is_accepted(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        settings = self._settings(
            DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}",
            LOG_USE_MEMORY_SINK=True,
        )
        app = create_app(settings)

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            session = client.app.state.db_session_factory()
            try:
                session.add(
                    SourceBindingORM(
                        binding_id="binding-action-001",
                        owner_type="industry",
                        owner_id="oil",
                        source_plugin_id="quantagent.official.source.rss",
                        effective_config_snapshot={"feed": "https://example.com/oil"},
                        schedule_policy={"interval_seconds": 600},
                        retry_policy={},
                        rate_limit_policy={},
                        status="active",
                        created_by="issue-226",
                        updated_by="issue-226",
                    )
                )
                session.commit()
            finally:
                session.close()

            csrf_token = self._login_with_client(client, settings)
            pause_response = client.post(
                "/api/v1/source-bindings/binding-action-001/actions/pause",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token},
            )
            repeat_pause_response = client.post(
                "/api/v1/source-bindings/binding-action-001/actions/pause",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token},
            )
            run_now_response = client.post(
                "/api/v1/source-bindings/binding-action-001/actions/run-now",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token, "X-Request-ID": "req-run-now-api"},
            )
            invalid_binding_response = client.post(
                "/api/v1/source-bindings/missing-binding/actions/pause",
                headers={settings.AUTH_CSRF_HEADER_NAME: csrf_token},
            )

            audit_handler = next(
                handler
                for handler in logging.getLogger("quantagent.api").handlers
                if isinstance(handler, InMemoryStructuredHandler)
            )
            session = client.app.state.db_session_factory()
            try:
                created_runs = session.query(SchedulerRunORM).filter(SchedulerRunORM.request_id == "req-run-now-api").all()
            finally:
                session.close()

        pause_body = pause_response.json()
        self.assertEqual(pause_response.status_code, 200)
        self.assertFalse(pause_body["data"]["already_in_target_state"])
        self.assertEqual(pause_body["data"]["target_state"], "paused")

        repeat_pause_body = repeat_pause_response.json()
        self.assertEqual(repeat_pause_response.status_code, 200)
        self.assertTrue(repeat_pause_body["data"]["already_in_target_state"])

        run_now_body = run_now_response.json()
        self.assertEqual(run_now_response.status_code, 200)
        self.assertEqual(run_now_body["data"]["request_id"], "req-run-now-api")
        self.assertEqual(len(created_runs), 1)
        self.assertEqual(created_runs[0].status, "queued")

        invalid_body = invalid_binding_response.json()
        self.assertEqual(invalid_binding_response.status_code, 404)
        self.assertEqual(invalid_body["error"]["code"], "NOT_FOUND")

        audit_records = [json.loads(record) for record in audit_handler.records]
        action_records = [
            record
            for record in audit_records
            if record.get("event") == "audit.context.bound" and record.get("action", "").startswith("source-binding.")
        ]
        self.assertTrue(action_records)
        self.assertTrue(
            any(
                record.get("audit_ref") == run_now_body["data"]["audit_ref"]
                and record.get("target_id") == "binding-action-001"
                and record.get("result") == "accepted"
                for record in action_records
            )
        )

    def test_discord_interactions_endpoint_returns_not_found_when_disabled(self) -> None:
        response = self.client.post("/api/v1/integrations/discord/interactions", content=b"{}")
        body = response.json()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(body["error"]["code"], "NOT_FOUND")

    def test_notification_ingress_endpoint_rejects_invalid_signature(self) -> None:
        app = create_app(
            self._settings(
                NOTIFICATION_INGRESS_ENABLED=True,
                NOTIFICATION_INGRESS_PLUGIN_ID="quantagent.official.notification.discord",
                NOTIFICATION_INGRESS_PLUGIN_CONFIG={"public_key": "a" * 64},
            )
        )
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/integrations/notifications/ingress",
                content=b'{"type":1}',
                headers={
                    "X-Signature-Timestamp": str(int(time.time())),
                    "X-Signature-Ed25519": "00",
                },
            )

        body = response.json()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(body["error"], "SIGNATURE_INVALID")

    def test_notification_ingress_endpoint_returns_pong_for_valid_ping(self) -> None:
        signing_key = SigningKey.generate()
        public_key = signing_key.verify_key.encode(encoder=HexEncoder).decode("utf-8")
        app = create_app(
            self._settings(
                NOTIFICATION_INGRESS_ENABLED=True,
                NOTIFICATION_INGRESS_PLUGIN_ID="quantagent.official.notification.discord",
                NOTIFICATION_INGRESS_PLUGIN_CONFIG={"public_key": public_key},
            )
        )
        body = b'{"type":1}'
        timestamp = str(int(time.time()))
        signature = signing_key.sign(timestamp.encode("utf-8") + body).signature.hex()

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/integrations/notifications/ingress",
                content=body,
                headers={
                    "X-Signature-Timestamp": timestamp,
                    "X-Signature-Ed25519": signature,
                    "X-Request-ID": "req-discord-ping",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], "req-discord-ping")
        self.assertEqual(response.json(), {"type": 1})

    def test_notification_ingress_endpoint_returns_response_for_valid_command(self) -> None:
        signing_key = SigningKey.generate()
        public_key = signing_key.verify_key.encode(encoder=HexEncoder).decode("utf-8")
        app = create_app(
            self._settings(
                NOTIFICATION_INGRESS_ENABLED=True,
                NOTIFICATION_INGRESS_PLUGIN_ID="quantagent.official.notification.discord",
                NOTIFICATION_INGRESS_PLUGIN_CONFIG={
                    "public_key": public_key,
                    "response_text": "API route received interaction.",
                },
            )
        )
        body = json.dumps(
            {
                "id": "1234567890",
                "application_id": "app-1",
                "type": 2,
                "guild_id": "guild-1",
                "channel_id": "channel-1",
                "member": {"user": {"id": "user-1"}},
                "data": {
                    "name": "notify",
                    "options": [{"name": "text", "type": 3, "value": "hello from discord"}],
                },
            }
        ).encode("utf-8")
        timestamp = str(int(time.time()))
        signature = signing_key.sign(timestamp.encode("utf-8") + body).signature.hex()

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/integrations/notifications/ingress",
                content=body,
                headers={
                    "X-Signature-Timestamp": timestamp,
                    "X-Signature-Ed25519": signature,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "type": 4,
                "data": {
                    "content": "API route received interaction.",
                    "flags": 64,
                },
            },
        )

    def test_notification_ingress_endpoint_enforces_plugin_allowlists(self) -> None:
        signing_key = SigningKey.generate()
        public_key = signing_key.verify_key.encode(encoder=HexEncoder).decode("utf-8")
        app = create_app(
            self._settings(
                NOTIFICATION_INGRESS_ENABLED=True,
                NOTIFICATION_INGRESS_PLUGIN_ID="quantagent.official.notification.discord",
                NOTIFICATION_INGRESS_PLUGIN_CONFIG={
                    "public_key": public_key,
                    "guild_allowlist": ["guild-allowed"],
                },
            )
        )
        body = json.dumps(
            {
                "id": "1234567890",
                "application_id": "app-1",
                "type": 2,
                "guild_id": "guild-blocked",
                "channel_id": "channel-1",
                "member": {"user": {"id": "user-1"}},
                "data": {
                    "name": "notify",
                    "options": [{"name": "text", "type": 3, "value": "hello from discord"}],
                },
            }
        ).encode("utf-8")
        timestamp = str(int(time.time()))
        signature = signing_key.sign(timestamp.encode("utf-8") + body).signature.hex()

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/integrations/notifications/ingress",
                content=body,
                headers={
                    "X-Signature-Timestamp": timestamp,
                    "X-Signature-Ed25519": signature,
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "GUILD_NOT_ALLOWED")

    def test_notification_ingress_endpoint_returns_bad_request_for_unsupported_type(self) -> None:
        signing_key = SigningKey.generate()
        public_key = signing_key.verify_key.encode(encoder=HexEncoder).decode("utf-8")
        app = create_app(
            self._settings(
                NOTIFICATION_INGRESS_ENABLED=True,
                NOTIFICATION_INGRESS_PLUGIN_ID="quantagent.official.notification.discord",
                NOTIFICATION_INGRESS_PLUGIN_CONFIG={"public_key": public_key},
            )
        )
        body = b'{"type":3}'
        timestamp = str(int(time.time()))
        signature = signing_key.sign(timestamp.encode("utf-8") + body).signature.hex()

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/integrations/notifications/ingress",
                content=body,
                headers={
                    "X-Signature-Timestamp": timestamp,
                    "X-Signature-Ed25519": signature,
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "UNSUPPORTED_EVENT_TYPE")

    def test_notification_ingress_endpoint_rejects_stale_timestamp(self) -> None:
        signing_key = SigningKey.generate()
        public_key = signing_key.verify_key.encode(encoder=HexEncoder).decode("utf-8")
        app = create_app(
            self._settings(
                NOTIFICATION_INGRESS_ENABLED=True,
                NOTIFICATION_INGRESS_PLUGIN_ID="quantagent.official.notification.discord",
                NOTIFICATION_INGRESS_PLUGIN_CONFIG={"public_key": public_key},
            )
        )
        body = b'{"type":1}'
        timestamp = "1"
        signature = signing_key.sign(timestamp.encode("utf-8") + body).signature.hex()

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/integrations/notifications/ingress",
                content=body,
                headers={
                    "X-Signature-Timestamp": timestamp,
                    "X-Signature-Ed25519": signature,
                },
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "TIMESTAMP_INVALID")

    def test_notification_ingress_endpoint_rejects_plugin_without_receive_handler(self) -> None:
        app = create_app(
            self._settings(
                NOTIFICATION_INGRESS_ENABLED=True,
                NOTIFICATION_INGRESS_PLUGIN_ID="quantagent.official.notification.discord",
                NOTIFICATION_INGRESS_PLUGIN_CONFIG={"public_key": "a" * 64},
            )
        )

        with patch("quantagent.api.services.plugin_registry.get_plugin_registry") as get_registry:
            get_registry.return_value = SimpleNamespace(
                get_plugin=lambda _plugin_id: SimpleNamespace(
                    status=PluginStatus.VALID,
                    manifest=SimpleNamespace(capabilities=("notification.receive",)),
                )
            )
            with patch("quantagent.api.services.notification_ingress.PluginRuntimeService.invoke") as invoke:
                invoke.return_value = SimpleNamespace(error=SimpleNamespace(code="boom"), result=None)
                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/integrations/notifications/ingress",
                        content=b'{"type":1}',
                        headers={
                            "X-Signature-Timestamp": str(int(time.time())),
                            "X-Signature-Ed25519": "00",
                        },
                    )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "SERVICE_UNAVAILABLE")

    def test_notification_ingress_endpoint_rejects_plugin_without_receive_capability(self) -> None:
        app = create_app(
            self._settings(
                NOTIFICATION_INGRESS_ENABLED=True,
                NOTIFICATION_INGRESS_PLUGIN_ID="quantagent.official.notification.discord",
                NOTIFICATION_INGRESS_PLUGIN_CONFIG={"public_key": "a" * 64},
            )
        )
        invalid_record = PluginRecord(
            id="quantagent.official.notification.discord",
            source=PluginSource.OFFICIAL,
            path=Path("/tmp/fake-plugin"),
            status=PluginStatus.VALID,
            manifest=PluginManifest(
                id="quantagent.official.notification.discord",
                name="Discord Notification",
                type=PluginType.NOTIFICATION,
                version="0.1.0",
                entrypoint="src.discord_plugin:plugin",
                capabilities=("notification.send",),
                config_schema="config.schema.json",
            ),
        )

        with patch("quantagent.api.services.plugin_registry.get_plugin_registry") as get_registry:
            get_registry.return_value = SimpleNamespace(get_plugin=lambda _plugin_id: invalid_record)
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/integrations/notifications/ingress",
                    content=b'{"type":1}',
                    headers={
                        "X-Signature-Timestamp": str(int(time.time())),
                        "X-Signature-Ed25519": "00",
                    },
                )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "SERVICE_UNAVAILABLE")

    def test_notification_ingress_endpoint_rejects_plugin_with_invalid_result_shape(self) -> None:
        signing_key = SigningKey.generate()
        public_key = signing_key.verify_key.encode(encoder=HexEncoder).decode("utf-8")
        app = create_app(
            self._settings(
                NOTIFICATION_INGRESS_ENABLED=True,
                NOTIFICATION_INGRESS_PLUGIN_ID="quantagent.official.notification.discord",
                NOTIFICATION_INGRESS_PLUGIN_CONFIG={"public_key": public_key},
            )
        )

        body = b'{"type":1}'
        timestamp = str(int(time.time()))
        signature = signing_key.sign(timestamp.encode("utf-8") + body).signature.hex()

        with patch("quantagent.api.services.plugin_registry.get_plugin_registry") as get_registry:
            get_registry.return_value = SimpleNamespace(
                get_plugin=lambda _plugin_id: SimpleNamespace(
                    status=PluginStatus.VALID,
                    manifest=SimpleNamespace(capabilities=("notification.receive",)),
                )
            )
            with patch("quantagent.api.services.notification_ingress.PluginRuntimeService.invoke") as invoke:
                invoke.return_value = SimpleNamespace(
                    error=None,
                    result=SimpleNamespace(output={"accepted": True, "code": "RECEIVED", "message": "ok", "response": "not-a-mapping", "item": {"interaction_id": "1", "source_id": "s", "text": "t"}, "retryable": False}),
                )
                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/integrations/notifications/ingress",
                        content=body,
                        headers={
                            "X-Signature-Timestamp": timestamp,
                            "X-Signature-Ed25519": signature,
                        },
                    )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "SERVICE_UNAVAILABLE")

    def test_notification_ingress_endpoint_rejects_success_result_without_response_payload(self) -> None:
        signing_key = SigningKey.generate()
        public_key = signing_key.verify_key.encode(encoder=HexEncoder).decode("utf-8")
        app = create_app(
            self._settings(
                NOTIFICATION_INGRESS_ENABLED=True,
                NOTIFICATION_INGRESS_PLUGIN_ID="quantagent.official.notification.discord",
                NOTIFICATION_INGRESS_PLUGIN_CONFIG={"public_key": public_key},
            )
        )

        body = b'{"type":1}'
        timestamp = str(int(time.time()))
        signature = signing_key.sign(timestamp.encode("utf-8") + body).signature.hex()

        with patch("quantagent.api.services.plugin_registry.get_plugin_registry") as get_registry:
            get_registry.return_value = SimpleNamespace(
                get_plugin=lambda _plugin_id: SimpleNamespace(
                    status=PluginStatus.VALID,
                    manifest=SimpleNamespace(capabilities=("notification.receive",)),
                )
            )
            with patch("quantagent.api.services.notification_ingress.PluginRuntimeService.invoke") as invoke:
                invoke.return_value = SimpleNamespace(
                    error=None,
                    result=SimpleNamespace(output={"accepted": True, "code": "RECEIVED", "message": "ok", "response": None, "item": {"interaction_id": "1", "source_id": "s", "text": "t"}, "retryable": False}),
                )
                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/integrations/notifications/ingress",
                        content=body,
                        headers={
                            "X-Signature-Timestamp": timestamp,
                            "X-Signature-Ed25519": signature,
                        },
                    )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "SERVICE_UNAVAILABLE")

    def test_notification_ingress_endpoint_allows_response_only_success_without_item(self) -> None:
        signing_key = SigningKey.generate()
        public_key = signing_key.verify_key.encode(encoder=HexEncoder).decode("utf-8")
        app = create_app(
            self._settings(
                NOTIFICATION_INGRESS_ENABLED=True,
                NOTIFICATION_INGRESS_PLUGIN_ID="quantagent.official.notification.discord",
                NOTIFICATION_INGRESS_PLUGIN_CONFIG={"public_key": public_key},
            )
        )

        body = json.dumps(
            {
                "id": "1234567890",
                "application_id": "app-1",
                "type": 2,
                "guild_id": "guild-1",
                "channel_id": "channel-1",
                "member": {"user": {"id": "user-1"}},
                "data": {
                    "name": "notify",
                    "options": [{"name": "text", "type": 3, "value": "hello from discord"}],
                },
            }
        ).encode("utf-8")
        timestamp = str(int(time.time()))
        signature = signing_key.sign(timestamp.encode("utf-8") + body).signature.hex()

        with patch("quantagent.api.services.plugin_registry.get_plugin_registry") as get_registry:
            get_registry.return_value = SimpleNamespace(
                get_plugin=lambda _plugin_id: SimpleNamespace(
                    status=PluginStatus.VALID,
                    manifest=SimpleNamespace(capabilities=("notification.receive",)),
                )
            )
            with patch("quantagent.api.services.notification_ingress.PluginRuntimeService.invoke") as invoke:
                invoke.return_value = SimpleNamespace(
                    error=None,
                    result=SimpleNamespace(
                        output={
                            "accepted": True,
                            "code": "CHALLENGE",
                            "message": "ok",
                            "response_status_code": 200,
                            "response": {"type": 4, "data": {"content": "ok", "flags": 64}},
                            "item": None,
                            "retryable": False,
                        }
                    ),
                )
                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/integrations/notifications/ingress",
                        content=body,
                        headers={
                            "X-Signature-Timestamp": timestamp,
                            "X-Signature-Ed25519": signature,
                        },
                    )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"type": 4, "data": {"content": "ok", "flags": 64}})

    def test_notification_ingress_endpoint_uses_injected_core_ingress_service(self) -> None:
        class _InjectedIngress:
            def __init__(self) -> None:
                self.calls = []

            async def receive(self, **kwargs):
                self.calls.append(kwargs)
                return SimpleNamespace(
                    receive_result=SimpleNamespace(
                        accepted=True,
                        response_status_code=200,
                        response={"type": 4, "data": {"content": "handoff queued", "flags": 64}},
                    )
                )

        injected = _InjectedIngress()
        app = create_app(
            self._settings(
                NOTIFICATION_INGRESS_ENABLED=True,
                NOTIFICATION_INGRESS_PLUGIN_ID="quantagent.official.notification.discord",
                NOTIFICATION_INGRESS_PLUGIN_CONFIG={"public_key": "a" * 64, "webhook_url": "https://discord.example/secret-token"},
            )
        )
        app.state.notification_core_ingress_service = injected

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/integrations/notifications/ingress",
                content=b'{"type":2}',
                headers={"X-Request-ID": "req-injected"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["content"], "handoff queued")
        self.assertEqual(len(injected.calls), 1)
        self.assertEqual(injected.calls[0]["plugin_id"], "quantagent.official.notification.discord")
        self.assertEqual(injected.calls[0]["request_id"], "req-injected")
        rendered = str(response.json())
        self.assertNotIn("secret-token", rendered)

    def test_missing_capability_is_forbidden(self) -> None:
        reduced_capabilities = frozenset({"plugin.configure"})
        issued_session = issue_session("local_admin", self.settings, capabilities=reduced_capabilities)
        with TestClient(self._protected_write_test_app()) as client:
            client.cookies.set(self.settings.AUTH_COOKIE_NAME, issued_session.value)
            response = client.post(
                "/test/protected-write",
                headers={self.settings.AUTH_CSRF_HEADER_NAME: issued_session.data.csrf_token},
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
        self.assertIn("integrations", schema["paths"]["/api/v1/integrations/notifications/ingress"]["post"]["tags"])
        self.assertIn("auth", schema["paths"]["/api/v1/auth/logout"]["post"]["tags"])
        self.assertIn("auth", schema["paths"]["/api/v1/auth/refresh"]["post"]["tags"])
        self.assertIn("auth", schema["paths"]["/api/v1/me"]["get"]["tags"])
        self.assertIn("plugins", schema["paths"]["/api/v1/plugins"]["get"]["tags"])
        self.assertIn("plugins", schema["paths"]["/api/v1/plugins/{plugin_id}"]["get"]["tags"])
        self.assertIn("plugins", schema["paths"]["/api/v1/plugins/{plugin_id}/config"]["get"]["tags"])
        self.assertIn("plugins", schema["paths"]["/api/v1/plugins/{plugin_id}/config-schema"]["get"]["tags"])
        self.assertIn("plugins", schema["paths"]["/api/v1/plugins/{plugin_id}/dependencies"]["get"]["tags"])
        self.assertIn("plugins", schema["paths"]["/api/v1/plugins/{plugin_id}/health"]["get"]["tags"])
        self.assertIn("plugins", schema["paths"]["/api/v1/plugins/{plugin_id}/audit"]["get"]["tags"])
        self.assertIn("plugins", schema["paths"]["/api/v1/plugins/actions/rescan"]["post"]["tags"])
        self.assertEqual(
            {
                path
                for path in schema["paths"]
                if path.startswith("/api/v1/wallet")
            },
            {
                "/api/v1/wallet/accounts/{account_id}",
                "/api/v1/wallet/accounts/{account_id}/cash-balances",
                "/api/v1/wallet/accounts/{account_id}/positions",
                "/api/v1/wallet/accounts/{account_id}/ledger-entries",
                "/api/v1/wallet/accounts/{account_id}/paper-orders",
                "/api/v1/wallet/accounts/{account_id}/paper-executions",
            },
        )
        self.assertIn("wallet", schema["paths"]["/api/v1/wallet/accounts/{account_id}"]["get"]["tags"])
        self.assertIn("wallet", schema["paths"]["/api/v1/wallet/accounts/{account_id}/cash-balances"]["get"]["tags"])
        self.assertNotIn("/api/v1/wallet/accounts", schema["paths"])
        self.assertNotIn("/api/v1/wallet/accounts/{account_id}/wallet-facts", schema["paths"])
        self.assertIn("models", schema["paths"]["/api/v1/models/providers"]["get"]["tags"])
        self.assertIn("models", schema["paths"]["/api/v1/models/providers"]["post"]["tags"])
        self.assertIn("models", schema["paths"]["/api/v1/models/providers/{provider_id}"]["get"]["tags"])
        self.assertIn("models", schema["paths"]["/api/v1/models/providers/{provider_id}"]["put"]["tags"])
        self.assertIn("models", schema["paths"]["/api/v1/models/providers/{provider_id}/actions/set-default"]["post"]["tags"])
        self.assertIn("models", schema["paths"]["/api/v1/models/providers/{provider_id}/actions/test-connection"]["post"]["tags"])
        self.assertIn("models", schema["paths"]["/api/v1/models/providers/{provider_id}/models"]["post"]["tags"])
        self.assertIn("models", schema["paths"]["/api/v1/models/providers/{provider_id}/models/{model_id}"]["put"]["tags"])
        self.assertIn("models", schema["paths"]["/api/v1/models/providers/{provider_id}/models/{model_id}"]["delete"]["tags"])
        self.assertIn("models", schema["paths"]["/api/v1/models/presets"]["get"]["tags"])
        self.assertIn("models", schema["paths"]["/api/v1/models/presets/{preset_key}"]["put"]["tags"])
        self.assertIn("models", schema["paths"]["/api/v1/models/invocations"]["get"]["tags"])
        self.assertIn("source-bindings", schema["paths"]["/api/v1/source-bindings"]["get"]["tags"])
        self.assertIn("source-bindings", schema["paths"]["/api/v1/source-bindings/{binding_id}"]["get"]["tags"])
        self.assertIn("source-bindings", schema["paths"]["/api/v1/source-bindings/{binding_id}/scheduler-runs"]["get"]["tags"])
        self.assertIn("source-bindings", schema["paths"]["/api/v1/source-bindings/{binding_id}/actions/run-now"]["post"]["tags"])
        self.assertIn("runtime", schema["paths"]["/api/v1/scheduler-runs"]["get"]["tags"])
        self.assertIn("runtime", schema["paths"]["/api/v1/scheduler-runs/{run_id}"]["get"]["tags"])
        self.assertIn("runtime", schema["paths"]["/api/v1/runtime/audit/news"]["get"]["tags"])
        approval_paths = {
            "/api/v1/approvals": ("get", "ApprovalListResponse"),
            "/api/v1/approvals/{approval_id}": ("get", "ApprovalDetailResponse"),
            "/api/v1/approvals/{approval_id}/actions/approve": ("post", "ApprovalActionResponse"),
            "/api/v1/approvals/{approval_id}/actions/reject": ("post", "ApprovalActionResponse"),
            "/api/v1/approvals/{approval_id}/actions/request-reanalysis": ("post", "ApprovalActionResponse"),
        }
        for path, (method, data_schema_name) in approval_paths.items():
            self.assertIn(path, schema["paths"])
            self.assertIn("approvals", schema["paths"][path][method]["tags"])
            response_ref = schema["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
            self.assertIn("ApiResponse_", response_ref)
            self.assertIn(data_schema_name, response_ref)

        approval_list_schema = self._resolve_response_schema(schema, "/api/v1/approvals")
        self.assertTrue({"code", "data", "msg", "error"}.issubset(approval_list_schema["properties"].keys()))
        approval_list_data_schema = self._resolve_schema_ref(schema, approval_list_schema["properties"]["data"])
        self.assertIn("items", approval_list_data_schema["properties"])
        self.assertIn("next_cursor", approval_list_data_schema["properties"])

        approval_detail_schema = self._resolve_response_schema(schema, "/api/v1/approvals/{approval_id}")
        self.assertTrue({"code", "data", "msg", "error"}.issubset(approval_detail_schema["properties"].keys()))
        approval_detail_data_schema = self._resolve_schema_ref(schema, approval_detail_schema["properties"]["data"])
        self.assertIn("audit_refs", approval_detail_data_schema["properties"])
        self.assertIn("decisions", approval_detail_data_schema["properties"])

        approval_action_schema = self._resolve_response_schema(
            schema,
            "/api/v1/approvals/{approval_id}/actions/approve",
            method="post",
        )
        self.assertTrue({"code", "data", "msg", "error"}.issubset(approval_action_schema["properties"].keys()))
        approval_action_data_schema = self._resolve_schema_ref(schema, approval_action_schema["properties"]["data"])
        self.assertIn("approval", approval_action_data_schema["properties"])
        self.assertIn("decision", approval_action_data_schema["properties"])
        self.assertNotIn("/api/v1/auth/test-actions/runtime-inspect", schema["paths"])

        login_schema = self._resolve_response_schema(schema, "/api/v1/auth/login", method="post")
        self.assertTrue({"code", "data", "msg", "error"}.issubset(login_schema["properties"].keys()))

        logout_schema = self._resolve_response_schema(schema, "/api/v1/auth/logout", method="post")
        self.assertTrue({"code", "data", "msg", "error"}.issubset(logout_schema["properties"].keys()))

        refresh_schema = self._resolve_response_schema(schema, "/api/v1/auth/refresh", method="post")
        refresh_data_schema = self._resolve_schema_ref(schema, refresh_schema["properties"]["data"])
        self.assertTrue(
            {"actor_id", "actor_type", "capabilities", "csrf_token", "expires_at", "max_expires_at"}.issubset(
                refresh_data_schema["properties"]
            )
        )

        me_schema = self._resolve_response_schema(schema, "/api/v1/me")
        me_data_schema = self._resolve_schema_ref(schema, me_schema["properties"]["data"])
        self.assertTrue({"actor_id", "actor_type", "capabilities", "csrf_token"}.issubset(me_data_schema["properties"]))

        plugins_schema = self._resolve_response_schema(schema, "/api/v1/plugins")
        self.assertTrue({"code", "data", "msg", "error"}.issubset(plugins_schema["properties"].keys()))
        plugin_record_variants = plugins_schema["properties"]["data"]["anyOf"]
        plugin_record_array_schema = next(variant for variant in plugin_record_variants if variant.get("type") == "array")
        plugin_record_schema = self._resolve_schema_ref(schema, plugin_record_array_schema["items"])
        manifest_schema = self._resolve_schema_ref(schema, plugin_record_schema["properties"]["manifest"]["anyOf"][0])
        self.assertIn("source_bindings", manifest_schema["properties"])

        wallet_account_schema = self._resolve_response_schema(schema, "/api/v1/wallet/accounts/{account_id}")
        wallet_account_data_schema = self._resolve_schema_ref(schema, wallet_account_schema["properties"]["data"])
        self.assertEqual(
            set(wallet_account_data_schema["properties"].keys()),
            {"account_id", "name", "mode", "base_currency", "created_at"},
        )
        self.assertEqual(wallet_account_data_schema["properties"]["mode"]["const"], "paper")

        wallet_cash_schema = self._resolve_response_schema(schema, "/api/v1/wallet/accounts/{account_id}/cash-balances")
        wallet_cash_data_variants = wallet_cash_schema["properties"]["data"]["anyOf"]
        wallet_cash_array_schema = next(variant for variant in wallet_cash_data_variants if variant.get("type") == "array")
        wallet_cash_items_schema = self._resolve_schema_ref(schema, wallet_cash_array_schema["items"])
        self.assertTrue(
            {
                "account_id",
                "currency",
                "total",
                "available",
                "locked",
                "unsettled",
                "updated_at",
            }.issubset(wallet_cash_items_schema["properties"])
        )

        models_schema = self._resolve_response_schema(schema, "/api/v1/models/providers")
        self.assertTrue({"code", "data", "msg", "error"}.issubset(models_schema["properties"].keys()))

        source_bindings_schema = self._resolve_response_schema(schema, "/api/v1/source-bindings")
        self.assertTrue({"code", "data", "msg", "error"}.issubset(source_bindings_schema["properties"].keys()))

        binding_runs_schema = self._resolve_response_schema(schema, "/api/v1/source-bindings/{binding_id}/scheduler-runs")
        self.assertTrue({"code", "data", "msg", "error"}.issubset(binding_runs_schema["properties"].keys()))
        binding_runs_data_schema = self._resolve_schema_ref(schema, binding_runs_schema["properties"]["data"])
        binding_runs_meta_schema = self._resolve_schema_ref(schema, binding_runs_data_schema["properties"]["meta"])
        binding_runs_page_schema = self._resolve_schema_ref(schema, binding_runs_meta_schema["properties"]["page"])
        self.assertIn("cursor", binding_runs_page_schema["properties"])
        self.assertIn("next_cursor", binding_runs_page_schema["properties"])

        scheduler_run_schema = self._resolve_response_schema(schema, "/api/v1/scheduler-runs/{run_id}")
        self.assertTrue({"code", "data", "msg", "error"}.issubset(scheduler_run_schema["properties"].keys()))

        runtime_audit_news_schema = self._resolve_response_schema(schema, "/api/v1/runtime/audit/news")
        self.assertTrue({"code", "data", "msg", "error"}.issubset(runtime_audit_news_schema["properties"].keys()))
        runtime_audit_news_data_schema = self._resolve_schema_ref(schema, runtime_audit_news_schema["properties"]["data"])
        self.assertTrue({"items", "next_cursor", "generated_at"}.issubset(runtime_audit_news_data_schema["properties"].keys()))

        agent_debug_stream_content = schema["paths"]["/api/v1/debug/agent-runs/fixtures/{fixture_id}/stream"]["post"][
            "responses"
        ]["200"]["content"]
        self.assertIn("text/event-stream", agent_debug_stream_content)
        self.assertNotIn("application/json", agent_debug_stream_content)

    def test_production_openapi_excludes_debug_routes(self) -> None:
        production_app = create_app(self._settings(APP_ENV="production"))
        with TestClient(production_app) as client:
            response = client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertIn("/api/v1/version", schema["paths"])
        self.assertIn("/api/v1/health", schema["paths"])
        self.assertIn("/api/v1/ready", schema["paths"])
        self.assertIn("/api/v1/wallet/accounts/{account_id}", schema["paths"])
        self.assertNotIn("/api/v1/debug/error", schema["paths"])
        self.assertNotIn("/api/v1/debug/success", schema["paths"])
        self.assertNotIn("/api/v1/debug/agent-runs/fixtures/{fixture_id}/stream", schema["paths"])
        self.assertNotIn("/api/v1/auth/test-actions/runtime-inspect", schema["paths"])

    def test_create_app_does_not_configure_logging_before_lifespan(self) -> None:
        shutdown_api_logging()
        logger = logging.getLogger("quantagent.api")
        before_handlers = list(logger.handlers)
        self.addCleanup(shutdown_api_logging)
        self.addCleanup(lambda: setattr(logger, "handlers", before_handlers))

        create_app(self._settings(AUTH_ENABLED=False))

        self.assertFalse(any(isinstance(handler, InMemoryStructuredHandler) for handler in logger.handlers))

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

    def _seed_runtime_audit_news(self, session) -> None:
        session.add_all(
            [
                SourceBindingORM(
                    binding_id="binding-runtime-001",
                    owner_type="industry",
                    owner_id="semiconductor",
                    source_plugin_id="quantagent.official.source.rss",
                    effective_config_snapshot={"feed": "https://example.com/rss"},
                    schedule_policy={"interval_seconds": 300},
                    retry_policy={"max_attempts": 3},
                    rate_limit_policy={"requests_per_minute": 10},
                    status="active",
                    created_by="test",
                    updated_by="test",
                ),
                SourceBindingORM(
                    binding_id="binding-runtime-002",
                    owner_type="industry",
                    owner_id="semiconductor",
                    source_plugin_id="quantagent.official.source.rss",
                    effective_config_snapshot={"feed": "https://example.com/packaging.xml"},
                    schedule_policy={"interval_seconds": 300},
                    retry_policy={"max_attempts": 3},
                    rate_limit_policy={"requests_per_minute": 10},
                    status="active",
                    created_by="test",
                    updated_by="test",
                ),
                SchedulerRunORM(
                    run_id="run-runtime-001",
                    binding_id="binding-runtime-001",
                    source_plugin_id="quantagent.official.source.rss",
                    source_plugin_version=None,
                    trigger_mode="scheduled",
                    request_id="req-run-runtime-001",
                    status="succeeded",
                    started_at=datetime(2026, 6, 1, 9, 0, 0, tzinfo=UTC),
                    finished_at=datetime(2026, 6, 1, 9, 0, 5, tzinfo=UTC),
                    duration_ms=5000,
                    captured_count=1,
                    metadata_json={"trace_id": "trace-runtime-001", "correlation_id": "corr-runtime-001"},
                ),
                RawEventORM(
                    raw_event_id="rawevt-runtime-001",
                    source_plugin_id="quantagent.official.source.rss",
                    external_id="entry-runtime-001",
                    canonical_url="https://semis.example.com/news/hbm",
                    title="HBM supply tightens",
                    content="HBM supply chain update for semiconductor audit.",
                    author="Memory Desk",
                    published_at=datetime(2026, 6, 1, 8, 30, 0, tzinfo=UTC),
                    first_captured_at=datetime(2026, 6, 1, 9, 0, 1, tzinfo=UTC),
                    last_captured_at=datetime(2026, 6, 1, 9, 0, 2, tzinfo=UTC),
                    raw_payload={"body": "full HBM body", "secret": "secret-token"},
                    metadata_json={"source": "SemiWire", "feed": "memory", "trace_id": "trace-runtime-001"},
                    canonical_dedupe_key="dedupe-runtime-001",
                    dedupe_strategy="canonical_url",
                    content_hash="hash-runtime-001",
                    first_binding_id="binding-runtime-001",
                    first_run_id="run-runtime-001",
                    duplicate_capture_count=0,
                    created_at=datetime(2026, 6, 1, 9, 0, 3, tzinfo=UTC),
                    updated_at=datetime(2026, 6, 1, 9, 0, 3, tzinfo=UTC),
                ),
                EventIntakeRoutedEventORM(
                    event_id="evt-routed-runtime-001",
                    schema_version="event_intake_decision.v1",
                    raw_event_id="rawevt-runtime-001",
                    source_message_id="evt-source-runtime-001",
                    analysis_request_id="evt-analysis-runtime-001",
                    binding_id="binding-runtime-001",
                    owner_type="industry",
                    owner_id="semiconductor",
                    request_id="req-1",
                    correlation_id="corr-runtime-001",
                    decision="route",
                    discard_reason="not_discarded",
                    status="success",
                    summary="HBM demand is directly relevant.",
                    output_json={
                        "schema_version": "event_intake_decision.v1",
                        "decision": "route",
                        "discard_reason": "not_discarded",
                        "quality": {
                            "is_spam": False,
                            "noise_flags": [],
                            "content_completeness": "full",
                            "enrichment_status": "succeeded",
                            "confidence": 0.88,
                        },
                        "industry_relevance": [
                            {
                                "industry_id": "semiconductor",
                                "relationship": "direct",
                                "relevance_score": 0.91,
                                "reason_summary": "HBM demand is directly relevant.",
                            }
                        ],
                        "structured_news": {
                            "canonical_title": "HBM demand update",
                            "short_summary": "HBM demand is directly relevant.",
                            "bullet_summary": ["HBM demand is directly relevant."],
                            "event_type": "supply_demand",
                            "entities": ["HBM"],
                            "companies": [],
                            "tickers": [],
                            "technologies": ["HBM"],
                            "products": ["memory"],
                            "locations": [],
                            "numbers": [],
                            "time_horizon": "near_term",
                            "source_facts": ["HBM demand and advanced packaging capacity tighten."],
                            "reasoning_prompt": "must redact prompt",
                            "uncertainties": [],
                        },
                        "routing": {
                            "target_industries": ["semiconductor"],
                            "target_topics": ["memory"],
                            "priority": "high",
                            "requires_deep_analysis": True,
                            "requires_human_review": False,
                            "dedupe_key_hint": "https://example.com/hbm",
                            "provider_raw_response": "must redact raw response",
                            "api_token": "secret-token",
                        },
                        "audit": {
                            "reason_summary": "Direct semiconductor memory relevance.",
                            "evidence_field_refs": ["article.title", "article.body_excerpt"],
                            "schema_validation_status": "valid",
                        },
                        "source": {
                            "plugin_id": "quantagent.official.source.rss",
                            "binding_id": "binding-runtime-001",
                            "url": "https://semis.example.com/news/hbm",
                            "title": "HBM supply tightens",
                            "published_at": "2026-06-01T08:30:00+00:00",
                            "source_name": "SemiWire",
                            "enrichment_status": "succeeded",
                            "degraded_reason": None,
                        },
                        "article": {
                            "content_completeness": "full",
                            "body_content_available": True,
                            "content_length_chars": 48,
                            "excerpt_start": 0,
                            "excerpt_end": 48,
                        },
                    },
                    key_fields={
                        "decision": "route",
                        "discard_reason": "not_discarded",
                        "short_summary": "HBM demand is directly relevant.",
                        "event_type": "supply_demand",
                        "target_industries": ["semiconductor"],
                        "target_topics": ["memory"],
                        "priority": "high",
                        "requires_deep_analysis": True,
                        "requires_human_review": False,
                        "confidence": 0.88,
                        "is_spam": False,
                        "relevance": "semiconductor / direct / 0.91",
                        "schema_validation_status": "valid",
                    },
                    source_snapshot={
                        "plugin_id": "quantagent.official.source.rss",
                        "binding_id": "binding-runtime-001",
                        "url": "https://semis.example.com/news/hbm",
                        "title": "HBM supply tightens",
                        "published_at": "2026-06-01T08:30:00+00:00",
                        "author": "Memory Desk",
                        "language": "en",
                        "feed_name": "memory",
                        "source_name": "SemiWire",
                        "source_tier": None,
                        "enrichment_status": "succeeded",
                        "degraded_reason": None,
                    },
                    article_snapshot={
                        "title": "HBM supply tightens",
                        "rss_summary": "HBM demand and advanced packaging capacity tighten.",
                        "body_excerpt": "HBM demand and advanced packaging capacity tighten.",
                        "body_content_available": True,
                        "content_length_chars": 48,
                        "excerpt_start": 0,
                        "excerpt_end": 48,
                        "content_completeness": "full",
                    },
                    provider_invocation_count=1,
                    invocation_metadata={"status": "succeeded", "provider_metadata": {"model": "router-preview"}},
                    created_at=datetime(2026, 6, 1, 9, 0, 6, tzinfo=UTC),
                ),
                RawEventORM(
                    raw_event_id="rawevt-runtime-002",
                    source_plugin_id="quantagent.official.source.rss",
                    external_id="entry-runtime-002",
                    canonical_url="https://news.example.com/articles/advanced-packaging",
                    title="Advanced packaging capacity expands",
                    content="Advanced packaging capacity expands across outsourced semiconductor assembly and test vendors.",
                    author="Foundry Desk",
                    published_at=datetime(2026, 6, 2, 7, 0, 0, tzinfo=UTC),
                    first_captured_at=datetime(2026, 6, 2, 7, 1, 0, tzinfo=UTC),
                    last_captured_at=datetime(2026, 6, 2, 7, 1, 2, tzinfo=UTC),
                    raw_payload={"body": "very large full article body", "secret": "secret-token"},
                    metadata_json={"source": "Packaging Daily", "feed": "advanced-packaging"},
                    canonical_dedupe_key="dedupe-runtime-002",
                    dedupe_strategy="canonical_url",
                    content_hash="hash-runtime-002",
                    first_binding_id="binding-runtime-002",
                    first_run_id=None,
                    duplicate_capture_count=1,
                    created_at=datetime(2026, 6, 2, 7, 1, 3, tzinfo=UTC),
                    updated_at=datetime(2026, 6, 2, 7, 1, 3, tzinfo=UTC),
                ),
                RawEventCaptureORM(
                    capture_id="capture-runtime-001",
                    raw_event_id="rawevt-runtime-001",
                    source_plugin_id="quantagent.official.source.rss",
                    source_binding_id="binding-runtime-001",
                    scheduler_run_id="run-runtime-001",
                    capture_dedupe_key="capture-dedupe-runtime-001",
                    capture_status="captured",
                    captured_at=datetime(2026, 6, 1, 9, 0, 1, tzinfo=UTC),
                    request_id="req-capture-001",
                    metadata_json={"trace_id": "trace-runtime-001", "correlation_id": "corr-runtime-001"},
                ),
                RawEventCaptureORM(
                    capture_id="capture-runtime-002",
                    raw_event_id="rawevt-runtime-002",
                    source_plugin_id="quantagent.official.source.rss",
                    source_binding_id="binding-runtime-002",
                    scheduler_run_id=None,
                    capture_dedupe_key="capture-dedupe-runtime-002",
                    capture_status="captured",
                    captured_at=datetime(2026, 6, 2, 7, 1, 0, tzinfo=UTC),
                    request_id="req-capture-002",
                    metadata_json={},
                ),
            ]
        )

    def _seed_approval(self, client: TestClient, approval_id: str) -> None:
        Base.metadata.create_all(client.app.state.db_engine)
        with client.app.state.db_session_factory() as session:
            repository = SQLAlchemyApprovalRepository(session)
            repository.save_action_request(
                ApprovalActionRequestModel(
                    id="action-api-1",
                    action_type="adjust_strategy",
                    action_side="increase_risk",
                    target_type="strategy",
                    target_id="strategy-api-1",
                    risk_flags=("high_risk",),
                    proposed_payload={"summary": "masked"},
                )
            )
            repository.save_approval_request(
                ApprovalRequestModel(
                    id=approval_id,
                    action_request_id="action-api-1",
                    target_type="strategy",
                    target_id="strategy-api-1",
                    action_type="adjust_strategy",
                    action_side="increase_risk",
                    risk_level="high",
                    urgency="normal",
                    summary="adjust_strategy increase_risk for strategy:strategy-api-1",
                    proposed_payload={"summary": "masked"},
                    required_confirmation_level=ApprovalConfirmationLevel.SOFT_CONFIRM,
                    expiration_action=ApprovalExpirationAction.EXPIRE_REJECT,
                    policy_source="api_test",
                    allowed_channels=("web",),
                )
            )
            session.commit()

    def _login(self) -> None:
        response = self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
        self.assertEqual(response.status_code, 200)

    def _login_with_client(self, client: TestClient, settings: Settings) -> str:
        response = client.post("/api/v1/auth/login", json={"password": settings.AUTH_ADMIN_PASSWORD})
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]["csrf_token"]

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
            "_env_file": None,
            "APP_ENV": "development",
            "DATABASE_URL": None,
            "RUNTIME_DIR": "runtime",
            "LOG_LEVEL": "INFO",
            "API_V1_PREFIX": "/api/v1",
            "API_HOST": "127.0.0.1",
            "API_PORT": 8000,
            "AUTH_ENABLED": True,
            "AUTH_ADMIN_PASSWORD": "test-admin-password",
            "AUTH_SESSION_SECRET": "test-session-secret-0123456789abcdef",
            "NOTIFICATION_INGRESS_ENABLED": False,
            "NOTIFICATION_INGRESS_PLUGIN_ID": "",
            "NOTIFICATION_INGRESS_PLUGIN_CONFIG": {},
        }
        baseline.update(overrides)
        return Settings(**baseline)

    def _current_session_payload(self) -> dict[str, object]:
        session_values = [cookie.value for cookie in self.client.cookies.jar if cookie.name == self.settings.AUTH_COOKIE_NAME]
        self.assertTrue(session_values)
        session_value = session_values[-1]
        return _deserialize_session(session_value, self.settings.AUTH_SESSION_SECRET or "")


if __name__ == "__main__":
    unittest.main()
