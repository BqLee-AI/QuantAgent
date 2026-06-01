from __future__ import annotations

import gzip
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Minimal self-contained DTOs for unit-testing the plugin without full platform.
# ---------------------------------------------------------------------------

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class RuntimeContext:
    plugin_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RawEventDraft:
    source_plugin_id: str
    source_type: str
    title: str
    external_id: str | None = None
    url: str | None = None
    canonical_url: str | None = None
    content: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    captured_at: datetime = field(default_factory=utc_now)
    raw_payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    dedupe_hint: str | None = None


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def make_plugin():
    from twelve_data_source import TwelveDataSourcePlugin

    return TwelveDataSourcePlugin()


def valid_config(api_key="test-api-key", symbols=None, market=None):
    if symbols is None:
        symbols = ["AAPL"]
    cfg: dict = {"symbols": symbols, "twelve_data_api_key": api_key}
    if market:
        cfg["market"] = market
    return cfg


def started_plugin(plugin=None, config=None):
    if plugin is None:
        plugin = make_plugin()
    if config is None:
        config = valid_config()
    plugin.load(RuntimeContext(plugin_id=plugin.id))
    plugin.start()
    return plugin, config


# ---------------------------------------------------------------------------
# lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_load_with_matching_context(self):
        plugin = make_plugin()
        plugin.load(RuntimeContext(plugin_id=plugin.id))
        assert plugin._loaded is True  # noqa: SLF001

    def test_load_rejects_mismatched_plugin_id(self):
        plugin = make_plugin()
        with pytest.raises(ValueError, match="plugin_id mismatch"):
            plugin.load(RuntimeContext(plugin_id="wrong.id"))

    def test_start_requires_load(self):
        plugin = make_plugin()
        with pytest.raises(RuntimeError, match="loaded before start"):
            plugin.start()

    def test_start_and_stop(self):
        plugin, _ = started_plugin()
        assert plugin._started is True  # noqa: SLF001
        plugin.stop()
        assert plugin._started is False  # noqa: SLF001

    def test_fetch_requires_start(self):
        plugin = make_plugin()
        plugin.load(RuntimeContext(plugin_id=plugin.id))
        with pytest.raises(RuntimeError, match="started before fetch"):
            plugin.fetch(None, valid_config())

    def test_health_check(self):
        plugin, _ = started_plugin()
        result = plugin.health_check()
        assert result["status"] == "ok"
        assert result["plugin_id"] == plugin.id
        assert result["started"] is True


# ---------------------------------------------------------------------------
# config validation
# ---------------------------------------------------------------------------


class TestConfigValidation:
    def test_missing_symbols_raises(self):
        plugin, _ = started_plugin()
        with pytest.raises(ValueError, match="non-empty symbols"):
            plugin.fetch(None, {"twelve_data_api_key": "k"})

    def test_empty_symbols_raises(self):
        plugin, _ = started_plugin()
        with pytest.raises(ValueError, match="non-empty symbols"):
            plugin.fetch(None, valid_config(symbols=[]))

    def test_symbol_must_be_non_empty_string(self):
        plugin, _ = started_plugin()
        with pytest.raises(ValueError, match="non-empty strings"):
            plugin.fetch(None, valid_config(symbols=["AAPL", "  "]))

    def test_missing_api_key_raises(self):
        plugin, _ = started_plugin()
        cfg = valid_config()
        del cfg["twelve_data_api_key"]
        with pytest.raises(ValueError, match="twelve_data_api_key"):
            plugin.fetch(None, cfg)


# ---------------------------------------------------------------------------
# fetch – happy path (mocked HTTP)
# ---------------------------------------------------------------------------

SINGLE_QUOTE_FIXTURE = {
    "symbol": "AAPL",
    "close": "185.64",
    "high": "186.10",
    "low": "184.20",
    "volume": "23456789",
    "currency": "USD",
    "exchange": "NASDAQ",
    "datetime": "2026-05-31 16:00:00",
}


BATCH_QUOTE_FIXTURE = {
    "AAPL": {
        "symbol": "AAPL",
        "close": "185.64",
        "currency": "USD",
        "exchange": "NASDAQ",
        "datetime": "2026-05-31 16:00:00",
    },
    "MSFT": {
        "symbol": "MSFT",
        "close": "420.30",
        "price": "420.30",
        "currency": "USD",
        "exchange": "NASDAQ",
        "timestamp": "1748736000",
    },
}


