"""
URL configuration for example_app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'reports', views.ReportsViewSet, basename='reports')

urlpatterns = [
    # Progressive delivery endpoints
    path('order-analytics/', views.OrderAnalyticsView.as_view(), name='order-analytics'),
    path('simple-progressive/', views.SimpleProgressiveView.as_view(), name='simple-progressive'),
    
    # ViewSet endpoints
    path('', include(router.urls)),
] 