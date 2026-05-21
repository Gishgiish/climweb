#!/bin/bash
# Bash strict mode: http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail

# ======================================================
# ENVIRONMENT VARIABLES USED DIRECTLY BY THIS ENTRYPOINT
# ======================================================

MIGRATE_ON_STARTUP=${MIGRATE_ON_STARTUP:-true}
COLLECT_STATICFILES_ON_STARTUP=${COLLECT_STATICFILES_ON_STARTUP:-true}
WATCH_GEOMANAGER_DATA_DIR=${WATCH_GEOMANAGER_DATA_DIR:-true}
GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR=${GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR:-/climweb/geomanager/data}

CLIMWEB_LOG_LEVEL=${CLIMWEB_LOG_LEVEL:-INFO}
CLIMWEB_NUM_OF_CELERY_WORKERS=${CLIMWEB_NUM_OF_CELERY_WORKERS:-}
GUNICORN_NUM_OF_WORKERS=${GUNICORN_NUM_OF_WORKERS:-}

CLIMWEB_CELERY_BEAT_DEBUG_LEVEL=${CLIMWEB_CELERY_BEAT_DEBUG_LEVEL:-INFO}

CLIMWEB_PORT="${CLIMWEB_PORT:-8000}"
# If a platform provides a PORT (e.g. Railway), prefer it so the container
# binds the port the platform expects.
CLIMWEB_PORT="${PORT:-${CLIMWEB_PORT}}"
export CLIMWEB_PORT

# get the current version of the app using the installed `climweb` package
# use the venv python to ensure package paths are available
CLIMWEB_APP_VERSION=$(/climweb/venv/bin/python -c "import climweb.version as v; print(v.__version__)")

show_help() {
    echo """
The available ClimWeb related commands and services are shown below:

ADMIN COMMANDS:
manage          : Manage ClimWeb and its database
shell           : Start a Django Python shell
install-plugin  : Installs a plugin (append --help for more info).
list-plugins    : Lists currently installed plugins.
help            : Show this message

SERVICE COMMANDS:
gunicorn            : Start ClimWeb using a prod ready gunicorn server:
                         * Waits for the postgres database to be available first.
                         * Automatically migrates the database on startup.
                         * Binds to 0.0.0.0
gunicorn-wsgi       : Same as gunicorn but runs a wsgi server
celery-worker       : Start the celery worker queue which runs async tasks
celery-beat         : Start the celery beat service used to schedule periodic jobs

DEV COMMANDS:
django-dev      : Start a normal Climweb backend django development server, performs
                  the same checks and setup as the gunicorn command above.

"""
}

show_startup_banner() {
  cat <<EOF
=========================================================================================
 ██████╗██╗     ██╗███╗   ███╗██╗    ██╗███████╗██████╗
██╔════╝██║     ██║████╗ ████║██║    ██║██╔════╝██╔══██╗
██║     ██║     ██║██╔████╔██║██║ █╗ ██║█████╗  ██████╔╝
██║     ██║     ██║██║╚██╔╝██║██║███╗██║██╔══╝  ██╔══██╗
╚██████╗███████╗██║██║ ╚═╝ ██║╚███╔███╔╝███████╗██████╔╝
 ╚═════╝╚══════╝╚═╝╚═╝     ╚═╝ ╚══╝╚══╝ ╚══════╝╚═════╝

Version $CLIMWEB_APP_VERSION

=========================================================================================
EOF
}

