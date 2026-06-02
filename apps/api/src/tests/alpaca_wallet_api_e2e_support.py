from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any, Mapping, Sequence
from urllib import error as urllib_error
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from quantagent.core.wallet import OrderSide, OrderType


ALPACA_PAPER_BASE_URL = "https://paper-api.alpaca.markets"
ALPACA_PAPER_BASE_URL_ENV = "ALPACA_PAPER_BASE_URL"
APCA_API_KEY_ID_ENV = "APCA_API_KEY_ID"
APCA_API_SECRET_KEY_ENV = "APCA_API_SECRET_KEY"
QUANTAGENT_ALPACA_PAPER_SMOKE_ENV = "QUANTAGENT_ALPACA_PAPER_SMOKE"
QUANTAGENT_ALPACA_WALLET_API_E2E_SMOKE_ENV = "QUANTAGENT_ALPACA_WALLET_API_E2E_SMOKE"
QUANTAGENT_ALPACA_WALLET_API_E2E_RUN_TOKEN_ENV = "QUANTAGENT_ALPACA_WALLET_API_E2E_RUN_TOKEN"
QUANTAGENT_ALPACA_WALLET_API_E2E_RUN_TOKEN_VALUE = "run-external-alpaca-smoke"
REDACTED = "<redacted>"
REDACTED_RESPONSE_BODY = "<redacted-response-body>"
REDACTED_MESSAGE = "<redacted-message>"
DEFAULT_MARKET = "ALPACA"
DEFAULT_TIMEOUT_SECONDS = 10.0

_SENSITIVE_VALUE_KEYS = frozenset(
    {
        "account_id",
        "account_number",
        "api_key",
        "api_key_id",
        "client_order_id",
        "id",
        "key_id",
        "order_id",
        "secret",
        "secret_key",
    }
)
_RAW_BODY_KEYS = frozenset({"body", "raw_body", "response_body"})


@dataclass(frozen=True)
class AlpacaPaperConfig:
    base_url: str
    api_key_id: str | None
    api_secret_key: str | None
    smoke_enabled: bool
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class AlpacaBrokerError:
    category: str
    message: str
    status_code: int | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


class AlpacaPaperRequestError(RuntimeError):
    def __init__(self, broker_error: AlpacaBrokerError) -> None:
        super().__init__(broker_error.message)
        self.broker_error = broker_error


@dataclass(frozen=True)
class AlpacaHttpResponse:
    status_code: int
    payload: Any
    raw_body: str | None = None


@dataclass(frozen=True)
class BrokerSimulatorAccount:
    account_id: str
    name: str
    base_currency: str = "USD"


@dataclass(frozen=True)
class BrokerSimulatorCashBalance:
    currency: str
    total: Decimal | str | int
    source_key: str | None = None


@dataclass(frozen=True)
class BrokerSimulatorPositionContext:
    instrument: str
    market: str
    currency: str
    quantity: Decimal | str | int
    average_cost: Decimal | str | int | None = None


@dataclass(frozen=True)
class BrokerSimulatorFixture:
    account: BrokerSimulatorAccount
    cash_balances: tuple[BrokerSimulatorCashBalance, ...] = ()
    position_contexts: tuple[BrokerSimulatorPositionContext, ...] = ()


@dataclass(frozen=True)
class BrokerSimulatorOrderInput:
    instrument: str
    market: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    currency: str
    broker_order_id: str | None = None
    client_order_id: str | None = None
    limit_price: Decimal | None = None
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class BrokerSimulatorExecutionInput:
    source_key: str
    instrument: str
    market: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    currency: str
    external_execution_id: str | None = None
    broker_order_id: str | None = None
    fee_amount: Decimal = Decimal("0")
    fee_currency: str | None = None
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class AlpacaMappedAccount:
    fixture: BrokerSimulatorFixture
    cash_currency: str
    cash_total: Decimal
    buying_power: Decimal | None
    broker_account_context: Mapping[str, Any]


@dataclass(frozen=True)
class AlpacaReadOnlySnapshot:
    fixture: BrokerSimulatorFixture
    buying_power: Decimal | None
    orders: tuple[BrokerSimulatorOrderInput, ...]


def load_alpaca_paper_config(env: Mapping[str, str] | None = None) -> AlpacaPaperConfig:
    source = env if env is not None else os.environ
    return AlpacaPaperConfig(
        base_url=(source.get(ALPACA_PAPER_BASE_URL_ENV) or ALPACA_PAPER_BASE_URL).strip(),
        api_key_id=_clean_optional(source.get(APCA_API_KEY_ID_ENV)),
        api_secret_key=_clean_optional(source.get(APCA_API_SECRET_KEY_ENV)),
        smoke_enabled=_env_flag_enabled(source.get(QUANTAGENT_ALPACA_PAPER_SMOKE_ENV)),
    )


