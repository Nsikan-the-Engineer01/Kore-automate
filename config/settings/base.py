from dotenv import load_dotenv
from pathlib import Path
from os import getenv, path
from loguru import logger
from corsheaders.defaults import default_headers

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent

APPS_DIR = BASE_DIR / "core_apps"
local_env_file = path.join(BASE_DIR, ".envs", ".env.local")

if path.isfile(local_env_file):
    load_dotenv(local_env_file)


# Application definition
DJANGO_APPS = [

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [

    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_countries',
    'phonenumber_field',
    'drf_spectacular',
    'djoser',
    'cloudinary',
    'django_filters',
    'djcelery_email',
    'django_celery_beat',
    
]

LOCAL_APPS = [

    'core_apps.user_profile',
    'core_apps.auth_user',
    'core_apps.common',
    'core_apps.goals',
    'core_apps.rules',
    'core_apps.integrations',
    'core_apps.integrations.paywithaccount',
    'core_apps.collections',
    'core_apps.transactions',
    'core_apps.webhooks',
    'core_apps.ledger',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [str(APPS_DIR / "templates")],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': getenv("POSTGRES_DB"),
        'USER' : getenv("POSTGRES_USER"),
        'PASSWORD' : getenv("POSTGRES_PASSWORD"),
        'HOST' : getenv("POSTGRES_HOST"),
        'PORT' : getenv("POSTGRES_PORT"),
        
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

SITE_ID = 1


# CORS / CSRF configuration
_cors_allowed_origins = getenv("CORS_ALLOWED_ORIGINS", "")
if _cors_allowed_origins:
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in _cors_allowed_origins.split(",") if origin.strip()]
else:
    CORS_ALLOWED_ORIGINS = []

CORS_ALLOW_CREDENTIALS = False
CORS_ALLOW_HEADERS = list(default_headers) + [
    "Authorization",
    "Content-Type",
    "X-Request-ID",
]

_csrf_trusted_origins = getenv("CSRF_TRUSTED_ORIGINS", "")
if _csrf_trusted_origins:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in _csrf_trusted_origins.split(",") if origin.strip()]
else:
    CSRF_TRUSTED_ORIGINS = []


# Django REST Framework configuration
_anon_throttle_rate = getenv("THROTTLE_RATE_ANON", "50/min")
_user_throttle_rate = getenv("THROTTLE_RATE_USER", "200/min")
_login_throttle_rate = getenv("THROTTLE_RATE_LOGIN", "10/min")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": _anon_throttle_rate,
        "user": _user_throttle_rate,
        "login": _login_throttle_rate,
    },
}


# PayWithAccount (OnePipe) API configuration
PWA_BASE_URL = getenv("PWA_BASE_URL", "https://api.dev.onepipe.io")
PWA_TRANSACT_PATH = getenv("PWA_TRANSACT_PATH", "/v2/transact")
PWA_QUERY_PATH = getenv("PWA_QUERY_PATH", "/transact/query")
PWA_VALIDATE_PATH = getenv("PWA_VALIDATE_PATH", "/transact/validate")
PWA_API_KEY = getenv("PWA_API_KEY", "")
PWA_CLIENT_SECRET = getenv("PWA_CLIENT_SECRET") or getenv("PWA_SECRET_KEY", "")
PWA_WEBHOOK_SECRET = getenv("PWA_WEBHOOK_SECRET", "")
PWA_MOCK_MODE = getenv("PWA_MOCK_MODE", "inspect")
PWA_REQUEST_TYPE = getenv("PWA_REQUEST_TYPE", "invoice")
# Request type overrides for specific transaction types (used by payload builders)
PWA_REQUEST_TYPE_INVOICE = getenv("PWA_REQUEST_TYPE_INVOICE", "invoice")
PWA_REQUEST_TYPE_DISBURSE = getenv("PWA_REQUEST_TYPE_DISBURSE", "disburse")
PWA_REQUEST_TYPE_SUBSCRIPTION = getenv("PWA_REQUEST_TYPE_SUBSCRIPTION", "subscription")
PWA_REQUEST_TYPE_INSTALMENT = getenv("PWA_REQUEST_TYPE_INSTALMENT", "instalment")
PWA_TIMEOUT_SECONDS = int(getenv("PWA_TIMEOUT_SECONDS", "30"))

# PayWithAccount configuration - consolidated for clean access
# Usage: from django.conf import settings; config = settings.PAYWITHACCOUNT
PAYWITHACCOUNT = {
    'base_url': PWA_BASE_URL,
    'transact_path': PWA_TRANSACT_PATH,
    'query_path': PWA_QUERY_PATH,
    'validate_path': PWA_VALIDATE_PATH,
    'api_key': PWA_API_KEY,
    'client_secret': PWA_CLIENT_SECRET,
    'webhook_secret': PWA_WEBHOOK_SECRET,
    'mock_mode': PWA_MOCK_MODE,
    'request_type': PWA_REQUEST_TYPE,
    'request_type_invoice': PWA_REQUEST_TYPE_INVOICE,
    'request_type_disburse': PWA_REQUEST_TYPE_DISBURSE,
    'request_type_subscription': PWA_REQUEST_TYPE_SUBSCRIPTION,
    'request_type_instalment': PWA_REQUEST_TYPE_INSTALMENT,
    'timeout_seconds': PWA_TIMEOUT_SECONDS,
}

# Kore Fee configuration
KORE_FEE_FLAT = getenv("KORE_FEE_FLAT")  # Flat fee amount (e.g., "100")
KORE_FEE_PERCENT = getenv("KORE_FEE_PERCENT")  # Percentage fee (e.g., "2.5")


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = str(BASE_DIR / "staticfiles")

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING_CONFIG = None

LOGURU_LOGGING = {
    "handlers": [
        {
            "sink": BASE_DIR / "logs/debug.log",
            "level": "DEBUG",
            "filter": lambda record: record["level"].no <= logger.level("WARNING").no,
            "format": "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - "
            "{message}",
            "rotation": "10MB",
            "retention": "30 days",
            "compression": "zip",
        },
        {
            "sink": BASE_DIR / "logs/error.log",
            "level": "ERROR",
            "format": "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - "
            "{message}",
            "rotation": "10MB",
            "retention": "30 days",
            "compression": "zip",
            "backtrace": True,
            "diagnose": True,
        },
    ],
}
logger.configure(**LOGURU_LOGGING)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"loguru": {"class": "interceptor.InterceptHandler"}},
    "root": {"handlers": ["loguru"], "level": "DEBUG"},
}

