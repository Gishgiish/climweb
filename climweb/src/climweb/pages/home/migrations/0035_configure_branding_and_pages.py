"""
Migration 0035: Configure branding assets and create essential pages.

Populates the following database records that are required for a fully
functional production site but are not created by earlier migrations:

  1. OrganisationSetting.logo  — uploads logo.svg as a Wagtail Image and
     assigns it to the site's OrganisationSetting.

  2. HomePage.hero_banner      — uploads the first available hero_banner PNG
     as a Wagtail Image and assigns it to the HomePage, together with
     hero_title and hero_subtitle text.

  3. ContactPage               — creates a /contact-us/ page under the
     HomePage if one does not already exist.

  4. Essential index pages     — creates NewsIndexPage, PublicationsIndexPage,
     EventIndexPage, etc. under the HomePage if they do not already exist.

All operations are idempotent: if the target record already has the field
populated, or if the source file is missing, the step is skipped silently.
All errors are logged to stdout so they appear in deployment logs.
"""

import os
import sys
import traceback

from django.db import migrations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_dir():
    """Return BASE_DIR = climweb/src/climweb (where manage.py lives)."""
    this_file = os.path.abspath(__file__)
    return os.path.normpath(os.path.join(this_file, *(['..'] * 4)))


def _create_wagtail_image(title, src_path):
    """
    Open *src_path* and create a Wagtail Image record for it.
    Returns the Image instance or None.

    We import the *real* Wagtail Image model here (not the historical
    proxy) because we need its file-handling logic (width/height detection,
    file_hash generation, storage upload, etc.).  This is safe: the
    wagtailimages schema is stable and the model is always available by
    the time this migration runs.
    """
    try:
        from django.core.files import File
        from wagtail.images import get_image_model

        if not os.path.isfile(src_path):
            print(f"  [0035] Source file not found, skipping: {src_path}", flush=True)
            return None

        ImageModel = get_image_model()
        filename = os.path.basename(src_path)

        # Open the source file and let Wagtail's Image.save() handle
        # storage upload, width/height detection, and file_hash generation.
        with open(src_path, 'rb') as fh:
            django_file = File(fh, name=filename)
            image = ImageModel(title=title)
            image.file = django_file
            image.save()

        print(f"  [0035] Created Wagtail Image: \"{title}\" (id={image.pk})", flush=True)
        return image

    except Exception as exc:
        print(f"  [0035] ERROR creating Wagtail Image for {src_path}: {exc}", flush=True)
        traceback.print_exc(file=sys.stdout)
        return None


# ---------------------------------------------------------------------------
# Step 1 – Assign logo to OrganisationSetting
# ---------------------------------------------------------------------------

def _assign_logo(apps, schema_editor):
    try:
        from wagtail.models import Site

        base_dir = _base_dir()
        logo_src = os.path.join(base_dir, 'config', 'static', 'img', 'logo.svg')

        # Retrieve the default site
        site = Site.objects.filter(is_default_site=True).first()
        if site is None:
            print("  [0035] No default Site found — skipping logo assignment.", flush=True)
            return

        # Use the real OrganisationSetting (contrib.settings are site-scoped)
        try:
            from climweb.base.models.site_settings import OrganisationSetting
        except ImportError as exc:
            print(f"  [0035] Could not import OrganisationSetting: {exc} — skipping logo.", flush=True)
            return

        org_setting = OrganisationSetting.for_site(site)

        if org_setting.logo_id:
            print(
                f"  [0035] OrganisationSetting already has a logo (id={org_setting.logo_id}) — skipping.",
                flush=True,
            )
            return

        image = _create_wagtail_image('AfriClimate Logo', logo_src)
        if image is None:
            return

        org_setting.logo = image
        org_setting.save()
        print(f"  [0035] Assigned logo (image id={image.pk}) to OrganisationSetting.", flush=True)

    except Exception as exc:
        print(f"  [0035] ERROR in _assign_logo: {exc}", flush=True)
        traceback.print_exc(file=sys.stdout)


# ---------------------------------------------------------------------------
# Step 2 – Assign hero banner to HomePage
# ---------------------------------------------------------------------------

