"""
Django-friendly progressive delivery parts system.
Provides advanced part management for complex progressive delivery scenarios.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple, Iterator, Callable
from django.http import HttpRequest
from django.utils.functional import cached_property

from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class ProgressivePart(ABC):
    """
    Abstract base class for progressive delivery parts.
    """

    def __init__(self, name: str = None, depends_on: List[str] = None):
        self.name = name
        self.depends_on = depends_on or []
        self._loaded = False

    @abstractmethod
    def get_data(self, request, **kwargs) -> Any:
        """
        Get the data for this part.

        Args:
            request: The Django request object
            **kwargs: Additional context data

        Returns:
            The data for this part
        """
        raise NotImplementedError("Subclasses must implement get_data()")

    def load_data(self, request, **kwargs) -> Any:
        """
        Load and return data for this part.

        Args:
            request: The Django request object
            **kwargs: Additional context data

        Returns:
            The loaded data
        """
        if not self._loaded:
            data = self.get_data(request, **kwargs)
            self._loaded = True
            return data
        return self.get_data(request, **kwargs)

    def reset(self):
        """Reset the loaded state."""
        self._loaded = False

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name})"


class FunctionPart(ProgressivePart):
    """
    A progressive part that uses a function to get data.

    This is useful for simple cases where you just want to
    pass a function that returns data.
    """

    def __init__(self, name: str, func: Callable, lazy: bool = True):
        """
        Initialize a function-based part.

        Args:
            name: The name of this part
            func: Function that takes (request, **kwargs) and returns data
            lazy: Whether to load data lazily
        """
        super().__init__(name, lazy)
        self.func = func

    def get_data(self, request, **kwargs) -> Any:
        """Get data using the provided function."""
        return self.func(request, **kwargs)


class ModelPart(ProgressivePart):
    """
    A progressive part that loads data from Django models.

    This provides a convenient way to load data from Django
    models with built-in serialization support.
    """

    def __init__(
        self, name: str, queryset=None, serializer_class=None, lazy: bool = True
    ):
        """
        Initialize a model-based part.

        Args:
            name: The name of this part
            queryset: Django queryset to load data from
            serializer_class: DRF serializer class to serialize data
            lazy: Whether to load data lazily
        """
        super().__init__(name, lazy)
        self.queryset = queryset
        self.serializer_class = serializer_class

    def get_data(self, request, **kwargs) -> Any:
        """Get data from the model queryset."""
        if self.queryset is None:
            return None

        # Get the queryset (could be lazy)
        queryset = self.queryset
        if callable(queryset):
            queryset = queryset(request, **kwargs)

        # Serialize if serializer is provided
        if self.serializer_class:
            serializer = self.serializer_class(queryset, many=True)
            return serializer.data

        # Return raw queryset values
        return list(queryset.values()) if hasattr(queryset, "values") else queryset


class ComputedPart(ProgressivePart):
    """
    A progressive part for computed/aggregated data.

    This is useful for analytics, statistics, and other
    computed values that might be expensive to calculate.
    """

    def __init__(self, name: str, lazy: bool = True):
        super().__init__(name, lazy)

    def get_data(self, request, **kwargs) -> Any:
        """Override this method to provide computed data."""
        return {}


class StaticPart(ProgressivePart):
    """
    A progressive part with static data.

    Useful for metadata, configuration, or other static content.
    """

    def __init__(self, name: str, data: Any, lazy: bool = False):
        """
        Initialize a static part.

        Args:
            name: The name of this part
            data: Static data to return
            lazy: Whether to load data lazily (usually False for static data)
        """
        super().__init__(name, lazy)
        self.static_data = data

    def get_data(self, request, **kwargs) -> Any:
        """Return the static data."""
        return self.static_data


class CachedPart(ProgressivePart):
    """
    A progressive part with caching support.
    """

    def __init__(
        self, name: str, cache_key: str = None, ttl: int = 300, lazy: bool = True
    ):
        """
        Initialize a cached part.

        Args:
            name: The name of this part
            cache_key: Cache key (auto-generated if None)
            ttl: Time to live in seconds
            lazy: Whether to load data lazily
        """
        super().__init__(name, lazy)
        self.cache_key = cache_key or f"partstream_{name}"
        self.ttl = ttl

    def get_data(self, request, **kwargs) -> Any:
        """Get data with caching support."""
        from django.core.cache import cache

        # Try to get from cache
        cached_data = cache.get(self.cache_key)
        if cached_data is not None:
            return cached_data

        # Get fresh data
        data = self.get_fresh_data(request, **kwargs)

        # Cache the data
        cache.set(self.cache_key, data, self.ttl)

        return data

    def get_fresh_data(self, request, **kwargs) -> Any:
        """Override this method to provide fresh data."""
        return {}


class ProgressivePartsRegistry:
    """
    Registry for managing progressive delivery parts.

    This provides a Django-friendly way to register and manage
    different parts of a progressive response.
    """

    def __init__(self):
        self.parts: List[ProgressivePart] = []
        self._cache_enabled = True

    def register(self, part: ProgressivePart) -> "ProgressivePartsRegistry":
        """
        Register a progressive part.

        Args:
            part: The progressive part to register

        Returns:
            Self for method chaining
        """
        self.parts.append(part)
        return self

    def add_function(
        self, name: str, func: Callable, lazy: bool = True
    ) -> "ProgressivePartsRegistry":
        """
        Add a function-based part.

        Args:
            name: Name of the part
            func: Function to call
            lazy: Whether to load lazily

        Returns:
            Self for method chaining
        """
        part = FunctionPart(name, func, lazy)
        return self.register(part)

    def add_model(
        self, name: str, queryset=None, serializer_class=None, lazy: bool = True
    ) -> "ProgressivePartsRegistry":
        """
        Add a model-based part.

        Args:
            name: Name of the part
            queryset: Django queryset
            serializer_class: DRF serializer class
            lazy: Whether to load lazily

        Returns:
            Self for method chaining
        """
        part = ModelPart(name, queryset, serializer_class, lazy)
        return self.register(part)

    def add_static(self, name: str, data: Any) -> "ProgressivePartsRegistry":
        """
        Add a static data part.

        Args:
            name: Name of the part
            data: Static data

        Returns:
            Self for method chaining
        """
        part = StaticPart(name, data, lazy=False)
        return self.register(part)

    def add_computed(
        self, name: str, compute_func: Callable, lazy: bool = True
    ) -> "ProgressivePartsRegistry":
        """
        Add a computed part.

        Args:
            name: Name of the part
            compute_func: Function to compute the data
            lazy: Whether to load lazily

        Returns:
            Self for method chaining
        """
        part = FunctionPart(name, compute_func, lazy)
        return self.register(part)

    def add_cached(
        self, name: str, data_func: Callable, ttl: int = 300, lazy: bool = True
    ) -> "ProgressivePartsRegistry":
        """
        Add a cached part.

        Args:
            name: Name of the part
            data_func: Function to get data
            ttl: Cache time to live
            lazy: Whether to load lazily

        Returns:
            Self for method chaining
        """

        class CachedFunctionPart(CachedPart):
            def get_fresh_data(self, request, **kwargs):
                return data_func(request, **kwargs)

        part = CachedFunctionPart(name, ttl=ttl, lazy=lazy)
        return self.register(part)

    def get_parts(self, request, **kwargs) -> List[Dict[str, Any]]:
        """
        Get all parts as a list of dictionaries.

        Args:
            request: Django request object
            **kwargs: Additional context

        Returns:
            List of part dictionaries
        """
        results = []

        for part in self.parts:
            try:
                data = part.load_data(request, **kwargs)
                results.append({part.name: data})
            except Exception as e:
                # Handle errors gracefully
                results.append(
                    {
                        part.name: {
                            "error": f"Failed to load {part.name}: {str(e)}",
                            "type": "loading_error",
                        }
                    }
                )

        return results

    def get_parts_tuples(self, request, **kwargs) -> List[tuple]:
        """
        Get all parts as a list of (name, data) tuples.

        Args:
            request: Django request object
            **kwargs: Additional context

        Returns:
            List of (name, data) tuples
        """
        results = []

        for part in self.parts:
            try:
                data = part.load_data(request, **kwargs)
                results.append((part.name, data))
            except Exception as e:
                # Handle errors gracefully
                error_data = {
                    "error": f"Failed to load {part.name}: {str(e)}",
                    "type": "loading_error",
                }
                results.append((part.name, error_data))

        return results

    def reset_cache(self):
        """Reset all cached data."""
        for part in self.parts:
            part.reset()

    def __len__(self) -> int:
        """Get number of parts."""
        return len(self.parts)

    def __getitem__(self, index: int) -> ProgressivePart:
        """Get part by index."""
        return self.parts[index]

    def __iter__(self):
        """Iterate over parts."""
        return iter(self.parts)


# Decorators for progressive parts
def progressive_part(name: str, lazy: bool = True):
    """
    Decorator to mark a method as a progressive part.

    Usage:
        @progressive_part("user_data")
        def get_user_data(self, request):
            return User.objects.all()
    """

    def decorator(func):
        func._progressive_part = True
        func._progressive_name = name
        func._progressive_lazy = lazy
        return func

    return decorator


def progressive_meta(func):
    """
    Decorator to mark a method as metadata.

    Usage:
        @progressive_meta
        def get_metadata(self, request):
            return {"timestamp": timezone.now()}
    """
    return progressive_part("meta", lazy=False)(func)


def progressive_data(name: str):
    """
    Decorator to mark a method as data.

    Usage:
        @progressive_data("orders")
        def get_orders(self, request):
            return Order.objects.all()
    """
    return progressive_part(name, lazy=True)


class RegistryMixin:
    """
    Mixin to add registry support to views.
    """

    def get_parts_registry(self) -> ProgressivePartsRegistry:
        """
        Get the parts registry.
        Override this method to define your parts.
        """
        registry = ProgressivePartsRegistry()

        # Auto-discover methods with decorators
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "_progressive_part") and attr._progressive_part:
                registry.add_function(
                    attr._progressive_name, attr, attr._progressive_lazy
                )

        return registry

    def get_parts(self) -> List[tuple]:
        """
        Get parts using the registry.
        """
        registry = self.get_parts_registry()
        return registry.get_parts_tuples(self.request)
