"""
Centralized FastAPI exception handlers enforcing the uniform error response contract:
{ "error": { "code": "...", "message": "...", "request_id": "..." } }
"""
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.errors import (
    AuthenticationError,
    DomainError,
    DuplicateFileError,
    EntityNotFoundError,
    ForbiddenError,
    InvalidFileError,
    LLMUnavailableError,
    ValidationError as DomainValidationError,
)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        status_code = 400
        if isinstance(exc, EntityNotFoundError):
            status_code = 404
        elif isinstance(exc, ForbiddenError):
            status_code = 403
        elif isinstance(exc, AuthenticationError):
            status_code = 401
        elif isinstance(exc, DuplicateFileError):
            status_code = 409
        elif isinstance(exc, InvalidFileError):
            status_code = 400
        elif isinstance(exc, LLMUnavailableError):
            status_code = 502
        elif isinstance(exc, DomainValidationError):
            status_code = 422

        request_id = str(uuid4())
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request_id,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        request_id = str(uuid4())
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": str(exc),
                    "request_id": request_id,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = str(uuid4())
        code_map = {
            400: "bad_request",
            401: "unauthenticated",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            422: "validation_error",
            429: "rate_limited",
            500: "internal_error",
            502: "llm_unavailable",
        }
        code = code_map.get(exc.status_code, "error")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": exc.detail,
                    "request_id": request_id,
                }
            },
        )

