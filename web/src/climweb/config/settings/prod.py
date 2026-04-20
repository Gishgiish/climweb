from .base import *
import os
import dj_database_url
from django.core.exceptions import ImproperlyConfigured

# SECURITY: Never run with DEBUG=True in production
DEBUG = False

# Allow your railway domain
ALLOWED_HOSTS = [
    '.up.railway.app',  # Allows any *.up.railway.app subdomain
    'localhost',      # For testing
    '127.0.0.1',
]

# Database from Render's DATABASE_URL environment variable
# Fail loudly if DATABASE_URL is missing or empty to avoid ambiguous errors
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL is None or DATABASE_URL.strip() == "":
    raise ImproperlyConfigured(
        "DATABASE_URL environment variable must be set and non-empty. "
        "Example: postgresql://user:password@host:5432/dbname"
    )

DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        engine=DB_ENGINE,
        conn_max_age=600,  # Keep connections alive longer
        conn_health_checks=True,
    )
}

# Static files configuration for WhiteNoise
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Security settings (HTTPS only in production)
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# WhiteNoise for serving static files
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this line
] + MIDDLEWARE

# Compress static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
