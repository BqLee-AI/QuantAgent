from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any, Mapping, Sequence
from urllib import error as urllib_error
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from quantagent.core.wallet import OrderSide, OrderType

from wallet_broker_simulator_harness import (
    BrokerSimulatorAccount,
    BrokerSimulatorCashBalance,
    BrokerSimulatorExecutionInput,
    BrokerSimulatorFixture,
    BrokerSimulatorOrderInput,
    BrokerSimulatorPositionContext,
)


ALPACA_PAPER_BASE_URL = "https://paper-api.alpaca.markets"
ALPACA_PAPER_BASE_URL_ENV = "ALPACA_PAPER_BASE_URL"
APCA_API_KEY_ID_ENV = "APCA_API_KEY_ID"
APCA_API_SECRET_KEY_ENV = "APCA_API_SECRET_KEY"
QUANTAGENT_ALPACA_PAPER_SMOKE_ENV = "QUANTAGENT_ALPACA_PAPER_SMOKE"
QUANTAGENT_ALPACA_PAPER_ORDER_SMOKE_ENV = "QUANTAGENT_ALPACA_PAPER_ORDER_SMOKE"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_ORDER_SYMBOL_WHITELIST = frozenset({"AAPL", "MSFT", "SPY"})
DEFAULT_ORDER_NOTIONAL_LIMIT_USD = Decimal("5")
DEFAULT_ORDER_QUANTITY_LIMIT = Decimal("1")
DEFAULT_ORDER_SMOKE_SYMBOL = "SPY"
DEFAULT_ORDER_SMOKE_NOTIONAL_USD = Decimal("1")
REDACTED = "<redacted>"
REDACTED_RESPONSE_BODY = "<redacted-response-body>"
REDACTED_MESSAGE = "<redacted-message>"
DEFAULT_MARKET = "ALPACA"

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


class AlpacaPaperRequestError(RuntimeError):
    def __init__(self, broker_error: "AlpacaBrokerError") -> None:
        super().__init__(broker_error.message)
        self.broker_error = broker_error


@dataclass(frozen=True)
class AlpacaPaperConfig:
    base_url: str
    api_key_id: str | None
    api_secret_key: str | None
    smoke_enabled: bool
    order_smoke_enabled: bool
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    symbol_whitelist: frozenset[str] = DEFAULT_ORDER_SYMBOL_WHITELIST
    max_notional_usd: Decimal = DEFAULT_ORDER_NOTIONAL_LIMIT_USD
    max_quantity: Decimal = DEFAULT_ORDER_QUANTITY_LIMIT

    def redacted(self) -> Mapping[str, Any]:
        return MappingProxyType(
            {
                "base_url": self.base_url,
                "api_key_id": REDACTED if self.api_key_id else "<missing>",
                "api_secret_key": REDACTED if self.api_secret_key else "<missing>",
                "smoke_enabled": self.smoke_enabled,
                "order_smoke_enabled": self.order_smoke_enabled,
                "timeout_seconds": self.timeout_seconds,
                "symbol_whitelist": tuple(sorted(self.symbol_whitelist)),
                "max_notional_usd": str(self.max_notional_usd),
                "max_quantity": str(self.max_quantity),
            }
        )


@dataclass(frozen=True)
class AlpacaHttpResponse:
    status_code: int
    payload: Any
    raw_body: str | None = None


@dataclass(frozen=True)
class AlpacaBrokerError:
    category: str
    message: str
    status_code: int | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


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


@dataclass(frozen=True)
class AlpacaOrderSmokeRequest:
    symbol: str
    notional_usd: Decimal | None = None
    quantity: Decimal | None = None
    side: str = "buy"
    order_type: str = "market"
    time_in_force: str = "day"


