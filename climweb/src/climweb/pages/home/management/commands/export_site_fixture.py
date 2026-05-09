from django.core.management.base import BaseCommand
from django.core.serializers import serialize
from wagtail.models import Site, Page
import json


class Command(BaseCommand):
    help = 'Export current Wagtail Site configuration as a fixture JSON file'

    def handle(self, *args, **options):
        sites = Site.objects.all()
        
        if not sites.exists():
            self.stderr.write('No sites found in database')
            return
        
        site_data = []
        for site in sites:
            site_data.append({
                'model': 'wagtailcore.site',
                'pk': site.pk,
                'fields': {
                    'hostname': site.hostname,
                    'port': site.port,
                    'site_name': site.site_name or '',
                    'is_default_site': site.is_default_site,
                    'root_page': site.root_page_id,
                }
            })
        
        # Output as JSON
        output = json.dumps(site_data, indent=2)
        
        # Write to file
        output_file = 'wagtail_site_export.json'
        with open(output_file, 'w') as f:
            f.write(output)
        
        self.stdout.write(self.style.SUCCESS(f'Site fixture exported to {output_file}'))
        self.stdout.write(f'Exported {len(site_data)} site(s)')
        
        # Also print to stdout for verification
        self.stdout.write('\nExported data:')
        self.stdout.write(output)
