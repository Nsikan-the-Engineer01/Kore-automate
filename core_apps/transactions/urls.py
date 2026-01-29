"""
URL configuration for Transaction app.

Registers TransactionViewSet with DRF router.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet


# Create router and register viewset
router = DefaultRouter()
router.register('', TransactionViewSet, basename='transactions')

# URL patterns
urlpatterns = [
    path('', include(router.urls)),
]
