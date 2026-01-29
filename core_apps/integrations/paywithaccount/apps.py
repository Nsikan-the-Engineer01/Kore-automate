from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PaywithaccountConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core_apps.integrations.paywithaccount'
    verbose_name = _("PayWithAccount")