def load_alpaca_paper_config(env: Mapping[str, str] | None = None) -> AlpacaPaperConfig:
    source = env if env is not None else os.environ
    return AlpacaPaperConfig(
        base_url=(source.get(ALPACA_PAPER_BASE_URL_ENV) or ALPACA_PAPER_BASE_URL).strip(),
        api_key_id=_clean_optional(source.get(APCA_API_KEY_ID_ENV)),
        api_secret_key=_clean_optional(source.get(APCA_API_SECRET_KEY_ENV)),
        smoke_enabled=_env_flag_enabled(source.get(QUANTAGENT_ALPACA_PAPER_SMOKE_ENV)),
        order_smoke_enabled=_env_flag_enabled(source.get(QUANTAGENT_ALPACA_PAPER_ORDER_SMOKE_ENV)),
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


def get_order_smoke_skip_reason(config: AlpacaPaperConfig, request: AlpacaOrderSmokeRequest) -> str | None:
    read_only_reason = get_read_only_smoke_skip_reason(config)
    if read_only_reason is not None:
        return read_only_reason
    if not config.order_smoke_enabled:
        return f"{QUANTAGENT_ALPACA_PAPER_ORDER_SMOKE_ENV} is not enabled."
    symbol = _normalize_symbol(request.symbol)
    if symbol not in config.symbol_whitelist:
        return f"Order smoke symbol is not allowlisted: {symbol}"
    try:
        _build_order_request_payload(request, config=config)
    except ValueError as exc:
        return str(exc)
    return None


def redact_sensitive_value(value: Any) -> Any:
    if value in (None, ""):
        return value
    return REDACTED


def sanitize_for_logs(payload: Any, *, key: str | None = None) -> Any:
    if isinstance(payload, Mapping):
        return {
            name: sanitize_for_logs(value, key=name)
            for name, value in payload.items()
        }
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

    if isinstance(exception, TimeoutError):
        return AlpacaBrokerError(
            category="timeout",
            message="alpaca paper request timed out",
            details=MappingProxyType(details),
        )
    if exception is not None:
        return AlpacaBrokerError(
            category="external_unavailable",
            message="alpaca paper endpoint is unavailable",
            details=MappingProxyType(details),
        )

    message_source = _extract_message(payload)
    message_lower = message_source.lower()
    if status_code in (401, 403) and "buying power" not in message_lower:
        category = "authentication_failed"
        message = "alpaca paper authentication failed"
    elif "symbol" in message_lower:
        category = "invalid_symbol"
        message = "alpaca paper rejected the symbol"
    elif "buying power" in message_lower:
        category = "insufficient_buying_power"
        message = "alpaca paper reported insufficient buying power"
    else:
        category = "external_unavailable"
        message = "alpaca paper endpoint returned an unavailable response"

    return AlpacaBrokerError(
        category=category,
        message=message,
        status_code=status_code,
        details=MappingProxyType(details),
    )


class UrllibAlpacaTransport:
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
        timeout_seconds: float,
    ) -> AlpacaHttpResponse:
        query = urlencode({name: value for name, value in (params or {}).items() if value is not None}, doseq=True)
        request_url = f"{url}?{query}" if query else url
        body = json.dumps(json_body).encode("utf-8") if json_body is not None else None
        request = Request(request_url, data=body, headers=dict(headers), method=method)
        if body is not None:
            request.add_header("Content-Type", "application/json")

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
        return self._request_json("GET", "/v2/account")

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

    def get_fill_activities(self, *, page_size: int = 100) -> Sequence[Mapping[str, Any]]:
        payload = self._request_json(
            "GET",
            "/v2/account/activities/FILL",
            params={"direction": "desc", "page_size": page_size},
        )
        _require_mapping_list(payload, field_name="activities")
        return payload

    def submit_order(self, request: AlpacaOrderSmokeRequest) -> Mapping[str, Any]:
        payload = self._request_json(
            "POST",
            "/v2/orders",
            json_body=_build_order_request_payload(request, config=self.config),
        )
        if not isinstance(payload, Mapping):
            raise ValueError("Alpaca submit order response must be a mapping.")
        return payload

    def get_order_by_client_order_id(self, client_order_id: str) -> Mapping[str, Any]:
        payload = self._request_json(
            "GET",
            "/v2/orders:by_client_order_id",
            params={"client_order_id": client_order_id},
        )
        if not isinstance(payload, Mapping):
            raise ValueError("Alpaca order by client_order_id response must be a mapping.")
        return payload

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
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
            json_body=json_body,
            timeout_seconds=self.config.timeout_seconds,
        )
        if response.status_code >= 400:
            details = response.payload if response.payload is not None else {"raw_body": response.raw_body}
            raise AlpacaPaperRequestError(
                map_alpaca_error(
                    status_code=response.status_code,
                    payload=details,
                )
            )
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


