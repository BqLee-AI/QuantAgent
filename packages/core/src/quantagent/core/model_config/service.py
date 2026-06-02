from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from typing import Any, Protocol
import urllib.error
from urllib import request as urllib_request

from sqlalchemy.orm import Session

from quantagent.core.model_config.crypto import ModelConfigCrypto, ModelConfigCryptoError
from quantagent.core.model_config.models import (
    ModelInvocationStatus,
    ModelPresetKey,
    ModelPresetStatus,
    ModelProviderKeyStatus,
    ModelProviderStatus,
    ModelProviderType,
    ModelResolutionSource,
)
from quantagent.core.model_config.orm import (
    ModelInvocationORM,
    ModelPresetBindingORM,
    ModelProviderModelORM,
    ModelProviderORM,
)
from quantagent.core.model_config.repository import ModelProviderRepository


DEFAULT_PROVIDER_NAME = "OpenAI Compatible"
DEFAULT_SMOKE_PROMPT = 'Reply with "ok".'
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
PRESET_TITLES: dict[ModelPresetKey, str] = {
    ModelPresetKey.GLOBAL_DEFAULT: "全局默认模型",
    ModelPresetKey.ECONOMY_TEXT: "经济型模型",
    ModelPresetKey.GENERAL_TEXT: "通用模型",
    ModelPresetKey.REASONING_TEXT: "深度推理模型",
    ModelPresetKey.MULTIMODAL: "多模态模型",
}
PRESET_DESCRIPTIONS: dict[ModelPresetKey, str] = {
    ModelPresetKey.GLOBAL_DEFAULT: "系统兜底使用的默认模型。",
    ModelPresetKey.ECONOMY_TEXT: "用于低成本摘要、筛选和轻量提取。",
    ModelPresetKey.GENERAL_TEXT: "用于日常通用文本任务。",
    ModelPresetKey.REASONING_TEXT: "用于复杂分析和高质量推理任务。",
    ModelPresetKey.MULTIMODAL: "用于图片、图表和视觉理解任务。",
}


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
class CreateModelProviderInput:
    name: str
    base_url: str | None = None
    api_key: str | None = None
    enabled: bool = True
    provider_type: ModelProviderType = ModelProviderType.OPENAI_COMPATIBLE
    is_default: bool = False


@dataclass(frozen=True)
class UpdateModelProviderInput:
    name: str
    base_url: str | None = None
    api_key: str | None = None
    enabled: bool = True
    provider_type: ModelProviderType = ModelProviderType.OPENAI_COMPATIBLE


@dataclass(frozen=True)
class CreateProviderModelInput:
    model_name: str
    enabled: bool = True
    supports_vision: bool = False
    is_global_default: bool = False


@dataclass(frozen=True)
class UpdateProviderModelInput:
    model_name: str
    enabled: bool = True
    supports_vision: bool = False
    is_global_default: bool = False


@dataclass(frozen=True)
class UpdateModelPresetInput:
    primary_model_id: int | None
    fallback_model_id: int | None


@dataclass(frozen=True)
class ModelTokenUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class ModelProviderModelResult:
    id: int
    provider_id: int
    model_name: str
    enabled: bool
    supports_vision: bool
    is_global_default: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ModelProviderSummaryResult:
    id: int
    provider_type: ModelProviderType
    name: str
    base_url: str | None
    enabled: bool
    is_default: bool
    status: ModelProviderStatus
    key_status: ModelProviderKeyStatus
    masked_key: str | None
    last_error: str | None
    model_count: int
    updated_at: datetime


@dataclass(frozen=True)
class ModelProviderDetailResult:
    id: int
    provider_type: ModelProviderType
    name: str
    base_url: str | None
    enabled: bool
    is_default: bool
    status: ModelProviderStatus
    key_status: ModelProviderKeyStatus
    masked_key: str | None
    last_error: str | None
    model_count: int
    models: list[ModelProviderModelResult]
    updated_at: datetime


@dataclass(frozen=True)
class ModelProviderListResult:
    default_provider_id: int | None
    providers: list[ModelProviderSummaryResult]


@dataclass(frozen=True)
class ModelPresetBindingResult:
    preset_key: ModelPresetKey
    title: str
    description: str
    primary_model: ModelProviderModelResult | None
    fallback_model: ModelProviderModelResult | None
    status: ModelPresetStatus
    validation_message: str | None


@dataclass(frozen=True)
class ResolvedModelResult:
    preset_key: ModelPresetKey
    source: ModelResolutionSource
    provider: ModelProviderORM
    model: ModelProviderModelORM


