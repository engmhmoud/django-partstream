"""
Security utilities for django-partstream.
"""

import logging
import time
from typing import Any, Dict, List, Tuple
from functools import wraps
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .exceptions import ProgressiveDeliveryError

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for progressive delivery endpoints."""

    def __init__(self, rate_limit: int = 100, burst_limit: int = 10):
        self.rate_limit = rate_limit
        self.burst_limit = burst_limit

    def is_allowed(self, request) -> bool:
        """Check if request is within rate limits."""
        # Use user ID if available, otherwise use IP
        identifier = getattr(request.user, "id", None) or self._get_client_ip(request)

        # Check burst rate (short-term)
        burst_key = f"partstream_burst:{identifier}"
        burst_count = cache.get(burst_key, 0)

        if burst_count >= self.burst_limit:
            return False

        # Check sustained rate (long-term)
        rate_key = f"partstream_rate:{identifier}"
        rate_count = cache.get(rate_key, 0)

        if rate_count >= self.rate_limit:
            return False

        # Update counters
        cache.set(burst_key, burst_count + 1, 10)  # 10 second window
        cache.set(rate_key, rate_count + 1, 60)  # 60 second window

        return True

    def get_reset_time(self, request) -> int | None:
        """Get when rate limit resets."""
        identifier = getattr(request.user, "id", None) or self._get_client_ip(request)
        rate_key = f"partstream_rate:{identifier}"

        try:
            ttl = cache.ttl(rate_key)
            if ttl and ttl > 0:
                return int(time.time()) + ttl
        except AttributeError:
            # Cache backend doesn't support TTL
            pass

        return None

    def _get_client_ip(self, request) -> str:
        """Get client IP address."""
        # Check for forwarded headers
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "unknown")

        return ip


class RequestValidator:
    """Simple request validation for security."""

    @staticmethod
    def validate_cursor(cursor: str) -> None:
        """Validate cursor format and size."""
        if not cursor:
            return

        # Check cursor size (prevent large cursor attacks)
        if len(cursor) > 1024:  # 1KB limit
            raise ProgressiveDeliveryError("Cursor too large")

        # Check for obvious malicious patterns
        suspicious_chars = ["<", ">", '"', "'", "&", "\x00", "\n", "\r"]
        if any(char in cursor for char in suspicious_chars):
            raise ProgressiveDeliveryError("Invalid cursor format")

    @staticmethod
    def validate_request_params(request) -> None:
        """Validate request parameters for suspicious content."""
        # Check for suspicious parameter names
        suspicious_params = ["__", "eval", "exec", "import", "system", "file", "script"]

        for param in request.GET.keys():
            if any(sus in param.lower() for sus in suspicious_params):
                raise ProgressiveDeliveryError("Suspicious request parameter")

        # Validate cursor if present
        cursor = request.GET.get("cursor")
        if cursor and isinstance(cursor, str):
            RequestValidator.validate_cursor(cursor)

        # Validate keys parameter if present
        keys = request.GET.get("keys")
        if keys and isinstance(keys, str):
            key_list = [k.strip() for k in keys.split(",")]
            if len(key_list) > 10:  # Reasonable limit
                raise ProgressiveDeliveryError("Too many keys requested")


class AuditLogger:
    """Simple audit logging for security events."""

    @staticmethod
    def log_access(request, parts_count: int, cursor_used: bool = False) -> None:
        """Log access to progressive delivery endpoints."""
        import logging

        logger = logging.getLogger("django_partstream.security")

        log_data = {
            "user_id": getattr(request.user, "id", None),
            "username": getattr(request.user, "username", "anonymous"),
            "ip": _get_client_ip(request),
            "path": request.path,
            "method": request.method,
            "parts_count": parts_count,
            "cursor_used": cursor_used,
            "timestamp": timezone.now().isoformat(),
        }

        logger.info(f"Progressive delivery access: {log_data}")

    @staticmethod
    def log_security_event(event_type: str, request, details: Dict[str, Any]) -> None:
        """Log security events."""
        import logging

        logger = logging.getLogger("django_partstream.security")

        log_data = {
            "event_type": event_type,
            "user_id": getattr(request.user, "id", None),
            "ip": _get_client_ip(request),
            "timestamp": timezone.now().isoformat(),
            "details": details,
        }

        logger.warning(f"Security event: {log_data}")


# Helper function for getting client IP


def _get_client_ip(request) -> str:
    """Get client IP address."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "unknown")
    return ip


# Simple security decorators for production use
def rate_limit(limit: int = 100, burst_limit: int = 10):
    """Simple rate limiting decorator."""

    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            rate_limiter = RateLimiter(rate_limit=limit, burst_limit=burst_limit)

            if not rate_limiter.is_allowed(request):
                from django.http import JsonResponse

                reset_time = rate_limiter.get_reset_time(request)
                response = JsonResponse(
                    {
                        "error": "Rate limit exceeded",
                        "retry_after": (
                            reset_time - int(time.time()) if reset_time else 60
                        ),
                    },
                    status=429,
                )

                AuditLogger.log_security_event(
                    "rate_limit_exceeded",
                    request,
                    {"limit": limit, "burst_limit": burst_limit},
                )

                return response

            return func(self, request, *args, **kwargs)

        return wrapper

    return decorator


def secure_request_validation(func):
    """Simple request validation decorator."""

    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        try:
            RequestValidator.validate_request_params(request)
        except ProgressiveDeliveryError as e:
            AuditLogger.log_security_event(
                "validation_failed", request, {"error": str(e)}
            )
            raise

        return func(self, request, *args, **kwargs)

    return wrapper


def require_authentication(func):
    """Simple authentication requirement decorator."""

    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.http import JsonResponse

            AuditLogger.log_security_event("unauthenticated_access", request, {})

            return JsonResponse(
                {
                    "error": "Authentication required",
                    "message": "You must be authenticated to access this endpoint",
                },
                status=401,
            )

        return func(self, request, *args, **kwargs)

    return wrapper


def validate_security_config():
    """Simple security configuration validation."""
    errors = []

    # Check if SECRET_KEY is set
    if not hasattr(settings, "SECRET_KEY") or not settings.SECRET_KEY:
        errors.append("SECRET_KEY must be set for secure cursor handling")

    # Check SECRET_KEY strength
    if hasattr(settings, "SECRET_KEY") and len(settings.SECRET_KEY) < 32:
        errors.append("SECRET_KEY should be at least 32 characters long")

    if errors:
        raise ProgressiveDeliveryError(
            f"Security configuration errors: {', '.join(errors)}"
        )


# Initialize security validation on import
try:
    validate_security_config()
except Exception:
    # Don't fail imports in development
    pass
