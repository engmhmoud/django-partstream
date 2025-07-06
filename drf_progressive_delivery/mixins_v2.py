"""
Improved Django REST Framework mixin for progressive delivery.

This version provides a more Django-friendly API while still supporting
the generator-based approach for backward compatibility.
"""

from typing import Generator, Tuple, Any, Dict, Optional, List, Union
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from datetime import datetime

from .cursors import CursorManager
from .exceptions import InvalidCursorError, CursorExpiredError, ProgressiveDeliveryError
from .parts import ProgressivePartsRegistry, ProgressivePart, FunctionPart, ModelPart, StaticPart


class ProgressiveDeliveryMixinV2:
    """
    Improved mixin for DRF views with Django-friendly progressive delivery.
    
    This version supports multiple ways to define response parts:
    1. Registry-based approach (recommended)
    2. Method-based approach with decorators
    3. Legacy generator approach (for backward compatibility)
    """
    
    # Configuration attributes
    progressive_chunk_size: int = 2
    progressive_cursor_ttl: Optional[int] = None
    progressive_cursor_param: str = 'cursor'
    progressive_use_lazy_loading: bool = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cursor_manager = CursorManager(ttl=self.progressive_cursor_ttl)
        self._parts_registry: Optional[ProgressivePartsRegistry] = None
        self._method_parts: Optional[List[ProgressivePart]] = None
    
    # ===== NEW: Registry-based approach =====
    
    def get_parts_registry(self) -> ProgressivePartsRegistry:
        """
        Get or create the parts registry.
        
        Override this method to define your response parts using the registry.
        
        Example:
            def get_parts_registry(self):
                registry = ProgressivePartsRegistry()
                
                # Add static metadata
                registry.add_static("meta", {"version": "1.0", "timestamp": timezone.now()})
                
                # Add model data with serializer
                registry.add_model("orders", 
                    queryset=Order.objects.filter(status='active'),
                    serializer_class=OrderSerializer
                )
                
                # Add computed data
                registry.add_function("analytics", self.get_analytics_data)
                
                return registry
        """
        if self._parts_registry is None:
            self._parts_registry = ProgressivePartsRegistry()
            
            # Try to auto-discover decorated methods
            self._autodiscover_method_parts()
        
        return self._parts_registry
    
    def _autodiscover_method_parts(self):
        """Automatically discover methods decorated with @progressive_part."""
        if self._method_parts is not None:
            return
        
        self._method_parts = []
        
        # Look for methods decorated with progressive_part
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, '_progressive_part') and attr._progressive_part:
                name = attr._progressive_name
                lazy = attr._progressive_lazy
                
                # Create a function part for this method
                def method_wrapper(request, method=attr, **kwargs):
                    return method(request, **kwargs)
                
                part = FunctionPart(name, method_wrapper, lazy)
                self._method_parts.append(part)
                self._parts_registry.register(part)
    
    # ===== NEW: Helper methods for common patterns =====
    
    def add_meta_data(self, request, **kwargs) -> Dict[str, Any]:
        """
        Override this method to provide metadata.
        
        This is automatically called if no other meta part is defined.
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "version": "1.0"
        }
    
    def add_model_data(self, request, **kwargs) -> List[Dict[str, Any]]:
        """
        Override this method to provide model-based data.
        
        Return a list of dictionaries, each containing a single key-value pair
        where the key is the part name and the value is the data.
        
        Example:
            return [
                {"orders": OrderSerializer(Order.objects.all(), many=True).data},
                {"products": ProductSerializer(Product.objects.all(), many=True).data}
            ]
        """
        return []
    
    def add_computed_data(self, request, **kwargs) -> List[Dict[str, Any]]:
        """
        Override this method to provide computed/analytics data.
        
        Example:
            return [
                {"analytics": self.calculate_analytics()},
                {"summary": self.calculate_summary()}
            ]
        """
        return []
    
    # ===== Legacy: Generator approach (for backward compatibility) =====
    
    def build_parts(self, request: Request) -> Generator[Tuple[str, Any], None, None]:
        """
        Legacy generator-based approach (for backward compatibility).
        
        If you override this method, it will be used instead of the registry approach.
        """
        return
        yield  # This makes it a generator function
    
    # ===== Core progressive delivery logic =====
    
    def get_all_parts(self, request: Request) -> List[Dict[str, Any]]:
        """
        Get all response parts using the appropriate method.
        
        Priority:
        1. Generator approach (if build_parts is overridden)
        2. Registry approach (recommended)
        3. Method-based approach (if methods are overridden)
        """
        # Check if build_parts is overridden (legacy approach)
        try:
            generator = self.build_parts(request)
            if generator is not None:
                parts_list = []
                for name, data in generator:
                    parts_list.append({name: data})
                if parts_list:  # If generator produced results, use them
                    return parts_list
        except (TypeError, StopIteration):
            pass
        
        # Use registry approach
        registry = self.get_parts_registry()
        if len(registry) > 0:
            return registry.get_parts(request)
        
        # Fallback to method-based approach
        return self._get_method_based_parts(request)
    
    def _get_method_based_parts(self, request: Request) -> List[Dict[str, Any]]:
        """Get parts using method-based approach as fallback."""
        parts = []
        
        # Add meta data
        meta_data = self.add_meta_data(request)
        if meta_data:
            parts.append({"meta": meta_data})
        
        # Add model data
        model_parts = self.add_model_data(request)
        parts.extend(model_parts)
        
        # Add computed data
        computed_parts = self.add_computed_data(request)
        parts.extend(computed_parts)
        
        return parts
    
    def get_progressive_response(self, request: Request) -> Response:
        """
        Get a progressive delivery response.
        
        This works the same as before but now supports multiple approaches
        for defining response parts.
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
            
            # Generate all parts using the appropriate method
            all_parts = self.get_all_parts(request)
            
            # Get the chunk of parts for this request
            end_index = start_index + self.progressive_chunk_size
            current_parts = all_parts[start_index:end_index]
            
            # Create response
            response_data = {
                "results": current_parts,
                "cursor": None,
                "meta": {
                    "total_parts": len(all_parts),
                    "current_chunk": len(current_parts),
                    "has_more": end_index < len(all_parts)
                }
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
        """Override the list method to use progressive delivery."""
        return self.get_progressive_response(request)
    
    def get(self, request: Request, *args, **kwargs) -> Response:
        """Override the get method to use progressive delivery."""
        return self.get_progressive_response(request)


# Convenience classes for different approaches

class RegistryProgressiveView(ProgressiveDeliveryMixinV2):
    """
    Base view for registry-based progressive delivery.
    
    Override get_parts_registry() to define your parts.
    """
    pass


class MethodProgressiveView(ProgressiveDeliveryMixinV2):
    """
    Base view for method-based progressive delivery.
    
    Override add_meta_data(), add_model_data(), add_computed_data() methods.
    """
    pass


class DecoratorProgressiveView(ProgressiveDeliveryMixinV2):
    """
    Base view for decorator-based progressive delivery.
    
    Use @progressive_part, @progressive_meta, @progressive_data decorators.
    """
    pass 