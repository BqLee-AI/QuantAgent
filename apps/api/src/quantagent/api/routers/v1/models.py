from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from quantagent.api.auth import SECRET_MANAGE_CAPABILITY, CurrentActor, require_capability, require_csrf
from quantagent.api.config.settings import Settings
from quantagent.api.db import get_db_session
from quantagent.api.http.errors import BadRequestError, ServiceUnavailableError
from quantagent.api.http.middleware import get_request_id
from quantagent.api.http.responses import ApiResponse
from quantagent.api.schemas.models import (
    ModelInvocationResponse,
    ModelPresetBindingResponse,
    ModelProviderDetailResponse,
    ModelProviderListResponse,
    ModelProviderModelResponse,
    RemoteProviderModelResponse,
    ModelProviderSummaryResponse,
    ModelTestConnectionResponse,
    ModelTokenUsageResponse,
    SaveModelProviderRequest,
    SaveProviderModelRequest,
    UpdateModelPresetRequest,
    UpdateModelProviderRequest,
    UpdateProviderModelRequest,
)
from quantagent.core.model_config import (
    CreateModelProviderInput,
    CreateProviderModelInput,
    ModelConfigService,
    ModelConfigServiceError,
    ModelInvocationResult,
    ModelPresetBindingResult,
    ModelPresetKey,
    ModelProviderDetailResult,
    ModelProviderListResult,
    ModelProviderModelResult,
    ModelProviderSummaryResult,
    ModelProviderType,
    RemoteProviderModelResult,
    UpdateModelPresetInput,
    UpdateModelProviderInput,
    UpdateProviderModelInput,
)


router = APIRouter(
    prefix="/models",
    tags=["models"],
    dependencies=[Depends(require_capability(SECRET_MANAGE_CAPABILITY))],
)


@router.get("/providers", response_model=ApiResponse[ModelProviderListResponse])
def list_model_providers(
    request: Request,
    session: Session = Depends(get_db_session),
) -> ApiResponse[ModelProviderListResponse]:
    return ApiResponse.success(_provider_list_response(_service(request, session).list_providers()))


@router.get("/providers/{provider_id}", response_model=ApiResponse[ModelProviderDetailResponse])
def get_model_provider(
    provider_id: int,
    request: Request,
    session: Session = Depends(get_db_session),
) -> ApiResponse[ModelProviderDetailResponse]:
    service = _service(request, session)
    try:
        return ApiResponse.success(_provider_detail_response(service.get_provider(provider_id)))
    except ModelConfigServiceError as exc:
        raise _api_error(exc) from exc


@router.post("/providers", response_model=ApiResponse[ModelProviderDetailResponse])
def create_model_provider(
    payload: SaveModelProviderRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_csrf),
) -> ApiResponse[ModelProviderDetailResponse]:
    service = _service(request, session)
    try:
        result = service.create_provider(
            CreateModelProviderInput(
                provider_type=ModelProviderType(payload.provider_type),
                name=payload.name,
                base_url=payload.base_url,
                api_key=payload.api_key,
                enabled=payload.enabled,
                is_default=payload.is_default,
            )
        )
    except ModelConfigServiceError as exc:
        raise _api_error(exc) from exc
    return ApiResponse.success(_provider_detail_response(result))


@router.put("/providers/{provider_id}", response_model=ApiResponse[ModelProviderDetailResponse])
def update_model_provider(
    provider_id: int,
    payload: UpdateModelProviderRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_csrf),
) -> ApiResponse[ModelProviderDetailResponse]:
    service = _service(request, session)
    try:
        result = service.update_provider(
            provider_id,
            UpdateModelProviderInput(
                provider_type=ModelProviderType(payload.provider_type),
                name=payload.name,
                base_url=payload.base_url,
                api_key=payload.api_key,
                enabled=payload.enabled,
            ),
        )
    except ModelConfigServiceError as exc:
        raise _api_error(exc) from exc
    return ApiResponse.success(_provider_detail_response(result))


@router.post("/providers/{provider_id}/actions/set-default", response_model=ApiResponse[ModelProviderDetailResponse])
def set_default_model_provider(
    provider_id: int,
    request: Request,
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_csrf),
) -> ApiResponse[ModelProviderDetailResponse]:
    service = _service(request, session)
    try:
        return ApiResponse.success(_provider_detail_response(service.set_default_provider(provider_id)))
    except ModelConfigServiceError as exc:
        raise _api_error(exc) from exc


@router.delete("/providers/{provider_id}", response_model=ApiResponse[dict[str, bool]])
def delete_model_provider(
    provider_id: int,
    request: Request,
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_csrf),
) -> ApiResponse[dict[str, bool]]:
    service = _service(request, session)
    try:
        service.delete_provider(provider_id)
    except ModelConfigServiceError as exc:
        raise _api_error(exc) from exc
    return ApiResponse.success({"deleted": True})


