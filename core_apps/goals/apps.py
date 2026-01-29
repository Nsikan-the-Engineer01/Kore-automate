from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GoalsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core_apps.goals'
    verbose_name = _("Goals")