def validate_paper_base_url(base_url: str) -> str:
    candidate = (base_url or "").strip()
    if not candidate:
        raise ValueError("Alpaca paper base URL is required.")
    parsed = urlsplit(candidate)
    if parsed.scheme != "https":
        raise ValueError("Alpaca paper base URL must use https.")
    if parsed.hostname != "paper-api.alpaca.markets":
        raise ValueError("Alpaca paper base URL must target paper-api.alpaca.markets.")
    if parsed.path not in ("", "/"):
        raise ValueError("Alpaca paper base URL must not include a path.")
    if parsed.query or parsed.fragment or parsed.username or parsed.password or parsed.port:
        raise ValueError("Alpaca paper base URL must not include query, fragment, auth or port.")
    return ALPACA_PAPER_BASE_URL


def get_read_only_smoke_skip_reason(config: AlpacaPaperConfig) -> str | None:
    if not config.smoke_enabled:
        return f"{QUANTAGENT_ALPACA_PAPER_SMOKE_ENV} is not enabled."
    try:
        validate_paper_base_url(config.base_url)
    except ValueError as exc:
        return str(exc)
    if not config.api_key_id or not config.api_secret_key:
        return "Alpaca paper credentials are missing."
    return None


def get_wallet_api_external_smoke_skip_reason(
    config: AlpacaPaperConfig,
    env: Mapping[str, str] | None = None,
) -> str | None:
    source = env if env is not None else os.environ
    if source.get(QUANTAGENT_ALPACA_WALLET_API_E2E_SMOKE_ENV) != "1":
        return f"{QUANTAGENT_ALPACA_WALLET_API_E2E_SMOKE_ENV} is not enabled."
    # 外部 smoke 需要本次命令显式 token，避免本机常驻 .env/direnv 变量让默认 discover 访问真实网络。
    if source.get(QUANTAGENT_ALPACA_WALLET_API_E2E_RUN_TOKEN_ENV) != (
        QUANTAGENT_ALPACA_WALLET_API_E2E_RUN_TOKEN_VALUE
    ):
        return f"{QUANTAGENT_ALPACA_WALLET_API_E2E_RUN_TOKEN_ENV} is not confirmed for this run."
    return get_read_only_smoke_skip_reason(config)


def redact_sensitive_value(value: Any) -> Any:
    if value in (None, ""):
        return value
    return REDACTED


def sanitize_for_logs(payload: Any, *, key: str | None = None) -> Any:
    if isinstance(payload, Mapping):
        return {name: sanitize_for_logs(value, key=name) for name, value in payload.items()}
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        return [sanitize_for_logs(value) for value in payload]
    normalized_key = (key or "").strip().lower()
    if normalized_key in _RAW_BODY_KEYS:
        return REDACTED_RESPONSE_BODY
    if normalized_key in _SENSITIVE_VALUE_KEYS or normalized_key.endswith("_id") or normalized_key.endswith("_secret"):
        return redact_sensitive_value(payload)
    if normalized_key.endswith("message") and isinstance(payload, str):
        return REDACTED_MESSAGE
    return payload


def map_alpaca_error(
    *,
    status_code: int | None = None,
    payload: Any = None,
    exception: Exception | None = None,
) -> AlpacaBrokerError:
    normalized_payload = sanitize_for_logs(payload)
    details = {"payload": normalized_payload} if payload is not None else {}

    if isinstance(exception, urllib_error.URLError) and isinstance(
        getattr(exception, "reason", None),
        (TimeoutError, socket.timeout),
    ):
        return AlpacaBrokerError("timeout", "alpaca paper request timed out", details=MappingProxyType(details))
    if isinstance(exception, (TimeoutError, socket.timeout)):
        return AlpacaBrokerError("timeout", "alpaca paper request timed out", details=MappingProxyType(details))
    if exception is not None:
        return AlpacaBrokerError(
            "external_unavailable",
            "alpaca paper endpoint is unavailable",
            details=MappingProxyType(details),
        )

    message_source = _extract_message(payload)
    message_lower = message_source.lower()
    if status_code in (401, 403) and "buying power" not in message_lower:
        category = "authentication_failed"
        message = "alpaca paper authentication failed"
    elif "buying power" in message_lower:
        category = "insufficient_buying_power"
        message = "alpaca paper reported insufficient buying power"
    elif "symbol" in message_lower:
        category = "invalid_symbol"
        message = "alpaca paper rejected the symbol"
    else:
        category = "external_unavailable"
        message = "alpaca paper endpoint returned an unavailable response"

    return AlpacaBrokerError(category, message, status_code=status_code, details=MappingProxyType(details))


