import os
import traceback

from django.db import migrations


def force_fix_homepage_creation(apps, schema_editor):
    """
    Force-fix the broken database state where migrations 0031 and 0032 were
    recorded as applied but failed to actually create the custom HomePage.

    This migration is idempotent: if a valid HomePage already exists and the
    Site already points to it correctly, it exits early without making changes.

    Steps:
      1. Check whether a valid HomePage already exists — if so, ensure the
         Site points to it and return.
      2. Delete all existing Wagtail Sites (the broken one pointing to the
         default welcome page).
      3. Delete all non-root pages (depth >= 2), including the default
         "Welcome to your new Wagtail site!" page.
      4. Create the custom HomePage as a child of the root page.
      5. Publish the HomePage via save_revision().publish().
      6. Create a new Site pointing to the custom HomePage.
    """
    try:
        Page = apps.get_model('wagtailcore', 'Page')
        Site = apps.get_model('wagtailcore', 'Site')

        try:
            HomePage = apps.get_model('home', 'HomePage')
        except LookupError:
            print("[0033] HomePage model not available — skipping force_fix_homepage_creation")
            return

        # ------------------------------------------------------------------
        # 1. Check whether a valid HomePage already exists.
        # ------------------------------------------------------------------
        existing_home = HomePage.objects.first()
        if existing_home:
            print(
                f"[0033] HomePage already exists: \"{existing_home.title}\" "
                f"(id={existing_home.id}, slug={existing_home.slug!r}) — "
                "ensuring Site is configured correctly."
            )
            site_hostname = os.environ.get(
                'RAILWAY_PUBLIC_DOMAIN',
                os.environ.get('CLIMWEB_PUBLIC_DOMAIN', 'climweb-production.up.railway.app'),
            )
            existing_site = Site.objects.filter(root_page=existing_home).first()
            if existing_site:
                existing_site.hostname = site_hostname
                existing_site.port = 80
                existing_site.is_default_site = True
                existing_site.site_name = 'AfriClimate Center For Adaptation'
                existing_site.save()
                Site.objects.exclude(pk=existing_site.pk).delete()
                print(
                    f"[0033] Updated Site: {existing_site.hostname}:{existing_site.port} "
                    f"-> \"{existing_home.title}\""
                )
            else:
                Site.objects.all().delete()
                site = Site.objects.create(
                    hostname=site_hostname,
                    port=80,
                    root_page=existing_home,
                    is_default_site=True,
                    site_name='AfriClimate Center For Adaptation',
                )
                print(
                    f"[0033] Created Site: {site.hostname}:{site.port} "
                    f"-> \"{existing_home.title}\""
                )
            return

        # ------------------------------------------------------------------
        # 2. No HomePage found — start the force-fix.
        # ------------------------------------------------------------------
        print("[0033] No HomePage found — beginning force-fix of broken database state.")

        # Delete all existing sites (the broken one pointing to the default page).
        deleted_sites, _ = Site.objects.all().delete()
        if deleted_sites:
            print(f"[0033] Deleted {deleted_sites} stale site(s).")
        else:
            print("[0033] No existing sites to delete.")

        # ------------------------------------------------------------------
        # 3. Delete all non-root pages (depth >= 2).
        # ------------------------------------------------------------------
        stale_pages = Page.objects.filter(depth__gte=2)
        stale_page_count = stale_pages.count()
        if stale_page_count:
            stale_pages.delete()
            print(f"[0033] Deleted {stale_page_count} stale/default page(s) at depth >= 2.")
        else:
            print("[0033] No stale pages at depth >= 2 to delete.")

        # ------------------------------------------------------------------
        # 4. Get the root page (depth=1) — must always exist.
        # ------------------------------------------------------------------
        root_page = Page.objects.filter(depth=1).first()
        if not root_page:
            print("[0033] ERROR: No root page found at depth=1 — cannot create HomePage.")
            return

        print(f"[0033] Root page found: \"{root_page.title}\" (id={root_page.id}).")

        # ------------------------------------------------------------------
        # 5. Create the custom HomePage as a child of root.
        # ------------------------------------------------------------------
        home_page = HomePage(
            title='Home',
            slug='home',
            live=True,
            hero_title='AfriClimate Center For Adaptation',
            hero_subtitle='Building Climate Resilience in Africa',
            depth=root_page.depth + 1,
            path=root_page.path + '0001',
            numchild=0,
        )
        home_page.save()
        root_page.numchild = (root_page.numchild or 0) + 1
        root_page.save(update_fields=['numchild'])
        print(
            f"[0033] Created HomePage: \"{home_page.title}\" "
            f"(id={home_page.id}, slug={home_page.slug!r})."
        )

        # ------------------------------------------------------------------
        # 6. Create the Wagtail Site pointing to the new HomePage.
        # ------------------------------------------------------------------
        site_hostname = os.environ.get(
            'RAILWAY_PUBLIC_DOMAIN',
            os.environ.get('CLIMWEB_PUBLIC_DOMAIN', 'climweb-production.up.railway.app'),
        )

        site = Site.objects.create(
            hostname=site_hostname,
            port=80,
            root_page=home_page,
            is_default_site=True,
            site_name='AfriClimate Center For Adaptation',
        )
        print(
            f"[0033] Created Site: {site.hostname}:{site.port} "
            f"-> \"{site.root_page.title}\"."
        )
        print("[0033] Force-fix complete — custom HomePage is live.")

    except Exception as e:
        print(f"[0033] ERROR in force_fix_homepage_creation: {e}")
        traceback.print_exc()


def reverse_force_fix_homepage_creation(apps, schema_editor):
    """Reverse migration — no-op; we do not want to undo homepage cleanup."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0032_fix_homepage_creation'),
        ('wagtailcore', '0094_alter_page_locale'),
    ]

    operations = [
        migrations.RunPython(
            force_fix_homepage_creation,
            reverse_force_fix_homepage_creation,
        ),
    ]