@router.post(
    "/providers/{provider_id}/actions/test-connection",
    response_model=ApiResponse[ModelTestConnectionResponse],
)
def test_model_provider_connection(
    provider_id: int,
    request: Request,
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_csrf),
) -> ApiResponse[ModelTestConnectionResponse]:
    service = _service(request, session)
    try:
        invocation = service.test_connection(provider_id, request_id=get_request_id(request))
        return ApiResponse.success(
            ModelTestConnectionResponse(success=True, invocation=_invocation_response(invocation))
        )
    except ModelConfigServiceError as exc:
        raise _api_error(exc) from exc


@router.get(
    "/providers/{provider_id}/remote-models",
    response_model=ApiResponse[list[RemoteProviderModelResponse]],
)
def list_remote_provider_models(
    provider_id: int,
    request: Request,
    session: Session = Depends(get_db_session),
) -> ApiResponse[list[RemoteProviderModelResponse]]:
    service = _service(request, session)
    try:
        models = service.list_remote_models(provider_id, request_id=get_request_id(request))
        return ApiResponse.success([_remote_provider_model_response(item) for item in models])
    except ModelConfigServiceError as exc:
        raise _api_error(exc) from exc


@router.post("/providers/{provider_id}/models", response_model=ApiResponse[ModelProviderModelResponse])
def create_provider_model(
    provider_id: int,
    payload: SaveProviderModelRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_csrf),
) -> ApiResponse[ModelProviderModelResponse]:
    service = _service(request, session)
    try:
        result = service.create_provider_model(
            provider_id,
            CreateProviderModelInput(
                model_name=payload.model_name,
                enabled=payload.enabled,
                supports_vision=payload.supports_vision,
                is_global_default=payload.is_global_default,
            ),
        )
    except ModelConfigServiceError as exc:
        raise _api_error(exc) from exc
    return ApiResponse.success(_provider_model_response(result))


@router.put("/providers/{provider_id}/models/{model_id}", response_model=ApiResponse[ModelProviderModelResponse])
def update_provider_model(
    provider_id: int,
    model_id: int,
    payload: UpdateProviderModelRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_csrf),
) -> ApiResponse[ModelProviderModelResponse]:
    service = _service(request, session)
    try:
        result = service.update_provider_model(
            provider_id,
            model_id,
            UpdateProviderModelInput(
                model_name=payload.model_name,
                enabled=payload.enabled,
                supports_vision=payload.supports_vision,
                is_global_default=payload.is_global_default,
            ),
        )
    except ModelConfigServiceError as exc:
        raise _api_error(exc) from exc
    return ApiResponse.success(_provider_model_response(result))


@router.delete("/providers/{provider_id}/models/{model_id}", response_model=ApiResponse[dict[str, bool]])
def delete_provider_model(
    provider_id: int,
    model_id: int,
    request: Request,
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_csrf),
) -> ApiResponse[dict[str, bool]]:
    service = _service(request, session)
    try:
        service.delete_provider_model(provider_id, model_id)
    except ModelConfigServiceError as exc:
        raise _api_error(exc) from exc
    return ApiResponse.success({"deleted": True})


@router.get("/presets", response_model=ApiResponse[list[ModelPresetBindingResponse]])
def list_model_presets(
    request: Request,
    session: Session = Depends(get_db_session),
) -> ApiResponse[list[ModelPresetBindingResponse]]:
    service = _service(request, session)
    try:
        presets = service.list_presets()
    except ModelConfigServiceError as exc:
        raise _api_error(exc) from exc
    return ApiResponse.success([_preset_response(item) for item in presets])


@router.put("/presets/{preset_key}", response_model=ApiResponse[ModelPresetBindingResponse])
def update_model_preset(
    preset_key: str,
    payload: UpdateModelPresetRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_csrf),
) -> ApiResponse[ModelPresetBindingResponse]:
    service = _service(request, session)
    try:
        result = service.update_preset(
            ModelPresetKey(preset_key),
            UpdateModelPresetInput(
                primary_model_id=payload.primary_model_id,
                fallback_model_id=payload.fallback_model_id,
            ),
        )
    except ValueError as exc:
        raise BadRequestError("Preset key is invalid", details={"code": "MODEL_PRESET_KEY_INVALID"}) from exc
    except ModelConfigServiceError as exc:
        raise _api_error(exc) from exc
    return ApiResponse.success(_preset_response(result))


