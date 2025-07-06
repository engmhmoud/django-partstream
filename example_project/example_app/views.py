"""
Example views demonstrating progressive delivery functionality.
"""

import time
from datetime import datetime
from typing import Generator, Tuple, Any
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.request import Request

# Import our progressive delivery package
# Note: In production, you would install this as a package
# For development, make sure the package is in your Python path
try:
    from drf_progressive_delivery.mixins import ProgressiveDeliveryMixin
except ImportError:
    # Fallback for development
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from drf_progressive_delivery.mixins import ProgressiveDeliveryMixin
from .models import Order, Product
from .serializers import OrderSerializer, ProductSerializer


class OrderAnalyticsView(ProgressiveDeliveryMixin, APIView):
    """
    Example view that demonstrates progressive delivery for order analytics.
    
    This view returns multiple parts:
    1. Meta information
    2. Order batches 
    3. Analytics data
    4. Summary statistics
    """
    
    # Configure progressive delivery
    progressive_chunk_size = 2  # Return 2 parts per request
    progressive_cursor_ttl = 3600  # 1 hour expiration
    
    def build_parts(self, request: Request) -> Generator[Tuple[str, Any], None, None]:
        """
        Build response parts for order analytics.
        
        This method demonstrates how to yield different types of data:
        - Database querysets
        - Computed analytics
        - External API calls (simulated)
        """
        
        # Part 1: Meta information
        yield ("meta", {
            "total_orders": Order.objects.count(),
            "total_products": Product.objects.count(),
            "generated_at": datetime.now().isoformat(),
            "version": "1.0"
        })
        
        # Part 2: Recent orders batch
        recent_orders = Order.objects.order_by('-created_at')[:10]
        yield ("orders_batch", OrderSerializer(recent_orders, many=True).data)
        
        # Part 3: Analytics data (simulated computation)
        time.sleep(0.1)  # Simulate computation time
        analytics_data = {
            "total_revenue": sum(order.total_amount for order in Order.objects.all()),
            "orders_by_status": {},
            "top_customers": []
        }
        
        # Calculate orders by status
        for status in ['pending', 'completed', 'cancelled']:
            analytics_data["orders_by_status"][status] = Order.objects.filter(status=status).count()
        
        yield ("analytics", analytics_data)
        
        # Part 4: Product inventory
        products = Product.objects.all()[:20]
        yield ("products_inventory", ProductSerializer(products, many=True).data)
        
        # Part 5: Summary statistics
        yield ("summary", {
            "avg_order_value": Order.objects.aggregate(avg=models.Avg('total_amount'))['avg'] or 0,
            "low_stock_products": Product.objects.filter(stock__lt=10).count(),
            "processing_time": datetime.now().isoformat()
        })


class ReportsViewSet(ProgressiveDeliveryMixin, ViewSet):
    """
    Example ViewSet demonstrating progressive delivery for reports.
    """
    
    progressive_chunk_size = 3  # Return 3 parts per request
    
    def build_parts(self, request: Request) -> Generator[Tuple[str, Any], None, None]:
        """Build parts for reports."""
        
        # Part 1: Report metadata
        yield ("report_meta", {
            "report_type": "comprehensive",
            "generated_by": request.user.username if request.user.is_authenticated else "anonymous",
            "timestamp": datetime.now().isoformat()
        })
        
        # Part 2: Sales data
        yield ("sales_data", {
            "total_sales": Order.objects.count(),
            "revenue": sum(order.total_amount for order in Order.objects.all()),
            "period": "all_time"
        })
        
        # Part 3: Customer insights
        yield ("customer_insights", {
            "total_customers": Order.objects.values('user').distinct().count(),
            "repeat_customers": 0,  # Simplified for example
            "new_customers": 0
        })
        
        # Part 4: Product performance
        yield ("product_performance", {
            "total_products": Product.objects.count(),
            "out_of_stock": Product.objects.filter(stock=0).count(),
            "low_stock": Product.objects.filter(stock__lt=10).count()
        })
    
    @action(detail=False, methods=['get'])
    def comprehensive_report(self, request):
        """Custom action using progressive delivery."""
        return self.get_progressive_response(request)


class SimpleProgressiveView(ProgressiveDeliveryMixin, APIView):
    """
    Simple example showing minimal progressive delivery implementation.
    """
    
    progressive_chunk_size = 1  # One part per request
    
    def build_parts(self, request: Request) -> Generator[Tuple[str, Any], None, None]:
        """Build simple parts."""
        
        # Simulate different data sources
        data_sources = [
            ("user_data", {"users": 100, "active": 80}),
            ("system_stats", {"cpu": 45, "memory": 60, "disk": 30}),
            ("external_api", {"weather": "sunny", "temperature": 25}),
            ("database_metrics", {"connections": 50, "queries": 1000}),
        ]
        
        for part_name, part_data in data_sources:
            # Simulate processing time
            time.sleep(0.05)
            yield (part_name, part_data)


# Add this import to fix the models.Avg issue
from django.db import models 