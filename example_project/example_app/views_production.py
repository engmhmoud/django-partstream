"""
Production-ready example views showcasing all django-partstream features
"""

import logging
import time
from decimal import Decimal
from typing import Dict, Any, List

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from django_partstream import ProgressiveView, lazy, safe_call, cached_for, with_timeout
from .models import Order, Product


logger = logging.getLogger(__name__)


class ProductionEcommerceAPI(ProgressiveView):
    """
    Production-ready e-commerce dashboard with all best practices:
    - Performance optimization
    - Error handling
    - Security
    - Monitoring
    - Caching
    - Rate limiting
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    chunk_size = 2
    cursor_ttl = 3600  # 1 hour

    def get_parts(self) -> List[tuple]:
        """
        Get all dashboard parts with optimized loading strategy
        """
        start_time = time.time()

        try:
            parts = [
                # Critical metadata - load immediately
                ("meta", self.get_metadata()),
                # User-specific data - load immediately for personalization
                ("user_info", self.get_user_info()),
                # Performance metrics - cached and safe
                (
                    "performance",
                    lazy(
                        safe_call(
                            self.get_performance_metrics,
                            fallback={"error": "Performance data unavailable"},
                        )
                    ),
                ),
                # Order statistics - cached for 5 minutes
                ("order_stats", lazy(self.get_cached_order_stats)),
                # Product analytics - potentially slow, with timeout
                (
                    "product_analytics",
                    lazy(
                        with_timeout(
                            safe_call(
                                self.get_product_analytics,
                                fallback={"error": "Analytics unavailable"},
                            ),
                            timeout=10,
                        )
                    ),
                ),
                # Financial reports - admin only, with special handling
                ("financial_reports", lazy(self.get_financial_reports)),
                # External integrations - might fail, with fallback
                (
                    "external_data",
                    lazy(
                        safe_call(
                            self.get_external_integrations,
                            fallback={"status": "External services unavailable"},
                        )
                    ),
                ),
                # Real-time notifications - websocket data
                ("notifications", lazy(self.get_realtime_notifications)),
            ]

            # Log performance
            setup_time = time.time() - start_time
            logger.info(
                f"Parts setup completed in {setup_time:.3f}s for user {self.request.user.id}"
            )

            return parts

        except Exception as e:
            logger.error(f"Error setting up parts for user {self.request.user.id}: {e}")
            raise

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get critical metadata - always load immediately
        """
        return {
            "timestamp": timezone.now().isoformat(),
            "user_id": self.request.user.id,
            "username": self.request.user.username,
            "version": "1.0.0",
            "environment": "production",
            "request_id": getattr(self.request, "request_id", "unknown"),
            "features": {
                "caching": True,
                "monitoring": True,
                "error_handling": True,
                "rate_limiting": True,
            },
        }

    def get_user_info(self) -> Dict[str, Any]:
        """
        Get user-specific information for personalization
        """
        user = self.request.user

        # Get user's order history efficiently
        user_orders = Order.objects.filter(user=user).aggregate(
            total_orders=Count("id"),
            total_spent=Sum("total"),
            avg_order_value=Avg("total"),
        )

        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "is_staff": user.is_staff,
            "is_premium": getattr(user, "is_premium", False),
            "member_since": user.date_joined.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "order_history": {
                "total_orders": user_orders["total_orders"] or 0,
                "total_spent": float(user_orders["total_spent"] or 0),
                "avg_order_value": float(user_orders["avg_order_value"] or 0),
            },
            "permissions": {
                "can_view_analytics": user.has_perm("app.view_analytics"),
                "can_view_financial": user.has_perm("app.view_financial"),
                "can_export_data": user.has_perm("app.export_data"),
            },
        }

    def get_performance_metrics(self, request) -> Dict[str, Any]:
        """
        Get system performance metrics - might fail, so wrapped in safe_call
        """
        try:
            import psutil

            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": (disk.used / disk.total) * 100,
                    "load_average": psutil.getloadavg(),
                },
                "database": {
                    "active_connections": self.get_db_connections(),
                    "query_count": getattr(request, "query_count", 0),
                    "cache_hit_rate": self.get_cache_hit_rate(),
                },
                "application": {
                    "response_time_avg": self.get_avg_response_time(),
                    "error_rate": self.get_error_rate(),
                    "requests_per_minute": self.get_requests_per_minute(),
                },
            }
        except ImportError:
            # psutil not available, return basic metrics
            return {
                "system": {"status": "Monitoring unavailable"},
                "database": {"active_connections": 0},
                "application": {"status": "Basic monitoring"},
            }

    @cached_for(300)  # Cache for 5 minutes
    def get_cached_order_stats(self, request) -> Dict[str, Any]:
        """
        Get order statistics - cached for performance
        """
        logger.info(f"Computing order stats for user {request.user.id}")

        # Simulate expensive computation
        time.sleep(0.1)

        today = timezone.now().date()

        # Get comprehensive order statistics
        stats = Order.objects.aggregate(
            total_orders=Count("id"),
            total_revenue=Sum("total"),
            avg_order_value=Avg("total"),
            today_orders=Count("id", filter=models.Q(created_at__date=today)),
            today_revenue=Sum("total", filter=models.Q(created_at__date=today)),
        )

        # Get top products
        top_products = Product.objects.annotate(order_count=Count("order")).order_by(
            "-order_count"
        )[:5]

        return {
            "overview": {
                "total_orders": stats["total_orders"] or 0,
                "total_revenue": float(stats["total_revenue"] or 0),
                "avg_order_value": float(stats["avg_order_value"] or 0),
            },
            "today": {
                "orders": stats["today_orders"] or 0,
                "revenue": float(stats["today_revenue"] or 0),
            },
            "top_products": [
                {
                    "id": product.id,
                    "name": product.name,
                    "order_count": product.order_count,
                    "price": float(product.price),
                }
                for product in top_products
            ],
            "computed_at": timezone.now().isoformat(),
            "cache_key": f"order_stats_{request.user.id}",
        }

    def get_product_analytics(self, request) -> Dict[str, Any]:
        """
        Get product analytics - potentially slow operation
        """
        logger.info(f"Computing product analytics for user {request.user.id}")

        # Simulate complex analytics computation
        time.sleep(0.2)

        # Get product performance data
        products = Product.objects.all()

        analytics = {
            "product_count": products.count(),
            "categories": {},
            "price_analysis": {},
            "stock_analysis": {},
            "performance_metrics": {},
        }

        # Category analysis
        for product in products:
            category = getattr(product, "category", "uncategorized")
            if category not in analytics["categories"]:
                analytics["categories"][category] = {
                    "count": 0,
                    "avg_price": 0,
                    "total_stock": 0,
                }

            analytics["categories"][category]["count"] += 1
            analytics["categories"][category]["total_stock"] += product.stock

        # Price analysis
        prices = [float(p.price) for p in products]
        if prices:
            analytics["price_analysis"] = {
                "min_price": min(prices),
                "max_price": max(prices),
                "avg_price": sum(prices) / len(prices),
                "median_price": sorted(prices)[len(prices) // 2],
            }

        # Stock analysis
        stocks = [p.stock for p in products]
        if stocks:
            analytics["stock_analysis"] = {
                "total_stock": sum(stocks),
                "avg_stock": sum(stocks) / len(stocks),
                "low_stock_count": len([s for s in stocks if s < 10]),
                "out_of_stock_count": len([s for s in stocks if s == 0]),
            }

        return analytics

    def get_financial_reports(self, request) -> Dict[str, Any]:
        """
        Get financial reports - admin only
        """
        if not request.user.is_staff:
            return {"error": "Insufficient permissions"}

        logger.info(f"Generating financial reports for admin user {request.user.id}")

        # Simulate financial computation
        time.sleep(0.15)

        # Get financial data
        financial_data = Order.objects.aggregate(
            gross_revenue=Sum("total"), order_count=Count("id")
        )

        # Calculate metrics
        gross_revenue = float(financial_data["gross_revenue"] or 0)
        order_count = financial_data["order_count"] or 0

        return {
            "revenue": {
                "gross": gross_revenue,
                "net": gross_revenue * 0.85,  # Assuming 15% costs
                "tax": gross_revenue * 0.08,  # Assuming 8% tax
                "fees": gross_revenue * 0.03,  # Assuming 3% fees
            },
            "orders": {
                "total": order_count,
                "avg_value": gross_revenue / order_count if order_count > 0 else 0,
            },
            "projections": {
                "monthly": gross_revenue * 1.2,
                "quarterly": gross_revenue * 3.5,
                "yearly": gross_revenue * 12.0,
            },
            "computed_at": timezone.now().isoformat(),
            "access_level": "admin",
        }

    def get_external_integrations(self, request) -> Dict[str, Any]:
        """
        Get data from external services - might fail
        """
        logger.info(f"Fetching external integrations for user {request.user.id}")

        # Simulate external API calls that might fail
        integrations = {}

        # Payment processor status
        try:
            # Simulate payment processor API
            time.sleep(0.05)
            integrations["payment_processor"] = {
                "status": "connected",
                "last_sync": timezone.now().isoformat(),
                "pending_transactions": 3,
            }
        except Exception as e:
            integrations["payment_processor"] = {"status": "error", "error": str(e)}

        # Shipping provider status
        try:
            # Simulate shipping API
            time.sleep(0.03)
            integrations["shipping"] = {
                "status": "connected",
                "pending_shipments": 12,
                "tracking_updates": 8,
            }
        except Exception as e:
            integrations["shipping"] = {"status": "error", "error": str(e)}

        # Email service status
        try:
            # Simulate email service API
            time.sleep(0.02)
            integrations["email_service"] = {
                "status": "connected",
                "emails_sent_today": 45,
                "bounce_rate": 2.1,
            }
        except Exception as e:
            integrations["email_service"] = {"status": "error", "error": str(e)}

        return integrations

    def get_realtime_notifications(self, request) -> Dict[str, Any]:
        """
        Get real-time notifications and alerts
        """
        logger.info(f"Fetching notifications for user {request.user.id}")

        # Get recent notifications
        notifications = []

        # Low stock alerts
        low_stock_products = Product.objects.filter(stock__lt=10)
        for product in low_stock_products:
            notifications.append(
                {
                    "type": "warning",
                    "title": "Low Stock Alert",
                    "message": f"{product.name} is running low ({product.stock} remaining)",
                    "timestamp": timezone.now().isoformat(),
                    "priority": "high" if product.stock < 5 else "medium",
                }
            )

        # Recent orders
        recent_orders = Order.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(minutes=30)
        ).order_by("-created_at")[:5]

        for order in recent_orders:
            notifications.append(
                {
                    "type": "info",
                    "title": "New Order",
                    "message": f"Order #{order.id} for ${order.total}",
                    "timestamp": order.created_at.isoformat(),
                    "priority": "low",
                }
            )

        # System alerts
        if self.get_error_rate() > 0.05:  # 5% error rate
            notifications.append(
                {
                    "type": "error",
                    "title": "High Error Rate",
                    "message": "System error rate is above threshold",
                    "timestamp": timezone.now().isoformat(),
                    "priority": "critical",
                }
            )

        return {
            "notifications": notifications,
            "unread_count": len(
                [n for n in notifications if n["priority"] in ["high", "critical"]]
            ),
            "last_updated": timezone.now().isoformat(),
        }

    # Helper methods for metrics
    def get_db_connections(self) -> int:
        """Get number of active database connections"""
        try:
            from django.db import connections

            return len(connections.all())
        except:
            return 0

    def get_cache_hit_rate(self) -> float:
        """Get cache hit rate percentage"""
        # This would typically come from your cache backend
        return 85.7  # Mock value

    def get_avg_response_time(self) -> float:
        """Get average response time in ms"""
        # This would typically come from your monitoring system
        return 127.5  # Mock value

    def get_error_rate(self) -> float:
        """Get error rate percentage"""
        # This would typically come from your monitoring system
        return 0.02  # Mock value (2%)

    def get_requests_per_minute(self) -> int:
        """Get requests per minute"""
        # This would typically come from your monitoring system
        return 1250  # Mock value


