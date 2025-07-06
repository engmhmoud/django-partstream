"""
Django REST Framework mixin for progressive delivery.
"""

from typing import Generator, Tuple, Any, Dict, Optional, List
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status

from .cursors import CursorManager
from .exceptions import InvalidCursorError, CursorExpiredError, ProgressiveDeliveryError


class ProgressiveDeliveryMixin:
    """
    Mixin for DRF views to provide progressive delivery of large JSON responses.
    
    Views using this mixin should implement the `build_parts()` method that yields
    response parts as (name, data) tuples.
    """
    
    # Configuration attributes
    progressive_chunk_size: int = 2
    progressive_cursor_ttl: Optional[int] = None  # No expiration by default
    progressive_cursor_param: str = 'cursor'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cursor_manager = CursorManager(ttl=self.progressive_cursor_ttl)
    
    def build_parts(self, request: Request) -> Generator[Tuple[str, Any], None, None]:
        """
        Generate response parts. Must be implemented by subclasses.
        
        Args:
            request: The HTTP request object
            
        Yields:
            Tuples of (part_name, part_data)
            
        Example:
            yield ("meta", {"total": 100, "created": datetime.now()})
            yield ("orders_batch", [order1, order2, order3])
            yield ("analytics", {"revenue": 1000, "orders": 50})
        """
        raise NotImplementedError("Subclasses must implement build_parts() method")
    
    def get_progressive_response(self, request: Request) -> Response:
        """
        Get a progressive delivery response.
        
        Args:
            request: The HTTP request object
            
        Returns:
            Response with results and cursor
        """
        try:
            # Get cursor from request
            cursor = request.GET.get(self.progressive_cursor_param)
            start_index = 0
            
            # If cursor provided, decode it to get the starting position
            if cursor:
                try:
                    cursor_data = self.cursor_manager.decode_cursor(cursor)
                    start_index = cursor_data.get('start_index', 0)
                except (InvalidCursorError, CursorExpiredError) as e:
                    return Response(
                        {"error": str(e)},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Generate all parts
            all_parts = list(self.build_parts(request))
            
            # Get the chunk of parts for this request
            end_index = start_index + self.progressive_chunk_size
            current_parts = all_parts[start_index:end_index]
            
            # Format response data
            results = []
            for part_name, part_data in current_parts:
                results.append({part_name: part_data})
            
            # Create response
            response_data = {
                "results": results,
                "cursor": None
            }
            
            # Add cursor if there are more parts
            if end_index < len(all_parts):
                next_cursor_data = {"start_index": end_index}
                response_data["cursor"] = self.cursor_manager.create_cursor(next_cursor_data)
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Progressive delivery error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def list(self, request: Request, *args, **kwargs) -> Response:
        """
        Override the list method to use progressive delivery.
        
        This method integrates with DRF's ViewSet pattern.
        """
        return self.get_progressive_response(request)
    
    def get(self, request: Request, *args, **kwargs) -> Response:
        """
        Override the get method to use progressive delivery.
        
        This method integrates with DRF's APIView pattern.
        """
        return self.get_progressive_response(request)


class ProgressiveDeliveryAPIView(ProgressiveDeliveryMixin):
    """
    Base API view with progressive delivery capabilities.
    
    Inherit from this class and implement build_parts() to get progressive delivery.
    """
    
    def get(self, request: Request, *args, **kwargs) -> Response:
        """Handle GET requests with progressive delivery."""
        return self.get_progressive_response(request)


class ProgressiveDeliveryViewSet(ProgressiveDeliveryMixin):
    """
    Base ViewSet with progressive delivery capabilities.
    
    Inherit from this class and implement build_parts() to get progressive delivery.
    """
    
    def list(self, request: Request, *args, **kwargs) -> Response:
        """Handle list requests with progressive delivery."""
        return self.get_progressive_response(request)
    
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        """Handle retrieve requests with progressive delivery."""
        return self.get_progressive_response(request) 