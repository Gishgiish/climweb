FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so \
    GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so.1 \
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

# Copy entrypoint script into the image (keeps Dockerfile lintable)
COPY climweb/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh


# Expose port (Railway will override this)
EXPOSE 8080

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]