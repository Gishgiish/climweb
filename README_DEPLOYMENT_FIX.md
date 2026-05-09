# Deployment Fix: Wagtail Default Welcome Page Issue

## Problem
Upon deployment to Railway.app, the system shows the default Wagtail welcome page instead of the configured HomePage.

## Root Causes Identified

1. **Hardcoded Port in Entrypoint Script**
   - The `climweb/docker/entrypoint.sh` script had `runtime_port = 80` hardcoded
   - Railway assigns dynamic ports (typically 8080), causing Wagtail site resolution to fail
   - **FIXED**: Now reads from `PORT` environment variable with fallback to 80

2. **Missing Site Configuration in Fixture**
   - `wagtail_prod_sync.json` only contained user accounts, no `wagtailcore.Site` objects
   - Without a proper Site object, Wagtail can't determine which page is the homepage
   - **FIXED**: Created `wagtail_site_fixture.json` and updated entrypoint to load it

3. **No Data Migration for Site Setup**
   - No migration existed to ensure HomePage and Site are created during initial setup
   - **FIXED**: Created migration `0031_create_default_homepage_site.py`

## Files Changed

### 1. `climweb/docker/entrypoint.sh`
- Fixed hardcoded port to use environment variable
- Added loading of site fixture before dynamic configuration
- Improved error handling and logging

### 2. `climbed/wagtail_site_fixture.json` (NEW)
- Contains Wagtail Site configuration
- Uses hostname='*' to match any domain
- Will be overridden by runtime configuration if RAILWAY_PUBLIC_DOMAIN is set

### 3. `climweb/src/climweb/pages/home/migrations/0031_create_default_homepage_site.py` (NEW)
- Creates default HomePage if none exists
- Configures Site during migration
- Ensures fresh deployments have working homepage

### 4. `climweb/src/climweb/pages/home/management/commands/export_site_fixture.py` (NEW)
- Utility command to export current Site configuration
- Useful for syncing production site settings to repository

## How It Works Now

1. **On Deployment:**
   - Migrations run (including new 0031 migration)
   - User fixture loaded (`wagtail_prod_sync.json`)
   - Site fixture loaded (`wagtail_site_fixture.json`)
   - Dynamic site configuration runs in entrypoint script
   - Site is configured with correct hostname and PORT

2. **Site Resolution:**
   - Wagtail matches incoming requests by hostname + port
   - Railway's proxy handles SSL termination
   - Site configured with port 80 works for HTTPS requests
   - Fallback to '*' hostname catches any unmatched domains

## Verification Steps

After deploying to Railway:

1. Check deployment logs for:
   ```
   Site created: your-domain.up.railway.app:80 -> Home (id=X)
   ```

2. Access Wagtail admin at `/admin/settings/sites/`
   - Verify site is configured correctly
   - Check hostname and port match your Railway domain

3. If issues persist, run manually via Django shell:
   ```python
   from wagtail.models import Site, Page
   homepage = Page.objects.filter(slug='home').first()
   Site.objects.all().delete()
   Site.objects.create(
       hostname='*',
       port=80,
       root_page=homepage,
       is_default_site=True,
       site_name='AfriClimate Center For Adaptation',
   )
   ```

## Environment Variables Required on Railway

```
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@africlimate.org
DJANGO_SUPERUSER_PASSWORD=<secure-password>
RAILWAY_PUBLIC_DOMAIN=climweb-production.up.railway.app
PORT=8080  # Railway sets this automatically
DATABASE_URL=<your-postgres-url>
```

## Additional Notes

- The migration uses `depth__gt=1` to find HomePage (root page has depth=1)
- Site fixture uses pk=1 and root_page=3 as defaults (adjust if needed)
- The entrypoint script deletes all existing sites before creating new one
- This ensures clean state on each deployment
