from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GoalViewSet


# Create a DRF router and register the GoalViewSet
router = DefaultRouter()
router.register('goals', GoalViewSet, basename='goals')

# Export urlpatterns for inclusion in main URL configuration
urlpatterns = [
    path('', include(router.urls)),
]
