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
RUN cat > /entrypoint.sh << 'ENTRYEOF'
#!/bin/bash
set -e

# Railway provides $PORT, default to 8080 if not set
PORT=${PORT:-8080}

echo "Waiting for database to be ready..."
sleep 20

echo "Running migrations..."
cd /app/climweb/src/climweb && python manage.py migrate --noinput

echo "Collecting static files..."
cd /app/climweb/src/climweb && python manage.py collectstatic --noinput

echo "Loading production fixture if present..."
if [ -f /app/climweb/wagtail_prod_sync.json ]; then
    cd /app/climweb/src/climweb && python manage.py loaddata /app/climweb/wagtail_prod_sync.json || true
else
    echo "No fixture file found at /app/climweb/wagtail_prod_sync.json, skipping."
fi

echo "Configuring Wagtail site and superuser..."
cd /app/climweb/src/climweb && python manage.py shell << 'PYEOF'
import os
import traceback
from wagtail.models import Site, Page
from django.contrib.auth import get_user_model

User = get_user_model()

# Read superuser credentials from environment variables
username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
email    = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')

# --- Wagtail site configuration ---
try:
    site_hostname = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'climweb-production.up.railway.app')

    # Remove any stale/conflicting default sites
    Site.objects.filter(
        hostname__in=['localhost', '127.0.0.1', '*', 'climweb-production.up.railway.app']
    ).delete()

    # Homepage detection: slug='home' is most reliable, then title match, then first root-level page
    homepage = (
        Page.objects.filter(slug='home').first()
        or Page.objects.filter(title__icontains='AfriClimate').first()
        or Page.objects.filter(depth=2).first()
    )

    if homepage:
        site, created = Site.objects.get_or_create(
            hostname=site_hostname,
            defaults=dict(
                port=80,
                root_page=homepage,
                is_default_site=True,
                site_name='AfriClimate Center For Adaptation',
            ),
        )
        if created:
            print(f"Site created: {site_hostname} -> {homepage.title} (id={homepage.id})")
        else:
            print(f"Site already exists: {site_hostname} -> {site.root_page} (id={site.id})")
    else:
        print("WARNING: No suitable homepage found. Wagtail site not configured.")
except Exception:
    print("ERROR: Failed to configure Wagtail site:")
    traceback.print_exc()

# --- Superuser creation ---
try:
    if username:
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            print(f"Superuser created: {username}")
        else:
            print(f"Superuser already exists: {username}")
    else:
        print(
            "WARNING: DJANGO_SUPERUSER_USERNAME is not set. "
            "Set DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, and "
            "DJANGO_SUPERUSER_PASSWORD in Railway environment variables to "
            "create a superuser automatically."
        )
except Exception:
    print("ERROR: Failed to create superuser:")
    traceback.print_exc()

# --- Verification output for deployment logs ---
try:
    print("Current sites:", list(Site.objects.values('id', 'hostname', 'root_page_id', 'is_default_site')))
    print("Superusers:", list(User.objects.filter(is_superuser=True).values('username', 'email')))
except Exception:
    traceback.print_exc()
PYEOF

echo "Starting Gunicorn..."
exec gunicorn climweb.config.wsgi:application --bind "0.0.0.0:${PORT}" --log-file -
ENTRYEOF
RUN chmod +x /entrypoint.sh


# Expose port (Railway will override this)
EXPOSE 8080

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]