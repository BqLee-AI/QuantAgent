from __future__ import annotations

from typing import Any


class AppError(Exception):
    """应用层异常基类，统一携带 HTTP 与响应包裹所需元信息。"""

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
    """客户端输入在传输层合法，但业务上不符合要求。"""

    def __init__(self, message: str = "Bad Request", *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            status_code=400,
            error_code=40000,
            error_key="BAD_REQUEST",
            details=details,
        )


class NotFoundError(AppError):
    """请求的资源或路由不存在。"""

    def __init__(self, message: str = "Not Found", *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            status_code=404,
            error_code=40400,
            error_key="NOT_FOUND",
            details=details,
        )


class UnauthorizedError(AppError):
    """请求缺少有效登录态或鉴权失败。"""

    def __init__(self, message: str = "Unauthorized", *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            status_code=401,
            error_code=40100,
            error_key="UNAUTHORIZED",
            details=details,
        )


class ForbiddenError(AppError):
    """请求主体已识别，但无权执行当前动作。"""

    def __init__(self, message: str = "Forbidden", *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            status_code=403,
            error_code=40300,
            error_key="FORBIDDEN",
            details=details,
        )


class InternalError(AppError):
    """服务端内部异常，对外统一表现为通用 500 错误。"""

    def __init__(self, message: str = "Internal Server Error", *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            status_code=500,
            error_code=50000,
            error_key="INTERNAL_ERROR",
            details=details,
        )


class ServiceUnavailableError(AppError):
    """依赖暂时不可用，调用方可在稍后重试。"""

    def __init__(self, message: str = "Service Unavailable", *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            status_code=503,
            error_code=50300,
            error_key="SERVICE_UNAVAILABLE",
            details=details,
            retryable=True,
        )