def _mock_response(body: bytes, headers: dict | None = None):
    if headers is None:
        headers = {}

    class _FakeResponse:
        def __init__(self):
            self.headers = headers

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return body

    return _FakeResponse()


class TestFetchSuccess:
    def test_single_symbol_returns_one_event(self):
        plugin, config = started_plugin()
        config["symbols"] = ["AAPL"]

        with patch(
            "twelve_data_source.urlopen",
            return_value=_mock_response(
                json.dumps(SINGLE_QUOTE_FIXTURE).encode("utf-8")
            ),
        ):
            events = plugin.fetch(None, config)

        assert len(events) == 1
        e = events[0]
        assert e.source_plugin_id == plugin.id
        assert e.source_type == "market_quote"
        assert e.external_id == "twelve_data:AAPL:2026-05-31 16:00:00"
        assert e.title == "AAPL @ 185.64"
        assert e.metadata["provider"] == "twelve_data"
        assert e.metadata["symbol"] == "AAPL"
        assert e.metadata["price"] == 185.64
        assert e.metadata["currency"] == "USD"
        assert e.metadata["market"] == "NASDAQ"

    def test_batch_symbols_returns_multiple_events(self):
        plugin, config = started_plugin()
        config["symbols"] = ["AAPL", "MSFT"]

        with patch(
            "twelve_data_source.urlopen",
            return_value=_mock_response(
                json.dumps(BATCH_QUOTE_FIXTURE).encode("utf-8")
            ),
        ):
            events = plugin.fetch(None, config)

        assert len(events) == 2
        symbols = {e.metadata["symbol"] for e in events}
        assert symbols == {"AAPL", "MSFT"}

    def test_market_from_config_overrides_response(self):
        plugin, config = started_plugin()
        config["market"] = "HKEX"
        config["symbols"] = ["AAPL"]

        with patch(
            "twelve_data_source.urlopen",
            return_value=_mock_response(
                json.dumps(SINGLE_QUOTE_FIXTURE).encode("utf-8")
            ),
        ):
            events = plugin.fetch(None, config)

        assert events[0].metadata["market"] == "HKEX"

    def test_url_encode_symbols(self):
        """Symbols are URL-encoded via urllib.parse.quote (space→%20 etc)."""
        plugin, config = started_plugin()
        config["symbols"] = ["BRK B", "AAPL"]  # space that *must* encode

        with patch(
            "twelve_data_source.urlopen",
            return_value=_mock_response(
                json.dumps(BATCH_QUOTE_FIXTURE).encode("utf-8")
            ),
        ) as mock_urlopen:
            events = plugin.fetch(None, config)

        call_args = mock_urlopen.call_args[0][0]
        url_str = (
            call_args.get_full_url()
            if hasattr(call_args, "get_full_url")
            else str(call_args)
        )
        query = url_str.split("?")[1] if "?" in url_str else ""
        # Space must be encoded as %20
        assert "BRK B" not in query
        assert "BRK%20B" in query
        assert len(events) >= 1

    def test_gzip_response_decompressed(self):
        """When Content-Encoding is gzip, the body must be decompressed."""
        plugin, config = started_plugin()
        raw_json = json.dumps(SINGLE_QUOTE_FIXTURE).encode("utf-8")
        compressed = gzip.compress(raw_json)

        with patch(
            "twelve_data_source.urlopen",
            return_value=_mock_response(compressed, {"Content-Encoding": "gzip"}),
        ):
            events = plugin.fetch(None, config)

        assert len(events) == 1
        assert events[0].metadata["price"] == 185.64

    def test_single_symbol_with_status_ok_not_misidentified_as_error(self):
        """Single-symbol response with status:"ok" should not be treated as error."""
        plugin, config = started_plugin()
        config["symbols"] = ["AAPL"]
        payload = {
            "symbol": "AAPL",
            "status": "ok",
            "close": "185.64",
            "datetime": "2026-05-31",
        }

        with patch(
            "twelve_data_source.urlopen",
            return_value=_mock_response(json.dumps(payload).encode("utf-8")),
        ):
            events = plugin.fetch(None, config)

        assert len(events) == 1
        assert events[0].metadata["symbol"] == "AAPL"

    def test_accept_json_header_sent(self):
        """Verify Accept: application/json header is sent."""
        plugin, config = started_plugin()

        with patch(
            "twelve_data_source.urlopen",
            return_value=_mock_response(
                json.dumps(SINGLE_QUOTE_FIXTURE).encode("utf-8")
            ),
        ) as mock_urlopen:
            plugin.fetch(None, config)

        call_args = mock_urlopen.call_args[0][0]
        if hasattr(call_args, "headers"):
            headers = dict(call_args.headers)
            assert headers.get("Accept") == "application/json"