@dataclass(frozen=True)
class ModelInvocationResult:
    id: int | None
    provider_id: int | None
    provider_type: ModelProviderType
    provider_name: str
    model: str
    preset_key: ModelPresetKey | None
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


@dataclass(frozen=True)
class StructuredModelCallResult:
    output: dict[str, Any]
    token_usage: ModelTokenUsage


@dataclass(frozen=True)
class RemoteProviderModelResult:
    id: str
    owned_by: str | None = None
    supports_vision: bool | None = None


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

    def list_remote_models(
        self,
        *,
        base_url: str | None,
        api_key: str,
        request_id: str | None,
    ) -> list[RemoteProviderModelResult]:
        ...

    def run_structured_json(
        self,
        *,
        base_url: str | None,
        model: str,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        request_id: str | None,
    ) -> StructuredModelCallResult:
        ...


class OpenAICompatibleModelClient:
    """Minimal OpenAI-compatible chat completions client used by provider smoke checks."""

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

    def list_remote_models(
        self,
        *,
        base_url: str | None,
        api_key: str,
        request_id: str | None,
    ) -> list[RemoteProviderModelResult]:
        candidate_endpoints = _candidate_model_list_endpoints(base_url)
        headers = {"Authorization": f"Bearer {api_key}"}
        if request_id:
            headers["X-Request-ID"] = request_id

        last_not_found: urllib.error.HTTPError | None = None
        for endpoint in candidate_endpoints:
            req = urllib_request.Request(endpoint, headers=headers, method="GET")
            try:
                with urllib_request.urlopen(req, timeout=15) as response:  # noqa: S310
                    body = response.read()
                parsed = json.loads(body.decode("utf-8"))
                data = parsed.get("data")
                if not isinstance(data, list):
                    raise ModelConfigServiceError(
                        "Model provider returned an invalid response",
                        code="MODEL_PROVIDER_RESPONSE_INVALID",
                    )
                results: list[RemoteProviderModelResult] = []
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    model_id = item.get("id")
                    if not isinstance(model_id, str) or not model_id.strip():
                        continue
                    owned_by = item.get("owned_by")
                    results.append(
                        RemoteProviderModelResult(
                            id=model_id.strip(),
                            owned_by=owned_by if isinstance(owned_by, str) and owned_by.strip() else None,
                            supports_vision=_infer_supports_vision(model_id),
                        )
                    )
                return results
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    last_not_found = exc
                    continue
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
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ModelConfigServiceError(
                    "Model provider returned an invalid response",
                    code="MODEL_PROVIDER_RESPONSE_INVALID",
                ) from exc

        if last_not_found is not None:
            raise ModelConfigServiceError(
                "Model provider request failed",
                code="MODEL_PROVIDER_HTTP_ERROR",
                safe_details={"status": 404},
            ) from last_not_found
        return []

    def run_structured_json(
        self,
        *,
        base_url: str | None,
        model: str,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        request_id: str | None,
    ) -> StructuredModelCallResult:
        endpoint = f"{(base_url or DEFAULT_OPENAI_BASE_URL).rstrip('/')}/chat/completions"
        payload = json.dumps(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"},
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
            with urllib_request.urlopen(req, timeout=30) as response:  # noqa: S310 - user-configured provider endpoint.
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

        choice_content = _extract_choice_content(parsed)
        if choice_content is None:
            raise ModelConfigServiceError(
                "Model provider returned an invalid response",
                code="MODEL_PROVIDER_RESPONSE_INVALID",
            )
        try:
            output = json.loads(choice_content)
        except json.JSONDecodeError as exc:
            raise ModelConfigServiceError(
                "Model provider returned non-JSON content",
                code="MODEL_PROVIDER_RESPONSE_INVALID",
            ) from exc
        if not isinstance(output, dict):
            raise ModelConfigServiceError(
                "Model provider returned an invalid JSON object",
                code="MODEL_PROVIDER_RESPONSE_INVALID",
            )

        usage = parsed.get("usage")
        token_usage = ModelTokenUsage()
        if isinstance(usage, dict):
            token_usage = ModelTokenUsage(
                prompt_tokens=_optional_int(usage.get("prompt_tokens")),
                completion_tokens=_optional_int(usage.get("completion_tokens")),
                total_tokens=_optional_int(usage.get("total_tokens")),
            )
        return StructuredModelCallResult(output=output, token_usage=token_usage)


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
        self._repository = ModelProviderRepository(session)

    def list_providers(self) -> ModelProviderListResult:
        providers = self._repository.list_providers()
        default_provider = self._repository.find_default_provider()
        return ModelProviderListResult(
            default_provider_id=default_provider.id if default_provider else None,
            providers=[self._provider_summary_result(item) for item in providers],
        )

    def get_provider(self, provider_id: int) -> ModelProviderDetailResult:
        provider = self._require_provider(provider_id)
        return self._provider_detail_result(provider)

    def create_provider(self, payload: CreateModelProviderInput) -> ModelProviderDetailResult:
        now = _utcnow()
        provider = ModelProviderORM(
            provider_type=payload.provider_type.value,
            name=payload.name,
            base_url=payload.base_url,
            enabled=payload.enabled,
            is_default=False,
            encrypted_api_key=None,
            last_error=None,
            created_at=now,
            updated_at=now,
        )
        if payload.api_key is not None:
            provider.encrypted_api_key = self._encrypt_key(payload.api_key)

        self._repository.create_provider(provider)
        if payload.is_default or self._repository.find_default_provider() is None:
            self._set_default_provider(provider)
        self._session.commit()
        self._session.refresh(provider)
        return self._provider_detail_result(provider)

    def update_provider(self, provider_id: int, payload: UpdateModelProviderInput) -> ModelProviderDetailResult:
        provider = self._require_provider(provider_id)
        provider.provider_type = payload.provider_type.value
        provider.name = payload.name
        provider.base_url = payload.base_url
        provider.enabled = payload.enabled
        provider.last_error = None
        provider.updated_at = _utcnow()
        if payload.api_key is not None:
            provider.encrypted_api_key = self._encrypt_key(payload.api_key)

        if provider.is_default and not provider.enabled:
            self._clear_default_provider_and_promote_next(excluding_provider_id=provider.id)

        self._session.commit()
        self._session.refresh(provider)
        return self._provider_detail_result(provider)

    def set_default_provider(self, provider_id: int) -> ModelProviderDetailResult:
        provider = self._require_provider(provider_id)
        self._set_default_provider(provider)
        self._session.commit()
        self._session.refresh(provider)
        return self._provider_detail_result(provider)

    def delete_provider(self, provider_id: int) -> None:
        provider = self._require_provider(provider_id)
        provider_models = self._repository.list_provider_models(provider.id)
        provider_model_ids = {model.id for model in provider_models}
        deleted_global_default = any(model.is_global_default for model in provider_models)

        if provider_model_ids:
            for binding in self._repository.list_preset_bindings():
                if binding.primary_model_id in provider_model_ids:
                    binding.primary_model_id = None
                if binding.fallback_model_id in provider_model_ids:
                    binding.fallback_model_id = None

        for invocation in self._repository.list_provider_invocations(provider.id):
            invocation.provider_id = None

        if deleted_global_default:
            self._repository.clear_global_default_model()

        for model in provider_models:
            self._repository.delete_provider_model(model)

        if provider.is_default:
            provider.is_default = False

        self._repository.delete_provider(provider)

        if deleted_global_default:
            self._promote_next_global_default(excluding_provider_id=provider.id)

        self._session.commit()

    def create_provider_model(self, provider_id: int, payload: CreateProviderModelInput) -> ModelProviderModelResult:
        provider = self._require_provider(provider_id)
        if self._repository.find_provider_model_by_name(provider_id=provider.id, model_name=payload.model_name):
            raise ModelConfigServiceError(
                "Model already exists under provider",
                code="MODEL_PROVIDER_MODEL_DUPLICATE",
                safe_details={"provider_id": provider.id},
            )

        now = _utcnow()
        model = ModelProviderModelORM(
            provider_id=provider.id,
            model_name=payload.model_name,
            enabled=payload.enabled,
            supports_vision=payload.supports_vision,
            is_global_default=False,
            created_at=now,
            updated_at=now,
        )
        self._repository.create_provider_model(model)
        if payload.is_global_default or self._repository.find_global_default_model() is None:
            self._set_global_default_model(model)
        provider.updated_at = _utcnow()
        self._session.commit()
        self._session.refresh(model)
        return _provider_model_result(model)

    def update_provider_model(
        self,
        provider_id: int,
        model_id: int,
        payload: UpdateProviderModelInput,
    ) -> ModelProviderModelResult:
        provider = self._require_provider(provider_id)
        model = self._require_provider_model(model_id)
        if model.provider_id != provider.id:
            raise ModelConfigServiceError("Provider model was not found", code="MODEL_PROVIDER_MODEL_NOT_FOUND")

        duplicate = self._repository.find_provider_model_by_name(provider_id=provider.id, model_name=payload.model_name)
        if duplicate is not None and duplicate.id != model.id:
            raise ModelConfigServiceError(
                "Model already exists under provider",
                code="MODEL_PROVIDER_MODEL_DUPLICATE",
                safe_details={"provider_id": provider.id},
            )

        model.model_name = payload.model_name
        model.enabled = payload.enabled
        model.supports_vision = payload.supports_vision
        model.updated_at = _utcnow()
        if payload.is_global_default:
            self._set_global_default_model(model)
        elif model.is_global_default and not payload.is_global_default:
            self._clear_global_default_and_promote_next(excluding_model_id=model.id)

        provider.updated_at = _utcnow()
        self._session.commit()
        self._session.refresh(model)
        return _provider_model_result(model)

    def delete_provider_model(self, provider_id: int, model_id: int) -> None:
        provider = self._require_provider(provider_id)
        model = self._require_provider_model(model_id)
        if model.provider_id != provider.id:
            raise ModelConfigServiceError("Provider model was not found", code="MODEL_PROVIDER_MODEL_NOT_FOUND")

        self._validate_delete_provider_model(model)
        was_global_default = model.is_global_default
        self._repository.delete_provider_model(model)
        if was_global_default:
            self._clear_global_default_and_promote_next(excluding_model_id=model.id)
        provider.updated_at = _utcnow()
        self._session.commit()

    def list_presets(self) -> list[ModelPresetBindingResult]:
        self._ensure_all_presets_exist()
        return [self._preset_binding_result(item) for item in self._repository.list_preset_bindings()]

    def update_preset(self, preset_key: ModelPresetKey, payload: UpdateModelPresetInput) -> ModelPresetBindingResult:
        self._ensure_all_presets_exist()
        primary_model = self._optional_provider_model(payload.primary_model_id)
        fallback_model = self._optional_provider_model(payload.fallback_model_id)
        self._validate_preset_models(preset_key, primary_model, fallback_model)
        binding = self._repository.upsert_preset_binding(
            preset_key=preset_key,
            primary_model_id=primary_model.id if primary_model else None,
            fallback_model_id=fallback_model.id if fallback_model else None,
        )
        self._session.commit()
        self._session.refresh(binding)
        return self._preset_binding_result(binding)

    def resolve_preset_model(self, preset_key: ModelPresetKey) -> ResolvedModelResult:
        binding = self._repository.get_preset_binding(preset_key)
        if binding is None or binding.primary_model_id is None:
            raise ModelConfigServiceError(
                "Preset primary model is not configured",
                code="MODEL_PRESET_PRIMARY_MISSING",
                safe_details={"preset_key": preset_key.value},
            )

        primary_model = self._require_provider_model(binding.primary_model_id)
        if self._is_usable_model(primary_model, preset_key):
            return self._resolved_model_result(preset_key, primary_model, ModelResolutionSource.PRIMARY)

        if binding.fallback_model_id is not None:
            fallback_model = self._require_provider_model(binding.fallback_model_id)
            if self._is_usable_model(fallback_model, preset_key):
                return self._resolved_model_result(preset_key, fallback_model, ModelResolutionSource.FALLBACK)

        global_default_model = self._repository.find_global_default_model()
        if global_default_model is not None and self._is_usable_model(global_default_model, preset_key):
            return self._resolved_model_result(
                preset_key,
                global_default_model,
                ModelResolutionSource.GLOBAL_DEFAULT,
            )

        raise ModelConfigServiceError(
            "No compatible model is available for preset",
            code="MODEL_PRESET_NO_AVAILABLE_MODEL",
            safe_details={"preset_key": preset_key.value},
        )

    def test_connection(
        self,
        provider_id: int,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> ModelInvocationResult:
        provider = self._require_provider(provider_id)
        model = self._pick_provider_test_model(provider)
        if not provider.encrypted_api_key:
            invocation = self._record_failed_invocation_and_commit(
                provider=provider,
                model_name=model.model_name if model else DEFAULT_PROVIDER_NAME,
                preset_key=ModelPresetKey.GLOBAL_DEFAULT,
                error_summary="MODEL_PROVIDER_KEY_MISSING",
                request_id=request_id,
                trace_id=trace_id,
            )
            raise ModelConfigServiceError(
                "Model provider API key is missing",
                code="MODEL_PROVIDER_KEY_MISSING",
                safe_details={"invocation_id": invocation.id, "provider_id": provider.id},
            )
        if not provider.enabled:
            invocation = self._record_failed_invocation_and_commit(
                provider=provider,
                model_name=model.model_name if model else DEFAULT_PROVIDER_NAME,
                preset_key=ModelPresetKey.GLOBAL_DEFAULT,
                error_summary="MODEL_PROVIDER_DISABLED",
                request_id=request_id,
                trace_id=trace_id,
            )
            raise ModelConfigServiceError(
                "Model provider is disabled",
                code="MODEL_PROVIDER_DISABLED",
                safe_details={"invocation_id": invocation.id, "provider_id": provider.id},
            )
        if model is None:
            invocation = self._record_failed_invocation_and_commit(
                provider=provider,
                model_name=DEFAULT_PROVIDER_NAME,
                preset_key=ModelPresetKey.GLOBAL_DEFAULT,
                error_summary="MODEL_PROVIDER_MODEL_MISSING",
                request_id=request_id,
                trace_id=trace_id,
            )
            raise ModelConfigServiceError(
                "Provider does not have an enabled model",
                code="MODEL_PROVIDER_MODEL_MISSING",
                safe_details={"invocation_id": invocation.id, "provider_id": provider.id},
            )

        try:
            # Plaintext exists only in this runtime scope; query APIs and invocation logs never receive it.
            api_key = self._crypto().decrypt(provider.encrypted_api_key)
            call_result = self._client.run_fixed_smoke(
                base_url=provider.base_url,
                model=model.model_name,
                api_key=api_key,
                request_id=request_id,
            )
        except ModelConfigCryptoError as exc:
            invocation = self._record_failed_invocation_and_commit(
                provider=provider,
                model_name=model.model_name,
                preset_key=ModelPresetKey.GLOBAL_DEFAULT,
                error_summary="MODEL_PROVIDER_DECRYPT_FAILED",
                request_id=request_id,
                trace_id=trace_id,
            )
            raise ModelConfigServiceError(
                "Model provider API key cannot be decrypted",
                code="MODEL_PROVIDER_DECRYPT_FAILED",
                safe_details={"invocation_id": invocation.id, "provider_id": provider.id},
            ) from exc
        except ModelConfigServiceError as exc:
            provider.last_error = exc.code
            invocation = self._record_failed_invocation_and_commit(
                provider=provider,
                model_name=model.model_name,
                preset_key=ModelPresetKey.GLOBAL_DEFAULT,
                error_summary=exc.code,
                request_id=request_id,
                trace_id=trace_id,
            )
            exc.safe_details.setdefault("invocation_id", invocation.id)
            exc.safe_details.setdefault("provider_id", provider.id)
            raise

        provider.last_error = None
        invocation = self._record_invocation(
            provider=provider,
            model_name=model.model_name,
            preset_key=ModelPresetKey.GLOBAL_DEFAULT,
            status=ModelInvocationStatus.SUCCEEDED,
            token_usage=call_result.token_usage,
            error_summary=None,
            request_id=request_id,
            trace_id=trace_id,
        )
        self._session.commit()
        return invocation

    def list_invocations(
        self,
        *,
        limit: int = 20,
        provider_id: int | None = None,
        preset_key: ModelPresetKey | None = None,
    ) -> list[ModelInvocationResult]:
        if provider_id is not None and self._repository.get_provider(provider_id) is None:
            raise ModelConfigServiceError("Model provider was not found", code="MODEL_PROVIDER_NOT_FOUND")
        return [
            _invocation_result(item)
            for item in self._repository.list_invocations(limit=limit, provider_id=provider_id, preset_key=preset_key)
        ]

    def invoke_structured_json(
        self,
        *,
        preset_key: ModelPresetKey,
        system_prompt: str,
        user_prompt: str,
        request_id: str | None = None,
        trace_id: str | None = None,
        agent_run_id: str | None = None,
    ) -> tuple[StructuredModelCallResult, ModelInvocationResult]:
        resolved = self.resolve_preset_model(preset_key)
        provider = resolved.provider
        model = resolved.model

        if not provider.encrypted_api_key:
            invocation = self._record_failed_invocation_and_commit(
                provider=provider,
                model_name=model.model_name,
                preset_key=preset_key,
                error_summary="MODEL_PROVIDER_KEY_MISSING",
                request_id=request_id,
                trace_id=trace_id,
            )
            raise ModelConfigServiceError(
                "Model provider API key is missing",
                code="MODEL_PROVIDER_KEY_MISSING",
                safe_details={"invocation_id": invocation.id, "provider_id": provider.id},
            )

        try:
            api_key = self._crypto().decrypt(provider.encrypted_api_key)
            call_result = self._client.run_structured_json(
                base_url=provider.base_url,
                model=model.model_name,
                api_key=api_key,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                request_id=request_id,
            )
        except ModelConfigCryptoError as exc:
            invocation = self._record_failed_invocation_and_commit(
                provider=provider,
                model_name=model.model_name,
                preset_key=preset_key,
                error_summary="MODEL_PROVIDER_DECRYPT_FAILED",
                request_id=request_id,
                trace_id=trace_id,
            )
            raise ModelConfigServiceError(
                "Model provider API key cannot be decrypted",
                code="MODEL_PROVIDER_DECRYPT_FAILED",
                safe_details={"invocation_id": invocation.id, "provider_id": provider.id},
            ) from exc
        except ModelConfigServiceError as exc:
            provider.last_error = exc.code
            invocation = self._record_failed_invocation_and_commit(
                provider=provider,
                model_name=model.model_name,
                preset_key=preset_key,
                error_summary=exc.code,
                request_id=request_id,
                trace_id=trace_id,
            )
            exc.safe_details.setdefault("invocation_id", invocation.id)
            exc.safe_details.setdefault("provider_id", provider.id)
            raise

        provider.last_error = None
        invocation = self._record_invocation(
            provider=provider,
            model_name=model.model_name,
            preset_key=preset_key,
            status=ModelInvocationStatus.SUCCEEDED,
            token_usage=call_result.token_usage,
            error_summary=None,
            request_id=request_id,
            trace_id=trace_id,
            agent_run_id=agent_run_id,
        )
        self._session.commit()
        return call_result, invocation

    def _encrypt_key(self, api_key: str) -> str:
        try:
            return self._crypto().encrypt(api_key)
        except ModelConfigCryptoError as exc:
            raise ModelConfigServiceError(
                "Model API key encryption is not configured",
                code="MODEL_CONFIG_ENCRYPTION_UNAVAILABLE",
            ) from exc

    def _require_provider(self, provider_id: int) -> ModelProviderORM:
        provider = self._repository.get_provider(provider_id)
        if provider is None:
            raise ModelConfigServiceError("Model provider was not found", code="MODEL_PROVIDER_NOT_FOUND")
        return provider

    def _require_provider_model(self, model_id: int) -> ModelProviderModelORM:
        model = self._repository.get_provider_model(model_id)
        if model is None:
            raise ModelConfigServiceError("Provider model was not found", code="MODEL_PROVIDER_MODEL_NOT_FOUND")
        return model

    def _optional_provider_model(self, model_id: int | None) -> ModelProviderModelORM | None:
        if model_id is None:
            return None
        return self._require_provider_model(model_id)

    def _set_default_provider(self, provider: ModelProviderORM) -> None:
        self._repository.clear_default_provider()
        provider.is_default = True
        provider.updated_at = _utcnow()

    def _clear_default_provider_and_promote_next(self, *, excluding_provider_id: int) -> None:
        self._repository.clear_default_provider()
        for candidate in self._repository.list_providers():
            if candidate.id == excluding_provider_id or not candidate.enabled:
                continue
            candidate.is_default = True
            candidate.updated_at = _utcnow()
            return

    def _set_global_default_model(self, model: ModelProviderModelORM) -> None:
        self._repository.clear_global_default_model()
        model.is_global_default = True
        model.updated_at = _utcnow()

    def _clear_global_default_and_promote_next(self, *, excluding_model_id: int) -> None:
        self._repository.clear_global_default_model()
        for provider in self._repository.list_providers():
            if not provider.enabled:
                continue
            for candidate in self._repository.list_provider_models(provider.id):
                if candidate.id == excluding_model_id or not candidate.enabled:
                    continue
                self._set_global_default_model(candidate)
                return

    def _validate_delete_provider_model(self, model: ModelProviderModelORM) -> None:
        for binding in self._repository.list_preset_bindings():
            if binding.primary_model_id == model.id or binding.fallback_model_id == model.id:
                raise ModelConfigServiceError(
                    "Provider model is still referenced by preset",
                    code="MODEL_PROVIDER_MODEL_IN_USE",
                    safe_details={"preset_key": binding.preset_key},
                )

    def _ensure_all_presets_exist(self) -> None:
        for preset_key in ModelPresetKey:
            if self._repository.get_preset_binding(preset_key) is None:
                self._repository.upsert_preset_binding(
                    preset_key=preset_key,
                    primary_model_id=None,
                    fallback_model_id=None,
                )
        self._session.flush()

    def _validate_preset_models(
        self,
        preset_key: ModelPresetKey,
        primary_model: ModelProviderModelORM | None,
        fallback_model: ModelProviderModelORM | None,
    ) -> None:
        if preset_key is not ModelPresetKey.GLOBAL_DEFAULT and primary_model is None:
            raise ModelConfigServiceError(
                "Preset primary model is required",
                code="MODEL_PRESET_PRIMARY_REQUIRED",
                safe_details={"preset_key": preset_key.value},
            )
        if primary_model and not self._is_bindable_model(primary_model, preset_key):
            raise ModelConfigServiceError(
                "Primary model does not satisfy preset requirements",
                code="MODEL_PRESET_PRIMARY_INVALID",
                safe_details={"preset_key": preset_key.value, "model_id": primary_model.id},
            )
        if fallback_model and not self._is_bindable_model(fallback_model, preset_key):
            raise ModelConfigServiceError(
                "Fallback model does not satisfy preset requirements",
                code="MODEL_PRESET_FALLBACK_INVALID",
                safe_details={"preset_key": preset_key.value, "model_id": fallback_model.id},
            )

    def _resolved_model_result(
        self,
        preset_key: ModelPresetKey,
        model: ModelProviderModelORM,
        source: ModelResolutionSource,
    ) -> ResolvedModelResult:
        provider = self._require_provider(model.provider_id)
        return ResolvedModelResult(
            preset_key=preset_key,
            source=source,
            provider=provider,
            model=model,
        )

    def _is_usable_model(
        self,
        model: ModelProviderModelORM,
        preset_key: ModelPresetKey,
        *,
        ignore_current_binding: bool = False,
    ) -> bool:
        provider = self._repository.get_provider(model.provider_id)
        if provider is None or not provider.enabled or not model.enabled:
            return False
        if preset_key is ModelPresetKey.MULTIMODAL and not model.supports_vision:
            return False
        if ignore_current_binding:
            return True
        return True

    def _is_bindable_model(self, model: ModelProviderModelORM, preset_key: ModelPresetKey) -> bool:
        provider = self._repository.get_provider(model.provider_id)
        if provider is None:
            return False
        if preset_key is ModelPresetKey.MULTIMODAL and not model.supports_vision:
            return False
        return True

    def _pick_provider_test_model(self, provider: ModelProviderORM) -> ModelProviderModelORM | None:
        models = self._repository.list_provider_models(provider.id)
        for candidate in models:
            if candidate.enabled:
                return candidate
        return None

    def _provider_summary_result(self, provider: ModelProviderORM) -> ModelProviderSummaryResult:
        models = self._repository.list_provider_models(provider.id)
        has_key = bool(provider.encrypted_api_key)
        status = ModelProviderStatus.CONFIGURED
        if not provider.enabled:
            status = ModelProviderStatus.DISABLED
        elif not has_key:
            status = ModelProviderStatus.MISSING_KEY
        elif provider.last_error:
            status = ModelProviderStatus.FAILED

        return ModelProviderSummaryResult(
            id=provider.id,
            provider_type=ModelProviderType(provider.provider_type),
            name=provider.name,
            base_url=provider.base_url,
            enabled=provider.enabled,
            is_default=provider.is_default,
            status=status,
            key_status=ModelProviderKeyStatus.CONFIGURED if has_key else ModelProviderKeyStatus.MISSING,
            # This marker is deliberately non-reversible; it only communicates configured state to the UI.
            masked_key="********" if has_key else None,
            last_error=provider.last_error,
            model_count=len(models),
            updated_at=provider.updated_at,
        )

    def _provider_detail_result(self, provider: ModelProviderORM) -> ModelProviderDetailResult:
        summary = self._provider_summary_result(provider)
        models = [_provider_model_result(item) for item in self._repository.list_provider_models(provider.id)]
        return ModelProviderDetailResult(
            id=summary.id,
            provider_type=summary.provider_type,
            name=summary.name,
            base_url=summary.base_url,
            enabled=summary.enabled,
            is_default=summary.is_default,
            status=summary.status,
            key_status=summary.key_status,
            masked_key=summary.masked_key,
            last_error=summary.last_error,
            model_count=summary.model_count,
            models=models,
            updated_at=summary.updated_at,
        )

    def _preset_binding_result(self, binding: ModelPresetBindingORM) -> ModelPresetBindingResult:
        preset_key = ModelPresetKey(binding.preset_key)
        primary_model = self._optional_provider_model(binding.primary_model_id)
        fallback_model = self._optional_provider_model(binding.fallback_model_id)
        status = ModelPresetStatus.CONFIGURED
        validation_message: str | None = None

        if preset_key is not ModelPresetKey.GLOBAL_DEFAULT and primary_model is None:
            status = ModelPresetStatus.MISSING_PRIMARY
            validation_message = "未配置主模型"
        elif primary_model is not None and not self._is_usable_model(primary_model, preset_key, ignore_current_binding=True):
            status = ModelPresetStatus.INVALID
            validation_message = "主模型不满足当前类别要求"
        elif fallback_model is not None and not self._is_usable_model(fallback_model, preset_key, ignore_current_binding=True):
            status = ModelPresetStatus.INVALID
            validation_message = "Fallback 模型不满足当前类别要求"

        return ModelPresetBindingResult(
            preset_key=preset_key,
            title=PRESET_TITLES[preset_key],
            description=PRESET_DESCRIPTIONS[preset_key],
            primary_model=_provider_model_result(primary_model) if primary_model else None,
            fallback_model=_provider_model_result(fallback_model) if fallback_model else None,
            status=status,
            validation_message=validation_message,
        )

    def _crypto(self) -> ModelConfigCrypto:
        return ModelConfigCrypto(self._encryption_key)

    def _record_invocation(
        self,
        *,
        provider: ModelProviderORM,
        model_name: str,
        preset_key: ModelPresetKey | None,
        status: ModelInvocationStatus,
        token_usage: ModelTokenUsage,
        error_summary: str | None,
        request_id: str | None,
        trace_id: str | None,
        agent_run_id: str | None = None,
    ) -> ModelInvocationResult:
        invocation = ModelInvocationORM(
            provider_id=provider.id,
            preset_key=preset_key.value if preset_key else None,
            provider_type=provider.provider_type,
            provider_name=provider.name,
            model=model_name,
            status=status.value,
            prompt_tokens=token_usage.prompt_tokens,
            completion_tokens=token_usage.completion_tokens,
            total_tokens=token_usage.total_tokens,
            error_summary=error_summary,
            request_id=request_id,
            trace_id=trace_id,
            agent_run_id=agent_run_id,
            created_at=_utcnow(),
        )
        self._session.add(invocation)
        provider.updated_at = _utcnow()
        self._session.flush()
        return _invocation_result(invocation)

    def list_remote_models(
        self,
        provider_id: int,
        *,
        request_id: str | None = None,
    ) -> list[RemoteProviderModelResult]:
        provider = self._require_provider(provider_id)
        if not provider.encrypted_api_key:
            raise ModelConfigServiceError(
                "Model provider API key is missing",
                code="MODEL_PROVIDER_KEY_MISSING",
                safe_details={"provider_id": provider.id},
            )
        try:
            api_key = self._crypto().decrypt(provider.encrypted_api_key)
            return self._client.list_remote_models(
                base_url=provider.base_url,
                api_key=api_key,
                request_id=request_id,
            )
        except ModelConfigCryptoError as exc:
            raise ModelConfigServiceError(
                "Model provider API key cannot be decrypted",
                code="MODEL_PROVIDER_DECRYPT_FAILED",
                safe_details={"provider_id": provider.id},
            ) from exc

    def _record_failed_invocation_and_commit(
        self,
        *,
        provider: ModelProviderORM,
        model_name: str,
        preset_key: ModelPresetKey | None,
        error_summary: str,
        request_id: str | None,
        trace_id: str | None,
    ) -> ModelInvocationResult:
        invocation = self._record_invocation(
            provider=provider,
            model_name=model_name,
            preset_key=preset_key,
            status=ModelInvocationStatus.FAILED,
            token_usage=ModelTokenUsage(),
            error_summary=error_summary,
            request_id=request_id,
            trace_id=trace_id,
        )
        self._session.commit()
        return invocation


def _provider_model_result(model: ModelProviderModelORM) -> ModelProviderModelResult:
    return ModelProviderModelResult(
        id=model.id,
        provider_id=model.provider_id,
        model_name=model.model_name,
        enabled=model.enabled,
        supports_vision=model.supports_vision,
        is_global_default=model.is_global_default,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _candidate_model_list_endpoints(base_url: str | None) -> list[str]:
    normalized = (base_url or DEFAULT_OPENAI_BASE_URL).rstrip("/")
    if normalized.endswith("/v1"):
        return [f"{normalized}/models", f"{normalized[:-3]}/models"]
    return [f"{normalized}/models", f"{normalized}/v1/models"]


def _infer_supports_vision(model_id: str) -> bool:
    lowered = model_id.lower()
    return any(token in lowered for token in ("vision", "vl", "omni", "gpt-4o", "gemini", "multimodal"))


def _invocation_result(invocation: ModelInvocationORM) -> ModelInvocationResult:
    return ModelInvocationResult(
        id=invocation.id,
        provider_id=invocation.provider_id,
        provider_type=ModelProviderType(invocation.provider_type),
        provider_name=invocation.provider_name,
        model=invocation.model,
        preset_key=ModelPresetKey(invocation.preset_key) if invocation.preset_key else None,
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


def _extract_choice_content(parsed: dict[str, Any]) -> str | None:
    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                text_parts.append(item["text"])
        joined = "".join(text_parts).strip()
        return joined or None
    return None
