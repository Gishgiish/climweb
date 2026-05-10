from django.db import migrations
from django.conf import settings
import os


def create_homepage_and_site(apps, schema_editor):
    """
    Create the HomePage and configure the default Wagtail Site.
    This ensures fresh deployments have a proper homepage instead of
    the default Wagtail welcome page.
    """
    # Only run in production deployments
    if not settings.DEBUG:
        try:
            # Get models
            Page = apps.get_model('wagtailcore', 'Page')
            Site = apps.get_model('wagtailcore', 'Site')

            # Check if HomePage model exists (might not be loaded yet in migrations)
            try:
                HomePage = apps.get_model('home', 'HomePage')
            except LookupError:
                print("HomePage model not available yet, skipping homepage creation")
                return

            # Check if a homepage already exists
            existing_home = HomePage.objects.first()
            if existing_home:
                print(f"HomePage already exists: {existing_home.title} (id={existing_home.id})")
                return

            # Get the root page (depth=1)
            root_page = Page.objects.filter(depth=1).first()
            if not root_page:
                print("ERROR: No root page found!")
                return

            # Create the HomePage
            home_page = HomePage(
                title='Home',
                slug='home',
                hero_title='AfriClimate Center For Adaptation',
                hero_subtitle='Building Climate Resilience in Africa',
            )
            root_page.add_child(instance=home_page)
            home_page.save_revision().publish()
            print(f"Created HomePage: {home_page.title} (id={home_page.id}, slug={home_page.slug})")

            # Configure the Site - use dynamic domain from environment or fallback
            site_hostname = os.environ.get(
                'RAILWAY_PUBLIC_DOMAIN',
                os.environ.get('CLIMWEB_PUBLIC_DOMAIN', 'climweb-production.up.railway.app')
            )

            # Delete any existing sites
            Site.objects.all().delete()

            # Create the site pointing to our HomePage
            site = Site.objects.create(
                hostname=site_hostname,
                port=80,  # Standard HTTP port for reverse proxy scenarios
                root_page=home_page,
                is_default_site=True,
                site_name='AfriClimate Center For Adaptation',
            )
            print(f"Created Site: {site.hostname}:{site.port} -> {site.root_page.title}")

        except Exception as e:
            print(f"ERROR in create_homepage_and_site: {e}")
            import traceback
            traceback.print_exc()


def remove_homepage_and_site(apps, schema_editor):
    """Reverse the migration."""
    try:
        Site = apps.get_model('wagtailcore', 'Site')
        HomePage = apps.get_model('home', 'HomePage')

        # Delete sites
        Site.objects.all().delete()

        # Delete homepage
        HomePage.objects.all().delete()

        print("Removed HomePage and Site configuration")
    except Exception as e:
        print(f"ERROR in remove_homepage_and_site: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0030_homepage_call_to_action_button_text_2_and_more'),
        ('wagtailcore', '0094_alter_page_locale'),
    ]

    operations = [
        migrations.RunPython(create_homepage_and_site, remove_homepage_and_site),
    ]