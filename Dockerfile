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
echo "Configuring Wagtail site and superuser..."\n\
cd /app/climweb/src/climweb && python manage.py shell << 'PYEOF'\n\
import os\n\
from wagtail.models import Site, Page\n\
from django.contrib.auth import get_user_model\n\
\n\
User = get_user_model()\n\
\n\
# Fix or create the site for Railway\n\
site_hostname = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "climweb-production.up.railway.app")\n\
\n\
# Delete conflicting sites (localhost, wildcard, or old railway domains)\n\
Site.objects.filter(hostname__in=["localhost", "127.0.0.1", "*", "climweb-production.up.railway.app"]).delete()\n\
\n\
# Get the homepage - try by title first, fallback to first root page\n\
homepage = Page.objects.filter(title__icontains="AfriClimate").first()\n\
if not homepage:\n\
    homepage = Page.objects.filter(depth=2).first()\n\
\n\
if homepage:\n\
    Site.objects.create(\n\
        hostname=site_hostname,\n\
        port=80,\n\
        root_page=homepage,\n\
        is_default_site=True,\n\
        site_name="AfriClimate Center For Adaptation"\n\
    )\n\
    print(f"Site created for: {site_hostname} -> {homepage.title}")\n\
else:\n\
    print("WARNING: No homepage found. Site not configured.")\n\
\n\
# Create superuser if it does not exist (avoids crash if already present)\n\
username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")\n\
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "africlimate.center@gmail.com")\n\
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "Mazingira@2026")\n\
\n\
if not User.objects.filter(username=username).exists():\n\
    User.objects.create_superuser(username=username, email=email, password=password)\n\
    print(f"Superuser {username} created")\n\
else:\n\
    print(f"Superuser {username} already exists")\n\
PYEOF\n\
\n\
echo "Starting Gunicorn..."\n\
exec gunicorn climweb.config.wsgi:application --bind 0.0.0.0:$PORT --log-file -\n' > /entrypoint.sh \
    && chmod +x /entrypoint.sh

# Expose port (Railway will override this)
EXPOSE 8080

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]