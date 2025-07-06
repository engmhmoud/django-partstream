"""
Example views demonstrating the new Django-friendly progressive delivery approaches.
"""

from datetime import datetime
from django.db.models import Sum, Avg, Count
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.request import Request

# Import our progressive delivery package
try:
    from drf_progressive_delivery.mixins_v2 import (
        ProgressiveDeliveryMixinV2, 
        RegistryProgressiveView,
        MethodProgressiveView,
        DecoratorProgressiveView
    )
    from drf_progressive_delivery.parts import (
        ProgressivePartsRegistry,
        ModelPart,
        ComputedPart,
        progressive_part,
        progressive_meta,
        progressive_data
    )
except ImportError:
    # Fallback for development
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from drf_progressive_delivery.mixins_v2 import (
        ProgressiveDeliveryMixinV2, 
        RegistryProgressiveView,
        MethodProgressiveView,
        DecoratorProgressiveView
    )
    from drf_progressive_delivery.parts import (
        ProgressivePartsRegistry,
        ModelPart,
        ComputedPart,
        progressive_part,
        progressive_meta,
        progressive_data
    )

from .models import Order, Product
from .serializers import OrderSerializer, ProductSerializer


# ===== Approach 1: Registry-based (Recommended) =====

class DashboardRegistryView(RegistryProgressiveView, APIView):
    """
    Dashboard view using the registry approach.
    
    This is the most flexible and Django-friendly approach.
    """
    
    progressive_chunk_size = 2
    
    def get_parts_registry(self):
        """Define response parts using the registry."""
        registry = ProgressivePartsRegistry()
        
        # Static metadata (loaded immediately)
        registry.add_static("meta", {
            "dashboard_type": "analytics",
            "generated_at": datetime.now().isoformat(),
            "version": "2.0"
        })
        
        # Model data with lazy loading and serialization
        registry.add_model(
            name="recent_orders",
            queryset=lambda request, **kwargs: Order.objects.order_by('-created_at')[:10],
            serializer_class=OrderSerializer,
            lazy=True
        )
        
        # Another model part
        registry.add_model(
            name="products_inventory", 
            queryset=Product.objects.all(),
            serializer_class=ProductSerializer,
            lazy=True
        )
        
        # Computed analytics (expensive operation, lazy loaded)
        registry.add_function("analytics", self._compute_analytics, lazy=True)
        
        # Summary data
        registry.add_function("summary", self._compute_summary, lazy=True)
        
        return registry
    
    def _compute_analytics(self, request, **kwargs):
        """Compute analytics data (expensive operation)."""
        return {
            "total_revenue": float(Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0),
            "total_orders": Order.objects.count(),
            "avg_order_value": float(Order.objects.aggregate(Avg('total_amount'))['total_amount__avg'] or 0),
            "orders_by_status": {
                "pending": Order.objects.filter(status="pending").count(),
                "completed": Order.objects.filter(status="completed").count(),
                "cancelled": Order.objects.filter(status="cancelled").count(),
            }
        }
    
    def _compute_summary(self, request, **kwargs):
        """Compute summary data."""
        return {
            "low_stock_products": Product.objects.filter(stock__lt=10).count(),
            "total_products": Product.objects.count(),
            "processing_time": datetime.now().isoformat()
        }


# ===== Approach 2: Method-based =====

class DashboardMethodView(MethodProgressiveView, APIView):
    """
    Dashboard view using the method-based approach.
    
    Override specific methods to provide data.
    """
    
    progressive_chunk_size = 2
    
    def add_meta_data(self, request, **kwargs):
        """Provide metadata for the response."""
        return {
            "dashboard_type": "method_based",
            "generated_at": datetime.now().isoformat(),
            "user": request.user.username if request.user.is_authenticated else "anonymous",
            "version": "2.0"
        }
    
    def add_model_data(self, request, **kwargs):
        """Provide model-based data."""
        return [
            {
                "orders": OrderSerializer(
                    Order.objects.order_by('-created_at')[:10], 
                    many=True
                ).data
            },
            {
                "products": ProductSerializer(
                    Product.objects.all()[:20], 
                    many=True
                ).data
            }
        ]
    
    def add_computed_data(self, request, **kwargs):
        """Provide computed/analytics data."""
        analytics = {
            "revenue": float(Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0),
            "orders_count": Order.objects.count(),
            "products_count": Product.objects.count()
        }
        
        summary = {
            "alerts": Product.objects.filter(stock__lt=5).count(),
            "timestamp": datetime.now().isoformat()
        }
        
        return [
            {"analytics": analytics},
            {"summary": summary}
        ]


# ===== Approach 3: Decorator-based =====