def _assign_hero_banner(apps, schema_editor):
    try:
        try:
            from climweb.pages.home.models import HomePage
        except ImportError as exc:
            print(f"  [0035] Could not import HomePage: {exc} — skipping hero banner.", flush=True)
            return

        home_page = HomePage.objects.live().first()
        if home_page is None:
            print("  [0035] No live HomePage found — skipping hero banner assignment.", flush=True)
            return

        if home_page.hero_banner_id:
            print(
                f"  [0035] HomePage already has a hero_banner (id={home_page.hero_banner_id}) — skipping.",
                flush=True,
            )
        else:
            base_dir = _base_dir()
            images_dir = os.path.join(base_dir, 'media', 'images')

            # Pick the first available original hero_banner PNG
            banner_src = None
            if os.path.isdir(images_dir):
                candidates = sorted([
                    f for f in os.listdir(images_dir)
                    if f.startswith('hero_banner') and f.endswith('.original.png')
                ])
                if candidates:
                    banner_src = os.path.join(images_dir, candidates[0])

            if banner_src is None:
                print(
                    f"  [0035] No hero_banner image found in {images_dir} — skipping banner assignment.",
                    flush=True,
                )
            else:
                image = _create_wagtail_image('AfriClimate Hero Banner', banner_src)
                if image is not None:
                    home_page.hero_banner = image
                    print(f"  [0035] Assigned hero_banner (image id={image.pk}) to HomePage.", flush=True)

        # Always update hero text if it still has the old placeholder values
        updated_fields = []

        if home_page.hero_title in ('AfriClimate Center For Adaptation', 'Home', ''):
            home_page.hero_title = 'Building Climate Resilience Across Africa'
            updated_fields.append('hero_title')

        if not home_page.hero_subtitle:
            home_page.hero_subtitle = 'Empowering Communities with Climate Information'
            updated_fields.append('hero_subtitle')

        if updated_fields or not home_page.hero_banner_id:
            home_page.save()
            if updated_fields:
                print(f"  [0035] Updated HomePage fields: {', '.join(updated_fields)}.", flush=True)

    except Exception as exc:
        print(f"  [0035] ERROR in _assign_hero_banner: {exc}", flush=True)
        traceback.print_exc(file=sys.stdout)


# ---------------------------------------------------------------------------
# Step 3 – Create ContactPage if missing
# ---------------------------------------------------------------------------

def _create_contact_page(apps, schema_editor):
    try:
        try:
            from climweb.pages.home.models import HomePage
            from climweb.pages.contact.models import ContactPage
        except ImportError as exc:
            print(f"  [0035] Could not import models for ContactPage: {exc} — skipping.", flush=True)
            return

        home_page = HomePage.objects.live().first()
        if home_page is None:
            print("  [0035] No live HomePage found — skipping ContactPage creation.", flush=True)
            return

        # Check whether a ContactPage already exists anywhere in the tree
        if ContactPage.objects.exists():
            existing = ContactPage.objects.first()
            print(
                f"  [0035] ContactPage already exists: \"{existing.title}\" "
                f"(id={existing.pk}, slug={existing.slug!r}) — skipping.",
                flush=True,
            )
            return

        contact_page = ContactPage(
            title='Contact Us',
            slug='contact-us',
            live=True,
            show_in_menus=True,
            # name / location are nullable in the DB (null=True) so we can
            # leave them blank here; an admin can fill them in via the CMS.
            name=None,
            location=None,
            # Email form fields — leave blank; admin configures them later.
            to_address='',
            from_address='',
            subject='Contact Us',
            thank_you_text='',
        )

        home_page.add_child(instance=contact_page)
        print(
            f"  [0035] Created ContactPage: \"{contact_page.title}\" "
            f"(id={contact_page.pk}, slug={contact_page.slug!r}) "
            f"under HomePage (id={home_page.pk}).",
            flush=True,
        )

    except Exception as exc:
        print(f"  [0035] ERROR in _create_contact_page: {exc}", flush=True)
        traceback.print_exc(file=sys.stdout)


# ---------------------------------------------------------------------------
# Step 4 – Create essential index pages under HomePage
# ---------------------------------------------------------------------------

