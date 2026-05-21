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

# If Railway sets a public domain for this deploy, include it explicitly
railway_domain = os.environ.get('RAILWAY_PUBLIC_DOMAIN') or os.environ.get('RAILWAY_STATIC_URL')
if railway_domain:
    railway_domain = railway_domain.strip()
    if railway_domain:
        ALLOWED_HOSTS.append(railway_domain)

# SECURITY: CSRF trusted origins for Railway and custom domains
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')
CSRF_TRUSTED_ORIGINS = [origin for origin in CSRF_TRUSTED_ORIGINS if origin]  # Remove empty strings
# Always add Railway domains
CSRF_TRUSTED_ORIGINS.extend(['https://*.up.railway.app', 'https://*.railway.app'])
if railway_domain:
    CSRF_TRUSTED_ORIGINS.append('https://%s' % railway_domain)

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
DATABASE_URL = os.environ.get("DATABASE_URL")

# Fail loudly on missing or empty DATABASE_URL (avoid dj_database_url.parse('') ValueError)
if DATABASE_URL is None or DATABASE_URL.strip() == "":
    raise ImproperlyConfigured(
        "DATABASE_URL environment variable must be set and non-empty. "
        "Example: postgresql://user:password@host:5432/dbname"
    )
if not DATABASE_URL or not DATABASE_URL.strip():
    raise ImproperlyConfigured("DATABASE_URL environment variable must be set")

# Parse the URL from the environment (explicitly request the project's DB engine)
db_config = dj_database_url.parse(DATABASE_URL, engine=DB_ENGINE)

# Ensure we use the project's DB_ENGINE (PostGIS wrapper) so GeoDjango ops are available
try:
    DB_ENGINE  # defined in base.py via import *
except NameError:
    # Fall back to the standard PostGIS backend if DB_ENGINE is not present
    DB_ENGINE = "django.contrib.gis.db.backends.postgis"

# Emergency override: allow ops teams to force a known PostGIS engine via env var.
# - `DB_ENGINE_OVERRIDE` if set will be used verbatim (useful for testing)
# - `FORCE_DB_ENGINE_TO_POSTGIS=true` will set the engine to Django's PostGIS backend
db_engine_override = os.environ.get('DB_ENGINE_OVERRIDE')
if db_engine_override:
    DB_ENGINE = db_engine_override
else:
    if os.environ.get('FORCE_DB_ENGINE_TO_POSTGIS', '').lower() in ('1', 'true', 'yes'):
        DB_ENGINE = 'django.contrib.gis.db.backends.postgis'

# Hard-set the engine to avoid accidental fallback to a plain postgresql backend
db_config['ENGINE'] = DB_ENGINE

# EXPLICITLY force sslmode to disable to override any URL params or defaults
db_config.setdefault('OPTIONS', {})
db_config['OPTIONS']['sslmode'] = 'disable'
db_config['OPTIONS']['connect_timeout'] = 10

# Set connection age for performance. Make configurable via env var so we can
# lower it on hosted platforms with tight connection limits (e.g. Railway).
db_config['CONN_MAX_AGE'] = int(os.environ.get('DB_CONNECTION_MAX_AGE', '60'))
# Enable Django's DB health checks integration when supported by the engine.
db_config['CONN_HEALTH_CHECKS'] = True

DATABASES = {
    'default': db_config
}
# Emit a sanitized DATABASE config to stdout so deploy logs contain the effective DB settings
try:
    import json
    san = dict(DATABASES['default'])
    san.pop('PASSWORD', None)
    san.pop('USER', None)
    print('SANITIZED_DATABASE_FROM_SETTINGS:', json.dumps(san))
except Exception:
    pass
# Note: Health check endpoint already exists at /api/_health/ in base urls