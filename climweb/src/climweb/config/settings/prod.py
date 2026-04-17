from .base import *
import os
import dj_database_url
from django.core.exceptions import ImproperlyConfigured

# SECURITY: Get SECRET_KEY from environment variable
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY environment variable must be set in production")

# SECURITY: Allow hosts from environment variable or default to Railway domains
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']
# Always add Railway domains
ALLOWED_HOSTS.extend(['.up.railway.app', '.railway.app'])

# SECURITY: CSRF trusted origins for Railway and custom domains
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')
CSRF_TRUSTED_ORIGINS = [origin for origin in CSRF_TRUSTED_ORIGINS if origin]  # Remove empty strings
# Always add Railway domains
CSRF_TRUSTED_ORIGINS.extend(['https://*.up.railway.app', 'https://*.railway.app'])

# SECURITY: SSL/HTTPS settings
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() in ('true', '1', 'yes')
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# WhiteNoise for static files
MIDDLEWARE.insert(MIDDLEWARE.index('django.middleware.security.SecurityMiddleware') + 1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Database configuration from DATABASE_URL
# Get the raw DATABASE_URL
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ImproperlyConfigured("DATABASE_URL environment variable must be set")

# Parse the URL manually to ensure we can force sslmode=disable
# This bypasses any automatic SSL detection by dj_database_url
db_config = dj_database_url.parse(DATABASE_URL)

if 'OPTIONS' not in db_config:
    db_config['OPTIONS'] = {}

# FORCE SSL MODE TO DISABLE
# Force disable SSL to be absolutely sure
db_config['OPTIONS']['sslmode'] = 'disable'
db_config['CONN_MAX_AGE'] = 600

DATABASES = {
    'default': db_config
}
# Note: Health check endpoint already exists at /api/_health/ in base urls