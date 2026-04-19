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
        fixture_path = os.path.normpath(os.path.join(settings.BASE_DIR, '..', 'wagtail_prod_sync.json'))
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
            site_hostname = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'climweb-production.up.railway.app')
            
            # Find the correct homepage first
            homepage = (
                Page.objects.filter(slug='home').first()
                or Page.objects.filter(title__icontains='AfriClimate').first()
                or Page.objects.filter(depth=2).first()
            )

            if not homepage:
                self.stderr.write('No homepage found; site not configured')
                return

            # Delete ALL existing sites to start fresh
            Site.objects.all().delete()
            self.stdout.write('Cleared all existing sites')

            # Create the correct site
            obj, created = Site.objects.update_or_create(
                hostname=site_hostname,
                defaults={
                    'port': 80,
                    'root_page': homepage,
                    'is_default_site': True,
                    'site_name': 'AfriClimate Center For Adaptation',
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created site {site_hostname} -> {homepage.title} (id={homepage.id})'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Updated site {site_hostname} -> {homepage.title} (id={homepage.id})'))
        except Exception:
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
            traceback.print_exc()

        # Print verification info
        try:
            self.stdout.write('Sites:')
            for s in Site.objects.all():
                self.stdout.write(f'  ID {s.id}: {s.hostname}:{s.port} (default={s.is_default_site}) -> {s.root_page}')

            self.stdout.write('Superusers:')
            for u in User.objects.filter(is_superuser=True):
                self.stdout.write(f'  {u.username} <{u.email}>')
        except Exception:
            traceback.print_exc()
