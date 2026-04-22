#!/usr/bin/env bash
set -e

# Railway provides $PORT, default to 8080 if not set
PORT=${PORT:-8080}

echo "Waiting for database to be ready..."
sleep 20

echo "Inspecting Django DB engine and DATABASE_URL (sanitized)..."
cd /app/climweb/src/climweb || true
python -m climweb.scripts.verify_db || {
    echo "verify_db failed; aborting startup"
    exit 2
}

echo "Running migrations (with retries)..."
cd /app/climweb/src/climweb || true
MAX_ATTEMPTS=6
attempt=1
until python manage.py migrate --noinput; do
    if [ $attempt -ge $MAX_ATTEMPTS ]; then
        echo "Migrations failed after $attempt attempts. Exiting."
        exit 1
    fi
    echo "Migrate attempt $attempt failed, retrying in 5s..."
    attempt=$((attempt+1))
    sleep 5
done

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

    # Aggressive strategy: remove all existing Site objects so the configured
    # site is the only one present. This avoids clashes with the default
    # Wagtail welcome site and ensures host+port resolution matches runtime.
    Site.objects.all().delete()
    print('Cleared all existing Wagtail Site objects')

    # Homepage detection: slug='home' is most reliable, then title match.
    # NOTE: No depth=2 fallback — that catches the default Wagtail welcome page (id=2).
    homepage = (
        Page.objects.filter(slug='home').first()
        or Page.objects.filter(title__icontains='AfriClimate').first()
    )

    if homepage:
        runtime_port = int(os.environ.get('PORT', os.environ.get('CLIMWEB_PORT', '80')))
        site, created = Site.objects.get_or_create(
            hostname=site_hostname,
            defaults=dict(
                port=runtime_port,
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
        print("WARNING: No suitable homepage found (no page with slug='home' or title containing 'AfriClimate').")
        print("WARNING: Wagtail site NOT configured — set it manually via the Wagtail admin (/cms/sites/).")
        print("INFO: All pages currently in the database:")
        for p in Page.objects.all().order_by('depth', 'id').values('id', 'slug', 'title', 'depth'):
            print(f"  id={p['id']}  depth={p['depth']}  slug={p['slug']!r}  title={p['title']!r}")
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

