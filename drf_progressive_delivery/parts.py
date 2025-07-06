"""
Django-friendly progressive delivery parts system.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Callable
from functools import cached_property


class ProgressivePart(ABC):
    """
    Abstract base class for progressive delivery parts.
    
    This provides a Django-friendly way to define response parts
    without using generators.
    """
    
    def __init__(self, name: str, lazy: bool = True):
        """
        Initialize a progressive part.
        
        Args:
            name: The name of this part in the response
            lazy: Whether to load data lazily (default: True)
        """
        self.name = name
        self.lazy = lazy
        self._data = None
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
        Load data with lazy loading support.
        
        Args:
            request: The Django request object
            **kwargs: Additional context data
            
        Returns:
            The loaded data
        """
        if not self.lazy:
            return self.get_data(request, **kwargs)
        
        if not self._loaded:
            self._data = self.get_data(request, **kwargs)
            self._loaded = True
        
        return self._data
    
    def reset(self):
        """Reset the cached data."""
        self._data = None
        self._loaded = False


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
    
    def __init__(self, name: str, queryset=None, serializer_class=None, lazy: bool = True):
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
        return list(queryset.values()) if hasattr(queryset, 'values') else queryset


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


class ProgressivePartsRegistry:
    """
    Registry for managing progressive delivery parts.
    
    This provides a Django-friendly way to register and manage
    different parts of a progressive response.
    """
    
    def __init__(self):
        self.parts: List[ProgressivePart] = []
        self._cache_enabled = True
    
    def register(self, part: ProgressivePart) -> 'ProgressivePartsRegistry':
        """
        Register a progressive part.
        
        Args:
            part: The progressive part to register
            
        Returns:
            Self for method chaining
        """
        self.parts.append(part)
        return self
    
    def add_function(self, name: str, func: Callable, lazy: bool = True) -> 'ProgressivePartsRegistry':
        """
        Add a function-based part.
        
        Args:
            name: The name of this part
            func: Function that returns data
            lazy: Whether to load data lazily
            
        Returns:
            Self for method chaining
        """
        part = FunctionPart(name, func, lazy)
        return self.register(part)
    
    def add_model(self, name: str, queryset=None, serializer_class=None, lazy: bool = True) -> 'ProgressivePartsRegistry':
        """
        Add a model-based part.
        
        Args:
            name: The name of this part
            queryset: Django queryset or function that returns queryset
            serializer_class: DRF serializer class
            lazy: Whether to load data lazily
            
        Returns:
            Self for method chaining
        """
        part = ModelPart(name, queryset, serializer_class, lazy)
        return self.register(part)
    
    def add_static(self, name: str, data: Any) -> 'ProgressivePartsRegistry':
        """
        Add a static data part.
        
        Args:
            name: The name of this part
            data: Static data
            
        Returns:
            Self for method chaining
        """
        part = StaticPart(name, data, lazy=False)
        return self.register(part)
    
    def get_parts(self, request, **kwargs) -> List[Dict[str, Any]]:
        """
        Get all parts as a list of dictionaries.
        
        Args:
            request: The Django request object
            **kwargs: Additional context data
            
        Returns:
            List of part dictionaries
        """
        result = []
        for part in self.parts:
            try:
                data = part.load_data(request, **kwargs)
                result.append({part.name: data})
            except Exception as e:
                # Handle errors gracefully
                result.append({part.name: {"error": str(e)}})
        
        return result
    
    def reset_cache(self):
        """Reset cached data for all parts."""
        for part in self.parts:
            part.reset()
    
    def __len__(self) -> int:
        """Return the number of registered parts."""
        return len(self.parts)
    
    def __getitem__(self, index: int) -> ProgressivePart:
        """Get a part by index."""
        return self.parts[index]
    
    def __iter__(self):
        """Iterate over registered parts."""
        return iter(self.parts)


# Convenience decorators for method-based parts
def progressive_part(name: str, lazy: bool = True):
    """
    Decorator to mark a method as a progressive part.
    
    Args:
        name: The name of this part
        lazy: Whether to load data lazily
    """
    def decorator(func):
        func._progressive_part = True
        func._progressive_name = name
        func._progressive_lazy = lazy
        return func
    return decorator


def progressive_meta(func):
    """Decorator for meta information parts."""
    return progressive_part("meta", lazy=False)(func)


def progressive_data(name: str):
    """Decorator for data parts."""
    return progressive_part(name, lazy=True) 