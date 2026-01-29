from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RulesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core_apps.rules'
    verbose_name = _("Rules")
