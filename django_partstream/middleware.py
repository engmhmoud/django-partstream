"""
Production middleware for django-partstream.
Provides security, monitoring, and error handling for progressive delivery endpoints.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from django.db import connection

from .exceptions import RateLimitExceededError, ValidationError

logger = logging.getLogger(__name__)


class ProgressiveDeliveryMiddleware(MiddlewareMixin):
    """
    Middleware for progressive delivery features.

    Provides:
    - Request timing and monitoring
    - Rate limiting
    - Security validation
    - Performance tracking
    - Audit logging
    """

    def __init__(self, get_response: Optional[Callable] = None):
        """Initialize middleware."""
        self.get_response = get_response

        # Initialize components
        self._initialize_components()

        super().__init__(get_response)

    def _initialize_components(self):
        """Initialize middleware components."""
        from .security import RateLimiter, AuditLogger
        from .performance import PerformanceMonitor

        # Get settings
        partstream_settings = getattr(settings, "DJANGO_PARTSTREAM", {})

        # Initialize rate limiter
        if partstream_settings.get("ENABLE_RATE_LIMITING", True):
            self.rate_limiter = RateLimiter(
                rate_limit=partstream_settings.get("RATE_LIMIT", 100),
                burst_limit=partstream_settings.get("BURST_LIMIT", 10),
            )
        else:
            self.rate_limiter = None

        # Initialize performance monitor
        if partstream_settings.get("ENABLE_MONITORING", True):
            self.performance_monitor = PerformanceMonitor()
        else:
            self.performance_monitor = None

        # Initialize audit logger
        if partstream_settings.get("ENABLE_AUDIT_LOGGING", True):
            self.audit_logger = AuditLogger()
        else:
            self.audit_logger = None

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Process incoming request."""
        # Record start time
        request._partstream_start_time = time.time()

        # Check if this is a partstream view
        if self._is_partstream_view(request):
            # Apply rate limiting
            if self.rate_limiter and not self.rate_limiter.is_allowed(request):
                if self.audit_logger:
                    self.audit_logger.log_security_event(
                        "rate_limit_exceeded", request, {"path": request.path}
                    )

                reset_time = self.rate_limiter.get_reset_time(request)
                return JsonResponse(
                    {
                        "error": "Rate limit exceeded",
                        "retry_after": (
                            reset_time - int(time.time()) if reset_time else 60
                        ),
                    },
                    status=429,
                )

            # Validate request
            try:
                self._validate_request(request)
            except ValidationError as e:
                if self.audit_logger:
                    self.audit_logger.log_security_event(
                        "validation_failed", request, {"error": str(e)}
                    )
                return JsonResponse({"error": str(e)}, status=400)

        return None

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        """Process outgoing response."""
        # Record performance metrics
        if hasattr(request, "_partstream_start_time") and self.performance_monitor:
            duration = time.time() - request._partstream_start_time

            # Record metrics
            self.performance_monitor.record_metric(
                "request_duration",
                duration,
                {
                    "path": request.path,
                    "method": request.method,
                    "status_code": str(response.status_code),
                    "view_type": getattr(request, "_partstream_view_class", "unknown"),
                },
            )

        # Log access for partstream views
        if self._is_partstream_view(request) and self.audit_logger:
            parts_count = getattr(request, "_partstream_parts_count", 0)
            cursor_used = "cursor" in request.GET

            self.audit_logger.log_access(request, parts_count, cursor_used)

        return response

    def process_exception(
        self, request: HttpRequest, exception: Exception
    ) -> Optional[HttpResponse]:
        """Process exceptions."""
        if self.audit_logger:
            self.audit_logger.log_security_event(
                "exception",
                request,
                {
                    "exception_type": type(exception).__name__,
                    "exception_message": str(exception),
                    "path": request.path,
                },
            )

        return None

    def _is_partstream_view(self, request: HttpRequest) -> bool:
        """Check if request is for a partstream view."""
        # Check URL patterns
        partstream_patterns = ["/api/", "/partstream/", "/progressive/"]

        return any(pattern in request.path for pattern in partstream_patterns)

    def _validate_request(self, request: HttpRequest) -> None:
        """Validate request parameters."""
        from .security import RequestValidator

        RequestValidator.validate_request_params(request)

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "unknown")
        return ip


class SecurityMiddleware(MiddlewareMixin):
    """Security-focused middleware for partstream views."""

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Process security validations."""
        # Basic security headers
        if request.method == "OPTIONS":
            return None

        # Check for suspicious patterns
        suspicious_patterns = ["../", "script>", "javascript:", "vbscript:"]
        query_string = request.META.get("QUERY_STRING", "")

        if any(pattern in query_string.lower() for pattern in suspicious_patterns):
            return JsonResponse({"error": "Suspicious request detected"}, status=400)

        return None

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        """Add security headers."""
        # Add security headers
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response


class PerformanceMiddleware(MiddlewareMixin):
    """Performance monitoring middleware."""

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Start performance tracking."""
        request._perf_start_time = time.time()
        request._perf_queries_start = len(connection.queries)
        return None

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        """Record performance metrics."""
        if hasattr(request, "_perf_start_time"):
            duration = time.time() - request._perf_start_time
            query_count = len(connection.queries) - getattr(
                request, "_perf_queries_start", 0
            )

            # Add performance headers for debugging
            if settings.DEBUG:
                response["X-Response-Time"] = f"{duration:.3f}s"
                response["X-Query-Count"] = str(query_count)

        return response
