"""
Exception classes for progressive delivery package.
"""

from rest_framework.exceptions import APIException


class ProgressiveDeliveryError(APIException):
    """Base exception for progressive delivery errors."""
    status_code = 500
    default_detail = "Progressive delivery error occurred"
    default_code = "progressive_delivery_error"


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