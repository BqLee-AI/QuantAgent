from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib import request as urllib_request
import json
import urllib.error

from sqlalchemy import select
from sqlalchemy.orm import Session

from quantagent.core.model_config.crypto import ModelConfigCrypto, ModelConfigCryptoError
from quantagent.core.model_config.models import (
    ModelConfigKeyStatus,
    ModelConfigProviderType,
    ModelConfigStatus,
    ModelInvocationStatus,
)
from quantagent.core.model_config.orm import ModelConfigORM, ModelInvocationORM


GLOBAL_MODEL_CONFIG_ID = 1
DEFAULT_PROVIDER_NAME = "OpenAI Compatible"
DEFAULT_SMOKE_PROMPT = 'Reply with "ok".'
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


class ModelConfigServiceError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        retryable: bool = False,
        safe_details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable
        self.safe_details = safe_details or {}


@dataclass(frozen=True)
class SaveModelConfigInput:
    name: str
    model: str
    base_url: str | None = None
    api_key: str | None = None
    enabled: bool = True
    provider_type: ModelConfigProviderType = ModelConfigProviderType.OPENAI_COMPATIBLE


@dataclass(frozen=True)
class ModelTokenUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class ModelConfigResult:
    provider_type: ModelConfigProviderType
    name: str
    base_url: str | None
    model: str
    enabled: bool
    status: ModelConfigStatus
    key_status: ModelConfigKeyStatus
    masked_key: str | None
    last_error: str | None
    updated_at: datetime | None


@dataclass(frozen=True)
class ModelInvocationResult:
    id: int | None
    provider_type: ModelConfigProviderType
    provider_name: str
    model: str
    status: ModelInvocationStatus
    token_usage: ModelTokenUsage
    error_summary: str | None
    request_id: str | None
    trace_id: str | None
    agent_run_id: str | None
    created_at: datetime


@dataclass(frozen=True)
class ModelCallResult:
    token_usage: ModelTokenUsage


class FixedModelCallClient(Protocol):
    def run_fixed_smoke(
        self,
        *,
        base_url: str | None,
        model: str,
        api_key: str,
        request_id: str | None,
    ) -> ModelCallResult:
        ...


class OpenAICompatibleModelClient:
    """Minimal OpenAI-compatible chat completions client used by V1 smoke checks."""

    def run_fixed_smoke(
        self,
        *,
        base_url: str | None,
        model: str,
        api_key: str,
        request_id: str | None,
    ) -> ModelCallResult:
        endpoint = f"{(base_url or DEFAULT_OPENAI_BASE_URL).rstrip('/')}/chat/completions"
        # The smoke check is fixed so user prompts, events, strategy text, and trading context never enter this path.
        payload = json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": DEFAULT_SMOKE_PROMPT}],
                "max_tokens": 8,
                "temperature": 0,
            }
        ).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if request_id:
            headers["X-Request-ID"] = request_id

        req = urllib_request.Request(endpoint, data=payload, headers=headers, method="POST")
        try:
            with urllib_request.urlopen(req, timeout=15) as response:  # noqa: S310 - user-configured provider endpoint.
                body = response.read()
        except urllib.error.HTTPError as exc:
            raise ModelConfigServiceError(
                "Model provider request failed",
                code="MODEL_PROVIDER_HTTP_ERROR",
                retryable=exc.code >= 500,
                safe_details={"status": exc.code},
            ) from exc
        except urllib.error.URLError as exc:
            raise ModelConfigServiceError(
                "Model provider is not reachable",
                code="MODEL_PROVIDER_UNREACHABLE",
                retryable=True,
            ) from exc
        except TimeoutError as exc:
            raise ModelConfigServiceError(
                "Model provider request timed out",
                code="MODEL_PROVIDER_TIMEOUT",
                retryable=True,
            ) from exc

        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ModelConfigServiceError(
                "Model provider returned an invalid response",
                code="MODEL_PROVIDER_RESPONSE_INVALID",
            ) from exc

        usage = parsed.get("usage")
        # Keep provider responses out of persistence/log surfaces; V1 only extracts aggregate usage counters.
        if not isinstance(usage, dict):
            return ModelCallResult(token_usage=ModelTokenUsage())
        return ModelCallResult(
            token_usage=ModelTokenUsage(
                prompt_tokens=_optional_int(usage.get("prompt_tokens")),
                completion_tokens=_optional_int(usage.get("completion_tokens")),
                total_tokens=_optional_int(usage.get("total_tokens")),
            )
        )


