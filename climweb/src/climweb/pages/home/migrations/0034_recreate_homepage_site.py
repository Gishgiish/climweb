import os
import traceback

from django.db import migrations, transaction


def recreate_homepage_and_site(apps, schema_editor):
    """
    Re-run homepage and site creation because migrations 0032 and 0033 were
    recorded as applied but never actually created the records (they failed
    at runtime in earlier deployments).

    This migration is idempotent: if a valid HomePage and Site already exist,
    it exits early.
    """
    try:
        Page = apps.get_model('wagtailcore', 'Page')
        Site = apps.get_model('wagtailcore', 'Site')

        try:
            HomePage = apps.get_model('home', 'HomePage')
        except LookupError:
            print("[0034] HomePage model not available — skipping.")
            return

        # 1. If a valid HomePage already exists, ensure Site points to it.
        existing_home = HomePage.objects.first()
        if existing_home:
            print(
                f"[0034] HomePage already exists: \"{existing_home.title}\" "
                f"(id={existing_home.id}) — ensuring Site is configured."
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
            else:
                Site.objects.all().delete()
                Site.objects.create(
                    hostname=site_hostname,
                    port=80,
                    root_page=existing_home,
                    is_default_site=True,
                    site_name='AfriClimate Center For Adaptation',
                )
            print("[0034] Site configured for existing HomePage.")
            return

        # 2. No HomePage — create one.
        print("[0034] No HomePage found — creating HomePage and Site.")

        Site.objects.all().delete()
        Page.objects.filter(depth__gte=2).delete()

        root_page = Page.objects.filter(depth=1).first()
        if not root_page:
            print("[0034] ERROR: No root page at depth=1.")
            return

        # Look up the ContentType for HomePage — required NOT NULL field on wagtailcore_page.
        # Historical models in migrations don't have Wagtail's custom save() that auto-assigns this.
        ContentType = apps.get_model('contenttypes', 'ContentType')
        homepage_ct = ContentType.objects.get(app_label='home', model='homepage')

        home_page = HomePage(
            title='Home',
            slug='home',
            live=True,
            hero_title='AfriClimate Center For Adaptation',
            hero_subtitle='Building Climate Resilience in Africa',
            depth=root_page.depth + 1,
            path=root_page.path + '0001',
            numchild=0,
            content_type=homepage_ct,
        )
        home_page.save()
        root_page.numchild = (root_page.numchild or 0) + 1
        root_page.save(update_fields=['numchild'])
        print(f"[0034] Created HomePage (id={home_page.id}).")

        site_hostname = os.environ.get(
            'RAILWAY_PUBLIC_DOMAIN',
            os.environ.get('CLIMWEB_PUBLIC_DOMAIN', 'climweb-production.up.railway.app'),
        )
        Site.objects.create(
            hostname=site_hostname,
            port=80,
            root_page=home_page,
            is_default_site=True,
            site_name='AfriClimate Center For Adaptation',
        )
        print("[0034] Created Site. Homepage fix complete.")

    except Exception as e:
        print(f"[0034] ERROR: {e}")
        traceback.print_exc()


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0033_force_fix_homepage_creation'),
        ('wagtailcore', '0094_alter_page_locale'),
    ]

    operations = [
        migrations.RunPython(
            recreate_homepage_and_site,
            migrations.RunPython.noop,
        ),
    ]
