from django.urls import path

from .views import health


app_name = "common"

urlpatterns = [
    path("health/", health, name="health"),
]

