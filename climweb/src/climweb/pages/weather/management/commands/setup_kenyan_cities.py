"""
Management command to set up Kenyan cities for weather forecast widget.
This creates major Kenyan cities with their coordinates for the forecast system.
"""
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.core.management import call_command
from forecastmanager.models import City
from forecastmanager.forecast_settings import ForecastSetting
from wagtail.models import Site


class Command(BaseCommand):
    help = 'Set up Kenyan cities for weather forecast widget'

    KENYAN_CITIES = [
        {'name': 'Nairobi', 'slug': 'nairobi', 'lon': 36.8219, 'lat': -1.2921},
        {'name': 'Mombasa', 'slug': 'mombasa', 'lon': 39.6682, 'lat': -4.0435},
        {'name': 'Kisumu', 'slug': 'kisumu', 'lon': 34.7680, 'lat': -0.0917},
        {'name': 'Nakuru', 'slug': 'nakuru', 'lon': 36.0800, 'lat': -0.3031},
        {'name': 'Eldoret', 'slug': 'eldoret', 'lon': 35.2698, 'lat': 0.5143},
        {'name': 'Garissa', 'slug': 'garissa', 'lon': 39.6401, 'lat': -0.4536},
        {'name': 'Nyeri', 'slug': 'nyeri', 'lon': 36.9475, 'lat': -0.4197},
        {'name': 'Meru', 'slug': 'meru', 'lon': 37.6556, 'lat': 0.0469},
        {'name': 'Kakamega', 'slug': 'kakamega', 'lon': 34.7519, 'lat': 0.2827},
        {'name': 'Malindi', 'slug': 'malindi', 'lon': 40.1167, 'lat': -3.2167},
        {'name': 'Kitale', 'slug': 'kitale', 'lon': 35.0062, 'lat': 1.0157},
        {'name': 'Wajir', 'slug': 'wajir', 'lon': 40.0573, 'lat': 1.7471},
        {'name': 'Marsabit', 'slug': 'marsabit', 'lon': 37.9903, 'lat': 2.3364},
        {'name': 'Lodwar', 'slug': 'lodwar', 'lon': 35.5964, 'lat': 3.1199},
        {'name': 'Mandera', 'slug': 'mandera', 'lon': 41.8670, 'lat': 3.9366},
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--default-city',
            type=str,
            default='nairobi',
            help='Slug of the city to set as default (default: nairobi)',
        )
        parser.add_argument(
            '--fetch-forecast',
            action='store_true',
            default=True,
            help='Fetch forecast data from Yr.no after setting up cities (default: True)',
        )

    def handle(self, *args, **options):
        default_city_slug = options['default_city']
        fetch_forecast = options['fetch_forecast']
        
        self.stdout.write(self.style.SUCCESS('Setting up Kenyan cities for weather forecast...'))
        
        created_count = 0
        updated_count = 0
        
        for city_data in self.KENYAN_CITIES:
            location = Point(city_data['lon'], city_data['lat'])
            
            city, created = City.objects.get_or_create(
                slug=city_data['slug'],
                defaults={
                    'name': city_data['name'],
                    'location': location,
                }
            )
            
            if created:
                self.stdout.write(f'  Created city: {city_data["name"]}')
                created_count += 1
            else:
                # Update coordinates in case they changed
                city.location = location
                city.save()
                self.stdout.write(f'  Updated city: {city_data["name"]}')
                updated_count += 1
        
        # Configure forecast settings
        site = Site.objects.filter(is_default_site=True).first()
        if site:
            forecast_setting, created = ForecastSetting.objects.get_or_create(site=site)
            
            # Enable automated forecasts from Yr.no
            if not forecast_setting.enable_auto_forecast:
                forecast_setting.enable_auto_forecast = True
                forecast_setting.save()
                self.stdout.write(self.style.SUCCESS('Enabled automated forecasts from Yr.no'))
            
            # Set default city
            default_city = City.objects.filter(slug=default_city_slug).first()
            if default_city and forecast_setting.default_city_id != default_city.id:
                forecast_setting.default_city = default_city
                forecast_setting.save()
                self.stdout.write(self.style.SUCCESS(f'Set default city to: {default_city.name}'))
        else:
            self.stdout.write(self.style.WARNING('No default site found. Forecast settings not configured.'))
        
        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Created {created_count} cities, updated {updated_count} cities.'
        ))
        
        # Fetch forecast data from Yr.no
        if fetch_forecast:
            self.stdout.write(self.style.SUCCESS('\nFetching forecast data from Yr.no...'))
            try:
                call_command('generate_forecast')
                self.stdout.write(self.style.SUCCESS('Forecast data fetched successfully!'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error fetching forecast data: {e}'))
