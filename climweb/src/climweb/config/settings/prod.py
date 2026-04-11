from .base import *
import os
import dj_database_url
from django.core.exceptions import ImproperlyConfigured

# SECURITY: Get SECRET_KEY from environment variable
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY environment variable must be set in production")