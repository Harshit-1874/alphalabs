"""
Global Error Handlers for FastAPI Application.

Purpose:
    Centralized error handling for all exceptions, providing consistent
    error responses and logging for debugging.

Usage:
    from error_handlers import register_error_handlers
    register_error_handlers(app)
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError as PydanticValidationError
import logging
from typing import Union

from exceptions import (
    AlphaLabException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    BusinessLogicError,
    ExternalAPIError,
    DatabaseError,
    InternalServerError,
    RateLimitError,
    TimeoutError
)

logger = logging.getLogger(__name__)


async def alphalab_exception_handler(request: Request, exc: AlphaLabException) -> JSONResponse:
    """
    Handle all custom AlphaLab exceptions.
    
    Args:
        request: The incoming request
        exc: The AlphaLab exception
        
    Returns:
        JSONResponse with error details
    """
    logger.error(
        f"AlphaLab Exception: {exc.code}",
        extra={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, PydanticValidationError]
) -> JSONResponse:
    """
    Handle FastAPI/Pydantic validation errors.
    
    Args:
        request: The incoming request
        exc: The validation exception
        
    Returns:
        JSONResponse with validation error details
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        "Validation error",
        extra={
            "errors": errors,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": errors}
            }
        }
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handle SQLAlchemy database errors.
    
    Args:
        request: The incoming request
        exc: The SQLAlchemy exception
        
    Returns:
        JSONResponse with error details
    """
    logger.error(
        f"Database error: {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )
    
    # Handle specific database errors
    if isinstance(exc, IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": "DATABASE_INTEGRITY_ERROR",
                    "message": "Database integrity constraint violated",
                    "details": {"error": "A record with this data already exists or violates constraints"}
                }
            }
        )
    
    # Generic database error
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "DATABASE_ERROR",
                "message": "A database error occurred",
                "details": {"error": "Please try again later"}
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all unhandled exceptions.
    
    Args:
        request: The incoming request
        exc: The exception
        
    Returns:
        JSONResponse with generic error message
    """
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": {"error": "Please try again later"}
            }
        }
    )


def register_error_handlers(app: FastAPI) -> None:
    """
    Register all error handlers with the FastAPI application.
    
    Args:
        app: The FastAPI application instance
    """
    # Custom AlphaLab exceptions
    app.add_exception_handler(AlphaLabException, alphalab_exception_handler)
    
    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)
    
    # Database errors
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    
    # Generic exception handler (catch-all)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Error handlers registered successfully")
