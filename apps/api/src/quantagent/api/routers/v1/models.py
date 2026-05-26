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
    ModelConfigResponse,
    ModelInvocationResponse,
    ModelTestConnectionResponse,
    ModelTokenUsageResponse,
    SaveModelConfigRequest,
)
from quantagent.core.model_config import (
    ModelConfigProviderType,
    ModelConfigResult,
    ModelConfigService,
    ModelConfigServiceError,
    ModelInvocationResult,
    SaveModelConfigInput,
)


router = APIRouter(
    prefix="/models",
    tags=["models"],
    dependencies=[Depends(require_capability(SECRET_MANAGE_CAPABILITY))],
)


@router.get("/config", response_model=ApiResponse[ModelConfigResponse])
def get_model_config(
    request: Request,
    session: Session = Depends(get_db_session),
) -> ApiResponse[ModelConfigResponse]:
    service = _service(request, session)
    return ApiResponse.success(_config_response(service.get_config()))


@router.put("/config", response_model=ApiResponse[ModelConfigResponse])
def save_model_config(
    payload: SaveModelConfigRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_csrf),
) -> ApiResponse[ModelConfigResponse]:
    service = _service(request, session)
    try:
        result = service.save_config(
            SaveModelConfigInput(
                provider_type=ModelConfigProviderType(payload.provider_type),
                name=payload.name,
                base_url=payload.base_url,
                model=payload.model,
                api_key=payload.api_key,
                enabled=payload.enabled,
            )
        )
    except ModelConfigServiceError as exc:
        raise _api_error(exc) from exc
    return ApiResponse.success(_config_response(result))


@router.post("/actions/test-connection", response_model=ApiResponse[ModelTestConnectionResponse])
def test_model_connection(
    request: Request,
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_csrf),
) -> ApiResponse[ModelTestConnectionResponse]:
    service = _service(request, session)
    try:
        invocation = service.test_connection(request_id=get_request_id(request))
        return ApiResponse.success(
            ModelTestConnectionResponse(success=True, invocation=_invocation_response(invocation))
        )
    except ModelConfigServiceError as exc:
        raise _api_error(exc) from exc


@router.get("/invocations", response_model=ApiResponse[list[ModelInvocationResponse]])
def list_model_invocations(
    request: Request,
    session: Session = Depends(get_db_session),
    limit: int = 20,
) -> ApiResponse[list[ModelInvocationResponse]]:
    service = _service(request, session)
    bounded_limit = max(1, min(limit, 100))
    return ApiResponse.success([_invocation_response(item) for item in service.list_invocations(limit=bounded_limit)])


def _service(request: Request, session: Session) -> ModelConfigService:
    settings: Settings = request.app.state.settings
    client = getattr(request.app.state, "model_call_client", None)
    return ModelConfigService(
        session,
        encryption_key=settings.MODEL_CONFIG_ENCRYPTION_KEY,
        client=client,
    )


def _config_response(result: ModelConfigResult) -> ModelConfigResponse:
    return ModelConfigResponse(
        provider_type=result.provider_type.value,
        name=result.name,
        base_url=result.base_url,
        model=result.model,
        enabled=result.enabled,
        status=result.status.value,
        key_status=result.key_status.value,
        masked_key=result.masked_key,
        last_error=result.last_error,
        updated_at=result.updated_at,
    )


def _invocation_response(result: ModelInvocationResult) -> ModelInvocationResponse:
    return ModelInvocationResponse(
        id=result.id,
        provider_type=result.provider_type.value,
        provider_name=result.provider_name,
        model=result.model,
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
    if error.retryable or error.code in {"MODEL_CONFIG_ENCRYPTION_UNAVAILABLE", "MODEL_CONFIG_DECRYPT_FAILED"}:
        return ServiceUnavailableError(error.message, details=details)
    return BadRequestError(error.message, details=details)