class ModelConfigService:
    def __init__(
        self,
        session: Session,
        *,
        encryption_key: str | None,
        client: FixedModelCallClient | None = None,
    ) -> None:
        self._session = session
        self._encryption_key = encryption_key
        self._client = client or OpenAICompatibleModelClient()

    def get_config(self) -> ModelConfigResult:
        return _config_result(self._get_config())

    def save_config(self, payload: SaveModelConfigInput) -> ModelConfigResult:
        config = self._get_config()
        now = _utcnow()
        if config is None:
            config = ModelConfigORM(
                id=GLOBAL_MODEL_CONFIG_ID,
                provider_type=payload.provider_type.value,
                name=payload.name,
                base_url=payload.base_url,
                model=payload.model,
                enabled=payload.enabled,
                encrypted_api_key=None,
                last_error=None,
                created_at=now,
                updated_at=now,
            )
            self._session.add(config)

        config.provider_type = payload.provider_type.value
        config.name = payload.name
        config.base_url = payload.base_url
        config.model = payload.model
        config.enabled = payload.enabled
        config.last_error = None
        config.updated_at = now
        if payload.api_key is not None:
            try:
                config.encrypted_api_key = self._crypto().encrypt(payload.api_key)
            except ModelConfigCryptoError as exc:
                raise ModelConfigServiceError(
                    "Model API key encryption is not configured",
                    code="MODEL_CONFIG_ENCRYPTION_UNAVAILABLE",
                ) from exc

        self._session.commit()
        self._session.refresh(config)
        return _config_result(config)

    def test_connection(self, *, request_id: str | None = None, trace_id: str | None = None) -> ModelInvocationResult:
        config = self._get_config()
        if config is None or not config.encrypted_api_key:
            invocation = self._record_invocation(
                config=config,
                status=ModelInvocationStatus.FAILED,
                token_usage=ModelTokenUsage(),
                error_summary="MODEL_CONFIG_KEY_MISSING",
                request_id=request_id,
                trace_id=trace_id,
            )
            raise ModelConfigServiceError(
                "Model API key is missing",
                code="MODEL_CONFIG_KEY_MISSING",
                safe_details={"invocation_id": invocation.id},
            )
        if not config.enabled:
            invocation = self._record_invocation(
                config=config,
                status=ModelInvocationStatus.FAILED,
                token_usage=ModelTokenUsage(),
                error_summary="MODEL_CONFIG_DISABLED",
                request_id=request_id,
                trace_id=trace_id,
            )
            raise ModelConfigServiceError(
                "Model config is disabled",
                code="MODEL_CONFIG_DISABLED",
                safe_details={"invocation_id": invocation.id},
            )

        try:
            # Plaintext exists only in this runtime scope; query APIs and invocation logs never receive it.
            api_key = self._crypto().decrypt(config.encrypted_api_key)
            call_result = self._client.run_fixed_smoke(
                base_url=config.base_url,
                model=config.model,
                api_key=api_key,
                request_id=request_id,
            )
        except ModelConfigCryptoError as exc:
            invocation = self._record_invocation(
                config=config,
                status=ModelInvocationStatus.FAILED,
                token_usage=ModelTokenUsage(),
                error_summary="MODEL_CONFIG_DECRYPT_FAILED",
                request_id=request_id,
                trace_id=trace_id,
            )
            raise ModelConfigServiceError(
                "Model API key cannot be decrypted",
                code="MODEL_CONFIG_DECRYPT_FAILED",
                safe_details={"invocation_id": invocation.id},
            ) from exc
        except ModelConfigServiceError as exc:
            config.last_error = exc.code
            invocation = self._record_invocation(
                config=config,
                status=ModelInvocationStatus.FAILED,
                token_usage=ModelTokenUsage(),
                error_summary=exc.code,
                request_id=request_id,
                trace_id=trace_id,
            )
            exc.safe_details.setdefault("invocation_id", invocation.id)
            raise

        config.last_error = None
        return self._record_invocation(
            config=config,
            status=ModelInvocationStatus.SUCCEEDED,
            token_usage=call_result.token_usage,
            error_summary=None,
            request_id=request_id,
            trace_id=trace_id,
        )

    def list_invocations(self, *, limit: int = 20) -> list[ModelInvocationResult]:
        statement = (
            select(ModelInvocationORM)
            .order_by(ModelInvocationORM.created_at.desc(), ModelInvocationORM.id.desc())
            .limit(limit)
        )
        return [_invocation_result(row) for row in self._session.scalars(statement).all()]

    def _get_config(self) -> ModelConfigORM | None:
        return self._session.get(ModelConfigORM, GLOBAL_MODEL_CONFIG_ID)

    def _crypto(self) -> ModelConfigCrypto:
        return ModelConfigCrypto(self._encryption_key)

    def _record_invocation(
        self,
        *,
        config: ModelConfigORM | None,
        status: ModelInvocationStatus,
        token_usage: ModelTokenUsage,
        error_summary: str | None,
        request_id: str | None,
        trace_id: str | None,
        agent_run_id: str | None = None,
    ) -> ModelInvocationResult:
        now = _utcnow()
        invocation = ModelInvocationORM(
            provider_type=(config.provider_type if config is not None else ModelConfigProviderType.OPENAI_COMPATIBLE.value),
            provider_name=(config.name if config is not None else DEFAULT_PROVIDER_NAME),
            model=(config.model if config is not None else ""),
            status=status.value,
            prompt_tokens=token_usage.prompt_tokens,
            completion_tokens=token_usage.completion_tokens,
            total_tokens=token_usage.total_tokens,
            error_summary=error_summary,
            request_id=request_id,
            trace_id=trace_id,
            agent_run_id=agent_run_id,
            created_at=now,
        )
        self._session.add(invocation)
        if config is not None:
            config.updated_at = now
        self._session.commit()
        self._session.refresh(invocation)
        return _invocation_result(invocation)


