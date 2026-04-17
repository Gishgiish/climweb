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
echo "Waiting for database to be ready..."\n\
sleep 10\n\
\n\
echo "Running migrations..."\n\
cd /app/climweb/src/climweb && python manage.py migrate --noinput\n\
\n\
echo "Collecting static files..."\n\
cd /app/climweb/src/climweb && python manage.py collectstatic --noinput\n\
\n\
echo "Starting Gunicorn..."\n\
exec gunicorn climweb.config.wsgi:application --bind 0.0.0.0:$PORT --log-file -\n' > /entrypoint.sh \
    && chmod +x /entrypoint.sh

# Expose port (Railway will override this)
EXPOSE 8000

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]