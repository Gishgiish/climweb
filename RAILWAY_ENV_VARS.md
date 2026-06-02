# Railway Environment Variables for ClimWeb

Minimum required variables:

- `DATABASE_URL` — full connection URL for the Postgres DB (must point to a PostGIS-enabled database). Example: `postgres://user:pass@host:5432/dbname`
- `SECRET_KEY` — Django secret key used in production

Recommended / Wagtail setup:

- `DJANGO_SETTINGS_MODULE` — (optional if image sets it) recommended: `climweb.config.settings.prod`
- `DJANGO_SUPERUSER_USERNAME` — for automatic superuser creation at startup
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`
- `RAILWAY_PUBLIC_DOMAIN` — used by entrypoint to set Wagtail `Site` hostname (e.g., `climweb-production.up.railway.app`)
 - `NEXTJS_SERVER_URL` — public URL of the deployed MapViewer (e.g., `https://mapviewer.yoursite.com`). This must be set in Railway's environment variables so `django_nextjs` can contact the Next.js server. If unset, MapViewer will be disabled and pages will return 503.

Database and connection tuning (optional):

- `DB_CONNECTION_MAX_AGE` — integer seconds for `CONN_MAX_AGE`
- `DB_CONN_HEALTH_CHECKS` — `True`/`False`
- `DB_DISABLE_SERVER_SIDE_CURSORS` — `True`/`False`
- `DB_SSL_REQUIRE` — `True`/`False` (if you require SSL)

Security and Hosts:

- `ALLOWED_HOSTS` — comma-separated list of hostnames
- `CSRF_TRUSTED_ORIGINS` — comma-separated list of origins
- `SECURE_SSL_REDIRECT` — `True`/`False`

Email (optional):

- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`

Runtime / build flags:

- `MIGRATE_ON_STARTUP` — `true`/`false` (default `true`)
- `COLLECT_STATICFILES_ON_STARTUP` — `true`/`false` (default `true`)

Geomanager / data ingestion (if used):

- `GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR` — path inside the container
- `WATCH_GEOMANAGER_DATA_DIR` — `true`/`false`

Optional monitoring / telemetry:

- `OTEL_EXPORTER_OTLP_ENDPOINT` and other OTEL env vars if you enable telemetry

Notes:
- Ensure the runtime image used by Railway includes GDAL/GEOS/PROJ native libraries. Use `Dockerfile.prod` (based on `osgeo/gdal`) or make sure buildpacks provide these libs.
- `DATABASE_URL` must refer to a PostGIS-enabled database; you can verify PostGIS with:

  ```bash
  railway run psql "$DATABASE_URL" -c "SELECT PostGIS_Version();"
  ```

- The repository contains a verifier script `climweb/src/climweb/scripts/verify_db.py` which will print a sanitized DB config and validate engine and PostGIS presence during container startup.
