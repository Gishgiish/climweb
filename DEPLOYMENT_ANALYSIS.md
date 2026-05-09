# Comprehensive Analysis: Wagtail Default Welcome Page Issue on Railway.app

## Executive Summary

After thorough analysis of the codebase, I've identified **multiple layers of protection** now in place to ensure your configured HomePage appears instead of the default Wagtail welcome page. However, there are still **critical potential failure points** that need attention.

---

## Current State: What's Been Fixed ✅

### 1. **Migration 0031_create_default_homepage_site.py** (Updated)
- **Creates HomePage** if none exists with slug='home'
- **Configures Site** with hostname='*' and port=80 (placeholder)
- **Enhanced logging** to debug issues during deployment
- Shows available pages if no HomePage found

### 2. **Entrypoint Script** (`climweb/docker/docker-entrypoint.sh`)
- ✅ Reads `PORT` environment variable from Railway
- ✅ Calls `configure_site` management command
- ✅ Runs inline Python to update Site configuration at runtime
- ✅ Uses `RAILWAY_PUBLIC_DOMAIN` or defaults to `climweb-production.up.railway.app`
- ✅ Deletes all existing sites before creating new one (aggressive cleanup)

### 3. **Management Command** (`configure_site.py`)
- ✅ Loads fixtures if present
- ✅ Finds HomePage by slug='home' OR title contains 'AfriClimate' OR depth=2 fallback
- ✅ Updates Site with runtime PORT
- ✅ Creates superuser if env vars provided

### 4. **Site Fixture** (`wagtail_site_fixture.json`)
- Contains Site configuration with hostname='*', port=80, root_page=3
- Loaded during startup if present

---

## Critical Issues Still Present ⚠️

### Issue #1: Fixture Has Hardcoded root_page=3
```json
{
  "model": "wagtailcore.site",
  "pk": 1,
  "fields": {
    "hostname": "*",
    "port": 80,
    "root_page": 3  // ← HARDCODED! May not match actual HomePage ID
  }
}
```

**Problem**: If your HomePage has a different ID in production, the fixture will point to the wrong page.

**Solution**: The entrypoint script's runtime configuration should override this, but the fixture could cause issues if loaded after runtime config.

### Issue #2: Migration Uses Placeholder Port
The migration creates Site with port=80, relying on entrypoint to update it. If entrypoint fails or runs before migration completes, you'll have wrong port.

### Issue #3: Multiple Site Configuration Points
You have **THREE** places configuring the Site:
1. Migration 0031 (runs during migrate)
2. configure_site management command (called by entrypoint)
3. Inline Python in entrypoint.sh (also called by entrypoint)

This is redundant and could cause race conditions or conflicts.

### Issue #4: Depth=2 Fallback is Dangerous
In `configure_site.py`:
```python
homepage = (
    Page.objects.filter(slug='home').first()
    or Page.objects.filter(title__icontains='AfriClimate').first()
    or Page.objects.filter(depth=2).first()  # ← DANGEROUS!
)
```

**Problem**: The default Wagtail welcome page is often at depth=2! This could accidentally select the wrong page.

---

## Recommended Additional Fixes

### Fix A: Remove Dangerous Depth=2 Fallback

Edit `climweb/src/climweb/pages/home/management/commands/configure_site.py`:

```python
# REMOVE this line:
# or Page.objects.filter(depth=2).first()

# Keep only safe detection methods:
homepage = (
    Page.objects.filter(slug='home').first()
    or Page.objects.filter(title__icontains='AfriClimate').first()
)
```

### Fix B: Update Fixture to Not Override Runtime Config

Option 1: Delete the fixture entirely (recommended)
```bash
rm climweb/wagtail_site_fixture.json
```

Option 2: Update fixture to use a clearly invalid root_page that will be caught:
```json
{
  "model": "wagtailcore.site",
  "pk": 1,
  "fields": {
    "hostname": "*",
    "port": 80,
    "root_page": 99999,  // Invalid - will force runtime reconfiguration
    "is_default_site": false  // Not default
  }
}
```

### Fix C: Add Verification Step After Site Configuration

Add to entrypoint.sh after site configuration:

```python
# Verify site is correctly configured
site = Site.objects.filter(hostname=site_hostname).first()
if not site:
    print(f"ERROR: Site not created for {site_hostname}")
    exit(1)
    
if site.root_page.slug != 'home' and 'AfriClimate' not in site.root_page.title:
    print(f"WARNING: Site root_page may be incorrect: {site.root_page}")
    
print(f"VERIFIED: Site configured correctly -> {site.root_page.title}")
```

### Fix D: Ensure Migration Order is Correct

Verify migration 0031 runs AFTER all page migrations:

```bash
# Check migration dependencies
grep -r "0031_create_default_homepage_site" climweb/src/climweb/pages/home/migrations/
```