class UrllibAlpacaTransport:
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, Any] | None = None,
        timeout_seconds: float,
    ) -> AlpacaHttpResponse:
        query = urlencode({name: value for name, value in (params or {}).items() if value is not None}, doseq=True)
        request_url = f"{url}?{query}" if query else url
        request = Request(request_url, headers=dict(headers), method=method)

        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                raw_bytes = response.read()
                raw_body = raw_bytes.decode("utf-8", errors="replace")
                return AlpacaHttpResponse(
                    status_code=response.status,
                    payload=_decode_json_body(raw_body),
                    raw_body=raw_body,
                )
        except urllib_error.HTTPError as exc:
            raw_body = exc.read().decode("utf-8", errors="replace")
            return AlpacaHttpResponse(
                status_code=exc.code,
                payload=_decode_json_body(raw_body),
                raw_body=raw_body,
            )
        except urllib_error.URLError as exc:
            raise AlpacaPaperRequestError(map_alpaca_error(exception=exc)) from exc
        except TimeoutError as exc:
            raise AlpacaPaperRequestError(map_alpaca_error(exception=exc)) from exc
        except OSError as exc:
            raise AlpacaPaperRequestError(map_alpaca_error(exception=exc)) from exc


class AlpacaPaperClient:
    def __init__(self, config: AlpacaPaperConfig, *, transport: Any | None = None) -> None:
        if not config.api_key_id or not config.api_secret_key:
            raise ValueError("Alpaca paper credentials are required.")
        self.config = config
        self.base_url = validate_paper_base_url(config.base_url)
        self.transport = transport or UrllibAlpacaTransport()

    def get_account(self) -> Mapping[str, Any]:
        payload = self._request_json("GET", "/v2/account")
        if not isinstance(payload, Mapping):
            raise ValueError("Alpaca account response must be a mapping.")
        return payload

    def get_positions(self) -> Sequence[Mapping[str, Any]]:
        payload = self._request_json("GET", "/v2/positions")
        _require_mapping_list(payload, field_name="positions")
        return payload

    def get_orders(self, *, status: str = "all", limit: int = 50) -> Sequence[Mapping[str, Any]]:
        payload = self._request_json(
            "GET",
            "/v2/orders",
            params={"status": status, "limit": limit, "direction": "desc"},
        )
        _require_mapping_list(payload, field_name="orders")
        return payload

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        response = self.transport.request(
            method,
            f"{self.base_url}{path}",
            headers={
                "Accept": "application/json",
                "APCA-API-KEY-ID": self.config.api_key_id or "",
                "APCA-API-SECRET-KEY": self.config.api_secret_key or "",
            },
            params=params,
            timeout_seconds=self.config.timeout_seconds,
        )
        if response.status_code >= 400:
            details = response.payload if response.payload is not None else {"raw_body": response.raw_body}
            raise AlpacaPaperRequestError(map_alpaca_error(status_code=response.status_code, payload=details))
        return response.payload


def fetch_read_only_snapshot(client: AlpacaPaperClient) -> AlpacaReadOnlySnapshot:
    account = map_alpaca_account(client.get_account())
    positions = tuple(map_alpaca_position(item) for item in client.get_positions())
    orders = tuple(map_alpaca_order(item) for item in client.get_orders())
    fixture = BrokerSimulatorFixture(
        account=account.fixture.account,
        cash_balances=account.fixture.cash_balances,
        position_contexts=positions,
    )
    return AlpacaReadOnlySnapshot(
        fixture=fixture,
        buying_power=account.buying_power,
        orders=orders,
    )


def map_alpaca_account(payload: Mapping[str, Any]) -> AlpacaMappedAccount:
    account_id = _require_text(payload, "id")
    currency = _normalize_currency(payload.get("currency", "USD"))
    cash_total = _require_decimal(payload, "cash")
    buying_power = _optional_decimal(payload.get("buying_power"))
    fixture = BrokerSimulatorFixture(
        account=BrokerSimulatorAccount(
            account_id=account_id,
            name=str(payload.get("account_number") or account_id),
            base_currency=currency,
        ),
        cash_balances=(BrokerSimulatorCashBalance(currency=currency, total=cash_total, source_key="alpaca:cash:seed"),),
    )
    return AlpacaMappedAccount(
        fixture=fixture,
        cash_currency=currency,
        cash_total=cash_total,
        buying_power=buying_power,
        broker_account_context=MappingProxyType(
            {
                "status": payload.get("status"),
                "buying_power": str(buying_power) if buying_power is not None else None,
            }
        ),
    )


