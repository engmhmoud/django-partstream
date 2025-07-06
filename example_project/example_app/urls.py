"""
URL configuration for example_app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, views_v2

# Create a router for ViewSets
router = DefaultRouter()
router.register(r"reports", views.ReportsViewSet, basename="reports")

urlpatterns = [
    # Original progressive delivery endpoints
    path(
        "order-analytics/", views.OrderAnalyticsView.as_view(), name="order-analytics"
    ),
    path(
        "simple-progressive/",
        views.SimpleProgressiveView.as_view(),
        name="simple-progressive",
    ),
    # New hybrid progressive delivery endpoints (supports both token-based and key-based)
    path("dashboard/", views_v2.DashboardHybridView.as_view(), name="dashboard"),
    path(
        "dashboard/manifest/",
        views_v2.DashboardHybridView.as_view(),
        name="dashboard-manifest",
    ),
    path(
        "dashboard/parts/",
        views_v2.DashboardHybridView.as_view(),
        name="dashboard-parts",
    ),
    # Comparison endpoint to explain the differences
    path("comparison/", views_v2.ComparisonView.as_view(), name="comparison"),
    # ViewSet endpoints
    path("", include(router.urls)),
]
