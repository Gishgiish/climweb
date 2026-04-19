FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu \
    GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu \
    PYTHONPATH=/app/climweb/src

# Install system dependencies
# Includes: Build tools, Postgres client, GDAL/GEOS/PROJ for geo, and CAIRO/PANGO for SVG rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    postgresql-client \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    binutils \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY climweb/requirements/ ./climweb/requirements/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install django-environ gunicorn whitenoise && \
    pip install -r climweb/requirements/base.txt 

# Copy the entire project
COPY climweb/ ./climweb/

# Create entrypoint script
RUN printf '#!/bin/bash\n\
set -e\n\
\n\
# Railway provides $PORT, default to 8080 if not set\n\
PORT=${PORT:-8080}\n\
\n\
echo "Waiting for database to be ready..."\n\
sleep 20\n\
\n\
echo "Running migrations..."\n\
cd /app/climweb/src/climweb && python manage.py migrate --noinput\n\
\n\
echo "Collecting static files..."\n\
cd /app/climweb/src/climweb && python manage.py collectstatic --noinput\n\
\n\
echo "Loading site/user fixture if present..."\n\
cd /app/climweb/src/climweb && python manage.py loaddata /app/climweb/wagtail_prod_sync.json || true\n\
echo "Configuring Wagtail site and superuser..."\n\
cd /app/climweb/src/climweb && python manage.py shell << 'PYEOF'\n\
import os, traceback\n\
from wagtail.models import Site, Page\n\
from django.contrib.auth import get_user_model\n\
User = get_user_model()\n\
\n\
# Read superuser info from environment; if unset we skip creation and prompt you to set them\n\
username = os.environ.get('DJANGO_SUPERUSER_USERNAME')\n\
email = os.environ.get('DJANGO_SUPERUSER_EMAIL')\n\
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')\n\
\n\
try:\n\
    # Determine site hostname (Railway typically sets RAILWAY_PUBLIC_DOMAIN)\n\
    site_hostname = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'climweb-production.up.railway.app')\n\
    # Delete conflicting sites (localhost, wildcard, or old railway domains)\n\
    Site.objects.filter(hostname__in=['localhost', '127.0.0.1', '*', 'climweb-production.up.railway.app']).delete()\n\
    # Get the homepage - prefer a stable slug, then title, then fallback to a root-level page\n\
    homepage = Page.objects.filter(slug='home').first() or Page.objects.filter(title__icontains='AfriClimate').first() or Page.objects.filter(depth=2).first()\n\
    if homepage:\n\
        Site.objects.create(\n\
            hostname=site_hostname,\n\
            port=80,\n\
            root_page=homepage,\n\
            is_default_site=True,\n\
            site_name='AfriClimate Center For Adaptation'\n\
        )\n\
        print(f"Site created for: {site_hostname} -> {homepage.title}")\n\
    else:\n\
        print('WARNING: No homepage found. Site not configured.')\n\
except Exception:\n\
    traceback.print_exc()\n\
\n\
try:\n\
    if username:\n\
        if not User.objects.filter(username=username).exists():\n\
            User.objects.create_superuser(username=username, email=email or '', password=password or '')\n\
            print(f'Superuser {username} created')\n\
        else:\n\
            print(f'Superuser {username} already exists')\n\
    else:\n\
        print('DJANGO_SUPERUSER_USERNAME not set; skipping superuser creation. Set DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, and DJANGO_SUPERUSER_PASSWORD in Railway secrets to create one automatically.')\n\
except Exception:\n\
    traceback.print_exc()\n\
\n\
# Verification output for logs\n\
try:\n\
    print('Sites:', list(Site.objects.values('id','hostname','root_page','is_default_site')))\n\
    print('Superusers:', list(User.objects.filter(is_superuser=True).values('username','email')))\n\
except Exception:\n\
    traceback.print_exc()\n\
PYEOF\n\
\n\
echo "Starting Gunicorn..."\n\
exec gunicorn climweb.config.wsgi:application --bind 0.0.0.0:$PORT --log-file -\n' > /entrypoint.sh \
    && chmod +x /entrypoint.sh

# Expose port (Railway will override this)
EXPOSE 8080

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]