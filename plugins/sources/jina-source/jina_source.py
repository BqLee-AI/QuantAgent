from __future__ import annotations

from collections.abc import Mapping
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from quantagent.plugin_sdk import (
    BasePlugin,
    PluginInvokeResult,
    SourceFetchInput,
    SourceFetchResult,
    SourceItemDraft,
)


DEFAULT_ENDPOINT = "https://r.jina.ai/http://{url_without_scheme}"


class JinaSourcePlugin(BasePlugin):
    async def invoke(self, request) -> PluginInvokeResult:
        fetch_input = SourceFetchInput.from_mapping(request.input)
        normalized = self._validate_config(self.context.config, fetch_input=fetch_input)
        reader_url = _build_reader_url(normalized["endpoint"], normalized["url"])
        http_request = Request(
            reader_url,
            headers={
                "User-Agent": "QuantAgent Jina Source/0.1",
                **normalized["headers"],
            },
        )
        with urlopen(http_request, timeout=normalized["timeout_seconds"]) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type")

        text = _decode_body(body, content_type).strip()
        if not text:
            raise ValueError("jina source returned empty content")

        title, content = _extract_title_and_content(text)
        result = SourceFetchResult(
            items=(
                SourceItemDraft(
                    external_id=normalized["url"],
                    url=normalized["url"],
                    title=title,
                    content=content,
                    raw_payload={
                        "requested_url": normalized["url"],
                        "reader_url": reader_url,
                        "content_length": len(content),
                    },
                    metadata={
                        "reader": "jina",
                        "requested_url": normalized["url"],
                        "reader_url": reader_url,
                    },
                ),
            ),
            metadata={"source": "jina"},
        )
        return PluginInvokeResult(output=result.to_mapping())

    def _validate_config(self, config: Mapping[str, Any], *, fetch_input: SourceFetchInput) -> dict[str, Any]:
        if not isinstance(config, Mapping):
            raise ValueError("Jina source config must be an object.")

        url = fetch_input.query or config.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("url must be a non-empty string")
        normalized_url = url.strip()
        parsed = urlparse(normalized_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("url scheme must be http or https")
        _reject_private_target(parsed)

        headers = config.get("headers", {})
        if not isinstance(headers, dict):
            raise ValueError("headers must be an object")
        normalized_headers: dict[str, str] = {}
        for key, value in headers.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("header names must be non-empty strings")
            if not isinstance(value, str):
                raise ValueError("header values must be strings")
            normalized_headers[key] = value

        timeout_seconds = int(config.get("timeout_seconds", 10))
        if timeout_seconds < 1:
            raise ValueError("timeout_seconds must be >= 1")
        if timeout_seconds > 60:
            raise ValueError("timeout_seconds must be <= 60")

        endpoint = config.get("endpoint", DEFAULT_ENDPOINT)
        if not isinstance(endpoint, str) or not endpoint.strip():
            raise ValueError("endpoint must be a non-empty string")

        return {
            "url": normalized_url,
            "headers": normalized_headers,
            "timeout_seconds": timeout_seconds,
            "endpoint": endpoint.strip(),
        }


def _reject_private_target(parsed) -> None:
    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise ValueError("url host must be present")
    if hostname == "localhost" or hostname.endswith(".local"):
        raise ValueError("private or local urls must not be sent to external reader")
    try:
        candidate = ip_address(hostname)
    except ValueError:
        return
    if candidate.is_private or candidate.is_loopback or candidate.is_link_local or candidate.is_reserved:
        raise ValueError("private or local urls must not be sent to external reader")


def _build_reader_url(endpoint: str, url: str) -> str:
    parsed = urlparse(url)
    url_without_scheme = f"{parsed.netloc}{parsed.path or ''}"
    if parsed.query:
        url_without_scheme = f"{url_without_scheme}?{parsed.query}"
    if parsed.fragment:
        url_without_scheme = f"{url_without_scheme}#{parsed.fragment}"
    return endpoint.format(
        url=url,
        url_without_scheme=url_without_scheme,
    )


def _decode_body(body: bytes, content_type: str | None) -> str:
    charset = "utf-8"
    if content_type:
        for piece in content_type.split(";"):
            key, _, value = piece.partition("=")
            if key.strip().lower() == "charset" and value.strip():
                charset = value.strip().strip("\"'")
                break
    for candidate in (charset, "utf-8"):
        try:
            return body.decode(candidate, errors="replace")
        except LookupError:
            continue
    return body.decode("utf-8", errors="replace")


def _extract_title_and_content(text: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("jina source returned empty content")

    first_line = lines[0]
    title = first_line.lstrip("#").strip() if first_line.startswith("#") else first_line
    content = "\n".join(lines)
    return title or "(untitled)", content


plugin = JinaSourcePlugin