run_setup_commands_if_configured() {
    startup_plugin_setup

        # migrate database
    if [ "$MIGRATE_ON_STARTUP" = "true" ]; then
        echo "python /climweb/climweb/src/climweb/manage.py migrate"
        /climweb/climweb/src/climweb/manage.py migrate --noinput
    fi

    # configure wagtail site
    /climweb/climweb/src/climweb/manage.py configure_site

        # collect staticfiles
    if [ "$COLLECT_STATICFILES_ON_STARTUP" = "true" ]; then
        echo "python /climweb/climweb/src/climweb/manage.py collectstatic --noinput --verbosity=0"
        /climweb/climweb/src/climweb/manage.py collectstatic --noinput --verbosity=0
    fi

    # initialize geomanager
    /climweb/climweb/src/climweb/manage.py initialize_geomanager

    # reset cms upgrade status (do not fail startup if cache/redis unavailable)
    /climweb/climweb/src/climweb/manage.py reset_cms_upgrade_status || echo "Warning: reset_cms_upgrade_status failed; continuing"

    # Configure Wagtail Site and optional superuser. Use runtime port so
    # host+port resolution matches the server (important on Railway).
    /climweb/venv/bin/python /climweb/climweb/src/climweb/manage.py shell <<'PYEOF' || echo "Warning: site configuration failed; continuing"
import os, traceback
from wagtail.models import Site, Page
from django.contrib.auth import get_user_model

User = get_user_model()

try:
    site_hostname = os.environ.get('RAILWAY_PUBLIC_DOMAIN', os.environ.get('CLIMWEB_PUBLIC_DOMAIN', 'climweb-production.up.railway.app'))

    # Safer behavior: preserve existing sites by default.
    # To force a reset (dev/one-off only), set FORCE_RESET_WAGTAIL_SITE=true
    try:
        force_reset = os.environ.get('FORCE_RESET_WAGTAIL_SITE', '')
        if str(force_reset).lower() in ('1', 'true', 'yes'):
            print('FORCE_RESET_WAGTAIL_SITE set: removing existing Wagtail sites')
            Site.objects.all().delete()
        else:
            print('Preserving existing Wagtail sites (set FORCE_RESET_WAGTAIL_SITE=true to reset)')
    except Exception:
        # If something goes wrong checking the env var, do not delete sites
        print('Warning: error while checking FORCE_RESET_WAGTAIL_SITE; preserving existing sites')

    # Homepage detection: slug='home' first, then title match
    # NOTE: Deliberately avoiding depth=2 fallback - that catches default Wagtail page!
    homepage = (
        Page.objects.filter(slug='home').first()
        or Page.objects.filter(title__icontains='AfriClimate').first()
    )

    if homepage:
        runtime_port = int(os.environ.get('PORT', os.environ.get('CLIMWEB_PORT', '80')))
        site, created = Site.objects.update_or_create(
            hostname=site_hostname,
            defaults={
                'port': runtime_port,
                'root_page': homepage,
                'is_default_site': True,
                'site_name': 'AfriClimate Center For Adaptation',
            },
        )
        if created:
            print(f"Site created: {site_hostname} -> {homepage.title} (id={homepage.id})")
        else:
            print(f"Site updated: {site_hostname} -> {site.root_page} (id={site.id})")
    else:
        print("WARNING: No suitable homepage found (no page with slug='home' or title containing 'AfriClimate').")
        print("WARNING: Wagtail site NOT configured — set it manually via the Wagtail admin (/cms/sites/).")
        print("INFO: All pages currently in the database:")
        for p in Page.objects.all().order_by('depth', 'id').values('id', 'slug', 'title', 'depth'):
            print(f"  id={p['id']}  depth={p['depth']}  slug={p['slug']!r}  title={p['title']!r}")
except Exception:
    print("ERROR: Failed to configure Wagtail site:")
    traceback.print_exc()

# Superuser creation
try:
    username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
    if username:
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            print(f"Superuser created: {username}")
        else:
            print(f"Superuser already exists: {username}")
    else:
        print("DJANGO_SUPERUSER_USERNAME not set; skipping superuser creation")
except Exception:
    print("ERROR: Failed to create superuser:")
    traceback.print_exc()
PYEOF

    # watch for new files in the geomanager auto-ingest data dir
    if [ "$WATCH_GEOMANAGER_DATA_DIR" = "true" ]; then
      echo "GeoManager Listening for new files in $GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR"
      # start command to watch for new files in the geomanager auto-ingest data dir
      while file=$(inotifywait -e create --format "%w%f" -r "$GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR"); do
        EXT=${file##*.}
        if [ "$EXT" = "tif" ] || [ "$EXT" = "nc" ]; then
          echo "New Geomanager ingestion file detected: $file"
          /climweb/climweb/src/climweb/manage.py ingest_geomanager_raster created "$file" --overwrite --clip
        fi
      done &
    fi
}

start_celery_worker() {
    startup_plugin_setup

    EXTRA_CELERY_ARGS=()

    if [[ -n "$CLIMWEB_NUM_OF_CELERY_WORKERS" ]]; then
        EXTRA_CELERY_ARGS+=(--concurrency "$CLIMWEB_NUM_OF_CELERY_WORKERS")
    fi
    exec celery -A climweb worker "${EXTRA_CELERY_ARGS[@]}" -l INFO "$@"
}

attachable_exec(){
    echo "$@"
    exec bash --init-file <(echo "history -s $*; $*")
}

run_server() {
    run_setup_commands_if_configured

    if [[ "$1" = "wsgi" ]]; then
        STARTUP_ARGS=(climweb.config.wsgi:application)
    elif [[ "$1" = "asgi" ]]; then
        STARTUP_ARGS=(-k uvicorn.workers.UvicornWorker climweb.config.asgi:application)
    else
        echo -e "\e[31mUnknown run_server argument $1 \e[0m" >&2
        exit 1
    fi

    WORKERS=${GUNICORN_NUM_OF_WORKERS:-2}
    if [ -z "$WORKERS" ]; then
        WORKERS=2
    fi

    exec gunicorn --workers="$WORKERS" \
        --worker-tmp-dir "${TMPDIR:-/dev/shm}" \
        --log-file=- \
        --access-logfile=- \
        --capture-output \
        -b "0.0.0.0:${CLIMWEB_PORT}" \
        --log-level="${CLIMWEB_LOG_LEVEL}" \
        "${STARTUP_ARGS[@]}" \
        "${@:2}"
}

setup_otel_vars(){
  EXTRA_OTEL_RESOURCE_ATTRIBUTES="service.namespace=ClimWeb,"
  EXTRA_OTEL_RESOURCE_ATTRIBUTES+="service.version=${CLIMWEB_APP_VERSION},"
  EXTRA_OTEL_RESOURCE_ATTRIBUTES+="deployment.environment=${CLIMWEB_DEPLOYMENT_ENV:-production}"

  if [[ -n "${OTEL_RESOURCE_ATTRIBUTES:-}" ]]; then
    OTEL_RESOURCE_ATTRIBUTES="${EXTRA_OTEL_RESOURCE_ATTRIBUTES},${OTEL_RESOURCE_ATTRIBUTES}"
  else
    OTEL_RESOURCE_ATTRIBUTES="$EXTRA_OTEL_RESOURCE_ATTRIBUTES"
  fi
  export OTEL_RESOURCE_ATTRIBUTES
  echo "OTEL_RESOURCE_ATTRIBUTES=$OTEL_RESOURCE_ATTRIBUTES"
}

# ======================================================
# COMMANDS
# ======================================================

if [[ -z "${1:-}" ]]; then
    # Default to gunicorn in production containers to ensure the service
    # always starts when no explicit command is provided.
    if [[ "${DJANGO_SETTINGS_MODULE:-}" == *"prod"* ]] || [[ "${CLIMWEB_DEPLOYMENT_ENV:-}" == "production" ]]; then
        set -- gunicorn
    else
        echo "Must provide arguments to docker-entrypoint.sh"
        show_help
        exit 1
    fi
fi

# activate virtualenv
source /climweb/venv/bin/activate

show_startup_banner

# Ensure legacy `web/src/climweb` path exists for older deployments that expect
# `/climweb/web/src/climweb/manage.py`. Create a symlink to the actual source
# tree if needed so entrypoint commands remain compatible.
if [ ! -d /climweb/web/src/climweb ] && [ -d /climweb/climweb/src/climweb ]; then
    ln -s /climweb/climweb/src/climweb /climweb/web/src/climweb || true
fi

# wait for required services to be available, using docker-compose-wait
/wait

# load plugin utils
source /climweb/plugins/utils.sh

setup_otel_vars

echo "Inspecting Django DB engine and DATABASE_URL (sanitized)..."
# Ensure LD_LIBRARY_PATH includes common system library directory used by GDAL
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}
echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"

