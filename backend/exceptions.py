"""
Custom Exception Classes for AlphaLab Backend.

Purpose:
    Define domain-specific exceptions for better error handling and
    more informative error messages throughout the application.

Usage:
    from exceptions import ValidationError, ExternalAPIError
    raise ValidationError("Invalid date range", details={"start": "2024-01-01"})
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class AlphaLabException(Exception):
    """Base exception class for all AlphaLab custom exceptions."""
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code or self.__class__.__name__.upper()
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        }


# Validation Exceptions (400)
class ValidationError(AlphaLabException):
    """Raised when input validation fails."""
    status_code = status.HTTP_400_BAD_REQUEST


class InvalidDateRangeError(ValidationError):
    """Raised when date range is invalid."""
    def __init__(self, start_date: str, end_date: str):
        super().__init__(
            message="End date must be after start date",
            code="INVALID_DATE_RANGE",
            details={"start_date": start_date, "end_date": end_date}
        )


class InvalidParameterError(ValidationError):
    """Raised when a parameter value is invalid."""
    def __init__(self, parameter: str, value: Any, reason: str):
        super().__init__(
            message=f"Invalid value for parameter '{parameter}': {reason}",
            code="INVALID_PARAMETER",
            details={"parameter": parameter, "value": str(value), "reason": reason}
        )


class MissingRequiredFieldError(ValidationError):
    """Raised when a required field is missing."""
    def __init__(self, field: str):
        super().__init__(
            message=f"Required field '{field}' is missing",
            code="MISSING_REQUIRED_FIELD",
            details={"field": field}
        )


# Authentication/Authorization Exceptions (401, 403)
class AuthenticationError(AlphaLabException):
    """Raised when authentication fails."""
    status_code = status.HTTP_401_UNAUTHORIZED


class AuthorizationError(AlphaLabException):
    """Raised when user doesn't have permission."""
    status_code = status.HTTP_403_FORBIDDEN


class ResourceOwnershipError(AuthorizationError):
    """Raised when user doesn't own the resource."""
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"You don't have permission to access this {resource_type}",
            code="RESOURCE_OWNERSHIP_ERROR",
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


# Not Found Exceptions (404)
class NotFoundError(AlphaLabException):
    """Raised when a resource is not found."""
    status_code = status.HTTP_404_NOT_FOUND


class SessionNotFoundError(NotFoundError):
    """Raised when a test session is not found."""
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Test session not found",
            code="SESSION_NOT_FOUND",
            details={"session_id": session_id}
        )


class AgentNotFoundError(NotFoundError):
    """Raised when an agent is not found."""
    def __init__(self, agent_id: str):
        super().__init__(
            message=f"Agent not found",
            code="AGENT_NOT_FOUND",
            details={"agent_id": agent_id}
        )


class ResultNotFoundError(NotFoundError):
    """Raised when a result is not found."""
    def __init__(self, result_id: str):
        super().__init__(
            message=f"Result not found",
            code="RESULT_NOT_FOUND",
            details={"result_id": result_id}
        )


# Business Logic Exceptions (422)
class BusinessLogicError(AlphaLabException):
    """Raised when business logic validation fails."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class AgentNotEligibleError(BusinessLogicError):
    """Raised when agent doesn't meet requirements for an operation."""
    def __init__(self, agent_id: str, reason: str):
        super().__init__(
            message=f"Agent is not eligible: {reason}",
            code="AGENT_NOT_ELIGIBLE",
            details={"agent_id": agent_id, "reason": reason}
        )


class SessionAlreadyActiveError(BusinessLogicError):
    """Raised when trying to start a session that's already active."""
    def __init__(self, session_id: str):
        super().__init__(
            message="Session is already active",
            code="SESSION_ALREADY_ACTIVE",
            details={"session_id": session_id}
        )


class InvalidSessionStateError(BusinessLogicError):
    """Raised when session is in wrong state for operation."""
    def __init__(self, session_id: str, current_state: str, required_state: str):
        super().__init__(
            message=f"Session must be in '{required_state}' state, currently '{current_state}'",
            code="INVALID_SESSION_STATE",
            details={
                "session_id": session_id,
                "current_state": current_state,
                "required_state": required_state
            }
        )


# External API Exceptions (502, 503)
class ExternalAPIError(AlphaLabException):
    """Raised when external API call fails."""
    status_code = status.HTTP_502_BAD_GATEWAY


class OpenRouterAPIError(ExternalAPIError):
    """Raised when OpenRouter API call fails."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(
            message=f"OpenRouter API error: {message}",
            code="OPENROUTER_API_ERROR",
            details={"api_status_code": status_code}
        )


class MarketDataAPIError(ExternalAPIError):
    """Raised when market data API call fails."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(
            message=f"Market data API error: {message}",
            code="MARKET_DATA_API_ERROR",
            details={"api_status_code": status_code}
        )


class CircuitBreakerOpenError(ExternalAPIError):
    """Raised when circuit breaker is open."""
    def __init__(self, service: str):
        super().__init__(
            message=f"Service '{service}' is temporarily unavailable (circuit breaker open)",
            code="CIRCUIT_BREAKER_OPEN",
            details={"service": service}
        )


# Database Exceptions (500)
class DatabaseError(AlphaLabException):
    """Raised when database operation fails."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    def __init__(self, message: str):
        super().__init__(
            message=f"Database connection error: {message}",
            code="DATABASE_CONNECTION_ERROR"
        )


# Internal Server Exceptions (500)
class InternalServerError(AlphaLabException):
    """Raised for unexpected internal errors."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class ConfigurationError(InternalServerError):
    """Raised when configuration is invalid or missing."""
    def __init__(self, message: str):
        super().__init__(
            message=f"Configuration error: {message}",
            code="CONFIGURATION_ERROR"
        )


# Rate Limiting Exceptions (429)
class RateLimitError(AlphaLabException):
    """Raised when rate limit is exceeded."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    
    def __init__(self, resource: str, limit: int = None, window: str = None, reset_at: int = None):
        """
        Initialize rate limit error.
        
        Args:
            resource: Resource that was rate limited
            limit: Rate limit value
            window: Time window for the limit
            reset_at: Unix timestamp (milliseconds) when rate limit resets
        """
        message = f"Rate limit exceeded for {resource}"
        if reset_at:
            import datetime
            reset_time = datetime.datetime.fromtimestamp(reset_at / 1000)
            message += f". Resets at {reset_time.isoformat()}"
        
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            details={
                "resource": resource,
                "limit": limit,
                "window": window,
                "reset_at": reset_at
            }
        )
        self.reset_at = reset_at  # Store for easy access


# Timeout Exceptions (504)
class TimeoutError(AlphaLabException):
    """Raised when operation times out."""
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    
    def __init__(self, operation: str, timeout_seconds: int):
        super().__init__(
            message=f"Operation '{operation}' timed out after {timeout_seconds} seconds",
            code="OPERATION_TIMEOUT",
            details={"operation": operation, "timeout_seconds": timeout_seconds}
        )


def alphalab_exception_to_http_exception(exc: AlphaLabException) -> HTTPException:
    """
    Convert AlphaLab exception to FastAPI HTTPException.
    
    Args:
        exc: AlphaLab exception instance
        
    Returns:
        HTTPException with appropriate status code and detail
    """
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.to_dict()
    )
