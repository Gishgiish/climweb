from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.management import call_command
from wagtail.models import Site, Page
from django.contrib.auth import get_user_model
import os
import traceback


class Command(BaseCommand):
    help = 'Load site fixture (if present), create/update Wagtail Site and optional superuser.'

    def handle(self, *args, **options):
        User = get_user_model()

        # Attempt to load fixture from repository root: climweb/wagtail_prod_sync.json
        # BASE_DIR is climweb/src/climweb (inside the container: /climweb/climweb/src/climweb),
        # so we need to go up two levels to reach /climweb/climweb/wagtail_prod_sync.json.
        # Also check the absolute container path as a fallback.
        fixture_path = os.path.normpath(os.path.join(settings.BASE_DIR, '..', '..', 'wagtail_prod_sync.json'))
        if not os.path.exists(fixture_path):
            # Fallback: absolute container path (in case BASE_DIR resolution differs)
            fixture_path = '/climweb/climweb/wagtail_prod_sync.json'
        if os.path.exists(fixture_path):
            try:
                self.stdout.write(f'Loading fixture: {fixture_path}')
                call_command('loaddata', fixture_path)
            except Exception:
                self.stderr.write('Failed to load fixture:')
                traceback.print_exc()
        else:
            self.stdout.write('No fixture found at %s; skipping loaddata' % fixture_path)

        # Configure site
        try:
            site_hostname = os.environ.get(
                'RAILWAY_PUBLIC_DOMAIN',
                os.environ.get('CLIMWEB_PUBLIC_DOMAIN', 'climweb-production.up.railway.app'),
            )

            # Find the HomePage instance directly by model type first, then fall
            # back to slug/title heuristics.  Importing here avoids circular
            # import issues at module load time.
            homepage = None
            try:
                from climweb.pages.home.models import HomePage
                homepage = HomePage.objects.live().first()
                if homepage:
                    self.stdout.write(f'Found HomePage via model: "{homepage.title}" (id={homepage.id}, slug={homepage.slug!r})')
            except Exception:
                self.stdout.write('Could not import HomePage model; falling back to slug/title search')
                traceback.print_exc()

            if not homepage:
                # Fallback: search by slug or title — do NOT use depth=2 as that
                # can match the default Wagtail welcome page.
                homepage = (
                    Page.objects.filter(slug='home').first()
                    or Page.objects.filter(title__icontains='AfriClimate').first()
                )
                if homepage:
                    self.stdout.write(f'Found homepage via fallback search: "{homepage.title}" (id={homepage.id}, slug={homepage.slug!r})')

            if not homepage:
                self.stderr.write(self.style.ERROR(
                    'No HomePage found in the database. '
                    'Wagtail site will NOT be configured. '
                    'Run migrations and load a fixture first, then re-run configure_site.'
                ))
                self.stdout.write('All pages currently in the database:')
                for p in Page.objects.all().order_by('depth', 'id'):
                    self.stdout.write(f'  id={p.id}  depth={p.depth}  slug={p.slug!r}  title={p.title!r}')
                # Do NOT delete existing sites if we cannot find a valid homepage.
                return

            # Use port 80 (standard HTTP) so Wagtail matches requests that arrive
            # without an explicit port in the Host header (the common case behind a
            # reverse proxy / Railway's edge network).  The server itself may bind
            # to a different port (e.g. $PORT=8080), but the Site record must
            # reflect what the *client* sends in the Host header.
            site_port = 80

            # Check whether a site for this hostname already exists.
            existing = Site.objects.filter(hostname=site_hostname).first()
            if existing:
                self.stdout.write(f'Site for {site_hostname} already exists (id={existing.id}); updating.')
                # Remove any other stale sites so there is no ambiguity.
                Site.objects.exclude(pk=existing.pk).delete()
                existing.port = site_port
                existing.root_page = homepage
                existing.is_default_site = True
                existing.site_name = 'AfriClimate Center For Adaptation'
                existing.save()
                self.stdout.write(self.style.SUCCESS(
                    f'Updated site: {site_hostname}:{site_port} -> "{homepage.title}" (id={homepage.id})'
                ))
            else:
                # No matching site — clear all stale entries and create a fresh one.
                deleted_count, _ = Site.objects.all().delete()
                if deleted_count:
                    self.stdout.write(f'Cleared {deleted_count} stale site(s)')
                site = Site.objects.create(
                    hostname=site_hostname,
                    port=site_port,
                    root_page=homepage,
                    is_default_site=True,
                    site_name='AfriClimate Center For Adaptation',
                )
                self.stdout.write(self.style.SUCCESS(
                    f'Created site: {site_hostname}:{site_port} -> "{homepage.title}" (id={homepage.id})'
                ))

        except Exception:
            self.stderr.write(self.style.ERROR('Failed to configure Wagtail site:'))
            traceback.print_exc()

        # Create superuser if env vars are set
        try:
            username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
            email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

            if username:
                if not User.objects.filter(username=username).exists():
                    User.objects.create_superuser(username=username, email=email or '', password=password or '')
                    self.stdout.write(self.style.SUCCESS(f'Created superuser: {username}'))
                else:
                    self.stdout.write(f'Superuser {username} already exists')
            else:
                self.stdout.write('DJANGO_SUPERUSER_USERNAME not set; skipping superuser creation')
        except Exception:
            self.stderr.write(self.style.ERROR('Failed to create superuser:'))
            traceback.print_exc()

        # Print verification info
        try:
            self.stdout.write('--- Site verification ---')
            sites = list(Site.objects.all())
            if sites:
                for s in sites:
                    self.stdout.write(
                        f'  ID {s.id}: {s.hostname}:{s.port} '
                        f'(default={s.is_default_site}) -> "{s.root_page}" '
                        f'(page id={s.root_page_id})'
                    )
            else:
                self.stderr.write(self.style.WARNING('  No sites configured!'))

            self.stdout.write('--- Superuser verification ---')
            for u in User.objects.filter(is_superuser=True):
                self.stdout.write(f'  {u.username} <{u.email}>')
        except Exception:
            traceback.print_exc()
