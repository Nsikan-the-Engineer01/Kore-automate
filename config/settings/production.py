"""
Production settings for Kore application.
Hardened security configuration for deployment.
"""

from .base import *
import os

# ============================================================================
# SECURITY SETTINGS - PRODUCTION HARDENING
# ============================================================================

# Debug mode - NEVER True in production
DEBUG = False

# Allowed hosts from environment variable
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost").split(",")
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]

# Proxy settings for reverse proxy (Nginx)
# Django needs to know it's behind HTTPS via X-Forwarded-Proto header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# SSL/HTTPS Redirect - controlled by environment variable
# Set to True only when SSL certificates are configured
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() == "true"

# Cookie security - controlled by environment variable
# Should be True when HTTPS is enabled
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False").lower() == "true"

# HTTPS-only cookies
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# HSTS (HTTP Strict Transport Security) - enable only with HTTPS
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False").lower() == "true"
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "False").lower() == "true"

# Security Headers
SECURE_CONTENT_SECURITY_POLICY = {
    "default-src": ("'self'",),
    "script-src": ("'self'",),
    "style-src": ("'self'", "'unsafe-inline'"),
    "img-src": ("'self'", "data:", "https:"),
    "font-src": ("'self'",),
    "connect-src": ("'self'",),
}

# X-Frame-Options: prevent clickjacking
X_FRAME_OPTIONS = "SAMEORIGIN"

# X-Content-Type-Options: prevent MIME sniffing
SECURE_CONTENT_TYPE_NOSNIFF = True

# X-XSS-Protection: enable browser XSS protection
SECURE_BROWSER_XSS_FILTER = True

# Referrer-Policy: control referrer information
REFERRER_POLICY = "strict-origin-when-cross-origin"

# Permissions-Policy: restrict browser permissions
PERMISSIONS_POLICY = {
    "accelerometer": "none",
    "ambient-light-sensor": "none",
    "autoplay": "none",
    "camera": "none",
    "geolocation": "none",
    "gyroscope": "none",
    "magnetometer": "none",
    "microphone": "none",
    "payment": "none",
    "usb": "none",
}

# ============================================================================
# STATIC FILES CONFIGURATION
# ============================================================================

STATIC_URL = "/static/"
STATIC_ROOT = "/app/staticfiles"

# Whitenoise for serving static files (optional, Nginx handles this in production)
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================================================================
# SESSION & CSRF CONFIGURATION
# ============================================================================

# Session configuration
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", "1209600"))  # 2 weeks
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_SAVE_EVERY_REQUEST = False

# CSRF configuration
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_FAILURE_VIEW = "rest_framework.exceptions.permission_denied"

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Production logging level
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Update loguru handlers with production log level
LOGURU_LOGGING = {
    "handlers": [
        {
            "sink": BASE_DIR / "logs/debug.log",
            "level": LOG_LEVEL,
            "filter": lambda record: record["level"].no <= logger.level("WARNING").no,
            "format": "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            "rotation": "10MB",
            "retention": "30 days",
            "compression": "zip",
        },
        {
            "sink": BASE_DIR / "logs/error.log",
            "level": "ERROR",
            "format": "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            "rotation": "10MB",
            "retention": "30 days",
            "compression": "zip",
            "backtrace": True,
            "diagnose": True,
        },
    ],
}
logger.configure(**LOGURU_LOGGING)

# ============================================================================
# CORS/CSRF CONFIGURATION (Already in base, but documented here)
# ============================================================================

# CORS: configured via environment variables in base.py
# CSRF_TRUSTED_ORIGINS: configured via environment variables in base.py
# Middleware order is important:
# 1. SecurityMiddleware (must be first)
# 2. CorsMiddleware (must be before session/auth)
# 3. Other middleware...

# ============================================================================
# SECURITY MIDDLEWARE CONFIGURATION
# ============================================================================

# SecurityMiddleware options for production
SECURE_REDIRECT_EXEMPT = []  # Paths that don't need redirects

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Database is configured in base.py via environment variables
# Connection pooling should be configured for production
DATABASES['default']['CONN_MAX_AGE'] = int(os.getenv("CONN_MAX_AGE", "600"))  # 10 minutes

# ============================================================================
# EMAIL CONFIGURATION (Optional, for production email sending)
# ============================================================================

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@example.com")

# ============================================================================
# ERROR TRACKING (Optional, e.g., Sentry)
# ============================================================================

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

# ============================================================================
# CELERY CONFIGURATION (Optional, for async tasks)
# ============================================================================

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

# ============================================================================
# REST FRAMEWORK CONFIGURATION
# ============================================================================

# Stricter throttling in production
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "anon": os.getenv("THROTTLE_RATE_ANON", "30/min"),
    "user": os.getenv("THROTTLE_RATE_USER", "100/min"),
    "login": os.getenv("THROTTLE_RATE_LOGIN", "5/min"),
}

# ============================================================================
# PAYWITHACOUNT (PWA) - Production mode
# ============================================================================

# PWA settings are configured in base.py, but ensure mock mode is appropriate
if PWA_MOCK_MODE not in ["inspect", "production"]:
    PWA_MOCK_MODE = "production"
