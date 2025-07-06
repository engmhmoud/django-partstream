"""
Example views demonstrating both token-based and key-based progressive delivery.
"""

import time
from datetime import datetime
from typing import Dict, Any, List
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response

# Import the new hybrid approach
from django_partstream import HybridProgressiveView, lazy, safe_call, cached_for
from .models import Order, Product
from .serializers import OrderSerializer, ProductSerializer


class DashboardHybridView(HybridProgressiveView):
    """
    Hybrid dashboard view supporting both token-based and key-based access.

    URLs:
    - Token-based: GET /api/dashboard/
    - Key-based: GET /api/dashboard/parts/?keys=meta,orders
    - Manifest: GET /api/dashboard/manifest/
    """

    # Configuration
    chunk_size = 2  # For token-based access
    max_keys_per_request = 5  # For key-based access

    def get_parts_manifest(self) -> Dict[str, Dict[str, Any]]:
        """
        Define the manifest of available parts.
        This is what clients see when they request /manifest/
        """
        return {
            "meta": {
                "size": "small",
                "type": "static",
                "description": "Basic metadata about the dashboard",
                "dependencies": [],
                "estimated_time_ms": 1,
            },
            "orders": {
                "size": "large",
                "type": "lazy",
                "description": "Recent orders from the database",
                "dependencies": ["meta"],
                "estimated_time_ms": 50,
            },
            "analytics": {
                "size": "medium",
                "type": "lazy",
                "description": "Computed analytics data",
                "dependencies": ["orders"],
                "estimated_time_ms": 100,
            },
            "products": {
                "size": "medium",
                "type": "lazy",
                "description": "Product inventory information",
                "dependencies": [],
                "estimated_time_ms": 30,
            },
            "summary": {
                "size": "small",
                "type": "lazy",
                "description": "Summary statistics",
                "dependencies": ["orders", "analytics"],
                "estimated_time_ms": 20,
            },
        }

    def get_parts(self):
        """
        Define the actual parts for progressive delivery.
        This is used by both token-based and key-based access.
        """
        return [
            ("meta", self.get_meta_data()),
            ("orders", lazy(self.get_orders_data)),
            ("analytics", lazy(self.get_analytics_data)),
            ("products", lazy(self.get_products_data)),
            (
                "summary",
                lazy(
                    safe_call(
                        self.get_summary_data, fallback={"error": "Summary unavailable"}
                    )
                ),
            ),
        ]

    def get_meta_data(self):
        """Static metadata - loads immediately."""
        return {
            "dashboard_version": "2.0",
            "generated_at": datetime.now().isoformat(),
            "user": (
                self.request.user.username
                if self.request.user.is_authenticated
                else "anonymous"
            ),
            "total_parts": 5,
        }

    def get_orders_data(self, request):
        """Recent orders - lazy loaded."""
        time.sleep(0.05)  # Simulate database query time
        recent_orders = Order.objects.order_by("-created_at")[:20]
        return {
            "orders": OrderSerializer(recent_orders, many=True).data,
            "total_count": Order.objects.count(),
        }

    def get_analytics_data(self, request):
        """Analytics computation - lazy loaded."""
        time.sleep(0.1)  # Simulate computation time

        # Simulate expensive analytics computation
        orders = Order.objects.all()
        analytics = {
            "total_revenue": sum(order.total_amount for order in orders),
            "orders_by_status": {
                "pending": orders.filter(status="pending").count(),
                "completed": orders.filter(status="completed").count(),
                "cancelled": orders.filter(status="cancelled").count(),
            },
            "average_order_value": orders.aggregate(avg=models.Avg("total_amount"))[
                "avg"
            ]
            or 0,
            "computation_time": datetime.now().isoformat(),
        }

        return analytics

    def get_products_data(self, request):
        """Product inventory - lazy loaded."""
        time.sleep(0.03)  # Simulate database query time
        products = Product.objects.all()[:50]
        return {
            "products": ProductSerializer(products, many=True).data,
            "low_stock_count": Product.objects.filter(stock__lt=10).count(),
            "out_of_stock_count": Product.objects.filter(stock=0).count(),
        }

    @cached_for(300)  # Cache for 5 minutes
    def get_summary_data(self, request):
        """Summary statistics - cached and lazy loaded."""
        time.sleep(0.02)  # Simulate computation time

        return {
            "total_orders": Order.objects.count(),
            "total_products": Product.objects.count(),
            "total_revenue": sum(order.total_amount for order in Order.objects.all()),
            "active_customers": Order.objects.values("user").distinct().count(),
            "summary_generated_at": datetime.now().isoformat(),
        }


