FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=climweb.config.settings.prod \
    PYTHONPATH=/app/climweb/src

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    postgresql-client \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    binutils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory to where manage.py actually lives
WORKDIR /app/climweb/src/climweb

# Copy requirements first for better caching
COPY climweb/requirements/ /app/climweb/requirements/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install django-environ gunicorn whitenoise psycopg2-binary && \
    pip install -r /app/climweb/requirements/base.txt 

# Copy the entire project
COPY climweb/ /app/climweb/

# Set environment variables for GDAL/GEOS
ENV GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu \
    GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu

# Verify manage.py exists
RUN ls -la /app/climweb/src/climweb/manage.py && \
    echo "✓ manage.py found at /app/climweb/src/climweb/manage.py"

# Create an entrypoint script to handle startup tasks
RUN echo '#!/bin/bash' > /entrypoint.sh && \
    echo 'set -e' >> /entrypoint.sh && \
    echo '' >> /entrypoint.sh && \
    echo '# Run migrations' >> /entrypoint.sh && \
    echo 'echo "Running database migrations..."' >> /entrypoint.sh && \
    echo 'python manage.py migrate --noinput || echo "Migration failed or not needed"' >> /entrypoint.sh && \
    echo '' >> /entrypoint.sh && \
    echo '# Collect static files' >> /entrypoint.sh && \
    echo 'echo "Collecting static files..."' >> /entrypoint.sh && \
    echo 'python manage.py collectstatic --noinput || echo "Collectstatic failed"' >> /entrypoint.sh && \
    echo '' >> /entrypoint.sh && \
    echo '# Start Gunicorn' >> /entrypoint.sh && \
    echo 'echo "Starting Gunicorn..."' >> /entrypoint.sh && \
    echo 'exec gunicorn climweb.config.wsgi:application --bind 0.0.0.0:$PORT --log-file -' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Expose port (Railway will override this)
EXPOSE 8000

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]