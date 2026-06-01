from __future__ import annotations

import gzip
import json
import time
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from quantagent.core.events.dto import RawEventDraft
from quantagent.core.sources.protocols import RuntimeContext

TWELVE_DATA_QUOTE_URL = "https://api.twelvedata.com/quote"
_DEFAULT_UA = "QuantAgent Twelve Data Source/0.2"
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


def _retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> Callable:
    """Exponential backoff retry for HTTP 429 / 5xx / URLError."""

    def decorator(func: Callable) -> Callable:
        def wrapper(self, *args, **kwargs) -> Any:  # noqa: ANN401
            last_error: Exception | None = None
            delay = base_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(self, *args, **kwargs)
                except RuntimeError as exc:
                    cause = exc.__cause__
                    if not isinstance(cause, (HTTPError, URLError)):
                        raise
                    # 429 with Retry-After
                    if isinstance(cause, HTTPError) and cause.code == 429:
                        retry_after = cause.headers.get("Retry-After") if hasattr(cause, "headers") else None  # type: ignore[union-attr]
                        if retry_after is not None:
                            try:
                                delay = float(retry_after)
                            except (TypeError, ValueError):
                                pass
                    if (
                        isinstance(cause, HTTPError)
                        and cause.code not in _RETRYABLE_STATUSES
                    ):
                        raise  # 4xx (non-429) not retryable
                    last_error = exc
                except URLError as exc:
                    last_error = exc  # type: ignore[assignment]
                if attempt < max_attempts:
                    time.sleep(delay)
                    delay = min(delay * backoff_factor, 30.0)
            raise RuntimeError(
                f"Twelve Data API request failed after {max_attempts} attempts"
            ) from last_error

        return wrapper

    return decorator


