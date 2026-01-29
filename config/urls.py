"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/v1/", include(("core_apps.common.urls", "common"), namespace="common")),
    path("api/v1/auth/", include(("core_apps.auth_user.urls", "auth"), namespace="auth")),
    path("api/v1/collections/", include(("core_apps.collections.urls", "collections"), namespace="collections")),
    path("api/v1/goals/", include(("core_apps.goals.urls", "goals"), namespace="goals")),
    path("api/v1/transactions/", include(("core_apps.transactions.urls", "transactions"), namespace="transactions")),
    path("api/v1/webhooks/", include(("core_apps.webhooks.urls", "webhooks"), namespace="webhooks")),
]
