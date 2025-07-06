"""
Utility functions for django-partstream.
"""

import logging
import time
import signal
from typing import Any, List, Tuple, Iterator, Callable
from functools import wraps
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class LazyFunction:
    """
    Wrapper for lazy-loaded functions.
    Functions wrapped with lazy() are only executed when actually called.
    """

    def __init__(self, func: Callable, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.name = getattr(func, '__name__', 'lazy_function')

    def __call__(self, request):
        """Execute the lazy function with the request parameter."""
        try:
            if self.args or self.kwargs:
                return self.func(request, *self.args, **self.kwargs)
            else:
                return self.func(request)
        except Exception as e:
            # Log the error but don't break the entire response
            import logging
            logger = logging.getLogger('django_partstream')
            logger.error(f"Error in lazy function {self.name}: {e}")
            raise


def lazy(func: Callable, *args, **kwargs) -> LazyFunction:
    """
    Mark a function for lazy loading.

    Usage:
        ("data", lazy(self.get_data))
        ("expensive", lazy(self.compute_analytics))

    Args:
        func: Function to wrap
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        LazyFunction wrapper
    """
    return LazyFunction(func, *args, **kwargs)


class SafeCall:
    """
    Wrapper for safe function calls with fallback support.
    """

    def __init__(
            self,
            func: Callable,
            fallback: Any = None,
            reraise: bool = False):
        self.func = func
        self.fallback = fallback
        self.reraise = reraise
        self.name = getattr(func, '__name__', 'safe_function')

    def __call__(self, request):
        """Execute the function safely with fallback on error."""
        try:
            if isinstance(self.func, LazyFunction):
                return self.func(request)
            else:
                return self.func(request)
        except Exception as e:
            import logging
            logger = logging.getLogger('django_partstream')
            logger.warning(f"Safe call failed for {self.name}: {e}")

            if self.reraise:
                raise

            if self.fallback is not None:
                return self.fallback

            return {
                "error": f"Function {self.name} failed",
                "message": str(e),
                "timestamp": timezone.now().isoformat()
            }


def safe_call(
        func: Callable,
        fallback: Any = None,
        reraise: bool = False) -> SafeCall:
    """
    Wrap a function to handle errors gracefully.

    Usage:
        ("data", lazy(safe_call(self.risky_function, fallback={"error": "Failed"})))

    Args:
        func: Function to wrap
        fallback: Value to return on error (default: error dict)
        reraise: Whether to reraise exceptions (default: False)

    Returns:
        SafeCall wrapper
    """
    return SafeCall(func, fallback, reraise)


def cached_for(ttl: int = 300, key_prefix: str = None):
    """
    Decorator to cache function results.

    Usage:
        @cached_for(300)  # Cache for 5 minutes
        def get_analytics(self, request):
            return expensive_computation()

    Args:
        ttl: Time to live in seconds (default: 300)
        key_prefix: Custom cache key prefix

    Returns:
        Decorated function with caching
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            func_name = func.__name__
            prefix = key_prefix or f"partstream_cache_{func_name}"

            # Include request user in cache key if available
            cache_key_parts = [prefix]
            if args and hasattr(args[0], 'request'):
                request = args[0].request
                if hasattr(request, 'user') and request.user.is_authenticated:
                    cache_key_parts.append(f"user_{request.user.id}")

            # Add args/kwargs to cache key
            if len(args) > 1:  # Skip self/request
                cache_key_parts.append(f"args_{hash(str(args[1:]))}")
            if kwargs:
                cache_key_parts.append(
                    f"kwargs_{hash(str(sorted(kwargs.items())))}")

            cache_key = "_".join(str(part) for part in cache_key_parts)

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)

            return result
        return wrapper
    return decorator


class TimeoutFunction:
    """
    Wrapper for functions with timeout support.
    """

    def __init__(self, func: Callable, timeout: int):
        self.func = func
        self.timeout = timeout
        self.name = getattr(func, '__name__', 'timeout_function')

    def __call__(self, request):
        """Execute function with timeout."""
        def timeout_handler(signum, frame):
            raise TimeoutError(
                f"Function {
                    self.name} timed out after {
                    self.timeout} seconds")

        # Set up timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(self.timeout)

        try:
            if isinstance(self.func, (LazyFunction, SafeCall)):
                result = self.func(request)
            else:
                result = self.func(request)
            return result
        finally:
            # Restore old handler and cancel alarm
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


def with_timeout(func: Callable, timeout: int = 30) -> TimeoutFunction:
    """
    Wrap a function with timeout protection.

    Usage:
        ("slow_data", lazy(with_timeout(self.slow_function, 10)))

    Args:
        func: Function to wrap
        timeout: Timeout in seconds (default: 30)

    Returns:
        TimeoutFunction wrapper
    """
    return TimeoutFunction(func, timeout)


def combine_wrappers(*wrappers):
    """
    Combine multiple function wrappers.

    Usage:
        ("data", lazy(combine_wrappers(
            safe_call(self.risky_function, fallback={"error": "Failed"}),
            with_timeout(timeout=10)
        )))
    """
    def wrapper(func):
        result = func
        for w in reversed(wrappers):
            if callable(w):
                result = w(result)
            else:
                result = w
        return result
    return wrapper


class PartStreamResponse:
    """
    Helper class for building progressive responses.
    """

    def __init__(self):
        self.parts = []

    def add_part(self, name: str, data: Any):
        """Add a part to the response."""
        self.parts.append((name, data))

    def add_lazy_part(self, name: str, func: Callable):
        """Add a lazy-loaded part."""
        self.parts.append((name, lazy(func)))

    def add_safe_part(self, name: str, func: Callable, fallback: Any = None):
        """Add a safe part with error handling."""
        self.parts.append((name, lazy(safe_call(func, fallback))))

    def add_cached_part(self, name: str, func: Callable, ttl: int = 300):
        """Add a cached part."""
        cached_func = cached_for(ttl)(func)
        self.parts.append((name, lazy(cached_func)))

    def get_parts(self):
        """Get all parts."""
        return self.parts


# Utility function for performance monitoring
def track_performance(func):
    """
    Decorator to track function performance.

    Usage:
        @track_performance
        def expensive_function(self, request):
            return compute_something()
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Log performance metrics
            import logging
            logger = logging.getLogger('django_partstream.performance')
            logger.info(f"{func.__name__} executed in {execution_time:.3f}s")

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            import logging
            logger = logging.getLogger('django_partstream.performance')
            logger.error(
                f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise

    return wrapper
