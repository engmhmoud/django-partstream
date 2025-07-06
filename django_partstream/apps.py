"""
Django app configuration for django_partstream.
"""

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import logging

logger = logging.getLogger(__name__)


class DjangoPartstreamConfig(AppConfig):
    """Configuration for django-partstream app."""

    name = "django_partstream"
    verbose_name = "Django PartStream"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """
        Called when Django starts up.
        Performs initial configuration and validation.
        """
        # Validate configuration
        self._validate_configuration()

        # Initialize components
        self._initialize_security()
        self._initialize_monitoring()
        self._setup_logging()

        logger.info("Django PartStream initialized successfully")

    def _validate_configuration(self):
        """Validate django_partstream configuration."""
        # Check for required Django settings
        if not hasattr(settings, "SECRET_KEY") or not settings.SECRET_KEY:
            raise ImproperlyConfigured(
                "SECRET_KEY is required for django-partstream cursor encryption"
            )

        # Get partstream settings
        partstream_settings = getattr(settings, "DJANGO_PARTSTREAM", {})

        # Validate rate limiting settings
        if partstream_settings.get("ENABLE_RATE_LIMITING", True):
            rate_limit = partstream_settings.get("RATE_LIMIT", 100)
            burst_limit = partstream_settings.get("BURST_LIMIT", 10)

            if rate_limit <= 0:
                raise ImproperlyConfigured("RATE_LIMIT must be positive")
            if burst_limit <= 0:
                raise ImproperlyConfigured("BURST_LIMIT must be positive")
            if burst_limit > rate_limit:
                logger.warning(
                    "BURST_LIMIT (%s) is higher than RATE_LIMIT (%s)",
                    burst_limit,
                    rate_limit,
                )

        # Validate cursor settings
        cursor_ttl = partstream_settings.get("DEFAULT_CURSOR_TTL", 3600)
        if cursor_ttl <= 0:
            raise ImproperlyConfigured("DEFAULT_CURSOR_TTL must be positive")

        # Validate chunk size
        chunk_size = partstream_settings.get("DEFAULT_CHUNK_SIZE", 2)
        if chunk_size <= 0:
            raise ImproperlyConfigured("DEFAULT_CHUNK_SIZE must be positive")

        logger.info("Configuration validation passed")

    def _initialize_security(self):
        """Initialize security components."""
        partstream_settings = getattr(settings, "DJANGO_PARTSTREAM", {})

        if partstream_settings.get("ENABLE_RATE_LIMITING", True):
            # Import here to avoid circular imports
            from .security import RateLimiter

            # Initialize rate limiter
            RateLimiter(
                rate_limit=partstream_settings.get("RATE_LIMIT", 100),
                burst_limit=partstream_settings.get("BURST_LIMIT", 10),
            )

            logger.info("Rate limiting initialized")

        if partstream_settings.get("ENABLE_AUDIT_LOGGING", True):
            logger.info("Audit logging enabled")

    def _initialize_monitoring(self):
        """Initialize monitoring components."""
        partstream_settings = getattr(settings, "DJANGO_PARTSTREAM", {})

        if partstream_settings.get("ENABLE_MONITORING", True):
            # Import here to avoid circular imports
            from .performance import PerformanceMonitor

            # Initialize performance monitor
            PerformanceMonitor()
            logger.info("Performance monitoring initialized")

        if partstream_settings.get("HEALTH_CHECK_ENABLED", True):
            logger.info("Health checks enabled")

    def _setup_logging(self):
        """Setup logging configuration."""
        partstream_settings = getattr(settings, "DJANGO_PARTSTREAM", {})

        # Set up security logging
        if partstream_settings.get("ENABLE_AUDIT_LOGGING", True):
            security_logger = logging.getLogger("django_partstream.security")
            if not security_logger.handlers:
                # Add default handler if none exists
                handler = logging.StreamHandler()
                handler.setLevel(logging.WARNING)
                formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
                handler.setFormatter(formatter)
                security_logger.addHandler(handler)

        # Set up performance logging
        if partstream_settings.get("TRACK_PERFORMANCE", True):
            perf_logger = logging.getLogger("django_partstream.performance")
            if not perf_logger.handlers:
                handler = logging.StreamHandler()
                handler.setLevel(logging.INFO)
                formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
                handler.setFormatter(formatter)
                perf_logger.addHandler(handler)

    @classmethod
    def get_default_settings(cls):
        """Get default settings for django-partstream."""
        return {
            # Performance
            "DEFAULT_CHUNK_SIZE": 2,
            "DEFAULT_CURSOR_TTL": 3600,
            "ENABLE_CACHING": True,
            "CACHE_TTL": 300,
            # Security
            "ENABLE_RATE_LIMITING": True,
            "RATE_LIMIT": 100,
            "BURST_LIMIT": 10,
            "ENABLE_AUDIT_LOGGING": True,
            "ENABLE_IP_FILTERING": False,
            "ALLOWED_IPS": [],
            "BLOCKED_IPS": [],
            # Monitoring
            "ENABLE_MONITORING": True,
            "TRACK_PERFORMANCE": True,
            "HEALTH_CHECK_ENABLED": True,
            # Limits
            "MAX_PARTS_PER_REQUEST": 50,
            "MAX_CURSOR_SIZE": 1024,
            "MAX_KEYS_PER_REQUEST": 10,
        }

    @classmethod
    def get_settings(cls):
        """Get current settings with defaults."""
        defaults = cls.get_default_settings()
        user_settings = getattr(settings, "DJANGO_PARTSTREAM", {})

        # Merge user settings with defaults
        merged_settings = defaults.copy()
        merged_settings.update(user_settings)

        return merged_settings


# Default app configuration
default_app_config = "django_partstream.apps.DjangoPartstreamConfig"
