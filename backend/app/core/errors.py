"""Consistent error envelope: {"error": {code, message, details, trace_id}}."""
from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details


def NotFound(what: str) -> AppError:  # noqa: N802
    return AppError(404, "not_found", f"{what} not found")


def Forbidden(msg: str = "You do not have permission to perform this action") -> AppError:  # noqa: N802
    return AppError(403, "forbidden", msg)


def Conflict(msg: str, details: Any = None) -> AppError:  # noqa: N802
    return AppError(409, "conflict", msg, details)


def BadRequest(msg: str, details: Any = None) -> AppError:  # noqa: N802
    return AppError(400, "bad_request", msg, details)


def _envelope(request: Request, status: int, code: str, message: str, details: Any = None) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", None)
    return JSONResponse(status_code=status, content={"error": {
        "code": code, "message": message, "details": details, "trace_id": trace_id}},
        headers={"X-Trace-Id": trace_id or ""})


def install_handlers(app) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return _envelope(request, exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        details = [{"loc": list(e.get("loc", [])), "msg": e.get("msg")} for e in exc.errors()]
        return _envelope(request, 422, "validation_error", "Request validation failed", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        code = {401: "unauthenticated", 403: "forbidden", 404: "not_found", 405: "method_not_allowed",
                429: "rate_limited"}.get(exc.status_code, "http_error")
        return _envelope(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        import logging
        logging.getLogger("tracetest").exception("Unhandled error", extra={"trace_id": getattr(request.state, "trace_id", None)})
        return _envelope(request, 500, "internal_error", "An unexpected error occurred")
