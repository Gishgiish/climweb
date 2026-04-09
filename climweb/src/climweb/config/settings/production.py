from .base import *

try:
    from .local import *
except ImportError:
    pass

# =============================================================================
# PRODUCTION SETTINGS
# =============================================================================

WAGTAIL_ENABLE_UPDATE_CHECK = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

MANIFEST_LOADER = {
    'cache': True,
}

# Enable caching in production
WAGTAIL_CACHE = True

FILE_UPLOAD_TEMP_DIR = env.str("FILE_UPLOAD_TEMP_DIR", None)
if FILE_UPLOAD_TEMP_DIR is None or not os.path.exists(FILE_UPLOAD_TEMP_DIR):
    FILE_UPLOAD_TEMP_DIR = "/climweb/tmp"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env.str('EMAIL_HOST', default="localhost")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", False)
EMAIL_PORT = os.getenv("EMAIL_PORT", "")
if not EMAIL_PORT:
    EMAIL_PORT = 25
else:
    EMAIL_PORT = env.int('EMAIL_PORT', default=25)

EMAIL_HOST_USER = env.str('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env.str('EMAIL_HOST_PASSWORD', default="")

# =============================================================================
# SECURITY SETTINGS
# =============================================================================

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', cast=None, default=[])
SECURE_CROSS_ORIGIN_OPENER_POLICY = env.str("SECURE_CROSS_ORIGIN_OPENER_POLICY", "same-origin")

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', cast=None, default=[])

# Security headers
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', True)
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', 31536000)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', True)
SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', True)
SECURE_BROWSER_XSS_FILTER = env.bool('SECURE_BROWSER_XSS_FILTER', True)
SECURE_CONTENT_TYPE_NOSNIFF = env.bool('SECURE_CONTENT_TYPE_NOSNIFF', True)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', True)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', True)
X_FRAME_OPTIONS = env.str('X_FRAME_OPTIONS', 'DENY')

# locales paths in production
if 'LOCALE_PATHS' in globals():
    LOCALE_PATHS = [
        p.replace('climweb/', '', 1) if p.startswith('climweb/') else p
        for p in LOCALE_PATHS
    ]