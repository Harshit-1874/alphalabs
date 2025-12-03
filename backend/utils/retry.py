"""
Retry Utilities with Exponential Backoff.

Purpose:
    Provide retry logic for external API calls and other operations
    that may fail temporarily.

Usage:
    from utils.retry import retry_with_backoff, CircuitBreaker
"""
import asyncio
import time
import logging
from typing import Callable, Any, Optional, Type, Tuple
from functools import wraps

from config import settings
from exceptions import CircuitBreakerOpenError, TimeoutError as AlphaLabTimeoutError

logger = logging.getLogger(__name__)


async def retry_with_backoff(
    func: Callable,
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    operation_name: Optional[str] = None
) -> Any:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts (default: from settings)
        base_delay: Initial delay in seconds (default: from settings)
        max_delay: Maximum delay in seconds (default: from settings)
        exceptions: Tuple of exception types to catch and retry
        operation_name: Name of operation for logging
        
    Returns:
        Result of the function call
        
    Raises:
        The last exception if all retries fail
    """
    max_retries = max_retries or settings.MAX_RETRIES
    base_delay = base_delay or settings.RETRY_BASE_DELAY
    max_delay = max_delay or settings.RETRY_MAX_DELAY
    operation_name = operation_name or func.__name__
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            
            if attempt == max_retries - 1:
                logger.error(
                    f"Operation '{operation_name}' failed after {max_retries} attempts",
                    extra={"operation": operation_name, "error": str(e)}
                )
                raise
            
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(
                f"Operation '{operation_name}' failed (attempt {attempt + 1}/{max_retries}), "
                f"retrying in {delay:.2f}s",
                extra={
                    "operation": operation_name,
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "delay": delay,
                    "error": str(e)
                }
            )
            await asyncio.sleep(delay)
    
    raise last_exception


def with_retry(
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator to add retry logic to async functions.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exception types to catch and retry
        
    Usage:
        @with_retry(max_retries=3, exceptions=(APIError,))
        async def fetch_data():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async def call_func():
                return await func(*args, **kwargs)
            
            return await retry_with_backoff(
                call_func,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                exceptions=exceptions,
                operation_name=func.__name__
            )
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for external service calls.
    
    States:
        - CLOSED: Normal operation, requests pass through
        - OPEN: Too many failures, requests fail immediately
        - HALF_OPEN: Testing if service recovered
    
    Usage:
        breaker = CircuitBreaker(service_name="openrouter")
        result = await breaker.call(make_api_request)
    """
    
    def __init__(
        self,
        service_name: str,
        failure_threshold: Optional[int] = None,
        timeout: Optional[int] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            service_name: Name of the service for logging
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before trying half-open state
        """
        self.service_name = service_name
        self.failure_threshold = failure_threshold or settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        self.timeout = timeout or settings.CIRCUIT_BREAKER_TIMEOUT
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open
        
        logger.info(
            f"Circuit breaker initialized for '{service_name}'",
            extra={
                "service": service_name,
                "failure_threshold": self.failure_threshold,
                "timeout": self.timeout
            }
        )
    
    async def call(self, func: Callable) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            
        Returns:
            Result of the function call
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Any exception from the function
        """
        # Check if circuit should transition from open to half-open
        if self.state == "open":
            if self.last_failure_time and time.time() - self.last_failure_time > self.timeout:
                logger.info(
                    f"Circuit breaker for '{self.service_name}' transitioning to half-open",
                    extra={"service": self.service_name}
                )
                self.state = "half_open"
            else:
                logger.warning(
                    f"Circuit breaker for '{self.service_name}' is open, rejecting request",
                    extra={"service": self.service_name}
                )
                raise CircuitBreakerOpenError(self.service_name)
        
        try:
            result = await func()
            
            # Success - reset if in half-open state
            if self.state == "half_open":
                logger.info(
                    f"Circuit breaker for '{self.service_name}' closing after successful call",
                    extra={"service": self.service_name}
                )
                self.state = "closed"
                self.failure_count = 0
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            logger.error(
                f"Circuit breaker for '{self.service_name}' recorded failure "
                f"({self.failure_count}/{self.failure_threshold})",
                extra={
                    "service": self.service_name,
                    "failure_count": self.failure_count,
                    "error": str(e)
                }
            )
            
            # Open circuit if threshold reached
            if self.failure_count >= self.failure_threshold:
                logger.error(
                    f"Circuit breaker for '{self.service_name}' opening due to failures",
                    extra={"service": self.service_name}
                )
                self.state = "open"
            
            raise
    
    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        logger.info(
            f"Circuit breaker for '{self.service_name}' manually reset",
            extra={"service": self.service_name}
        )
        self.state = "closed"
        self.failure_count = 0
        self.last_failure_time = None


async def with_timeout(func: Callable, timeout_seconds: int, operation_name: str) -> Any:
    """
    Execute async function with timeout.
    
    Args:
        func: Async function to execute
        timeout_seconds: Timeout in seconds
        operation_name: Name of operation for error message
        
    Returns:
        Result of the function call
        
    Raises:
        AlphaLabTimeoutError: If operation times out
    """
    try:
        return await asyncio.wait_for(func(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.error(
            f"Operation '{operation_name}' timed out after {timeout_seconds}s",
            extra={"operation": operation_name, "timeout": timeout_seconds}
        )
        raise AlphaLabTimeoutError(operation_name, timeout_seconds)
