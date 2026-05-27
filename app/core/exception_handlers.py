# app/core/exception_handlers.py

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation failed.",
            "errors": exc.errors()
        },
    )


def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail or "An error occurred."
        },
    )


def server_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on our server. Please try again later."}
    )