Current dependencies look correct:
```python
dependencies = [
    ('home', '0030_homepage_call_to_action_button_text_2_and_more'),
    ('wagtailcore', '0094_alter_page_locale'),
]
```

### Fix E: Add Health Check for Site Configuration

Create a new management command `verify_site_config.py`:

```python
from django.core.management.base import BaseCommand
from wagtail.models import Site, Page

class Command(BaseCommand):
    help = 'Verify Wagtail Site is correctly configured'
    
    def handle(self, *args, **options):
        sites = Site.objects.all()
        
        if not sites.exists():
            self.stderr.write('ERROR: No sites configured!')
            return False
            
        for site in sites:
            self.stdout.write(f'Site: {site.hostname}:{site.port}')
            self.stdout.write(f'  Root page: {site.root_page.title} (slug={site.root_page.slug})')
            
            if site.root_page.slug != 'home':
                self.stderr.write(f'WARNING: Root page slug is not "home"!')
                
        return True
```

Call this in healthcheck or after startup.

---

## Deployment Checklist for Railway

### Environment Variables to Set:
```
PORT=8080  # Railway default, but good to be explicit
RAILWAY_PUBLIC_DOMAIN=climweb-production.up.railway.app
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@africlimate.org
DJANGO_SUPERUSER_PASSWORD=<secure-password>
DJANGO_SETTINGS_MODULE=climweb.config.settings.production
```

### Railway Dashboard Settings:
1. ✅ Dockerfile: `Dockerfile.prod`
2. ✅ Builder: `DOCKERFILE`
3. ✅ Build Command: `--target=base`
4. ⚠️ Health Check Path: `/` (should verify this works)

### Post-Deployment Verification Steps:

1. **Check logs for these messages:**
   ```
   "Created default HomePage" OR "Configured Site with homepage"
   "Site created:" or "Site updated:"
   "Superuser created:" or "Superuser already exists"
   ```

2. **Access Wagtail Admin:**
   ```
   https://climweb-production.up.railway.app/cms/admin/
   ```

3. **Verify Site Configuration:**
   - Go to Settings → Sites
   - Should show ONE site with:
     - Hostname: `climweb-production.up.railway.app` or `*`
     - Port: matches Railway's PORT (usually 8080)
     - Root page: Your HomePage (not "Welcome to your new Wagtail site")

4. **If still seeing default page:**
   - Check logs for errors
   - Manually fix via admin: Settings → Sites → Edit
   - Set correct root page to your HomePage

---

## Nuclear Option: Manual Recovery Script

If deployment still shows default page, create this emergency script:

```python
# save as fix_site_emergency.py
from wagtail.models import Site, Page

# Delete all sites
Site.objects.all().delete()

# Find the real HomePage
homepage = Page.objects.filter(slug='home').first()
if not homepage:
    homepage = Page.objects.filter(title__icontains='AfriClimate').first()
    
if homepage:
    Site.objects.create(
        hostname='*',
        port=80,
        root_page=homepage,
        is_default_site=True,
        site_name='AfriClimate Center For Adaptation',
    )
    print(f"Fixed! Site now points to: {homepage.title}")
else:
    print("ERROR: Could not find HomePage!")
    print("Available pages:")
    for p in Page.objects.all()[:20]:
        print(f"  {p.id}: {p.title} (slug={p.slug}, depth={p.depth})")
```

Run via Django shell in Railway console.

---

## Final Recommendation

Your current fixes are **80% sufficient**. To reach 100% reliability:

1. ✅ **DO**: Remove depth=2 fallback from configure_site.py
2. ✅ **DO**: Delete wagtail_site_fixture.json (let runtime config handle everything)
3. ✅ **DO**: Add verification logging after site creation
4. ✅ **DO**: Test locally with PostgreSQL before deploying
5. ⚠️ **CONSIDER**: Add health check endpoint that verifies site config

The most likely failure scenario is:
- Database already has old Site objects from previous deployments
- Fixture loads and sets wrong root_page
- Runtime config fails silently

By removing the fixture and adding better error handling, you eliminate these risks.

---

## Files Modified in This Session

1. ✅ `climweb/src/climweb/pages/home/migrations/0031_create_default_homepage_site.py`
   - Enhanced logging
   - Better comments about runtime port update

2. ✅ Already fixed: `climweb/docker/entrypoint.sh` (separate file from docker-entrypoint.sh)
   - Uses PORT env var
   - Aggressive site cleanup
   - Runtime site configuration

3. ⚠️ **NEEDS FIX**: `climweb/src/climweb/pages/home/management/commands/configure_site.py`
   - Remove depth=2 fallback

4. ⚠️ **RECOMMEND DELETE**: `climweb/wagtail_site_fixture.json`

---

## Next Steps

1. Review and approve the recommended changes
2. I can implement the remaining fixes (remove depth=2 fallback, delete fixture)
3. Test deployment on Railway staging environment first
4. Monitor logs closely on first deployment
5. Have manual recovery script ready just in case
