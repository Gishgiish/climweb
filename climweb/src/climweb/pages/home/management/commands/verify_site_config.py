from django.core.management.base import BaseCommand
from wagtail.models import Site, Page


class Command(BaseCommand):
    help = 'Verify Wagtail Site is correctly configured for production deployment'

    def handle(self, *args, **options):
        sites = Site.objects.all()
        
        if not sites.exists():
            self.stderr.write(self.style.ERROR('ERROR: No sites configured!'))
            self.stderr.write('Run configure_site command to set up the site.')
            return False
            
        success = True
        
        for site in sites:
            self.stdout.write(f'Site ID {site.id}:')
            self.stdout.write(f'  Hostname: {site.hostname}')
            self.stdout.write(f'  Port: {site.port}')
            self.stdout.write(f'  Is Default: {site.is_default_site}')
            self.stdout.write(f'  Root page: {site.root_page.title} (slug={site.root_page.slug}, id={site.root_page_id})')
            
            # Check if root page is likely the correct homepage
            if site.root_page.slug != 'home':
                self.stderr.write(self.style.WARNING(f'  ⚠️ WARNING: Root page slug is not "home"!'))
                success = False
            else:
                self.stdout.write(self.style.SUCCESS('  ✓ Root page slug is "home"'))
                
            if 'AfriClimate' not in site.root_page.title and site.root_page.slug != 'home':
                self.stderr.write(self.style.WARNING(f'  ⚠️ WARNING: Root page title does not contain "AfriClimate"!'))
                success = False
                
            # Check for default Wagtail welcome page
            if site.root_page.title == 'Welcome to your new Wagtail site!':
                self.stderr.write(self.style.ERROR('  ✗ ERROR: Site is pointing to default Wagtail welcome page!'))
                success = False
                
            self.stdout.write('')
        
        if success:
            self.stdout.write(self.style.SUCCESS('✓ Site configuration looks correct!'))
        else:
            self.stderr.write(self.style.WARNING('\n⚠️ Site configuration may have issues. Review warnings above.'))
            self.stderr.write('You can fix this by running: python manage.py configure_site')
        
        return success
