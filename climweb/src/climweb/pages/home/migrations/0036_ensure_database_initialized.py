"""
Migration 0036: Ensure database is properly initialized.

This migration guards against the scenario where the container starts but
migrations were not applied (e.g. the entrypoint script was not invoked
correctly). It checks whether the core Wagtail tables exist and, if they do,
ensures the Site object and HomePage are present and correctly configured.

All operations are idempotent: safe to run multiple times on a fully
initialized database. All actions are logged to stdout so they appear in
deployment logs.
"""

import sys
import traceback

from django.db import migrations, connection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _table_exists(table_name):
    """Return True if *table_name* exists in the current database."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.tables"
            "  WHERE table_schema = 'public' AND table_name = %s"
            ")",
            [table_name],
        )
        return cursor.fetchone()[0]


# ---------------------------------------------------------------------------
# Step 1 – Verify core tables exist and log database state
# ---------------------------------------------------------------------------

def _check_database_state(apps, schema_editor):
    """
    Check whether the core Wagtail tables exist and log the result.

    If wagtailcore_site does not exist at this point, it means the migration
    runner itself is creating the tables right now (i.e. this is a fresh
    database). In that case we log a warning and return — the subsequent
    steps will handle object creation once the tables are available.
    """
    core_tables = [
        'wagtailcore_page',
        'wagtailcore_site',
        'wagtailcore_locale',
        'django_content_type',
    ]

    print("[0036] Checking core database tables...", flush=True)
    all_present = True
    for table in core_tables:
        exists = _table_exists(table)
        status = "OK" if exists else "MISSING"
        print(f"  [0036] {table}: {status}", flush=True)
        if not exists:
            all_present = False

    if all_present:
        print("[0036] All core tables present — database is initialized.", flush=True)
    else:
        print(
            "[0036] WARNING: Some core tables are missing. "
            "This is expected on a brand-new database where migrations are "
            "running for the first time. The Site/HomePage setup steps below "
            "will be skipped and should be handled by the entrypoint script "
            "after all migrations complete.",
            flush=True,
        )

    return all_present


# ---------------------------------------------------------------------------
# Step 2 – Ensure Site object exists
# ---------------------------------------------------------------------------

def _ensure_site(apps, schema_editor):
    """
    Ensure at least one Wagtail Site record exists and is marked as default.

    Uses the historical model proxy so this migration remains stable even if
    the real Site model changes in future Wagtail versions.
    """
    if not _table_exists('wagtailcore_site'):
        print("  [0036] wagtailcore_site table missing — skipping Site check.", flush=True)
        return

    try:
        import os

        Site = apps.get_model('wagtailcore', 'Site')
        Page = apps.get_model('wagtailcore', 'Page')

        site_count = Site.objects.count()
        print(f"  [0036] Current Site count: {site_count}", flush=True)

        if site_count > 0:
            # Ensure exactly one site is marked as default.
            default_sites = Site.objects.filter(is_default_site=True)
            if default_sites.count() == 0:
                first_site = Site.objects.first()
                first_site.is_default_site = True
                first_site.save()
                print(
                    f"  [0036] No default site found — marked site id={first_site.pk} as default.",
                    flush=True,
                )
            else:
                print(
                    f"  [0036] Default site already configured (id={default_sites.first().pk}).",
                    flush=True,
                )
            return

        # No sites at all — try to create one pointing at the HomePage.
        print("  [0036] No Site records found — attempting to create one.", flush=True)

        # Find a suitable root page (HomePage by slug, or depth=2 fallback).
        homepage = (
            Page.objects.filter(slug='home').first()
            or Page.objects.filter(depth=2).first()
        )

        if homepage is None:
            print(
                "  [0036] No suitable root page found for Site — skipping Site creation. "
                "Run manage.py create_homepage after migrations complete.",
                flush=True,
            )
            return

        site_hostname = os.environ.get(
            'RAILWAY_PUBLIC_DOMAIN',
            os.environ.get('CLIMWEB_PUBLIC_DOMAIN', 'localhost'),
        )

        Site.objects.create(
            hostname=site_hostname,
            port=80,
            root_page=homepage,
            is_default_site=True,
            site_name='AfriClimate Center For Adaptation',
        )
        print(
            f"  [0036] Created Site: {site_hostname}:80 -> \"{homepage.title}\" (id={homepage.pk}).",
            flush=True,
        )

    except Exception as exc:
        print(f"  [0036] ERROR in _ensure_site: {exc}", flush=True)
        traceback.print_exc(file=sys.stdout)


# ---------------------------------------------------------------------------
# Step 3 – Ensure HomePage exists
# ---------------------------------------------------------------------------

def _ensure_homepage(apps, schema_editor):
    """
    Ensure a HomePage record exists in the Wagtail page tree.

    If no HomePage is found, log a clear message directing operators to run
    manage.py create_homepage. We do not attempt to create the HomePage here
    because doing so correctly requires the real Wagtail model (not the
    historical proxy) and the treebeard tree-management methods.
    """
    if not _table_exists('wagtailcore_page'):
        print("  [0036] wagtailcore_page table missing — skipping HomePage check.", flush=True)
        return

    try:
        # Use the real model so we get accurate results.
        try:
            from climweb.pages.home.models import HomePage
        except ImportError as exc:
            print(f"  [0036] Could not import HomePage: {exc} — skipping.", flush=True)
            return

        home_count = HomePage.objects.count()
        print(f"  [0036] Current HomePage count: {home_count}", flush=True)

        if home_count > 0:
            home = HomePage.objects.first()
            print(
                f"  [0036] HomePage exists: \"{home.title}\" "
                f"(id={home.pk}, slug={home.slug!r}, live={home.live}).",
                flush=True,
            )
        else:
            print(
                "  [0036] WARNING: No HomePage found in the database. "
                "The entrypoint script will run manage.py create_homepage "
                "after migrations complete to create it automatically.",
                flush=True,
            )

    except Exception as exc:
        print(f"  [0036] ERROR in _ensure_homepage: {exc}", flush=True)
        traceback.print_exc(file=sys.stdout)


# ---------------------------------------------------------------------------
# Top-level migration function
# ---------------------------------------------------------------------------

def ensure_database_initialized(apps, schema_editor):
    print("[0036] ensure_database_initialized — start", flush=True)

    tables_ok = _check_database_state(apps, schema_editor)

    if tables_ok:
        _ensure_homepage(apps, schema_editor)
        _ensure_site(apps, schema_editor)
    else:
        print(
            "[0036] Skipping Site/HomePage checks because core tables are missing. "
            "This is normal on a fresh database — the entrypoint will configure "
            "the site after all migrations have run.",
            flush=True,
        )

    print("[0036] ensure_database_initialized — done", flush=True)


def reverse_ensure_database_initialized(apps, schema_editor):
    """Reverse is a no-op — we do not want to undo site/page configuration."""
    pass


# ---------------------------------------------------------------------------
# Migration class
# ---------------------------------------------------------------------------

class Migration(migrations.Migration):

    dependencies = [
        ('home', '0035_configure_branding_and_pages'),
    ]

    operations = [
        migrations.RunPython(
            ensure_database_initialized,
            reverse_ensure_database_initialized,
        ),
    ]
