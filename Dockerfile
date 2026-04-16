# syntax = docker/dockerfile:1.5

FROM ghcr.io/osgeo/gdal:ubuntu-full-3.7.0 as base

ARG UID=1001
ENV UID=${UID}
ARG GID=1001
ENV GID=${GID}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Create user/group in one layer
RUN if getent group $GID > /dev/null; then \
        existing_group=$(getent group $GID | cut -d: -f1); \
        if [ "$existing_group" != "climweb_docker_group" ]; then \
            groupmod -n climweb_docker_group "$existing_group"; \
        fi; \
    else \
        groupadd -g $GID climweb_docker_group; \
    fi && \
    useradd --shell /bin/bash -u $UID -g $GID -o -c "" -m climweb_docker_user -l || true

ENV DOCKER_USER=climweb_docker_user

# Install packages - NOTE: Removed cache mounts to avoid Railway ID issues
# Railway requires specific ID format: s/<service id>-<target path>
# Instead, use standard RUN without cache mounts for reliability
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        cron \
        tini \
        gosu \
        inotify-tools \
        libffi-dev \
        python3-venv \
        python3-pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install docker-compose wait
ARG DOCKER_COMPOSE_WAIT_VERSION=2.12.1
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/${DOCKER_COMPOSE_WAIT_VERSION}/wait /wait
RUN chmod +x /wait

# Create directories and set permissions BEFORE switching user
RUN mkdir -p /climweb/web /climweb/plugins /climweb/tmp /root/.cache/pip && \
    chown -R $UID:$GID /climweb /root/.cache/pip

# Enable pip caching
ENV PIP_CACHE_DIR=/root/.cache/pip
ENV PIP_NO_CACHE_DIR=0

# NOW switch to non-root user
USER $UID:$GID

# Copy requirements and install Python dependencies
COPY --chown=$UID:$GID ./climweb/requirements/base.txt /climweb/requirements/
RUN python3 -m venv /climweb/venv && \
    . /climweb/venv/bin/activate && \
    pip3 install -r /climweb/requirements/base.txt

# Copy application code
COPY --chown=$UID:$GID ./climweb /climweb/climweb
COPY --chown=$UID:$GID ./web /climweb/web

# Create runtime directories
RUN mkdir -p /climweb/web/src/climweb/static \
    /climweb/web/src/climweb/media \
    /climweb/web/src/climweb/backup \
    /climweb/geomanager/data && \
    chown -R $UID:$GID /climweb/web/src/climweb /climweb/geomanager/data

WORKDIR /climweb/web

ENV PYTHONUNBUFFERED=1

# Copy deploy plugins
COPY --chown=$UID:$GID ./deploy/plugins/*.sh /climweb/plugins/

ENV GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR=/climweb/geomanager/data

# Install climweb package
RUN chmod a+x /climweb/climweb/docker/docker-entrypoint.sh && \
    /climweb/venv/bin/pip install --no-cache-dir -e /climweb/climweb/

ENTRYPOINT ["/usr/bin/tini", "--", "/bin/bash", "/climweb/web/docker/docker-entrypoint.sh"]

ENV PATH="/climweb/venv/bin:$PATH"
ENV DJANGO_SETTINGS_MODULE='climweb.config.settings.prod'

CMD ["gunicorn", "climweb.config.wsgi:application", "--bind", "0.0.0.0:8000", "--log-file", "-"]

FROM base as dev
USER $UID:$GID
ENV DJANGO_SETTINGS_MODULE='climweb.config.settings.dev'
CMD ["django-dev-no-attach"]