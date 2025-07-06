"""
Django PartStream - Progressive Delivery for Django APIs

A Django package for implementing progressive delivery patterns in REST APIs.
Supports both token-based and key-based progressive loading with security,
performance monitoring, and caching features.

Usage:
    from django_partstream import ProgressiveView

    class MyView(ProgressiveView):
        def get_parts(self):
            return [
                ('data', self.get_data),
                ('metadata', self.get_metadata),
            ]
"""

__version__ = "1.0.0"
__author__ = "Django PartStream Team"
__email__ = "team@django-partstream.com"

# Core components that don't require Django settings
from .exceptions import (
    ProgressiveDeliveryError,
    InvalidCursorError,
    CursorExpiredError,
    RateLimitExceededError,
    ValidationError,
    ConfigurationError,
    AuthenticationError,
    PermissionError,
    CacheError,
)

from .utils import (
    lazy,
    safe_call,
    cached_for,
    with_timeout,
    LazyFunction,
)

# Conditional imports that require Django settings


def _get_views():
    """Lazy import of view classes to avoid Django settings issues."""
    try:
        from .views import (
            ProgressiveView,
            SimpleProgressiveView,
            ConditionalProgressiveView,
            CachedProgressiveView,
            HybridProgressiveView,
        )

        return {
            "ProgressiveView": ProgressiveView,
            "SimpleProgressiveView": SimpleProgressiveView,
            "ConditionalProgressiveView": ConditionalProgressiveView,
            "CachedProgressiveView": CachedProgressiveView,
            "HybridProgressiveView": HybridProgressiveView,
        }
    except ImportError:
        return {}


def _get_components():
    """Lazy import of Django-dependent components."""
    try:
        from .cursors import CursorManager
        from .formatters import ProgressiveResponseFormatter
        from .security import RateLimiter, AuditLogger, RequestValidator
        from .performance import PerformanceMonitor
        from .middleware import ProgressiveDeliveryMiddleware
        from .parts import ProgressivePart, ProgressivePartsRegistry

        return {
            "CursorManager": CursorManager,
            "ProgressiveResponseFormatter": ProgressiveResponseFormatter,
            "RateLimiter": RateLimiter,
            "AuditLogger": AuditLogger,
            "RequestValidator": RequestValidator,
            "PerformanceMonitor": PerformanceMonitor,
            "ProgressiveDeliveryMiddleware": ProgressiveDeliveryMiddleware,
            "ProgressivePart": ProgressivePart,
            "ProgressivePartsRegistry": ProgressivePartsRegistry,
        }
    except ImportError:
        return {}


# Lazy loading helper


def __getattr__(name):
    """Lazy loading of Django-dependent components."""
    # Try views first
    views = _get_views()
    if name in views:
        return views[name]

    # Try other components
    components = _get_components()
    if name in components:
        return components[name]

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Public API - always available
__all__ = [
    # Core exceptions
    "ProgressiveDeliveryError",
    "InvalidCursorError",
    "CursorExpiredError",
    "RateLimitExceededError",
    "ValidationError",
    "ConfigurationError",
    "AuthenticationError",
    "PermissionError",
    "CacheError",
    # Utilities
    "lazy",
    "safe_call",
    "cached_for",
    "with_timeout",
    "LazyFunction",
    # Views (lazy loaded)
    "ProgressiveView",
    "SimpleProgressiveView",
    "ConditionalProgressiveView",
    "CachedProgressiveView",
    "HybridProgressiveView",
    # Components (lazy loaded)
    "CursorManager",
    "ProgressiveResponseFormatter",
    "RateLimiter",
    "AuditLogger",
    "RequestValidator",
    "PerformanceMonitor",
    "ProgressiveDeliveryMiddleware",
    "ProgressivePart",
    "ProgressivePartsRegistry",
]

# Version info
VERSION = (1, 0, 0)


def get_version():
    """Get version string."""
    return ".".join(str(v) for v in VERSION)


# Default Django app config
default_app_config = "django_partstream.apps.DjangoPartstreamConfig"
