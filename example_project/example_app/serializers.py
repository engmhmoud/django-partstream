from rest_framework import serializers
from .models import Order, Product


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model."""

    class Meta:
        model = Order
        fields = ["id", "user", "total_amount", "status", "created_at"]


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model."""

    class Meta:
        model = Product
        fields = ["id", "name", "price", "stock", "created_at"]