class ProductionAnalyticsAPI(ProgressiveView):
    """
    Production analytics API with advanced features
    """

    permission_classes = [IsAuthenticated]
    chunk_size = 1  # Load one analytics section at a time
    cursor_ttl = 7200  # 2 hours for analytics

    def get_parts(self) -> List[tuple]:
        """
        Get analytics parts optimized for performance
        """
        if not self.request.user.has_perm("app.view_analytics"):
            return [("error", {"message": "Insufficient permissions"})]

        return [
            (
                "meta",
                {
                    "analytics_type": "comprehensive",
                    "timestamp": timezone.now().isoformat(),
                },
            ),
            ("user_analytics", lazy(self.get_user_analytics)),
            ("product_analytics", lazy(self.get_product_performance)),
            ("financial_analytics", lazy(self.get_financial_analysis)),
            ("predictive_analytics", lazy(self.get_predictive_models)),
            ("real_time_metrics", lazy(self.get_real_time_metrics)),
        ]

    @cached_for(600)  # Cache for 10 minutes
    def get_user_analytics(self, request) -> Dict[str, Any]:
        """
        Get comprehensive user analytics
        """
        # This would include user behavior, segmentation, retention, etc.
        return {
            "user_segments": {"premium": 25, "regular": 150, "new": 30},
            "retention_rate": 68.5,
            "churn_rate": 8.2,
            "lifetime_value": 245.67,
        }

    @cached_for(300)  # Cache for 5 minutes
    def get_product_performance(self, request) -> Dict[str, Any]:
        """
        Get product performance analytics
        """
        # This would include sales performance, trending products, etc.
        return {
            "top_performers": ["Product A", "Product B", "Product C"],
            "conversion_rates": {"Product A": 12.5, "Product B": 8.7},
            "inventory_turnover": 4.2,
        }

    @cached_for(1800)  # Cache for 30 minutes
    def get_financial_analysis(self, request) -> Dict[str, Any]:
        """
        Get financial analysis - admin only
        """
        if not request.user.is_staff:
            return {"error": "Admin access required"}

        return {
            "revenue_trends": {"month": 15000, "quarter": 42000},
            "profit_margins": {"gross": 65.5, "net": 22.1},
            "cash_flow": {"positive": True, "amount": 12500},
        }

    def get_predictive_models(self, request) -> Dict[str, Any]:
        """
        Get predictive analytics - potentially slow
        """
        # This would include ML models, forecasting, etc.
        time.sleep(0.3)  # Simulate ML computation

        return {
            "demand_forecast": {"next_week": 150, "next_month": 650},
            "revenue_prediction": {"next_quarter": 55000},
            "churn_prediction": {"high_risk_users": 12},
        }

    def get_real_time_metrics(self, request) -> Dict[str, Any]:
        """
        Get real-time metrics
        """
        return {
            "active_users": 45,
            "current_orders": 8,
            "revenue_today": 3250.75,
            "server_status": "healthy",
        }


