"""
Health check management command for django-partstream.
Production-ready health monitoring and diagnostics.
"""

import sys
import time
import json
import logging
from django.core.management.base import BaseCommand
from django.core.management.color import make_style
from django.conf import settings
from django.db import connection
from django.core.cache import cache
from django.utils import timezone


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Health check command for django-partstream.

    Usage:
        python manage.py partstream_health_check
        python manage.py partstream_health_check --verbose
        python manage.py partstream_health_check --format=json
    """

    help = "Perform health checks for django-partstream components"

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            choices=["text", "json"],
            default="text",
            help="Output format (default: text)",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=30,
            help="Timeout in seconds for health checks (default: 30)",
        )

    def handle(self, *args, **options):
        """Run health checks and report results."""
        self.verbosity = options["verbosity"]
        self.format = options["format"]
        self.timeout = options["timeout"]

        # Collect all health check results
        results = {
            "timestamp": timezone.now().isoformat(),
            "status": "healthy",
            "checks": {},
            "summary": {"total": 0, "passed": 0, "failed": 0, "warnings": 0},
        }

        # Run all health checks
        checks = [
            ("configuration", self._check_configuration),
            ("security", self._check_security),
            ("database", self._check_database),
            ("cache", self._check_cache),
            ("cursor_encryption", self._check_cursor_encryption),
            ("performance", self._check_performance),
            ("logging", self._check_logging),
        ]

        for check_name, check_func in checks:
            try:
                if self.verbosity >= 2:
                    self.stdout.write(f"Running {check_name} check...")

                check_result = check_func()
                results["checks"][check_name] = check_result
                results["summary"]["total"] += 1

                if check_result["status"] == "passed":
                    results["summary"]["passed"] += 1
                elif check_result["status"] == "warning":
                    results["summary"]["warnings"] += 1
                else:
                    results["summary"]["failed"] += 1
                    results["status"] = "unhealthy"

            except Exception as e:
                results["checks"][check_name] = {
                    "status": "failed",
                    "message": f"Health check failed: {str(e)}",
                    "details": {"exception": str(e)},
                }
                results["summary"]["total"] += 1
                results["summary"]["failed"] += 1
                results["status"] = "unhealthy"

        # Output results
        self._output_results(results)

        # Exit with appropriate code
        if results["status"] != "healthy":
            sys.exit(1)

    def _check_configuration(self):
        """Check django-partstream configuration."""
        try:
            from django_partstream.apps import DjangoPartstreamConfig

            # Check if SECRET_KEY is configured
            if not hasattr(settings, "SECRET_KEY") or not settings.SECRET_KEY:
                return {
                    "status": "failed",
                    "message": "SECRET_KEY not configured",
                    "details": {
                        "issue": "Missing SECRET_KEY required for cursor encryption"
                    },
                }

            # Get settings
            partstream_settings = DjangoPartstreamConfig.get_settings()

            # Check critical settings
            issues = []
            if partstream_settings["DEFAULT_CHUNK_SIZE"] <= 0:
                issues.append("DEFAULT_CHUNK_SIZE must be positive")
            if partstream_settings["DEFAULT_CURSOR_TTL"] <= 0:
                issues.append("DEFAULT_CURSOR_TTL must be positive")
            if partstream_settings["RATE_LIMIT"] <= 0:
                issues.append("RATE_LIMIT must be positive")

            if issues:
                return {
                    "status": "failed",
                    "message": "Configuration issues found",
                    "details": {"issues": issues},
                }

            return {
                "status": "passed",
                "message": "Configuration is valid",
                "details": {
                    "chunk_size": partstream_settings["DEFAULT_CHUNK_SIZE"],
                    "cursor_ttl": partstream_settings["DEFAULT_CURSOR_TTL"],
                    "rate_limit": partstream_settings["RATE_LIMIT"],
                },
            }

        except Exception as e:
            return {
                "status": "failed",
                "message": f"Configuration check failed: {str(e)}",
                "details": {"exception": str(e)},
            }

    def _check_security(self):
        """Check security components."""
        try:
            from django_partstream.security import RateLimiter
            from django_partstream.cursors import CursorManager

            # Test rate limiter
            RateLimiter()

            # Test cursor manager
            cursor_manager = CursorManager()
            test_cursor = cursor_manager.create_cursor({"test": "data"})
            decoded = cursor_manager.decode_cursor(test_cursor)

            if decoded.get("test") != "data":
                return {
                    "status": "failed",
                    "message": "Cursor encryption/decryption failed",
                    "details": {"issue": "Cursor test failed"},
                }

            return {
                "status": "passed",
                "message": "Security components working",
                "details": {
                    "rate_limiter": "operational",
                    "cursor_encryption": "operational",
                },
            }

        except Exception as e:
            return {
                "status": "failed",
                "message": f"Security check failed: {str(e)}",
                "details": {"exception": str(e)},
            }

    def _check_database(self):
        """Check database connectivity."""
        try:
            start_time = time.time()

            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

            response_time = (time.time() - start_time) * 1000

            if result[0] != 1:
                return {
                    "status": "failed",
                    "message": "Database query failed",
                    "details": {"issue": "Unexpected query result"},
                }

            status = "passed"
            if response_time > 1000:  # > 1 second
                status = "warning"

            return {
                "status": status,
                "message": f"Database responsive in {response_time:.1f}ms",
                "details": {
                    "response_time_ms": response_time,
                    "vendor": connection.vendor,
                },
            }

        except Exception as e:
            return {
                "status": "failed",
                "message": f"Database check failed: {str(e)}",
                "details": {"exception": str(e)},
            }

    def _check_cache(self):
        """Check cache functionality."""
        try:
            start_time = time.time()

            # Test cache set/get
            test_key = f"partstream_health_check_{int(time.time())}"
            test_value = "health_check_value"

            cache.set(test_key, test_value, 60)
            retrieved_value = cache.get(test_key)
            cache.delete(test_key)

            response_time = (time.time() - start_time) * 1000

            if retrieved_value != test_value:
                return {
                    "status": "failed",
                    "message": "Cache set/get failed",
                    "details": {"issue": "Cache value mismatch"},
                }

            status = "passed"
            if response_time > 100:  # > 100ms
                status = "warning"

            return {
                "status": status,
                "message": f"Cache responsive in {response_time:.1f}ms",
                "details": {
                    "response_time_ms": response_time,
                    "backend": str(cache.__class__.__name__),
                },
            }

        except Exception as e:
            return {
                "status": "failed",
                "message": f"Cache check failed: {str(e)}",
                "details": {"exception": str(e)},
            }

    def _check_cursor_encryption(self):
        """Check cursor encryption functionality."""
        try:
            from django_partstream.cursors import CursorManager

            start_time = time.time()

            cursor_manager = CursorManager(ttl=3600)

            # Test data
            test_data = {
                "index": 5,
                "user_id": 123,
                "timestamp": time.time(),
                "data": "test_data_with_special_chars_!@#$%^&*()",
            }

            # Create and decode cursor
            cursor = cursor_manager.create_cursor(test_data)
            decoded_data = cursor_manager.decode_cursor(cursor)

            response_time = (time.time() - start_time) * 1000

            # Verify data integrity
            for key, value in test_data.items():
                if decoded_data.get(key) != value:
                    return {
                        "status": "failed",
                        "message": f"Cursor data integrity failed for key: {key}",
                        "details": {"expected": value, "actual": decoded_data.get(key)},
                    }

            # Check cursor format (should be URL-safe)
            if any(char in cursor for char in ["+", "/", "="]):
                return {
                    "status": "warning",
                    "message": "Cursor contains non-URL-safe characters",
                    "details": {"cursor_sample": cursor[:50] + "..."},
                }

            return {
                "status": "passed",
                "message": f"Cursor encryption working in {response_time:.1f}ms",
                "details": {
                    "response_time_ms": response_time,
                    "cursor_length": len(cursor),
                    "data_integrity": "verified",
                },
            }

        except Exception as e:
            return {
                "status": "failed",
                "message": f"Cursor encryption check failed: {str(e)}",
                "details": {"exception": str(e)},
            }

    def _check_performance(self):
        """Check performance monitoring components."""
        try:
            from django_partstream.performance import PerformanceMonitor

            start_time = time.time()

            # Test performance monitor
            monitor = PerformanceMonitor()

            # Test metric recording
            monitor.record_metric("test_metric", 1.0, {"test": "health_check"})

            response_time = (time.time() - start_time) * 1000

            return {
                "status": "passed",
                "message": f"Performance monitoring working in {response_time:.1f}ms",
                "details": {
                    "response_time_ms": response_time,
                    "monitoring": "operational",
                },
            }

        except Exception as e:
            return {
                "status": "failed",
                "message": f"Performance check failed: {str(e)}",
                "details": {"exception": str(e)},
            }

    def _check_logging(self):
        """Check logging configuration."""
        try:
            # Test loggers
            loggers = [
                "django_partstream",
                "django_partstream.security",
                "django_partstream.performance",
            ]

            logger_status = {}
            for logger_name in loggers:
                logger = logging.getLogger(logger_name)
                logger_status[logger_name] = {
                    "level": logger.level,
                    "handlers": len(logger.handlers),
                    "effective_level": logger.getEffectiveLevel(),
                }

            return {
                "status": "passed",
                "message": "Logging configuration verified",
                "details": {"loggers": logger_status},
            }

        except Exception as e:
            return {
                "status": "failed",
                "message": f"Logging check failed: {str(e)}",
                "details": {"exception": str(e)},
            }

    def _output_results(self, results):
        """Output health check results."""
        if self.format == "json":
            self.stdout.write(json.dumps(results, indent=2))
        else:
            self._output_text_results(results)

    def _output_text_results(self, results):
        """Output results in text format."""
        # Header
        status_color = (
            self.style.SUCCESS if results["status"] == "healthy" else self.style.ERROR
        )
        self.stdout.write(
            f"\nDjango PartStream Health Check - {status_color(results['status'].upper())}"
        )
        self.stdout.write(f"Timestamp: {results['timestamp']}")
        self.stdout.write("-" * 50)

        # Individual checks
        for check_name, check_result in results["checks"].items():
            status = check_result["status"]
            message = check_result["message"]

            if status == "passed":
                status_str = self.style.SUCCESS("✓ PASSED")
            elif status == "warning":
                status_str = self.style.WARNING("⚠ WARNING")
            else:
                status_str = self.style.ERROR("✗ FAILED")

            self.stdout.write(f"{check_name.replace('_', ' ').title()}: {status_str}")
            self.stdout.write(f"  {message}")

            if self.verbosity >= 2 and "details" in check_result:
                for key, value in check_result["details"].items():
                    self.stdout.write(f"    {key}: {value}")

            self.stdout.write("")

        # Summary
        summary = results["summary"]
        self.stdout.write("-" * 50)
        self.stdout.write("Summary:")
        self.stdout.write(f"  Total checks: {summary['total']}")
        self.stdout.write(f"  {self.style.SUCCESS('Passed')}: {summary['passed']}")
        if summary["warnings"] > 0:
            self.stdout.write(
                f"  {self.style.WARNING('Warnings')}: {summary['warnings']}"
            )
        if summary["failed"] > 0:
            self.stdout.write(f"  {self.style.ERROR('Failed')}: {summary['failed']}")

        self.stdout.write("")
