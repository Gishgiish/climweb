from django.core.management.base import BaseCommand
from wagtail.models import Site

class Command(BaseCommand):
    help = 'Fix Wagtail site configuration for production'

    def handle(self, *args, **options):
        # Clean up duplicates
        sites = Site.objects.all()
        self.stdout.write("Current sites:")
        for s in sites:
            self.stdout.write(f"  ID {s.id}: {s.hostname}:{s.port} (default={s.is_default_site}) -> {s.root_page}")
        
        # Delete site with wrong root page if it exists
        wrong_sites = Site.objects.filter(root_page__title__contains="Eldoret")
        if wrong_sites.exists():
            count = wrong_sites.count()
            wrong_sites.delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {count} site(s) with wrong root page'))
        
        # Update or create the correct site
        try:
            site = Site.objects.get(id=2)
            site.hostname = 'climweb-production.up.railway.app'
            site.port = 80
            site.is_default_site = True
            site.site_name = 'AfriClimate Center For Adaptation'
            site.save()
            self.stdout.write(self.style.SUCCESS(f'Updated site: {site.hostname}'))
        except Site.DoesNotExist:
            # If site 2 doesn't exist, update whichever one has the correct homepage
            site = Site.objects.exclude(root_page__title__contains="Eldoret").first()
            if site:
                site.hostname = 'climweb-production.up.railway.app'
                site.port = 80
                site.is_default_site = True
                site.site_name = 'AfriClimate Center For Adaptation'
                site.save()
                self.stdout.write(self.style.SUCCESS(f'Updated site: {site.hostname}'))