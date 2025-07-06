"""
Simplified Progressive Delivery API for Django REST Framework.

This is a much simpler version that focuses on the most common use cases.
"""

from typing import List, Tuple, Any, Callable, Union
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from django.utils import timezone

from .cursors import CursorManager
from .exceptions import InvalidCursorError, CursorExpiredError


class lazy:
    """
    Wrapper to mark a function as lazy-loaded.
    
    Usage:
        return [
            ("meta", {"timestamp": now()}),           # Always loads
            ("orders", lazy(self.get_orders)),        # Lazy load
            ("analytics", lazy(self.expensive_calc))  # Lazy load
        ]
    """
    
    def __init__(self, func: Callable):
        self.func = func
        self.is_lazy = True
        self._cached_result = None
        self._loaded = False
    
    def __call__(self, *args, **kwargs):
        if not self._loaded:
            self._cached_result = self.func(*args, **kwargs)
            self._loaded = True
        return self._cached_result
    
    def reset(self):
        """Reset cached result."""
        self._cached_result = None
        self._loaded = False


class ProgressiveView(APIView):
    """
    Simplified progressive delivery view.
    
    Just override get_parts() and return a list of (name, data) tuples.
    """
    
    # Simple configuration
    chunk_size = 2
    cursor_ttl = 3600  # 1 hour
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cursor_manager = CursorManager(ttl=self.cursor_ttl)
    
    def get_parts(self) -> List[Tuple[str, Any]]:
        """
        Return response parts as (name, data) tuples.
        
        Override this method to define your API response parts.
        
        Returns:
            List of (name, data) tuples where:
            - name: String identifier for this part
            - data: Any JSON-serializable data or lazy() wrapper
        
        Example:
            return [
                ("meta", {"timestamp": timezone.now()}),
                ("orders", Order.objects.all()[:100]),
                ("analytics", lazy(self.get_analytics))
            ]
        """
        return []
    
    def get(self, request: Request, *args, **kwargs) -> Response:
        """Handle GET requests with progressive delivery."""
        try:
            # Get cursor from request
            cursor = request.GET.get('cursor')
            start_index = 0
            
            # If cursor provided, decode it
            if cursor:
                try:
                    cursor_data = self.cursor_manager.decode_cursor(cursor)
                    start_index = cursor_data.get('start_index', 0)
                except (InvalidCursorError, CursorExpiredError) as e:
                    return Response(
                        {"error": str(e)},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Get all parts
            all_parts = self.get_parts()
            
            # Get current chunk
            end_index = start_index + self.chunk_size
            current_chunk = all_parts[start_index:end_index]
            
            # Load data for current chunk
            results = []
            for part_name, part_data in current_chunk:
                try:
                    # Handle lazy loading
                    if isinstance(part_data, lazy):
                        data = part_data(request)
                    else:
                        data = part_data
                    
                    results.append({part_name: data})
                
                except Exception as e:
                    # Graceful error handling
                    results.append({
                        part_name: {
                            "error": f"Failed to load {part_name}: {str(e)}",
                            "type": "loading_error"
                        }
                    })
            
            # Create response
            response_data = {
                "results": results,
                "cursor": None,
                "meta": {
                    "total_parts": len(all_parts),
                    "current_chunk_size": len(results),
                    "has_more": end_index < len(all_parts),
                    "chunk_index": start_index // self.chunk_size
                }
            }
            
            # Add cursor if more parts exist
            if end_index < len(all_parts):
                next_cursor_data = {"start_index": end_index}
                response_data["cursor"] = self.cursor_manager.create_cursor(next_cursor_data)
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Progressive delivery failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SimpleProgressiveView(ProgressiveView):
    """
    Even simpler view with predefined methods for common patterns.
    
    Override get_meta(), get_data(), get_analytics() methods.
    """
    
    def get_parts(self) -> List[Tuple[str, Any]]:
        """Build parts from predefined methods."""
        parts = []
        
        # Add meta if available
        try:
            meta = self.get_meta()
            if meta:
                parts.append(("meta", meta))
        except NotImplementedError:
            pass
        
        # Add main data if available  
        try:
            data = self.get_data()
            if data:
                parts.append(("data", data))
        except NotImplementedError:
            pass
        
        # Add analytics if available
        try:
            analytics = self.get_analytics()
            if analytics:
                parts.append(("analytics", lazy(lambda r: analytics)))
        except NotImplementedError:
            pass
        
        return parts
    
    def get_meta(self) -> dict:
        """Override to provide metadata."""
        raise NotImplementedError("Override get_meta() to provide metadata")
    
    def get_data(self) -> Any:
        """Override to provide main data."""
        raise NotImplementedError("Override get_data() to provide main data")
    
    def get_analytics(self) -> Any:
        """Override to provide analytics data."""
        raise NotImplementedError("Override get_analytics() to provide analytics")


# Helper functions for common patterns
def safe_call(func: Callable, fallback: Any = None) -> Callable:
    """
    Wrapper that handles exceptions gracefully.
    
    Args:
        func: Function to call
        fallback: Value to return if function fails
    
    Returns:
        Wrapped function that won't raise exceptions
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return fallback or {
                "error": f"Operation failed: {str(e)}",
                "type": "safe_call_error"
            }
    return wrapper


def with_timeout(func: Callable, timeout_seconds: int = 30) -> Callable:
    """
    Wrapper that adds timeout to function calls.
    
    Args:
        func: Function to call
        timeout_seconds: Maximum time to wait
    
    Returns:
        Wrapped function with timeout
    """
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Function timed out after {timeout_seconds} seconds")
    
    def wrapper(*args, **kwargs):
        # Set timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
        
        try:
            result = func(*args, **kwargs)
            signal.alarm(0)  # Cancel timeout
            return result
        except TimeoutError:
            return {
                "error": f"Operation timed out after {timeout_seconds} seconds",
                "type": "timeout_error"
            }
    
    return wrapper


def cached_for(seconds: int = 300):
    """
    Decorator to cache function results.
    
    Args:
        seconds: Cache duration in seconds
    
    Returns:
        Cached function
    """
    def decorator(func: Callable):
        cache = {}
        
        def wrapper(*args, **kwargs):
            import time
            
            # Create cache key
            key = str(args) + str(kwargs)
            now = time.time()
            
            # Check if cached result is still valid
            if key in cache:
                result, timestamp = cache[key]
                if now - timestamp < seconds:
                    return result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache[key] = (result, now)
            return result
        
        return wrapper
    return decorator 