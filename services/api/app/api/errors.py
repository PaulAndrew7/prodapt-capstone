"""Standard error envelope (§5.4): code, message, request_id, retryable, safe details.

Internal exception text, SQL and provider payloads never reach the client; they go to
the server log keyed by the same request ID.
"""

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.domain.contracts import ApiError

log = logging.getLogger("clause.api")

REQUEST_ID_HEADER = "X-Request-ID"


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details


def not_found(what: str) -> AppError:
    return AppError(404, "not_found", f"{what} was not found.")


def not_implemented(feature: str) -> AppError:
    return AppError(501, "not_implemented", f"{feature} is not implemented yet.")


def request_id_of(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    return rid if isinstance(rid, str) else uuid.uuid4().hex


def _envelope(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    retryable: bool,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    body = ApiError(
        code=code,
        message=message,
        request_id=request_id_of(request),
        retryable=retryable,
        details=details,
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(exclude_none=True))


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        # Accept a caller's ID only if it is short and plain; otherwise mint one.
        ok = 0 < len(incoming) <= 64 and incoming.replace("-", "").isalnum()
        request.state.request_id = incoming if ok else uuid.uuid4().hex
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request.state.request_id
        return response


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return _envelope(
            request, exc.status_code, exc.code, exc.message, exc.retryable, exc.details
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": list(e.get("loc", ())), "msg": e.get("msg", ""), "type": e.get("type", "")}
            for e in exc.errors()
        ]
        return _envelope(
            request, 422, "validation_error", "The request is not valid.", False, details
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {401: "unauthenticated", 403: "forbidden", 404: "not_found", 405: "not_allowed"}
        return _envelope(
            request,
            exc.status_code,
            codes.get(exc.status_code, "http_error"),
            str(exc.detail),
            exc.status_code >= 500,
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("Unhandled error (request_id=%s)", request_id_of(request))
        return _envelope(
            request, 500, "internal_error", "Something went wrong on the server.", True
        )
