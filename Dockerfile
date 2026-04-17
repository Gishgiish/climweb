FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies including PostGIS and geo-libraries
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

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY climweb/requirements/ ./climweb/requirements/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install django-environ gunicorn whitenoise && \
    pip install -r climweb/requirements/base.txt && 

# Copy the entire project
COPY climweb/ ./climweb/

# Set environment variables for GDAL/GEOS
ENV GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu \
    GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu \
    PYTHONPATH=/app/climweb/src

# Collect static files
WORKDIR /app/climweb/src
RUN python ../manage.py collectstatic --noinput

# Expose port (Railway will override this)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/api/_health/')" || exit 1

# Start command (Railway will override with its own)
CMD ["gunicorn", "climweb.config.wsgi:application", "--bind", "0.0.0.0:8000", "--log-file", "-"]