def map_alpaca_order(payload: Mapping[str, Any]) -> BrokerSimulatorOrderInput:
    return BrokerSimulatorOrderInput(
        instrument=_require_text(payload, "symbol"),
        market=_normalize_market(payload),
        side=_map_side(_require_text(payload, "side")),
        order_type=_map_order_type(_require_text(payload, "type")),
        quantity=_require_decimal(payload, "qty"),
        currency=_normalize_currency(payload.get("currency", "USD")),
        broker_order_id=_clean_optional(payload.get("id")),
        client_order_id=_clean_optional(payload.get("client_order_id")),
        limit_price=_optional_decimal(payload.get("limit_price")),
        requested_at=_parse_timestamp(payload.get("submitted_at")),
    )


def map_alpaca_position(payload: Mapping[str, Any]) -> BrokerSimulatorPositionContext:
    return BrokerSimulatorPositionContext(
        instrument=_require_text(payload, "symbol"),
        market=_normalize_market(payload),
        currency=_normalize_currency(payload.get("currency", "USD")),
        quantity=_require_decimal(payload, "qty"),
        average_cost=_optional_decimal(payload.get("avg_entry_price")),
    )


def map_alpaca_fill_activity(payload: Mapping[str, Any], *, account_id: str) -> BrokerSimulatorExecutionInput:
    activity_id = _require_text(payload, "id")
    return BrokerSimulatorExecutionInput(
        source_key=f"{account_id}:alpaca:activity:{activity_id}",
        instrument=_require_text(payload, "symbol"),
        market=_normalize_market(payload),
        side=_map_side(_require_text(payload, "side")),
        quantity=_require_decimal(payload, "qty"),
        price=_require_decimal(payload, "price"),
        currency=_normalize_currency(payload.get("currency", "USD")),
        external_execution_id=activity_id,
        broker_order_id=_clean_optional(payload.get("order_id")),
        fee_amount=_optional_decimal(payload.get("fee")) or Decimal("0"),
        fee_currency=_normalize_currency(payload.get("currency", "USD")),
        executed_at=_parse_timestamp(payload.get("transaction_time")),
    )


def _decode_json_body(raw_body: str) -> Any:
    if not raw_body.strip():
        return None
    try:
        return json.loads(raw_body)
    except json.JSONDecodeError:
        return {"raw_body": raw_body}


def _extract_message(payload: Any) -> str:
    if isinstance(payload, Mapping):
        for key in ("message", "error", "code"):
            value = payload.get(key)
            if isinstance(value, str):
                return value
    if isinstance(payload, str):
        return payload
    return ""


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if value in (None, ""):
        raise ValueError("Alpaca timestamp is required.")
    text = str(value).strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _require_mapping_list(payload: Any, *, field_name: str) -> None:
    if not isinstance(payload, list) or any(not isinstance(item, Mapping) for item in payload):
        raise ValueError(f"Alpaca {field_name} response must be a list of mappings.")


def _normalize_currency(value: Any) -> str:
    currency = str(value or "USD").strip().upper()
    if not currency:
        raise ValueError("Currency is required.")
    return currency


def _normalize_market(payload: Mapping[str, Any]) -> str:
    for key in ("exchange", "asset_exchange", "market"):
        value = _clean_optional(payload.get(key))
        if value:
            return value.upper()
    return DEFAULT_MARKET


def _map_side(value: str) -> OrderSide:
    normalized = value.strip().lower()
    if normalized == "buy":
        return OrderSide.BUY
    if normalized == "sell":
        return OrderSide.SELL
    raise ValueError(f"Unsupported Alpaca side: {value}")


def _map_order_type(value: str) -> OrderType:
    normalized = value.strip().lower()
    if normalized == "market":
        return OrderType.MARKET
    if normalized == "limit":
        return OrderType.LIMIT
    raise ValueError(f"Unsupported Alpaca order type: {value}")


def _require_text(payload: Mapping[str, Any], key: str) -> str:
    value = _clean_optional(payload.get(key))
    if value is None:
        raise ValueError(f"Alpaca payload is missing {key}.")
    return value


def _require_decimal(payload: Mapping[str, Any], key: str) -> Decimal:
    return _to_decimal(payload.get(key), field_name=key)


def _optional_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    return _to_decimal(value, field_name="optional_decimal")


def _to_decimal(value: Any, *, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"Invalid decimal for {field_name}: {value!r}") from exc


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _env_flag_enabled(value: Any) -> bool:
    return str(value or "").strip() == "1"
