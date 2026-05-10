import os

from django.db import migrations


def fix_homepage_and_site(apps, schema_editor):
    """
    Clean up the broken default Wagtail state left by a failed 0031 migration
    and recreate the custom HomePage + Site configuration.

    This migration is idempotent: if a valid HomePage already exists and the
    Site already points to it, it does nothing.
    """
    try:
        Page = apps.get_model('wagtailcore', 'Page')
        Site = apps.get_model('wagtailcore', 'Site')

        try:
            HomePage = apps.get_model('home', 'HomePage')
        except LookupError:
            print("HomePage model not available, skipping fix_homepage_and_site")
            return

        # ------------------------------------------------------------------
        # 1. Check whether a valid HomePage already exists.
        # ------------------------------------------------------------------
        existing_home = HomePage.objects.first()
        if existing_home:
            # A HomePage exists — make sure the Site points to it and exit.
            print(
                f"HomePage already exists: \"{existing_home.title}\" "
                f"(id={existing_home.id}); ensuring Site is configured correctly."
            )
            site_hostname = os.environ.get(
                'RAILWAY_PUBLIC_DOMAIN',
                os.environ.get('CLIMWEB_PUBLIC_DOMAIN', 'climweb-production.up.railway.app'),
            )
            existing_site = Site.objects.filter(root_page=existing_home).first()
            if existing_site:
                # Update hostname / port in case they drifted.
                existing_site.hostname = site_hostname
                existing_site.port = 80
                existing_site.is_default_site = True
                existing_site.site_name = 'AfriClimate Center For Adaptation'
                existing_site.save()
                # Remove any other stale sites.
                Site.objects.exclude(pk=existing_site.pk).delete()
                print(
                    f"Updated Site: {existing_site.hostname}:{existing_site.port} "
                    f"-> \"{existing_home.title}\""
                )
            else:
                # No site points to our HomePage — clear all and create one.
                Site.objects.all().delete()
                site = Site.objects.create(
                    hostname=site_hostname,
                    port=80,
                    root_page=existing_home,
                    is_default_site=True,
                    site_name='AfriClimate Center For Adaptation',
                )
                print(
                    f"Created Site: {site.hostname}:{site.port} "
                    f"-> \"{existing_home.title}\""
                )
            return

        # ------------------------------------------------------------------
        # 2. No HomePage found — delete the broken default Wagtail pages and
        #    recreate everything from scratch.
        # ------------------------------------------------------------------

        # Delete all existing sites first so we start clean.
        deleted_sites, _ = Site.objects.all().delete()
        if deleted_sites:
            print(f"Deleted {deleted_sites} stale site(s)")

        # Delete the default Wagtail "Welcome to your new Wagtail site!" page
        # (depth=2, slug='home') and any other non-root pages so the tree is
        # clean before we insert our own HomePage.
        default_pages = Page.objects.filter(depth__gte=2)
        deleted_pages = default_pages.count()
        if deleted_pages:
            default_pages.delete()
            print(f"Deleted {deleted_pages} default/stale page(s) at depth >= 2")

        # ------------------------------------------------------------------
        # 3. Get the root page (depth=1) — this must always exist.
        # ------------------------------------------------------------------
        root_page = Page.objects.filter(depth=1).first()
        if not root_page:
            print("ERROR: No root page found — cannot create HomePage")
            return

        # ------------------------------------------------------------------
        # 4. Create the custom HomePage as a child of root.
        # ------------------------------------------------------------------
        home_page = HomePage(
            title='Home',
            slug='home',
            hero_title='AfriClimate Center For Adaptation',
            hero_subtitle='Building Climate Resilience in Africa',
        )
        home_page.parent_page = root_page
        home_page.save()
        home_page.save_revision().publish()
        print(
            f"Created HomePage: \"{home_page.title}\" "
            f"(id={home_page.id}, slug={home_page.slug!r})"
        )

        # ------------------------------------------------------------------
        # 5. Create the Wagtail Site pointing to the new HomePage.
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
            f"Created Site: {site.hostname}:{site.port} "
            f"-> \"{site.root_page.title}\""
        )

    except Exception as e:
        print(f"ERROR in fix_homepage_and_site: {e}")
        import traceback
        traceback.print_exc()


def reverse_fix_homepage_and_site(apps, schema_editor):
    """Reverse migration — no-op; we do not want to undo homepage cleanup."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0031_create_default_homepage_site'),
        ('wagtailcore', '0094_alter_page_locale'),
    ]

    operations = [
        migrations.RunPython(
            fix_homepage_and_site,
            reverse_fix_homepage_and_site,
        ),
    ]
