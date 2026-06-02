from django.core.management.base import BaseCommand
from django.db import transaction
import os


class Command(BaseCommand):
    help = "Create the HomePage and configure the Wagtail Site idempotently."

    def handle(self, *args, **options):
        try:
            # Import inside the method to avoid app-loading issues at import time
            try:
                from wagtail.models import Page, Site
            except Exception:
                from wagtail.core.models import Page, Site

            from climweb.pages.home.models import HomePage

            # If a HomePage already exists, ensure a Site points to it and exit.
            existing = HomePage.objects.first()
            site_hostname = os.environ.get(
                'RAILWAY_PUBLIC_DOMAIN',
                os.environ.get('CLIMWEB_PUBLIC_DOMAIN', 'climweb-production.up.railway.app'),
            )
            runtime_port = int(os.environ.get('PORT', os.environ.get('CLIMWEB_PORT', '80')))

            if existing:
                self.stdout.write(f'HomePage already exists: "{existing.title}" (id={existing.id})')
                site, created = Site.objects.get_or_create(
                    root_page=existing,
                    defaults={
                        'hostname': site_hostname,
                        'port': runtime_port,
                        'is_default_site': True,
                        'site_name': 'AfriClimate Center For Adaptation',
                    },
                )
                if not created:
                    site.hostname = site_hostname
                    site.port = runtime_port
                    site.is_default_site = True
                    site.site_name = 'AfriClimate Center For Adaptation'
                    site.save()
                    self.stdout.write(f'Updated Site: {site.hostname}:{site.port} -> {site.root_page.title}')
                else:
                    self.stdout.write(f'Created Site: {site.hostname}:{site.port} -> {site.root_page.title}')
                return

            # Otherwise create the HomePage as a child of the root page.
            root = Page.objects.filter(depth=1).first()
            if not root:
                self.stderr.write('ERROR: No root page found (depth=1). Cannot create HomePage.')
                return

            # Use a transaction to ensure we leave the DB in a consistent state.
            with transaction.atomic():
                home = HomePage(
                    title='Home',
                    slug='home',
                    hero_title='AfriClimate Center For Adaptation',
                    hero_subtitle='Building Climate Resilience in Africa',
                    live=True,
                )
                # Prefer the high-level API to maintain tree integrity.
                try:
                    root.add_child(instance=home)
                except Exception:
                    # Fallback: set tree fields manually if add_child fails.
                    home.depth = (root.depth or 1) + 1
                    home.path = (root.path or '') + '0001'
                    home.numchild = 0
                    home.save()
                    root.numchild = (root.numchild or 0) + 1
                    root.save(update_fields=['numchild'])

                # Publish the page
                try:
                    home.save_revision().publish()
                except Exception:
                    # If publishing fails, continue — page exists and can be published later.
                    self.stdout.write('Warning: publish failed; page created but not published')

                # Create or ensure the Site points to the new HomePage.
                Site.objects.filter(root_page=home).delete()
                Site.objects.create(
                    hostname=site_hostname,
                    port=runtime_port,
                    root_page=home,
                    is_default_site=True,
                    site_name='AfriClimate Center For Adaptation',
                )
                self.stdout.write(f'Created HomePage and Site: {site_hostname}:{runtime_port}')

        except Exception as exc:
            self.stderr.write(f'ERROR: failed to create homepage/site: {exc}')
            raise