@router.get("/invocations", response_model=ApiResponse[list[ModelInvocationResponse]])
def list_model_invocations(
    request: Request,
    session: Session = Depends(get_db_session),
    limit: int = 20,
    provider_id: int | None = None,
    preset_key: str | None = None,
) -> ApiResponse[list[ModelInvocationResponse]]:
    service = _service(request, session)
    bounded_limit = max(1, min(limit, 100))
    try:
        invocations = service.list_invocations(
            limit=bounded_limit,
            provider_id=provider_id,
            preset_key=ModelPresetKey(preset_key) if preset_key else None,
        )
    except ValueError as exc:
        raise BadRequestError("Preset key is invalid", details={"code": "MODEL_PRESET_KEY_INVALID"}) from exc
    except ModelConfigServiceError as exc:
        raise _api_error(exc) from exc
    return ApiResponse.success([_invocation_response(item) for item in invocations])


def _service(request: Request, session: Session) -> ModelConfigService:
    settings: Settings = request.app.state.settings
    client = getattr(request.app.state, "model_call_client", None)
    return ModelConfigService(
        session,
        encryption_key=settings.MODEL_CONFIG_ENCRYPTION_KEY,
        client=client,
    )


def _provider_list_response(result: ModelProviderListResult) -> ModelProviderListResponse:
    return ModelProviderListResponse(
        default_provider_id=result.default_provider_id,
        providers=[_provider_summary_response(item) for item in result.providers],
    )


def _provider_summary_response(result: ModelProviderSummaryResult) -> ModelProviderSummaryResponse:
    return ModelProviderSummaryResponse(
        id=result.id,
        provider_type=result.provider_type.value,
        name=result.name,
        base_url=result.base_url,
        enabled=result.enabled,
        is_default=result.is_default,
        status=result.status.value,
        key_status=result.key_status.value,
        masked_key=result.masked_key,
        last_error=result.last_error,
        model_count=result.model_count,
        updated_at=result.updated_at,
    )


def _provider_detail_response(result: ModelProviderDetailResult) -> ModelProviderDetailResponse:
    return ModelProviderDetailResponse(
        **_provider_summary_response(
            ModelProviderSummaryResult(
                id=result.id,
                provider_type=result.provider_type,
                name=result.name,
                base_url=result.base_url,
                enabled=result.enabled,
                is_default=result.is_default,
                status=result.status,
                key_status=result.key_status,
                masked_key=result.masked_key,
                last_error=result.last_error,
                model_count=result.model_count,
                updated_at=result.updated_at,
            )
        ).model_dump(),
        models=[_provider_model_response(item) for item in result.models],
    )


def _provider_model_response(result: ModelProviderModelResult) -> ModelProviderModelResponse:
    return ModelProviderModelResponse(
        id=result.id,
        provider_id=result.provider_id,
        model_name=result.model_name,
        enabled=result.enabled,
        supports_vision=result.supports_vision,
        is_global_default=result.is_global_default,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


def _remote_provider_model_response(result: RemoteProviderModelResult) -> RemoteProviderModelResponse:
    return RemoteProviderModelResponse(
        id=result.id,
        owned_by=result.owned_by,
        supports_vision=result.supports_vision,
    )


def _preset_response(result: ModelPresetBindingResult) -> ModelPresetBindingResponse:
    return ModelPresetBindingResponse(
        preset_key=result.preset_key.value,
        title=result.title,
        description=result.description,
        primary_model=_provider_model_response(result.primary_model) if result.primary_model else None,
        fallback_model=_provider_model_response(result.fallback_model) if result.fallback_model else None,
        status=result.status.value,
        validation_message=result.validation_message,
    )


def _invocation_response(result: ModelInvocationResult) -> ModelInvocationResponse:
    return ModelInvocationResponse(
        id=result.id,
        provider_id=result.provider_id,
        provider_type=result.provider_type.value,
        provider_name=result.provider_name,
        model=result.model,
        preset_key=result.preset_key.value if result.preset_key else None,
        status=result.status.value,
        token_usage=ModelTokenUsageResponse(
            prompt_tokens=result.token_usage.prompt_tokens,
            completion_tokens=result.token_usage.completion_tokens,
            total_tokens=result.token_usage.total_tokens,
        ),
        error_summary=result.error_summary,
        request_id=result.request_id,
        trace_id=result.trace_id,
        agent_run_id=result.agent_run_id,
        created_at=result.created_at,
    )


def _api_error(error: ModelConfigServiceError) -> BadRequestError | ServiceUnavailableError:
    # Core exposes only safe details; the route keeps provider payloads and secret material out of HTTP errors.
    details = {"code": error.code, **error.safe_details}
    if error.retryable or error.code in {"MODEL_CONFIG_ENCRYPTION_UNAVAILABLE", "MODEL_PROVIDER_DECRYPT_FAILED"}:
        return ServiceUnavailableError(error.message, details=details)
    return BadRequestError(error.message, details=details)