def map_alpaca_position(payload: Mapping[str, Any]) -> BrokerSimulatorPositionContext:
    return BrokerSimulatorPositionContext(
        instrument=_require_text(payload, "symbol"),
        market=_normalize_market(payload),
        currency=_normalize_currency(payload.get("currency", "USD")),
        quantity=_require_decimal(payload, "qty"),
        average_cost=_require_decimal(payload, "avg_entry_price"),
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


def map_alpaca_fill_activity(
    payload: Mapping[str, Any],
    *,
    account_id: str,
) -> BrokerSimulatorExecutionInput:
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
        executed_at=_parse_timestamp(payload.get("transaction_time")),
    )


def build_order_smoke_request(
    *,
    symbol: str = DEFAULT_ORDER_SMOKE_SYMBOL,
    notional_usd: Decimal | str | int | None = DEFAULT_ORDER_SMOKE_NOTIONAL_USD,
    quantity: Decimal | str | int | None = None,
) -> AlpacaOrderSmokeRequest:
    return AlpacaOrderSmokeRequest(
        symbol=_normalize_symbol(symbol),
        notional_usd=_optional_decimal(notional_usd),
        quantity=_optional_decimal(quantity),
    )


def generate_client_order_id() -> str:
    return f"quantagent-alpaca-smoke-{uuid.uuid4().hex[:20]}"


def _build_order_request_payload(
    request: AlpacaOrderSmokeRequest,
    *,
    config: AlpacaPaperConfig,
) -> Mapping[str, Any]:
    symbol = _normalize_symbol(request.symbol)
    if request.notional_usd is not None and request.quantity is not None:
        raise ValueError("Order smoke request must choose notional or quantity, not both.")
    if request.notional_usd is None and request.quantity is None:
        raise ValueError("Order smoke request requires notional or quantity.")
    payload: dict[str, Any] = {
        "symbol": symbol,
        "side": request.side,
        "type": request.order_type,
        "time_in_force": request.time_in_force,
        "client_order_id": generate_client_order_id(),
    }
    if request.notional_usd is not None:
        if request.notional_usd <= 0:
            raise ValueError("Order smoke notional must be greater than 0.")
        if request.notional_usd > config.max_notional_usd:
            raise ValueError(f"Order smoke notional exceeds {config.max_notional_usd} USD.")
        payload["notional"] = _format_decimal(request.notional_usd)
    if request.quantity is not None:
        if request.quantity <= 0:
            raise ValueError("Order smoke quantity must be greater than 0.")
        if request.quantity > config.max_quantity:
            raise ValueError(f"Order smoke quantity exceeds {config.max_quantity}.")
        payload["qty"] = _format_decimal(request.quantity)
    return payload


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


def _require_mapping_list(payload: Any, *, field_name: str) -> None:
    if not isinstance(payload, list) or any(not isinstance(item, Mapping) for item in payload):
        raise ValueError(f"Alpaca {field_name} response must be a list of mappings.")


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if value in (None, ""):
        return datetime.now(timezone.utc)
    text = str(value).strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


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


def _normalize_symbol(value: Any) -> str:
    symbol = str(value or "").strip().upper()
    if not symbol:
        raise ValueError("Order smoke symbol is required.")
    return symbol


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


def _format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    formatted = format(normalized, "f")
    return formatted.rstrip("0").rstrip(".") or "0"


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _env_flag_enabled(value: Any) -> bool:
    return str(value or "").strip() == "1"
