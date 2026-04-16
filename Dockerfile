# syntax = docker/dockerfile:1.5

# Use ubuntu-full variant which has GDAL + common build tools pre-installed
FROM ghcr.io/osgeo/gdal:ubuntu-full-3.7.0 as base

ARG UID
ENV UID=${UID:-1001}
ARG GID
ENV GID=${GID:-1001}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Create or rename group to climweb_docker_group with desired GID
RUN if getent group $GID > /dev/null; then \
        existing_group=$(getent group $GID | cut -d: -f1); \
        if [ "$existing_group" != "climweb_docker_group" ]; then \
            groupmod -n climweb_docker_group "$existing_group"; \
        fi; \
    else \
        groupadd -g $GID climweb_docker_group; \
    fi

RUN useradd --shell /bin/bash -u $UID -g $GID -o -c "" -m climweb_docker_user -l || exit 0

ENV DOCKER_USER=climweb_docker_user

# Install ONLY what's NOT already in ubuntu-full base image
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    tini \
    gosu \
    inotify-tools \
    libmagic1 \
    libffi-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install docker-compose wait
ARG DOCKER_COMPOSE_WAIT_VERSION
ENV DOCKER_COMPOSE_WAIT_VERSION=${DOCKER_COMPOSE_WAIT_VERSION:-2.12.1}
ARG DOCKER_COMPOSE_WAIT_PLATFORM_SUFFIX
ENV DOCKER_COMPOSE_WAIT_PLATFORM_SUFFIX=${DOCKER_COMPOSE_WAIT_PLATFORM_SUFFIX:-}

ADD https://github.com/ufoscout/docker-compose-wait/releases/download/$DOCKER_COMPOSE_WAIT_VERSION/wait${DOCKER_COMPOSE_WAIT_PLATFORM_SUFFIX} /wait
RUN chmod +x /wait

# Create directories and set correct permissions
RUN mkdir -p /climweb/web /climweb/plugins && chown -R $UID:$GID /climweb



# Enable pip caching for faster rebuilds
ENV PIP_CACHE_DIR=/root/.cache/pip
ENV PIP_NO_CACHE_DIR=0
RUN mkdir -p /root/.cache/pip && chown -R $UID:$GID /root/.cache/pip

USER $UID:$GID

# Copy requirements first for better layer caching
COPY ./climweb/requirements/base.txt /climweb/requirements/
RUN python3 -m venv /climweb/venv

# hadolint ignore=SC1091
RUN . /climweb/venv/bin/activate && \
     pip3 install -r /climweb/requirements/base.txt

# Copy the climweb package (has setup.py)
COPY --chown=$UID:$GID ./climweb /climweb/climweb

# Copy the web directory (Django project + pre-built Vue assets)
COPY --chown=$UID:$GID ./web /climweb/web

# Vue build is SKIPPED - assets pre-built locally and committed

# Create static and media directories
RUN mkdir -p /climweb/web/src/climweb/static \
    && mkdir -p /climweb/web/src/climweb/media \
    && mkdir -p /climweb/web/src/climweb/backup \
    && chown -R $UID:$GID /climweb/web/src/climweb

# Create a tmp directory for django to use
RUN mkdir -p /climweb/tmp && chown -R $UID:$GID /climweb/tmp

WORKDIR /climweb/web

# Ensure that Python outputs everything that's printed inside
ENV PYTHONUNBUFFERED 1

# Copy deploy plugins
COPY --chown=$UID:$GID ./deploy/plugins/*.sh /climweb/plugins/

# Create a directory for raster data to be auto-ingested
ENV GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR=/climweb/geomanager/data
RUN mkdir -p $GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR && chown -R $UID:$GID $GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR

# Install climweb as a package (from correct path)
RUN chmod a+x /climweb/climweb/docker/docker-entrypoint.sh && \
    /climweb/venv/bin/pip install --no-cache-dir -e /climweb/climweb/

ENTRYPOINT ["/usr/bin/tini", "--", "/bin/bash", "/climweb/web/docker/docker-entrypoint.sh"]

# Add the venv to the path
ENV PATH="/climweb/venv/bin:$PATH"

# Production settings
ENV DJANGO_SETTINGS_MODULE='climweb.config.settings.prod'

# Production CMD for gunicorn
CMD ["gunicorn", "climweb.config.wsgi:application", "--bind", "0.0.0.0:8000", "--log-file", "-"]

FROM base as dev

USER $UID:$GID

# Override for dev mode
ENV DJANGO_SETTINGS_MODULE='climweb.config.settings.dev'
CMD ["django-dev-no-attach"]
