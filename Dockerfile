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
    pip install -r /app/climweb/requirements/base.txt && \
    pip install -e /app/climweb/

# Copy the entire project
COPY climweb/ /app/climweb/

# Set environment variables for GDAL/GEOS
ENV GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu \
    GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu

# Verify manage.py exists
RUN ls -la /app/climweb/src/climweb/manage.py && \
    echo "✓ manage.py found at /app/climweb/src/climweb/manage.py"

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/api/_health/')" || exit 1

# Start command
CMD ["gunicorn", "climweb.config.wsgi:application", "--bind", "0.0.0.0:8000", "--log-file", "-"]