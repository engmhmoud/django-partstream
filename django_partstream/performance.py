"""
Performance monitoring and optimization utilities for django-partstream.
"""

import logging
import time
import threading
from contextlib import contextmanager
from typing import Any, Dict, List, Tuple
from functools import wraps
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.db import connection

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Simple performance monitoring for production use."""

    def __init__(self):
        self.metrics = {}
        self.lock = threading.Lock()

    def record_metric(self, metric_name: str, value: Any, tags: Dict[str, str] = None):
        """Record a simple metric."""
        metric_data = {
            "name": metric_name,
            "value": value,
            "tags": tags or {},
            "timestamp": timezone.now().isoformat(),
        }

        # Store in cache for collection
        cache_key = f"partstream:metrics:{metric_name}"
        metrics_list = cache.get(cache_key, [])
        metrics_list.append(metric_data)

        # Keep only last 50 metrics to prevent memory bloat
        if len(metrics_list) > 50:
            metrics_list = metrics_list[-50:]

        cache.set(cache_key, metrics_list, 3600)  # 1 hour

    def get_metrics(self, metric_name: str = None) -> Dict[str, Any]:
        """Get collected metrics."""
        if metric_name:
            cache_key = f"partstream:metrics:{metric_name}"
            return cache.get(cache_key, [])

        # Get basic metrics only
        basic_metrics = ["response_time", "cache_hit", "cache_miss", "error_count"]
        all_metrics = {}

        for metric in basic_metrics:
            cache_key = f"partstream:metrics:{metric}"
            all_metrics[metric] = cache.get(cache_key, [])

        return all_metrics


# Global performance monitor
performance_monitor = PerformanceMonitor()


@contextmanager
def performance_timer(operation: str):
    """Simple context manager for timing operations."""
    start_time = time.time()
    query_count_start = len(connection.queries)

    try:
        yield
    finally:
        duration = time.time() - start_time
        query_count = len(connection.queries) - query_count_start

        performance_monitor.record_metric(
            "response_time",
            duration * 1000,  # Convert to milliseconds
            {"operation": operation, "query_count": str(query_count)},
        )


class CacheManager:
    """Simple caching for progressive delivery."""

    @staticmethod
    def get_cache_key(prefix: str, user_id: int = None, **kwargs) -> str:
        """Generate cache key."""
        key_parts = ["partstream", prefix]

        if user_id:
            key_parts.append(f"user:{user_id}")

        for k, v in kwargs.items():
            key_parts.append(f"{k}:{v}")

        return ":".join(key_parts)

    @staticmethod
    def cached_function(ttl: int = 300, key_prefix: str = None, per_user: bool = True):
        """Simple decorator for caching function results."""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate simple cache key
                cache_key_parts = {
                    "func": func.__name__,
                    "args": str(hash(str(args))),
                    "kwargs": str(hash(str(sorted(kwargs.items())))),
                }

                if per_user and args and hasattr(args[0], "request"):
                    user_id = getattr(args[0].request.user, "id", None)
                    if user_id:
                        cache_key_parts["user"] = user_id

                cache_key = CacheManager.get_cache_key(
                    key_prefix or func.__name__, **cache_key_parts
                )

                # Try to get from cache
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    performance_monitor.record_metric(
                        "cache_hit", 1, {"function": func.__name__}
                    )
                    return cached_result

                # Execute function
                with performance_timer(f"function_{func.__name__}"):
                    result = func(*args, **kwargs)

                # Cache result
                cache.set(cache_key, result, ttl)
                performance_monitor.record_metric(
                    "cache_miss", 1, {"function": func.__name__}
                )

                return result

            return wrapper

        return decorator

    @staticmethod
    def invalidate_cache_pattern(pattern: str):
        """Invalidate cache keys matching pattern."""
        try:
            cache_keys = cache.keys(f"partstream:{pattern}*")
            for key in cache_keys:
                cache.delete(key)
        except AttributeError:
            # Cache backend doesn't support key listing
            pass


class QueryOptimizer:
    """Simple database query optimization utilities."""

    @staticmethod
    def track_queries(func):
        """Simple decorator to track database queries."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            initial_queries = len(connection.queries)

            with performance_timer(f"query_tracking_{func.__name__}"):
                result = func(*args, **kwargs)

            final_queries = len(connection.queries)
            query_count = final_queries - initial_queries

            performance_monitor.record_metric(
                "query_count", query_count, {"function": func.__name__}
            )

            # Log warning for too many queries
            if query_count > 10:
                import logging

                logger = logging.getLogger("django_partstream.performance")
                logger.warning(f"High query count ({query_count}) in {func.__name__}")

            return result

        return wrapper


# Simple decorators for production use
def cached_for(ttl: int = 300):
    """Simple caching decorator."""
    return CacheManager.cached_function(ttl=ttl)


def track_performance(func):
    """Simple performance tracking decorator."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        with performance_timer(func.__name__):
            return func(*args, **kwargs)

    return wrapper


def track_queries(func):
    """Simple query tracking decorator."""
    return QueryOptimizer.track_queries(func)


def get_performance_summary() -> Dict[str, Any]:
    """Get a simple performance summary."""
    metrics = performance_monitor.get_metrics()

    summary = {
        "timestamp": timezone.now().isoformat(),
        "cache_hits": len(metrics.get("cache_hit", [])),
        "cache_misses": len(metrics.get("cache_miss", [])),
        "errors": len(metrics.get("error_count", [])),
        "avg_response_time": 0,
    }

    # Calculate average response time
    response_times = [m["value"] for m in metrics.get("response_time", [])]
    if response_times:
        summary["avg_response_time"] = sum(response_times) / len(response_times)

    # Calculate cache hit rate
    total_cache_requests = summary["cache_hits"] + summary["cache_misses"]
    if total_cache_requests > 0:
        summary["cache_hit_rate"] = summary["cache_hits"] / total_cache_requests * 100
    else:
        summary["cache_hit_rate"] = 0

    return summary