# Print GDAL version for debugging early in startup
python -c "from osgeo import gdal; print('GDAL version:', getattr(gdal, '__version__', 'unknown'))" || echo "Warning: unable to import GDAL to print version"

# Run verify script (this will call django.setup() before DB checks)
python -m climweb.scripts.verify_db || {
    echo "verify_db failed; aborting startup"
    exit 2
}

case "$1" in
django-dev)
    run_setup_commands_if_configured
    echo "Running Development Server on 0.0.0.0:${CLIMWEB_PORT}"
    echo "Press CTRL-p CTRL-q to close this session without stopping the container."
    export OTEL_SERVICE_NAME=climweb-dev
    attachable_exec climweb runserver "0.0.0.0:${CLIMWEB_PORT}"
    ;;
django-dev-no-attach)
    run_setup_commands_if_configured
    echo "Running Development Server on 0.0.0.0:${CLIMWEB_PORT}"
    export OTEL_SERVICE_NAME=climweb-dev
    climweb runserver "0.0.0.0:${CLIMWEB_PORT}"
    ;;
gunicorn)
    export OTEL_SERVICE_NAME="climweb-asgi"
    run_server asgi "${@:2}"
    ;;
gunicorn-wsgi)
    export OTEL_SERVICE_NAME="climweb-wsgi"
    run_server wsgi "${@:2}"
    ;;
manage)
    export OTEL_SERVICE_NAME=climweb-manage
    exec climweb "${@:2}"
    ;;
shell)
    export OTEL_SERVICE_NAME=climweb-shell
    exec climweb shell
    ;;
celery-worker)
    export OTEL_SERVICE_NAME="climweb-celery-worker"
    start_celery_worker -Q celery -n default-worker@%h "${@:2}"
    ;;
celery-beat)
    startup_plugin_setup
    export OTEL_SERVICE_NAME="climweb-celery-beat"
    exec celery -A climweb beat -l "${CLIMWEB_CELERY_BEAT_DEBUG_LEVEL}" -S django_celery_beat.schedulers:DatabaseScheduler "${@:2}"
    ;;
install-plugin)
    exec /climweb/plugins/install_plugin.sh --runtime "${@:2}"
    ;;
*)
    echo "Unknown command $1"
    show_help
    exit 2
    ;;
esac
