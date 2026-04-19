Deployment notes for Railway.app

Required environment variables (set these as Railway project secrets):

- `DATABASE_URL` - your production database URL (required by prod settings)
- `SECRET_KEY` - Django `SECRET_KEY` (required in prod)
- `ALLOWED_HOSTS` - optional; `prod.py` will always allow `.up.railway.app` and `.railway.app`
- `RAILWAY_PUBLIC_DOMAIN` - the Railway public domain for your service (e.g. `climweb-production.up.railway.app`). Used to create the Wagtail `Site` object if needed.
- `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD` - optional; if set the entrypoint will create the superuser during startup.

How this deployment config works

- The container entrypoint now attempts to `loaddata` the repository fixture `climweb/wagtail_prod_sync.json` at startup. This imports saved `auth.user` and `wagtailcore.site` objects when present.
- If the fixture is not present or does not configure the site correctly, the entrypoint runs logic to create/update a `Site` object using `RAILWAY_PUBLIC_DOMAIN` and a stable homepage lookup.
- Superuser creation is controlled by the `DJANGO_SUPERUSER_*` environment variables. If you do not set them, no superuser will be created automatically.

Verification commands (run inside the container or using `manage.py`):

```bash
# List configured Wagtail sites
python manage.py shell -c "from wagtail.models import Site; print(list(Site.objects.values('id','hostname','root_page','is_default_site')))"

# List superusers
python manage.py shell -c "from django.contrib.auth import get_user_model; User=get_user_model(); print(list(User.objects.filter(is_superuser=True).values('username','email')))"
```

If you prefer to run configuration manually, you can run the management command we provide:

```bash
python manage.py configure_site
```

This command will attempt to load `climweb/wagtail_prod_sync.json` (if present), create/update the `Site`, and create a superuser if the env vars are set.

Security note: Do not hardcode production passwords in the repository. Use Railway secrets for `DJANGO_SUPERUSER_PASSWORD` and `SECRET_KEY`.
