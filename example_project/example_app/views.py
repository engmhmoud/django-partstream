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
from django.db import models

# Import the new django_partstream package
from django_partstream import ProgressiveView, lazy, safe_call
from .models import Order, Product
from .serializers import OrderSerializer, ProductSerializer


class OrderAnalyticsView(ProgressiveView):
    """
    Example view using the new ProgressiveView class.

    This view returns multiple parts:
    1. Meta information
    2. Order batches
    3. Analytics data
    4. Summary statistics
    """

    # Configure progressive delivery
    chunk_size = 2  # Return 2 parts per request
    cursor_ttl = 3600  # 1 hour expiration

    def get_parts(self):
        """
        Define response parts for order analytics.
        """
        return [
            # Part 1: Meta information
            (
                "meta",
                {
                    "total_orders": Order.objects.count(),
                    "total_products": Product.objects.count(),
                    "generated_at": datetime.now().isoformat(),
                    "version": "1.0",
                },
            ),
            # Part 2: Recent orders batch
            ("orders_batch", lazy(self.get_recent_orders)),
            # Part 3: Analytics data (simulated computation)
            ("analytics", lazy(self.get_analytics_data)),
            # Part 4: Product inventory
            ("products_inventory", lazy(self.get_products_inventory)),
            # Part 5: Summary statistics
            ("summary", lazy(self.get_summary_stats)),
        ]

    def get_recent_orders(self, request):
        """Get recent orders batch."""
        recent_orders = Order.objects.order_by("-created_at")[:10]
        return OrderSerializer(recent_orders, many=True).data

    def get_analytics_data(self, request):
        """Get analytics data with simulated computation."""
        time.sleep(0.1)  # Simulate computation time
        analytics_data = {
            "total_revenue": sum(order.total_amount for order in Order.objects.all()),
            "orders_by_status": {},
            "top_customers": [],
        }

        # Calculate orders by status
        for status in ["pending", "completed", "cancelled"]:
            analytics_data["orders_by_status"][status] = Order.objects.filter(
                status=status
            ).count()

        return analytics_data

    def get_products_inventory(self, request):
        """Get product inventory."""
        products = Product.objects.all()[:20]
        return ProductSerializer(products, many=True).data

    def get_summary_stats(self, request):
        """Get summary statistics."""
        return {
            "avg_order_value": Order.objects.aggregate(avg=models.Avg("total_amount"))[
                "avg"
            ]
            or 0,
            "low_stock_products": Product.objects.filter(stock__lt=10).count(),
            "processing_time": datetime.now().isoformat(),
        }


class ReportsViewSet(ProgressiveView, ViewSet):
    """
    Example ViewSet demonstrating progressive delivery for reports.
    """

    chunk_size = 3  # Return 3 parts per request

    def get_parts(self):
        """Define parts for reports."""
        return [
            # Part 1: Report metadata
            (
                "report_meta",
                {
                    "report_type": "comprehensive",
                    "generated_by": (
                        self.request.user.username
                        if self.request.user.is_authenticated
                        else "anonymous"
                    ),
                    "timestamp": datetime.now().isoformat(),
                },
            ),
            # Part 2: Sales data
            ("sales_data", lazy(self.get_sales_data)),
            # Part 3: Customer insights
            ("customer_insights", lazy(self.get_customer_insights)),
            # Part 4: Product performance
            ("product_performance", lazy(self.get_product_performance)),
        ]

    def get_sales_data(self, request):
        """Get sales data."""
        return {
            "total_sales": Order.objects.count(),
            "revenue": sum(order.total_amount for order in Order.objects.all()),
            "period": "all_time",
        }

    def get_customer_insights(self, request):
        """Get customer insights."""
        return {
            "total_customers": Order.objects.values("user").distinct().count(),
            "repeat_customers": 0,  # Simplified for example
            "new_customers": 0,
        }

    def get_product_performance(self, request):
        """Get product performance."""
        return {
            "total_products": Product.objects.count(),
            "out_of_stock": Product.objects.filter(stock=0).count(),
            "low_stock": Product.objects.filter(stock__lt=10).count(),
        }

    @action(detail=False, methods=["get"])
    def comprehensive_report(self, request):
        """Custom action using progressive delivery."""
        return self.get(request)

    def list(self, request):
        """List action with progressive delivery."""
        return self.get(request)


class SimpleProgressiveView(ProgressiveView):
    """
    Simple example showing minimal progressive delivery implementation.
    """

    chunk_size = 1  # One part per request

    def get_parts(self):
        """Build simple parts."""
        return [
            ("user_data", {"users": 100, "active": 80}),
            ("system_stats", lazy(self.get_system_stats)),
            ("external_api", lazy(self.get_external_data)),
            ("database_metrics", lazy(self.get_db_metrics)),
        ]

    def get_system_stats(self, request):
        """Get system stats."""
        time.sleep(0.05)  # Simulate processing time
        return {"cpu": 45, "memory": 60, "disk": 30}

    def get_external_data(self, request):
        """Get external API data."""
        time.sleep(0.05)  # Simulate processing time
        return {"weather": "sunny", "temperature": 25}

    def get_db_metrics(self, request):
        """Get database metrics."""
        time.sleep(0.05)  # Simulate processing time
        return {"connections": 50, "queries": 1000}