class HealthCheckAPI(ProgressiveView):
    """
    Health check API for monitoring
    """

    permission_classes = []  # Public endpoint
    chunk_size = 10  # Return all at once

    def get_parts(self) -> List[tuple]:
        """
        Get system health status
        """
        return [
            ("timestamp", timezone.now().isoformat()),
            ("database", lazy(self.check_database)),
            ("cache", lazy(self.check_cache)),
            ("external_services", lazy(self.check_external_services)),
            ("performance", lazy(self.check_performance)),
        ]

    def check_database(self, request) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            from django.db import connection

            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return {"status": "healthy", "latency": "< 1ms"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def check_cache(self, request) -> Dict[str, Any]:
        """Check cache connectivity"""
        try:
            cache.set("health_check", "ok", 10)
            result = cache.get("health_check")
            return {"status": "healthy" if result == "ok" else "unhealthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def check_external_services(self, request) -> Dict[str, Any]:
        """Check external service connectivity"""
        # This would check your external APIs, payment processors, etc.
        return {"status": "healthy", "services": ["payment", "shipping", "email"]}

    def check_performance(self, request) -> Dict[str, Any]:
        """Check system performance"""
        start_time = time.time()

        # Simulate some work
        time.sleep(0.01)

        response_time = (time.time() - start_time) * 1000

        return {
            "response_time_ms": round(response_time, 2),
            "memory_usage": "normal",
            "cpu_usage": "normal",
        }
