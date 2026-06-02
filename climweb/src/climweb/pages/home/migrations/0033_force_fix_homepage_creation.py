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
    # No-op: moved force-fix behavior to manage.py create_homepage
    print('[0033] NOTE: force_fix_homepage_creation is a no-op; run manage.py create_homepage')
    return


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