class TwelveDataSourcePlugin:
    id = "quantagent.official.source.twelve_data"

    def __init__(self) -> None:
        self._loaded = False
        self._started = False

    # ---- lifecycle ----------------------------------------------------------

    def load(self, context: RuntimeContext) -> None:
        if context.plugin_id != self.id:
            raise ValueError(
                f"runtime context plugin_id mismatch: {context.plugin_id}"
            )
        self._loaded = True

    def start(self) -> None:
        if not self._loaded:
            raise RuntimeError("Twelve Data source must be loaded before start.")
        self._started = True

    def stop(self) -> None:
        self._started = False

    def reload(self, config: dict[str, Any]) -> None:
        self._validate_config(config)

    def health_check(self) -> dict[str, Any]:
        return {"status": "ok", "plugin_id": self.id, "started": self._started}

    # ---- fetch --------------------------------------------------------------

    def fetch(
        self, cursor: str | None, config: dict[str, Any]
    ) -> list[RawEventDraft]:
        del cursor
        if not self._started:
            raise RuntimeError("Twelve Data source must be started before fetch.")
        self._validate_config(config)

        api_key = config.get("twelve_data_api_key")
        if not api_key:
            raise ValueError(
                "twelve_data_api_key must be provided in effective_config "
                "by the platform. Do not put the real API key in the plugin's "
                "config.schema.json or README."
            )

        symbols: list[str] = config["symbols"]
        timeout = int(config.get("timeout_seconds", 10))
        market: str | None = config.get("market")

        encoded = ",".join(quote(s, safe="") for s in symbols)
        url = f"{TWELVE_DATA_QUOTE_URL}?symbol={encoded}&apikey={api_key}"

        response_body = self._call_api(url, timeout)
        raw_data = self._parse_json(response_body)
        return self._parse_quotes(raw_data, symbols, market)

    # ---- internal -----------------------------------------------------------

    @_retry(max_attempts=3, base_delay=1.0, backoff_factor=2.0)
    def _call_api(self, url: str, timeout: int) -> bytes:
        headers = {
            "User-Agent": _DEFAULT_UA,
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        }
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
        except HTTPError as exc:
            msg = f"Twelve Data API returned HTTP {exc.code}: {exc.reason}"
            raise RuntimeError(msg) from exc
        except URLError as exc:
            raise RuntimeError(
                f"Twelve Data API request failed: {exc.reason}"
            ) from exc
        return body

    @staticmethod
    def _parse_json(raw: bytes) -> dict[str, Any]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            preview = raw[:200].decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Twelve Data returned non-JSON response (first 200 chars): {preview}"
            ) from exc

    def _parse_quotes(
        self,
        raw_data: dict[str, Any],
        symbols: list[str],
        market: str | None,
    ) -> list[RawEventDraft]:
        # API-level error: {"status":"error","code":400,...}
        if raw_data.get("status") == "error":
            self._handle_api_error(raw_data)
            return []  # unreachable; keeps type checker happy

        # Single symbol → API returns flat dict; batch → per-symbol dict.
        if len(symbols) == 1:
            by_symbol = {symbols[0]: raw_data}
        else:
            by_symbol = raw_data

        events: list[RawEventDraft] = []
        for symbol in symbols:
            symbol_data = by_symbol.get(symbol)
            if symbol_data is None:
                continue
            if isinstance(symbol_data, dict) and symbol_data.get("status") == "error":
                continue
            events.append(self._symbol_to_event(symbol, symbol_data, market))

        if not events:
            raise RuntimeError(
                "Twelve Data returned no usable quote data for the requested symbols."
            )
        return events

    def _symbol_to_event(
        self,
        symbol: str,
        data: dict[str, Any],
        market: str | None,
    ) -> RawEventDraft:
        price = self._extract_price(data, symbol)
        quote_timestamp = self._extract_timestamp(data)
        currency = data.get("currency")
        resolved_market = market or data.get("exchange") or data.get("market")

        external_id = f"twelve_data:{symbol}:{quote_timestamp}"
        title = f"{symbol} @ {price}"

        return RawEventDraft(
            source_plugin_id=self.id,
            source_type="market_quote",
            external_id=external_id,
            title=title,
            content=json.dumps(data, ensure_ascii=False),
            captured_at=datetime.now(timezone.utc),
            raw_payload={
                "symbol": symbol,
                "response": data,
            },
            metadata={
                "provider": "twelve_data",
                "symbol": symbol,
                "price": price,
                "currency": currency,
                "market": resolved_market,
                "quote_timestamp": quote_timestamp,
            },
        )

    # ---- helpers ------------------------------------------------------------

    @staticmethod
    def _extract_price(data: dict[str, Any], symbol: str) -> float:
        for key in ("close", "price", "last"):
            val = data.get(key)
            if val is not None:
                try:
                    return float(val)
                except (TypeError, ValueError):
                    pass
        available = [k for k in ("close", "price", "last") if k in data]
        hint = f"available fields: {sorted(data.keys())}" if data else "response is empty"
        raise ValueError(
            f"Twelve Data response for {symbol} missing required price field "
            f"(tried: close, price, last; {hint})."
        )

    @staticmethod
    def _extract_timestamp(data: dict[str, Any]) -> str:
        for key in ("timestamp", "datetime"):
            val = data.get(key)
            if val:
                return str(val)
        server_time = data.get("server_time")
        if server_time:
            return str(server_time)
        raise ValueError(
            "Twelve Data response missing timestamp field (tried: timestamp, datetime)"
            "; cannot construct external_id."
        )

    @staticmethod
    def _handle_api_error(raw_data: dict[str, Any]) -> None:
        status = raw_data.get("status")
        code = raw_data.get("code")
        message = raw_data.get("message", "unknown error")
        raise RuntimeError(
            f"Twelve Data API error (status={status}, code={code}): {message}"
        )

    @staticmethod
    def _validate_config(config: dict[str, Any]) -> None:
        symbols = config.get("symbols")
        if not isinstance(symbols, list) or not symbols:
            raise ValueError(
                "Twelve Data source config requires a non-empty symbols list."
            )
        if any(not isinstance(s, str) or not s.strip() for s in symbols):
            raise ValueError("Twelve Data source symbols must be non-empty strings.")


plugin = TwelveDataSourcePlugin()