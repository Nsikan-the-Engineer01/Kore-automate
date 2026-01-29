from django.urls import path
from core_apps.webhooks.views import PayWithAccountWebhookView

urlpatterns = [
    path('paywithaccount/', PayWithAccountWebhookView.as_view(), name='webhook-paywithaccount'),
]