# Each entry: (module_path, class_name, title, slug)
# We use direct model imports (not apps.get_model()) so that the real Wagtail
# model class is used — historical proxies returned by apps.get_model() lack
# the treebeard methods (add_child, etc.) required to insert pages correctly.
_ESSENTIAL_PAGES = [
    ('climweb.pages.news.models',                        'NewsIndexPage',         'News & Updates', 'news'),
    ('climweb.pages.publications.models',                'PublicationsIndexPage', 'Publications',   'publications'),
    ('climweb.pages.events.models',                      'EventIndexPage',        'Events',         'events'),
    ('climweb.pages.services.models',                    'ServiceIndexPage',      'Services',       'services'),
    ('climweb.pages.organisation_pages.organisation.models', 'OrganisationIndexPage', 'Organisations', 'organisations'),
    ('climweb.pages.mediacenter.models',                 'MediaIndexPage',        'Media Center',   'media'),
    ('climweb.pages.glossary.models',                    'GlossaryIndexPage',     'Glossary',       'glossary'),
    ('climweb.pages.flex_page.models',                   'FlexPage',              'About Us',       'about'),
]


def _import_model(module_path, class_name):
    """
    Import *class_name* from *module_path*.
    Returns the class or None, logging any ImportError to stdout.
    """
    try:
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, class_name)
    except (ImportError, AttributeError) as exc:
        print(f"  [0035] Could not import {module_path}.{class_name}: {exc} — skipping.", flush=True)
        return None


def _create_essential_pages(apps, schema_editor):
    try:
        try:
            from climweb.pages.home.models import HomePage
        except ImportError as exc:
            print(f"  [0035] Could not import HomePage: {exc} — skipping essential pages.", flush=True)
            return

        home_page = HomePage.objects.live().first()
        if home_page is None:
            print("  [0035] No live HomePage found — skipping essential pages creation.", flush=True)
            return

        print(f"  [0035] Creating essential pages under HomePage (id={home_page.pk})...", flush=True)

        for module_path, class_name, title, slug in _ESSENTIAL_PAGES:
            try:
                PageModel = _import_model(module_path, class_name)
                if PageModel is None:
                    continue

                # Skip if a page of this type already exists anywhere in the tree
                if PageModel.objects.exists():
                    existing = PageModel.objects.first()
                    print(
                        f"  [0035] {class_name} already exists: "
                        f"\"{existing.title}\" (id={existing.pk}, slug={existing.slug!r}) — skipping.",
                        flush=True,
                    )
                    continue

                # Also skip if a child with the same slug already exists under HomePage
                if home_page.get_children().filter(slug=slug).exists():
                    print(
                        f"  [0035] A child page with slug={slug!r} already exists "
                        f"under HomePage — skipping {class_name}.",
                        flush=True,
                    )
                    continue

                page = PageModel(
                    title=title,
                    slug=slug,
                    live=True,
                    show_in_menus=True,
                )
                home_page.add_child(instance=page)
                print(
                    f"  [0035] Created {class_name}: \"{page.title}\" "
                    f"(id={page.pk}, slug={page.slug!r}) under HomePage (id={home_page.pk}).",
                    flush=True,
                )

            except Exception as exc:
                print(f"  [0035] ERROR creating {class_name} (slug={slug!r}): {exc}", flush=True)
                traceback.print_exc(file=sys.stdout)

    except Exception as exc:
        print(f"  [0035] ERROR in _create_essential_pages: {exc}", flush=True)
        traceback.print_exc(file=sys.stdout)


# ---------------------------------------------------------------------------
# Top-level migration function
# ---------------------------------------------------------------------------

def configure_branding_and_pages(apps, schema_editor):
    print("[0035] configure_branding_and_pages — start", flush=True)
    _assign_logo(apps, schema_editor)
    _assign_hero_banner(apps, schema_editor)
    _create_contact_page(apps, schema_editor)
    _create_essential_pages(apps, schema_editor)
    print("[0035] configure_branding_and_pages — done", flush=True)


def reverse_configure_branding_and_pages(apps, schema_editor):
    """Reverse is a no-op — we do not want to delete uploaded images or pages."""
    pass


# ---------------------------------------------------------------------------
# Migration class
# ---------------------------------------------------------------------------

class Migration(migrations.Migration):

    dependencies = [
        ('home', '0034_recreate_homepage_site'),
        ('base', '0036_add_openweathermap_api_key'),
        ('contact', '0003_alter_contactpage_location'),
        ('wagtailimages', '0027_image_description'),
        ('wagtailcore', '0094_alter_page_locale'),
    ]

    operations = [
        migrations.RunPython(
            configure_branding_and_pages,
            reverse_configure_branding_and_pages,
        ),
    ]
