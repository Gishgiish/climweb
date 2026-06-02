from django.db import migrations
from django.conf import settings
import os


def create_homepage_and_site(apps, schema_editor):
    """No-op data migration.

    Content creation previously performed here has been moved to a management
    command `create_homepage` which should be run after `migrate` by the
    deployment tooling. Keeping this migration as a no-op makes `migrate`
    idempotent and avoids performing Wagtail tree operations during schema
    migrations which can cause transactional failures.
    """
    print('NOTE: create_homepage_and_site is a no-op; run manage.py create_homepage')


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