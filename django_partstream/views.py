"""
Django views for progressive delivery.
"""

import logging
from typing import List, Dict, Any, Tuple
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .parts import ProgressivePart
from .cursors import CursorManager
from .formatters import ProgressiveResponseFormatter
from .security import RateLimiter, RequestValidator, AuditLogger
from .performance import PerformanceMonitor
from .exceptions import (
    ProgressiveDeliveryError,
    RateLimitExceededError,
    CursorExpiredError,
    InvalidCursorError,
    ValidationError
)
from .utils import LazyFunction

logger = logging.getLogger(__name__)


class ProgressiveView(APIView):
    """
    Simplified progressive delivery view using token-based approach.

    This is the main class for 80% of progressive delivery use cases.
    Override get_parts() to define your response parts.

    Example:
        class MyAPI(ProgressiveView):
            def get_parts(self):
                return [
                    ("meta", {"timestamp": timezone.now()}),
                    ("data", lazy(self.get_data))
                ]

            def get_data(self, request):
                return {"users": User.objects.count()}
    """

    # Configuration
    chunk_size = 2  # Number of parts to return per request
    cursor_ttl = 3600  # Cursor time-to-live in seconds (1 hour)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cursor_manager = CursorManager(ttl=self.cursor_ttl)

    def get_parts(self) -> List[Tuple[str, Any]]:
        """
        Define the parts of your progressive response.

        Override this method to return a list of (name, data) tuples.
        Use lazy() for expensive operations.

        Returns:
            List of (part_name, part_data) tuples

        Example:
            return [
                ("meta", {"timestamp": timezone.now()}),
                ("orders", lazy(self.get_orders)),
                ("analytics", lazy(safe_call(self.get_analytics, fallback={"error": "N/A"})))
            ]
        """
        raise NotImplementedError("Subclasses must implement get_parts()")

    def get(self, request, *args, **kwargs):
        """
        Handle GET request with progressive delivery.

        Args:
            request: Django request object

        Returns:
            JSON response with progressive data and cursor
        """
        try:
            # Get cursor from request
            cursor = request.GET.get('cursor')
            start_index = 0

            if cursor:
                try:
                    cursor_data = self.cursor_manager.decode_cursor(cursor)
                    start_index = cursor_data.get('index', 0)
                except (InvalidCursorError, CursorExpiredError) as e:
                    logger.warning(f"Invalid cursor: {e}")
                    return Response(
                        {"error": str(e)},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Get all parts
            try:
                all_parts = self.get_parts()
            except Exception as e:
                logger.error(f"Error getting parts: {e}")
                raise ProgressiveDeliveryError("Failed to retrieve parts")

            if not all_parts:
                all_parts = []

            # Calculate chunk boundaries
            end_index = min(start_index + self.chunk_size, len(all_parts))
            chunk_parts = all_parts[start_index:end_index]

            # Process the chunk
            results = []
            for part_name, part_data in chunk_parts:
                try:
                    # Execute lazy functions
                    if isinstance(part_data, LazyFunction):
                        processed_data = part_data(request)
                    else:
                        processed_data = part_data

                    results.append({part_name: processed_data})

                except Exception as e:
                    logger.error(f"Error processing part '{part_name}': {e}")
                    # Continue with other parts, include error info
                    results.append({
                        part_name: {
                            "error": f"Failed to load {part_name}",
                            "message": str(e),
                            "timestamp": timezone.now().isoformat()
                        }
                    })

            # Generate next cursor if more parts available
            next_cursor = None
            if end_index < len(all_parts):
                next_cursor = self.cursor_manager.create_cursor({
                    'index': end_index,
                    'user_id': getattr(request.user, 'id', None)
                })

            # Build response
            response_data = {
                'results': results,
                'cursor': next_cursor,
                'meta': {
                    'total_parts': len(all_parts),
                    'current_chunk_size': len(results),
                    'has_more': next_cursor is not None,
                    'timestamp': timezone.now().isoformat()
                }
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except ProgressiveDeliveryError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in progressive view: {e}")
            return Response({"error": "Internal server error",
                             "message": "An unexpected error occurred during progressive delivery"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, *args, **kwargs):
        """Handle POST requests the same way as GET."""
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Get additional context data for parts.
        Override this to provide context to your part functions.
        """
        return {}

    def handle_error(self, error: Exception, part_name: str) -> Dict[str, Any]:
        """
        Handle errors in part processing.
        Override this to customize error handling.

        Args:
            error: The exception that occurred
            part_name: Name of the part that failed

        Returns:
            Dictionary with error information
        """
        return {
            "error": f"Failed to load {part_name}",
            "message": str(error),
            "timestamp": timezone.now().isoformat()
        }


class SimpleProgressiveView(ProgressiveView):
    """
    Even simpler progressive view for basic use cases.

    Just override get_data() to return your parts list.
    """

    def get_data(self) -> List[Dict[str, Any]]:
        """
        Return a simple list of data dictionaries.

        Example:
            return [
                {"users": {"count": 100}},
                {"orders": {"count": 50}},
                {"products": {"count": 200}}
            ]
        """
        raise NotImplementedError("Subclasses must implement get_data()")

    def get_parts(self) -> List[Tuple[str, Any]]:
        """Convert simple data to parts format."""
        data_list = self.get_data()
        parts = []

        for i, data_dict in enumerate(data_list):
            for key, value in data_dict.items():
                parts.append((key, value))

        return parts


class ConditionalProgressiveView(ProgressiveView):
    """
    Progressive view with conditional parts based on permissions.
    """

    def get_public_parts(self) -> List[Tuple[str, Any]]:
        """Get parts available to all users."""
        return []

    def get_authenticated_parts(self) -> List[Tuple[str, Any]]:
        """Get parts available to authenticated users."""
        return []

    def get_staff_parts(self) -> List[Tuple[str, Any]]:
        """Get parts available to staff users."""
        return []

    def get_parts(self) -> List[Tuple[str, Any]]:
        """Build parts list based on user permissions."""
        parts = []

        # Always include public parts
        parts.extend(self.get_public_parts())

        # Add authenticated user parts
        if self.request.user.is_authenticated:
            parts.extend(self.get_authenticated_parts())

        # Add staff parts
        if self.request.user.is_staff:
            parts.extend(self.get_staff_parts())

        return parts


class CachedProgressiveView(ProgressiveView):
    """
    Progressive view with built-in caching support.
    """

    cache_ttl = 300  # 5 minutes default cache TTL

    def get_cache_key(self, part_name: str) -> str:
        """
        Generate cache key for a part.

        Args:
            part_name: Name of the part

        Returns:
            Cache key string
        """
        user_id = getattr(self.request.user, 'id', 'anonymous')
        return f"partstream_{part_name}_{user_id}_{self.__class__.__name__}"

    def get_cached_part(self, part_name: str, part_func: Any) -> Any:
        """
        Get part data with caching.

        Args:
            part_name: Name of the part
            part_func: Function or data to cache

        Returns:
            Cached or fresh part data
        """
        if not isinstance(part_func, LazyFunction):
            return part_func

        from django.core.cache import cache

        cache_key = self.get_cache_key(part_name)
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            logger.info(f"Cache hit for part: {part_name}")
            return cached_result

        # Execute function and cache result
        result = part_func(self.request)
        cache.set(cache_key, result, self.cache_ttl)
        logger.info(f"Cached part: {part_name} for {self.cache_ttl}s")

        return result


class HybridProgressiveView(ProgressiveView):
    """
    Hybrid progressive delivery view supporting both token-based and key-based access.

    Supports:
    - Token-based: GET /api/data/ or GET /api/data/?cursor=token
    - Key-based: GET /api/data/parts/?keys=meta,orders
    - Manifest: GET /api/data/manifest/

    Example:
        class MyAPI(HybridProgressiveView):
            def get_parts_manifest(self):
                return {
                    "meta": {"size": "small", "dependencies": []},
                    "orders": {"size": "large", "dependencies": ["meta"]},
                    "analytics": {"size": "medium", "dependencies": ["orders"]}
                }

            def get_parts(self):
                return [
                    ("meta", {"timestamp": timezone.now()}),
                    ("orders", lazy(self.get_orders)),
                    ("analytics", lazy(self.get_analytics))
                ]
    """

    # Security settings for key-based access
    max_keys_per_request = 10
    allowed_keys = None  # Override to restrict available keys

    def get_parts_manifest(self) -> Dict[str, Dict[str, Any]]:
        """
        Get manifest of available parts.

        Returns:
            Dictionary with part metadata
        """
        # Default implementation - extract from get_parts()
        parts = self.get_parts()
        manifest = {}

        for i, (part_name, part_data) in enumerate(parts):
            is_lazy = isinstance(part_data, LazyFunction)
            manifest[part_name] = {
                "key": part_name,
                "index": i,
                "type": "lazy" if is_lazy else "static",
                "size": "unknown",
                "dependencies": []
            }

        return manifest

    def get_parts_by_keys(self, keys: List[str], request) -> Dict[str, Any]:
        """
        Get specific parts by their keys.

        Args:
            keys: List of part keys to retrieve
            request: Django request object

        Returns:
            Dictionary with requested parts
        """
        # Security check
        if len(keys) > self.max_keys_per_request:
            raise ProgressiveDeliveryError(
                f"Too many keys requested. Maximum: {
                    self.max_keys_per_request}")

        # Get all parts
        all_parts = self.get_parts()
        parts_dict = {name: data for name, data in all_parts}

        # Filter by requested keys
        results = {}
        for key in keys:
            if key not in parts_dict:
                results[key] = {"error": f"Part '{key}' not found"}
                continue

            # Check if key is allowed
            if self.allowed_keys and key not in self.allowed_keys:
                results[key] = {"error": f"Part '{key}' not allowed"}
                continue

            try:
                part_data = parts_dict[key]
                if isinstance(part_data, LazyFunction):
                    results[key] = part_data(request)
                else:
                    results[key] = part_data
            except Exception as e:
                logger.error(f"Error loading part '{key}': {e}")
                results[key] = {
                    "error": f"Failed to load {key}",
                    "message": str(e),
                    "timestamp": timezone.now().isoformat()
                }

        return results

    def get(self, request, *args, **kwargs):
        """
        Handle GET request with both token-based and key-based support.
        """
        # Check if this is a manifest request
        if request.path.endswith('/manifest/'):
            return self.get_manifest(request)

        # Check if this is a key-based parts request
        if request.path.endswith('/parts/'):
            return self.get_parts_by_keys_endpoint(request)

        # Default to token-based approach
        return super().get(request, *args, **kwargs)

    def get_manifest(self, request):
        """Handle manifest requests."""
        try:
            manifest = self.get_parts_manifest()
            return Response({
                "parts": manifest,
                "access_methods": {
                    "token_based": f"{request.build_absolute_uri('.')}",
                    "key_based": f"{request.build_absolute_uri('./parts/')}",
                    "manifest": f"{request.build_absolute_uri('./manifest/')}"
                },
                "timestamp": timezone.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error generating manifest: {e}")
            return Response(
                {"error": "Failed to generate manifest"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_parts_by_keys_endpoint(self, request):
        """Handle key-based parts requests."""
        try:
            keys_param = request.GET.get('keys', '')
            if not keys_param:
                return Response(
                    {"error": "Missing 'keys' parameter"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            keys = [k.strip() for k in keys_param.split(',') if k.strip()]
            if not keys:
                return Response(
                    {"error": "No valid keys provided"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            results = self.get_parts_by_keys(keys, request)

            return Response({
                "results": results,
                "requested_keys": keys,
                "timestamp": timezone.now().isoformat()
            })

        except ProgressiveDeliveryError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in key-based request: {e}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
