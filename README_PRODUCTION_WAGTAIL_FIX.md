Issue: Deployed site shows Wagtail's default welcome page instead of the configured ClimWeb homepage

Summary
-------
When deploying to Railway the site served the Wagtail default page instead of the ClimWeb homepage. Logs showed the app running with production settings and the DB checks passing, but the Wagtail Site resolution did not match the runtime server port/host. As a result incoming requests were routed to the default Wagtail site.

Root cause
----------
- Wagtail resolves a request to a `Site` by matching the request `Host` header and the server `port`. In the repository the entrypoint and management command created the `Site` object with a hard-coded `port=80`.
- Railway provides the container port as `PORT` (commonly `8080`) and the process inside the container may bind to that port. If Wagtail `Site` is created with `port=80` while the server listens on `8080`, the host+port lookup fails and Wagtail falls back to the default site.
- Additionally, some management/entrypoint scripts were not using `PORT` at runtime to set site port, and a management command (`configure_site`) also used `port=80`.

What I changed (fixes)
---------------------
1. Make site creation use the runtime `PORT` environment variable (fallback to `CLIMWEB_PORT`/80):
   - `climweb/climweb/docker/entrypoint.sh` (entrypoint used by top-level Docker image)
   - `climweb/climweb/src/climweb/pages/home/management/commands/configure_site.py` (management command used to configure site)
   - `climweb/climweb/docker/docker-entrypoint.sh` (production image entrypoint already uses `CLIMWEB_PORT` to bind Gunicorn and now exports it from `PORT` if present)

2. Ensure `RAILWAY_PUBLIC_DOMAIN` is used as the site hostname when available and that `ALLOWED_HOSTS` includes Railway domains (already present in `prod.py`).

3. Keep DB and PostGIS verification intact (the existing `verify_db` check is useful and remains in the entrypoint). The recent AppConfig `ready()` logs a warning if a backend attribute is missing — this is non-fatal and only diagnostic.

How to verify locally (replicate on Railway)
--------------------------------------------
1. Build the production image:

```bash
docker build -f Dockerfile.prod -t climweb:prod .
```

2. Run the image with a Railway-style `PORT` and test site resolution (replace DATABASE_URL and SECRET_KEY):

```bash
PORT=8080 DATABASE_URL='postgresql://user:pass@host:5432/climweb' SECRET_KEY='secret' \
  docker run --rm -e PORT -e DATABASE_URL -e SECRET_KEY -p 8080:8080 climweb:prod
```

3. Visit the deployed URL (http://localhost:8080) and confirm the ClimWeb homepage (not Wagtail default) appears.

Deployment checklist for Railway
-------------------------------
- Use `Dockerfile.prod` as the build target (set in `railway.toml`).
- Set `RAILWAY_PUBLIC_DOMAIN` to the public domain Railway assigns (e.g., `climweb-production.up.railway.app`).
- Set `DATABASE_URL` and `SECRET_KEY` as Railway secrets.
- Ensure the service uses the built image's default `CMD` (Gunicorn) and does not override the start command to a development server.
- Optionally set `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD` to create a superuser on first boot.

Notes and caveats
-----------------
- The AppConfig `DbEngineConfig.ready()` currently logs a warning if it cannot find a `geo_db_type` on the PostGIS DatabaseWrapper. This does not prevent startup, but it indicates a mismatch between the project's DB engine wrapper and the installed backend. If you prefer a fail-fast behavior, modify `apps.py` to raise instead of logging.
- If the repository contains an in-repo fixture `wagtail_prod_sync.json`, the entrypoint will attempt to `loaddata` it which may already set the `Site`; the runtime `PORT` will still be applied by the updated logic when the site is created/updated.

Questions
---------
- Do you want `DbEngineConfig.ready()` to be fatal on validation failure, or leave it as a warning?
- Should we also force an `update_or_create` (replace) behavior that deletes all existing `Site` objects and recreates a single known site? Current commands use `get_or_create` / `update_or_create` — both are conservative.

If you want, I can now:
- Run a build+smoke test locally (I will need your `DATABASE_URL` + `SECRET_KEY` env values), or
- Apply an aggressive `Site` replace behavior (delete all sites then create one) so there is no chance the default Wagtail site remains.

Aggressive replace-all-sites strategy applied
------------------------------------------
I applied the aggressive strategy during startup which deletes all existing Wagtail `Site` objects and recreates a single site for the runtime domain/port. Files changed:

- `climweb/climweb/docker/entrypoint.sh` — now clears all existing sites and creates the configured site using the runtime `PORT`.
- `climweb/climweb/src/climweb/pages/home/management/commands/configure_site.py` — uses runtime `PORT` and already clears existing sites.

This ensures there is a single authoritative `Site` matching the Railway runtime and avoids fallback to the Wagtail welcome page.
