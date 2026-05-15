from __future__ import annotations

from typing import Any


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        error_code: int,
        error_key: str,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.error_key = error_key
        self.details = details
        self.retryable = retryable


class BadRequestError(AppError):
    def __init__(self, message: str = "Bad Request", *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            status_code=400,
            error_code=40000,
            error_key="BAD_REQUEST",
            details=details,
        )


class NotFoundError(AppError):
    def __init__(self, message: str = "Not Found", *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            status_code=404,
            error_code=40400,
            error_key="NOT_FOUND",
            details=details,
        )


class InternalError(AppError):
    def __init__(self, message: str = "Internal Server Error", *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            status_code=500,
            error_code=50000,
            error_key="INTERNAL_ERROR",
            details=details,
        )