class ComparisonView(APIView):
    """
    View to demonstrate the differences between token-based and key-based approaches.
    """

    def get(self, request):
        """
        Return a comparison of both approaches.
        """
        base_url = request.build_absolute_uri("/api/dashboard/")

        return Response(
            {
                "progressive_delivery_approaches": {
                    "token_based": {
                        "description": "Sequential loading with encrypted cursors",
                        "use_case": "When you want to control the loading order and prevent expensive operations",
                        "endpoints": {
                            "first_request": base_url,
                            "subsequent_requests": base_url
                            + "?cursor=<encrypted_cursor>",
                        },
                        "example_flow": [
                            f"1. GET {base_url}",
                            "2. Receive first chunk + cursor",
                            f"3. GET {base_url}?cursor=<encrypted_cursor>",
                            "4. Receive next chunk + cursor",
                            "5. Continue until cursor is null",
                        ],
                        "pros": [
                            "Secure - prevents tampering with cursors",
                            "Controlled loading order",
                            "Good for workflows that need sequence",
                            "Server controls when expensive operations run",
                        ],
                        "cons": [
                            "Less flexible for clients",
                            "Cannot parallelize requests",
                            "Sequential only",
                        ],
                    },
                    "key_based": {
                        "description": "Flexible loading with specific part keys",
                        "use_case": "When clients know what they want and can handle parallelization",
                        "endpoints": {
                            "manifest": base_url + "manifest/",
                            "specific_parts": base_url + "parts/?keys=meta,orders",
                            "single_part": base_url + "parts/?keys=analytics",
                        },
                        "example_flow": [
                            f"1. GET {base_url}manifest/ (discover available parts)",
                            f"2. GET {base_url}parts/?keys=meta,orders (get specific parts)",
                            f"3. GET {base_url}parts/?keys=analytics (get other parts in parallel)",
                        ],
                        "pros": [
                            "Very flexible for clients",
                            "Can parallelize requests",
                            "Better for caching individual parts",
                            "More RESTful approach",
                        ],
                        "cons": [
                            "Clients can trigger expensive operations",
                            "More complex security considerations",
                            "Need to manage dependencies manually",
                        ],
                    },
                    "hybrid_approach": {
                        "description": "Best of both worlds - supports both patterns",
                        "recommendation": "Use token-based for sequential workflows, key-based for flexible access",
                        "endpoints": {
                            "token_based": base_url,
                            "key_based": base_url + "parts/",
                            "manifest": base_url + "manifest/",
                        },
                    },
                },
                "performance_comparison": {
                    "token_based": {
                        "initial_response_time": "Fast (only loads chunk_size parts)",
                        "memory_usage": "Low (only current chunk in memory)",
                        "parallelization": "No",
                        "client_complexity": "Low",
                    },
                    "key_based": {
                        "initial_response_time": "Variable (depends on requested keys)",
                        "memory_usage": "Variable (depends on requested parts)",
                        "parallelization": "Yes",
                        "client_complexity": "Medium",
                    },
                },
                "security_comparison": {
                    "token_based": {
                        "cursor_security": "Encrypted cursors prevent tampering",
                        "rate_limiting": "Built-in progressive rate limiting",
                        "attack_surface": "Low",
                    },
                    "key_based": {
                        "parameter_validation": "Validates requested keys",
                        "rate_limiting": "Limits keys per request",
                        "attack_surface": "Medium (clients can probe for keys)",
                    },
                },
            }
        )


# Import fix for models
from django.db import models