def _config_result(config: ModelConfigORM | None) -> ModelConfigResult:
    if config is None:
        return ModelConfigResult(
            provider_type=ModelConfigProviderType.OPENAI_COMPATIBLE,
            name=DEFAULT_PROVIDER_NAME,
            base_url=None,
            model="",
            enabled=False,
            status=ModelConfigStatus.MISSING_KEY,
            key_status=ModelConfigKeyStatus.MISSING,
            masked_key=None,
            last_error=None,
            updated_at=None,
        )

    has_key = bool(config.encrypted_api_key)
    status = ModelConfigStatus.CONFIGURED
    if not config.enabled:
        status = ModelConfigStatus.DISABLED
    elif not has_key:
        status = ModelConfigStatus.MISSING_KEY
    elif config.last_error:
        status = ModelConfigStatus.FAILED

    return ModelConfigResult(
        provider_type=ModelConfigProviderType(config.provider_type),
        name=config.name,
        base_url=config.base_url,
        model=config.model,
        enabled=config.enabled,
        status=status,
        key_status=ModelConfigKeyStatus.CONFIGURED if has_key else ModelConfigKeyStatus.MISSING,
        # This marker is deliberately non-reversible; it only communicates configured state to the UI.
        masked_key="********" if has_key else None,
        last_error=config.last_error,
        updated_at=config.updated_at,
    )


def _invocation_result(invocation: ModelInvocationORM) -> ModelInvocationResult:
    return ModelInvocationResult(
        id=invocation.id,
        provider_type=ModelConfigProviderType(invocation.provider_type),
        provider_name=invocation.provider_name,
        model=invocation.model,
        status=ModelInvocationStatus(invocation.status),
        token_usage=ModelTokenUsage(
            prompt_tokens=invocation.prompt_tokens,
            completion_tokens=invocation.completion_tokens,
            total_tokens=invocation.total_tokens,
        ),
        error_summary=invocation.error_summary,
        request_id=invocation.request_id,
        trace_id=invocation.trace_id,
        agent_run_id=invocation.agent_run_id,
        created_at=invocation.created_at,
    )


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _utcnow() -> datetime:
    return datetime.now(UTC)