# ---------------------------------------------------------------------------
# fetch – API error paths
# ---------------------------------------------------------------------------


class TestFetchApiErrors:
    def test_http_error(self):
        from urllib.error import HTTPError

        plugin, config = started_plugin()
        with patch(
            "twelve_data_source.urlopen",
            side_effect=HTTPError(
                "https://api.twelvedata.com/quote", 429, "Too Many Requests", {}, None
            ),
        ):
            with pytest.raises(RuntimeError, match="failed after 3 attempts"):
                plugin.fetch(None, config)

    def test_urllib_error_retries_then_fails(self):
        from urllib.error import URLError

        plugin, config = started_plugin()
        with patch(
            "twelve_data_source.urlopen",
            side_effect=URLError("connection refused"),
        ):
            with pytest.raises(RuntimeError, match="failed after 3 attempts"):
                plugin.fetch(None, config)

    def test_retry_succeeds_on_second_attempt(self):
        from urllib.error import URLError

        plugin, config = started_plugin()
        with patch(
            "twelve_data_source.urlopen",
            side_effect=[
                URLError("connection refused"),
                _mock_response(json.dumps(SINGLE_QUOTE_FIXTURE).encode("utf-8")),
            ],
        ):
            events = plugin.fetch(None, config)
        assert len(events) == 1

    def test_retry_respects_retry_after_429(self):
        from urllib.error import HTTPError

        plugin, config = started_plugin()
        # Simulate a fake HTTPError with headers
        with patch(
            "twelve_data_source.urlopen",
            side_effect=HTTPError(
                "https://api.twelvedata.com/quote", 429, "Too Many Requests",
                {}, None  # no headers → default delay
            ),
        ), patch("twelve_data_source.time.sleep") as mock_sleep:
            try:
                plugin.fetch(None, config)
            except RuntimeError:
                pass
            # First retry sleep should use default base_delay (1s)
            assert mock_sleep.call_count >= 2  # at least 2 retries

    def test_api_status_error_response(self):
        plugin, config = started_plugin()
        payload = {"status": "error", "code": 400, "message": "Invalid API key"}
        with patch(
            "twelve_data_source.urlopen",
            return_value=_mock_response(json.dumps(payload).encode("utf-8")),
        ):
            with pytest.raises(RuntimeError, match="Invalid API key"):
                plugin.fetch(None, config)

    def test_partial_symbol_error_still_returns_valid_events(self):
        plugin, config = started_plugin()
        config["symbols"] = ["AAPL", "MSFT"]
        payload = {
            "AAPL": {"symbol": "AAPL", "close": "185.64", "datetime": "2026-05-31"},
            "MSFT": {"status": "error", "message": "symbol not found"},
        }
        with patch(
            "twelve_data_source.urlopen",
            return_value=_mock_response(json.dumps(payload).encode("utf-8")),
        ):
            events = plugin.fetch(None, config)
        assert len(events) == 1
        assert events[0].metadata["symbol"] == "AAPL"

    def test_non_json_response_raises_with_preview(self):
        plugin, config = started_plugin()
        html_body = b"<html><body>502 Bad Gateway</body></html>"
        with patch(
            "twelve_data_source.urlopen",
            return_value=_mock_response(html_body),
        ):
            with pytest.raises(RuntimeError, match="non-JSON response"):
                plugin.fetch(None, config)

    def test_http_4xx_non_retryable_fails_immediately(self):
        from urllib.error import HTTPError

        plugin, config = started_plugin()
        with patch(
            "twelve_data_source.urlopen",
            side_effect=HTTPError(
                "https://api.twelvedata.com/quote", 403, "Forbidden", {}, None
            ),
        ):
            with pytest.raises(RuntimeError, match="HTTP 403"):
                plugin.fetch(None, config)