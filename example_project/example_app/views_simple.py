"""
Example views using the simple API
"""
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_partstream import ProgressiveView, lazy, safe_call, cached_for
from .models import Order, Product


class SimpleEcommerceAPI(ProgressiveView):
    """
    Simple e-commerce dashboard using the new simple API
    """
    permission_classes = [IsAuthenticated]
    chunk_size = 2  # Load 2 parts per request
    
    def get_parts(self):
        return [
            ("meta", {
                "timestamp": timezone.now().isoformat(),
                "user": self.request.user.username
            }),
            ("stats", lazy(self.get_stats)),
            ("orders", lazy(self.get_recent_orders)),
            ("products", lazy(self.get_products))
        ]
    
    def get_stats(self, request):
        """Get basic stats - might take a while"""
        return {
            "total_users": User.objects.count(),
            "total_orders": Order.objects.count(),
            "total_products": Product.objects.count(),
            "revenue": Order.objects.aggregate(Sum('total'))['total__sum'] or 0
        }
    
    def get_recent_orders(self, request):
        """Get recent orders"""
        orders = Order.objects.select_related('user').order_by('-created_at')[:10]
        return [{
            "id": order.id,
            "user": order.user.username,
            "total": float(order.total),
            "created_at": order.created_at.isoformat()
        } for order in orders]
    
    def get_products(self, request):
        """Get products - might fail"""
        products = Product.objects.all()[:10]
        return [{
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "stock": product.stock
        } for product in products]


class SafeAPI(ProgressiveView):
    """
    Example using safe_call for error handling
    """
    def get_parts(self):
        return [
            ("meta", {"timestamp": timezone.now()}),
            ("safe_data", lazy(safe_call(self.risky_operation, fallback={"error": "Service unavailable"}))),
            ("external", lazy(safe_call(self.external_api, fallback={"error": "External API failed"})))
        ]
    
    def risky_operation(self, request):
        """This operation might fail"""
        # Simulate a risky operation
        import random
        if random.random() < 0.5:
            raise Exception("Random failure")
        return {"success": True, "data": "Important data"}
    
    def external_api(self, request):
        """This external API might fail"""
        # Simulate external API call
        import random
        if random.random() < 0.3:
            raise Exception("External API timeout")
        return {"external_data": "Data from external service"}


class CachedAPI(ProgressiveView):
    """
    Example using cached_for decorator
    """
    def get_parts(self):
        return [
            ("meta", {"timestamp": timezone.now()}),
            ("analytics", lazy(self.get_cached_analytics))
        ]
    
    @cached_for(300)  # Cache for 5 minutes
    def get_cached_analytics(self, request):
        """Expensive computation that should be cached"""
        # Simulate expensive computation
        import time
        time.sleep(0.1)  # Pretend this takes time
        
        return {
            "total_revenue": Order.objects.aggregate(Sum('total'))['total__sum'] or 0,
            "avg_order_value": Order.objects.aggregate(
                avg_total=Sum('total') / Count('id')
            )['avg_total'] or 0,
            "computed_at": timezone.now().isoformat()
        }


class ConditionalAPI(ProgressiveView):
    """
    Example with conditional parts based on permissions
    """
    def get_parts(self):
        parts = [
            ("meta", {"timestamp": timezone.now()}),
            ("public_data", lazy(self.get_public_data))
        ]
        
        if self.request.user.is_authenticated:
            parts.append(("user_data", lazy(self.get_user_data)))
        
        if self.request.user.is_staff:
            parts.append(("admin_data", lazy(self.get_admin_data)))
        
        return parts
    
    def get_public_data(self, request):
        return {
            "total_products": Product.objects.count(),
            "message": "This is public data"
        }
    
    def get_user_data(self, request):
        return {
            "user_orders": Order.objects.filter(user=request.user).count(),
            "message": "This is user-specific data"
        }
    
    def get_admin_data(self, request):
        return {
            "total_users": User.objects.count(),
            "total_revenue": Order.objects.aggregate(Sum('total'))['total__sum'] or 0,
            "message": "This is admin data"
        } 