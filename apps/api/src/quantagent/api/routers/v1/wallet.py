from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Annotated, TypeVar

from fastapi import APIRouter, Query, Request
from sqlalchemy.exc import SQLAlchemyError

from quantagent.api.db import DB_SESSION_FACTORY_STATE_KEY
from quantagent.api.http.errors import BadRequestError, NotFoundError, ServiceUnavailableError
from quantagent.api.http.responses import ApiResponse
from quantagent.api.schemas.wallet import (
    WalletAccountResponse,
    WalletCashBalanceResponse,
    WalletLedgerEntryResponse,
    WalletPaperExecutionResponse,
    WalletPaperOrderResponse,
    WalletPositionResponse,
)
from quantagent.core.wallet import WalletService


router = APIRouter(prefix="/wallet", tags=["wallet"])
logger = logging.getLogger("quantagent.api")

_UNKNOWN_ACCOUNT_PREFIX = "Unknown trading account:"
_LIMIT_ERROR_MESSAGE = "limit must be greater than zero."
_PAPER_ONLY_ERROR_MESSAGE = "Portfolio Wallet Core V1 only supports paper accounts."
_T = TypeVar("_T")


@router.get(
    "/accounts/{account_id}",
    response_model=ApiResponse[WalletAccountResponse],
    tags=["wallet"],
)
def get_wallet_account(account_id: str, request: Request) -> ApiResponse[WalletAccountResponse]:
    account = _require_wallet_account(_get_wallet_service(request), account_id)
    return ApiResponse.success(WalletAccountResponse.from_snapshot(account))


@router.get(
    "/accounts/{account_id}/cash-balances",
    response_model=ApiResponse[list[WalletCashBalanceResponse]],
    tags=["wallet"],
)
def list_wallet_cash_balances(account_id: str, request: Request) -> ApiResponse[list[WalletCashBalanceResponse]]:
    service = _get_wallet_service(request)
    _require_wallet_account(service, account_id)
    balances = _map_wallet_value_error(lambda: service.list_cash_balances(account_id), account_id=account_id)
    return ApiResponse.success([WalletCashBalanceResponse.from_snapshot(item) for item in balances])


@router.get(
    "/accounts/{account_id}/positions",
    response_model=ApiResponse[list[WalletPositionResponse]],
    tags=["wallet"],
)
def list_wallet_positions(account_id: str, request: Request) -> ApiResponse[list[WalletPositionResponse]]:
    service = _get_wallet_service(request)
    _require_wallet_account(service, account_id)
    positions = _map_wallet_value_error(lambda: service.list_positions(account_id), account_id=account_id)
    return ApiResponse.success([WalletPositionResponse.from_snapshot(item) for item in positions])


@router.get(
    "/accounts/{account_id}/ledger-entries",
    response_model=ApiResponse[list[WalletLedgerEntryResponse]],
    tags=["wallet"],
)
def list_wallet_ledger_entries(
    account_id: str,
    request: Request,
    limit: Annotated[int | None, Query(gt=0)] = None,
) -> ApiResponse[list[WalletLedgerEntryResponse]]:
    service = _get_wallet_service(request)
    _require_wallet_account(service, account_id)
    entries = _map_wallet_value_error(lambda: service.list_ledger_entries(account_id, limit=limit), account_id=account_id)
    return ApiResponse.success([WalletLedgerEntryResponse.from_snapshot(item) for item in entries])


@router.get(
    "/accounts/{account_id}/paper-orders",
    response_model=ApiResponse[list[WalletPaperOrderResponse]],
    tags=["wallet"],
)
def list_wallet_paper_orders(account_id: str, request: Request) -> ApiResponse[list[WalletPaperOrderResponse]]:
    service = _get_wallet_service(request)
    _require_wallet_account(service, account_id)
    orders = _map_wallet_value_error(lambda: service.list_paper_orders(account_id), account_id=account_id)
    return ApiResponse.success([WalletPaperOrderResponse.from_snapshot(item) for item in orders])


@router.get(
    "/accounts/{account_id}/paper-executions",
    response_model=ApiResponse[list[WalletPaperExecutionResponse]],
    tags=["wallet"],
)
def list_wallet_paper_executions(account_id: str, request: Request) -> ApiResponse[list[WalletPaperExecutionResponse]]:
    service = _get_wallet_service(request)
    _require_wallet_account(service, account_id)
    executions = _map_wallet_value_error(lambda: service.list_paper_executions(account_id), account_id=account_id)
    return ApiResponse.success([WalletPaperExecutionResponse.from_snapshot(item) for item in executions])


def _get_wallet_service(request: Request) -> WalletService:
    service = getattr(request.app.state, "wallet_service", None)
    if service is not None:
        return service

    session_factory = getattr(request.app.state, DB_SESSION_FACTORY_STATE_KEY, None)
    if session_factory is None:
        raise ServiceUnavailableError("Database not configured")
    return WalletService(session_factory)


def _require_wallet_account(service: WalletService, account_id: str):
    account = _map_wallet_value_error(lambda: service.get_trading_account(account_id), account_id=account_id)
    if account is None:
        raise NotFoundError("Wallet account not found", details={"account_id": account_id})
    return account


def _map_wallet_value_error(operation: Callable[[], _T], *, account_id: str) -> _T:
    try:
        return operation()
    except SQLAlchemyError as exc:
        logger.warning("Wallet query failed: %s", exc.__class__.__name__)
        raise ServiceUnavailableError("Database not ready") from exc
    except ValueError as exc:
        message = str(exc)
        if message.startswith(_UNKNOWN_ACCOUNT_PREFIX):
            raise NotFoundError("Wallet account not found", details={"account_id": account_id}) from exc
        if _LIMIT_ERROR_MESSAGE in message:
            raise BadRequestError("Invalid wallet query", details={"field": "limit"}) from exc
        if message == _PAPER_ONLY_ERROR_MESSAGE:
            raise BadRequestError("Wallet API only supports paper accounts") from exc
        raise BadRequestError("Invalid wallet request") from exc
