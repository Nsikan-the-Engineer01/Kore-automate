from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AuthUserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core_apps.auth_user'
    verbose_name = _("User Auth")
