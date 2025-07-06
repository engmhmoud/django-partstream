"""
Exception classes for django-partstream package.
Enhanced error handling for production environments.
"""

import logging
from typing import Dict, Any, Optional
from rest_framework.exceptions import APIException
from django.utils import timezone

logger = logging.getLogger("django_partstream.exceptions")


class ProgressiveDeliveryError(APIException):
    """Base exception for progressive delivery errors."""

    status_code = 500
    default_detail = "Progressive delivery error occurred"
    default_code = "progressive_delivery_error"

    def __init__(
        self, detail=None, code=None, context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize with optional context for better debugging.

        Args:
            detail: Error message
            code: Error code
            context: Additional context for debugging
        """
        super().__init__(detail, code)
        self.context = context or {}
        self.timestamp = timezone.now().isoformat()

        # Log the error with context
        logger.error(
            f"ProgressiveDeliveryError: {detail or self.default_detail}",
            extra={
                "error_code": code or self.default_code,
                "context": self.context,
                "timestamp": self.timestamp,
            },
        )


class InvalidCursorError(ProgressiveDeliveryError):
    """Exception raised when cursor is invalid or tampered."""

    status_code = 400
    default_detail = "Invalid cursor provided"
    default_code = "invalid_cursor"


class CursorExpiredError(ProgressiveDeliveryError):
    """Exception raised when cursor has expired."""

    status_code = 400
    default_detail = "Cursor has expired"
    default_code = "cursor_expired"


class RateLimitExceededError(ProgressiveDeliveryError):
    """Exception raised when rate limit is exceeded."""

    status_code = 429
    default_detail = "Rate limit exceeded"
    default_code = "rate_limit_exceeded"

    def __init__(self, detail=None, retry_after: int = 60, **kwargs):
        super().__init__(detail, **kwargs)
        self.retry_after = retry_after


class ValidationError(ProgressiveDeliveryError):
    """Exception raised for validation errors."""

    status_code = 400
    default_detail = "Validation error"
    default_code = "validation_error"


class AuthenticationError(ProgressiveDeliveryError):
    """Exception raised for authentication errors."""

    status_code = 401
    default_detail = "Authentication required"
    default_code = "authentication_required"


class PermissionError(ProgressiveDeliveryError):
    """Exception raised for permission errors."""

    status_code = 403
    default_detail = "Permission denied"
    default_code = "permission_denied"


class PartProcessingError(ProgressiveDeliveryError):
    """Exception raised when a part fails to process."""

    status_code = 500
    default_detail = "Part processing failed"
    default_code = "part_processing_error"

    def __init__(self, part_name: str, detail=None, **kwargs):
        super().__init__(detail, **kwargs)
        self.part_name = part_name
        self.context["part_name"] = part_name


class TimeoutError(ProgressiveDeliveryError):
    """Exception raised when operation times out."""

    status_code = 504
    default_detail = "Operation timed out"
    default_code = "timeout_error"

    def __init__(self, operation: str, timeout: int, detail=None, **kwargs):
        super().__init__(detail, **kwargs)
        self.operation = operation
        self.timeout = timeout
        self.context.update({"operation": operation, "timeout": timeout})


class CacheError(ProgressiveDeliveryError):
    """Exception raised for cache-related errors."""

    status_code = 500
    default_detail = "Cache error"
    default_code = "cache_error"


class ConfigurationError(ProgressiveDeliveryError):
    """Exception raised for configuration errors."""

    status_code = 500
    default_detail = "Configuration error"
    default_code = "configuration_error"


# Error handler functions for production
def handle_part_error(
    part_name: str, error: Exception, fallback_data: Any = None
) -> Dict[str, Any]:
    """
    Handle errors in part processing with graceful degradation.

    Args:
        part_name: Name of the part that failed
        error: The exception that occurred
        fallback_data: Data to return if available

    Returns:
        Dictionary with error information or fallback data
    """
    error_info = {
        "error": f"Failed to load {part_name}",
        "message": str(error),
        "timestamp": timezone.now().isoformat(),
        "part_name": part_name,
    }

    # Log the error
    logger.error(
        f"Part processing error for '{part_name}': {error}",
        extra={
            "part_name": part_name,
            "error_type": error.__class__.__name__,
            "error_message": str(error),
        },
        exc_info=True,
    )

    # Return fallback data if available
    if fallback_data is not None:
        error_info["fallback_used"] = "true"
        error_info["data"] = fallback_data

    return error_info


def handle_cursor_error(cursor: str, error: Exception) -> Dict[str, Any]:
    """
    Handle cursor-related errors with appropriate logging.

    Args:
        cursor: The problematic cursor
        error: The exception that occurred

    Returns:
        Dictionary with error information
    """
    # Truncate cursor for logging (security)
    cursor_sample = cursor[:20] + "..." if len(cursor) > 20 else cursor

    logger.warning(
        f"Cursor error: {error}",
        extra={
            "cursor_sample": cursor_sample,
            "cursor_length": len(cursor),
            "error_type": error.__class__.__name__,
        },
    )

    return {
        "error": "Invalid or expired cursor",
        "message": "Please refresh the page and try again",
        "timestamp": timezone.now().isoformat(),
        "code": "cursor_error",
    }


def handle_validation_error(
    request_data: Dict[str, Any], error: Exception
) -> Dict[str, Any]:
    """
    Handle validation errors with detailed information.

    Args:
        request_data: The request data that failed validation
        error: The validation error

    Returns:
        Dictionary with error information
    """
    logger.warning(
        f"Validation error: {error}",
        extra={
            "request_data": {k: str(v)[:100] for k, v in request_data.items()},
            "error_type": error.__class__.__name__,
        },
    )

    return {
        "error": "Validation failed",
        "message": str(error),
        "timestamp": timezone.now().isoformat(),
        "code": "validation_error",
    }


def handle_timeout_error(operation: str, timeout: int) -> Dict[str, Any]:
    """
    Handle timeout errors with appropriate context.

    Args:
        operation: The operation that timed out
        timeout: The timeout value in seconds

    Returns:
        Dictionary with error information
    """
    logger.error(
        f"Operation '{operation}' timed out after {timeout} seconds",
        extra={"operation": operation, "timeout": timeout},
    )

    return {
        "error": f"Operation '{operation}' timed out",
        "message": f"The operation took longer than {timeout} seconds to complete",
        "timestamp": timezone.now().isoformat(),
        "timeout": timeout,
        "code": "timeout_error",
    }


# Context manager for error handling
class ErrorHandler:
    """Context manager for handling errors in progressive delivery operations."""

    def __init__(
        self, operation: str, fallback_data: Any = None, log_level: str = "error"
    ):
        self.operation = operation
        self.fallback_data = fallback_data
        self.log_level = log_level

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            log_func = getattr(logger, self.log_level, logger.error)
            log_func(
                f"Error in {self.operation}: {exc_val}",
                extra={
                    "operation": self.operation,
                    "error_type": exc_type.__name__ if exc_type else "Unknown",
                    "error_message": str(exc_val) if exc_val else "Unknown error",
                },
                exc_info=True,
            )

            # Don't suppress the exception unless we have fallback data
            return self.fallback_data is not None

        return False