class DashboardDecoratorView(DecoratorProgressiveView, APIView):
    """
    Dashboard view using decorators.
    
    Use decorators to mark methods as progressive parts.
    """
    
    progressive_chunk_size = 2
    
    @progressive_meta
    def get_meta_info(self, request, **kwargs):
        """Get metadata (loaded immediately)."""
        return {
            "dashboard_type": "decorator_based",
            "generated_at": datetime.now().isoformat(),
            "version": "2.0"
        }
    
    @progressive_data("orders")
    def get_orders_data(self, request, **kwargs):
        """Get orders data (lazy loaded)."""
        orders = Order.objects.order_by('-created_at')[:10]
        return OrderSerializer(orders, many=True).data
    
    @progressive_data("products")
    def get_products_data(self, request, **kwargs):
        """Get products data (lazy loaded)."""
        products = Product.objects.all()[:20]
        return ProductSerializer(products, many=True).data
    
    @progressive_part("analytics", lazy=True)
    def get_analytics_data(self, request, **kwargs):
        """Get analytics data (lazy loaded)."""
        return {
            "total_revenue": float(Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0),
            "avg_order_value": float(Order.objects.aggregate(Avg('total_amount'))['total_amount__avg'] or 0),
            "orders_by_status": {
                status: Order.objects.filter(status=status).count()
                for status in ['pending', 'completed', 'cancelled']
            }
        }
    
    @progressive_part("summary", lazy=True)
    def get_summary_data(self, request, **kwargs):
        """Get summary data (lazy loaded)."""
        return {
            "low_stock_alerts": Product.objects.filter(stock__lt=10).count(),
            "out_of_stock": Product.objects.filter(stock=0).count(),
            "total_products": Product.objects.count(),
            "timestamp": datetime.now().isoformat()
        }


# ===== Custom Progressive Part Example =====

class AnalyticsPart(ComputedPart):
    """
    Custom progressive part for analytics.
    
    This shows how to create reusable progressive parts.
    """
    
    def __init__(self, name="analytics", lazy=True):
        super().__init__(name, lazy)
    
    def get_data(self, request, **kwargs):
        """Compute analytics data."""
        # Simulate expensive computation
        import time
        time.sleep(0.1)
        
        return {
            "computed_at": datetime.now().isoformat(),
            "total_orders": Order.objects.count(),
            "total_revenue": float(Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0),
            "customer_count": Order.objects.values('user').distinct().count(),
            "avg_order_value": float(Order.objects.aggregate(Avg('total_amount'))['total_amount__avg'] or 0)
        }


class CustomPartsView(ProgressiveDeliveryMixinV2, APIView):
    """
    Example using custom progressive parts.
    """
    
    progressive_chunk_size = 2
    
    def get_parts_registry(self):
        """Use custom progressive parts."""
        registry = ProgressivePartsRegistry()
        
        # Add custom analytics part
        registry.register(AnalyticsPart("analytics", lazy=True))
        
        # Add other parts
        registry.add_static("meta", {
            "view_type": "custom_parts",
            "timestamp": datetime.now().isoformat()
        })
        
        registry.add_model(
            "orders",
            queryset=Order.objects.all()[:5],
            serializer_class=OrderSerializer
        )
        
        return registry


# ===== Simple Example =====

class SimpleProgressiveView(ProgressiveDeliveryMixinV2, APIView):
    """
    Simplest possible progressive delivery view.
    
    Just override add_model_data or add_computed_data.
    """
    
    progressive_chunk_size = 1  # One part per request
    
    def add_model_data(self, request, **kwargs):
        """Simple model data."""
        return [
            {"users": {"count": 100, "active": 80}},
            {"orders": {"count": Order.objects.count()}},
            {"products": {"count": Product.objects.count()}},
            {"system": {"status": "healthy", "version": "1.0"}}
        ]


# ===== ViewSet Example =====

class ReportsViewSetV2(ProgressiveDeliveryMixinV2, ViewSet):
    """
    ViewSet example with progressive delivery.
    """
    
    progressive_chunk_size = 3
    
    def get_parts_registry(self):
        """Registry for reports."""
        registry = ProgressivePartsRegistry()
        
        registry.add_static("report_meta", {
            "report_type": "comprehensive",
            "generated_at": datetime.now().isoformat()
        })
        
        registry.add_function("sales_data", self._get_sales_data)
        registry.add_function("customer_data", self._get_customer_data)
        registry.add_function("product_data", self._get_product_data)
        
        return registry
    
    def _get_sales_data(self, request, **kwargs):
        """Get sales data."""
        return {
            "total_revenue": float(Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0),
            "total_orders": Order.objects.count(),
            "period": "all_time"
        }
    
    def _get_customer_data(self, request, **kwargs):
        """Get customer data."""
        return {
            "total_customers": Order.objects.values('user').distinct().count(),
            "repeat_customers": 0,  # Simplified
            "new_customers": 0
        }
    
    def _get_product_data(self, request, **kwargs):
        """Get product data."""
        return {
            "total_products": Product.objects.count(),
            "low_stock": Product.objects.filter(stock__lt=10).count(),
            "out_of_stock": Product.objects.filter(stock=0).count()
        }
    
    @action(detail=False, methods=['get'])
    def comprehensive(self, request):
        """Custom action with progressive delivery."""
        return self.get_progressive_response(request) 