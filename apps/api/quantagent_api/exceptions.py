from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from quantagent_api.errors import AppError, InternalError
from quantagent_api.middleware import get_request_id
from quantagent_api.responses import ApiErrorDetail, ApiResponse


logger = logging.getLogger("quantagent_api")


def _error_payload(
    *,
    status_code: int,
    response_code: int,
    error_key: str,
    message: str,
    request_id: str,
    details: dict[str, Any] | None = None,
    retryable: bool = False,
) -> JSONResponse:
    body = ApiResponse(
        code=response_code,
        data=None,
        msg=message,
        error=ApiErrorDetail(
            code=error_key,
            request_id=request_id,
            trace_id=None,
            details=details or {},
            retryable=retryable,
        ),
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = get_request_id(request)
        fields = []
        for error in exc.errors():
            fields.append(
                {
                    "loc": [str(part) for part in error.get("loc", ())],
                    "msg": error.get("msg", "Invalid input"),
                    "type": error.get("type", "value_error"),
                }
            )
        return _error_payload(
            status_code=422,
            response_code=42200,
            error_key="VALIDATION_ERROR",
            message="Validation Error",
            request_id=request_id,
            details={"fields": fields},
        )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = get_request_id(request)
        return _error_payload(
            status_code=exc.status_code,
            response_code=exc.error_code,
            error_key=exc.error_key,
            message=exc.message,
            request_id=request_id,
            details=exc.details,
            retryable=exc.retryable,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = get_request_id(request)
        status_code = exc.status_code
        response_code = status_code * 100
        if status_code == 400:
            error_key = "BAD_REQUEST"
            message = "Bad Request"
        elif status_code == 404:
            error_key = "NOT_FOUND"
            message = "Not Found"
        elif status_code == 405:
            error_key = "METHOD_NOT_ALLOWED"
            message = "Method Not Allowed"
        else:
            error_key = "HTTP_ERROR"
            if status_code >= 500:
                message = "Internal Server Error"
            else:
                message = exc.detail if isinstance(exc.detail, str) else str(status_code)
        return _error_payload(
            status_code=status_code,
            response_code=response_code,
            error_key=error_key,
            message=message,
            request_id=request_id,
            details={},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = get_request_id(request)
        logger.exception("Unhandled exception", extra={"request_id": request_id})
        error = InternalError()
        return _error_payload(
            status_code=error.status_code,
            response_code=error.error_code,
            error_key=error.error_key,
            message=error.message,
            request_id=request_id,
            details={},
        )
