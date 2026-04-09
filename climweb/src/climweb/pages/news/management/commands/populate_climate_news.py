"""
Management command to populate sample geo-centric climate news articles.
Creates news articles about climate and climate adaptation for various Kenyan locations.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from wagtail.models import Page
from climweb.pages.news.models import NewsPage, NewsType, NewsIndexPage


class Command(BaseCommand):
    help = 'Populate sample geo-centric climate news articles'

    SAMPLE_NEWS = [
        {
            'title': 'Nairobi County Launches Urban Climate Resilience Strategy',
            'subtitle': 'New initiative aims to protect 5 million residents from climate impacts',
            'location': 'Nairobi',
            'body': '<p>Nairobi County has unveiled a comprehensive Urban Climate Resilience Strategy aimed at protecting over 5 million residents from the increasing impacts of climate change. The strategy focuses on green infrastructure, flood management, and heat mitigation in urban areas.</p><p>The initiative includes plans to plant 10 million trees across the county, establish green corridors, and improve drainage systems in flood-prone areas like Kibera and Mathare.</p>',
            'is_featured': True,
            'is_visible_on_homepage': True,
        },
        {
            'title': 'Mombasa Coastal Erosion Threatens Historic Sites',
            'subtitle': 'Rising sea levels put heritage sites at risk',
            'location': 'Mombasa',
            'body': '<p>Rising sea levels and increased storm intensity are accelerating coastal erosion along Mombasa\'s shoreline, threatening historic sites and local communities. The Kenya Marine and Fisheries Research Institute reports that some areas have lost up to 2 meters of coastline annually.</p><p>Local authorities are working with international partners to develop coastal protection measures including mangrove restoration and seawall construction.</p>',
            'is_featured': True,
            'is_visible_on_homepage': True,
        },
        {
            'title': 'Kisumu Farmers Adopt Climate-Smart Agriculture',
            'subtitle': 'New techniques help farmers cope with unpredictable rainfall',
            'location': 'Kisumu',
            'body': '<p>Farmers in Kisumu County are increasingly adopting climate-smart agriculture techniques to cope with unpredictable rainfall patterns. The initiative, supported by the county government and international NGOs, has trained over 5,000 farmers in drought-resistant crop varieties and water conservation methods.</p><p>Early results show a 30% increase in crop yields despite reduced rainfall, demonstrating the effectiveness of these adaptation strategies.</p>',
            'is_featured': False,
            'is_visible_on_homepage': True,
        },
        {
            'title': 'Nakuru Lake Level Rise Displaces Communities',
            'subtitle': 'Over 1,000 families affected by rising waters',
            'location': 'Nakuru',
            'body': '<p>Rising water levels at Lake Nakuru have displaced over 1,000 families in the past year, forcing communities to relocate to higher ground. The Kenya Meteorological Department attributes the rise to increased rainfall in the catchment areas and reduced evaporation due to changing weather patterns.</p><p>The county government has established temporary shelters and is working on long-term resettlement plans for affected communities.</p>',
            'is_featured': False,
            'is_visible_on_homepage': True,
        },
        {
            'title': 'Eldoret Renewable Energy Project Powers 50,000 Homes',
            'subtitle': 'Solar and wind initiative reduces carbon emissions',
            'location': 'Eldoret',
            'body': '<p>A major renewable energy project in Eldoret has begun supplying clean electricity to over 50,000 homes, significantly reducing the region\'s carbon footprint. The project combines solar panels and wind turbines to provide reliable power even during cloudy or calm weather.</p><p>The initiative is part of Kenya\'s commitment to generate 100% of its electricity from renewable sources by 2030.</p>',
            'is_featured': True,
            'is_visible_on_homepage': True,
        },
        {
            'title': 'Garissa Drought Early Warning System Saves Livestock',
            'subtitle': 'New technology helps pastoralists prepare for dry seasons',
            'location': 'Garissa',
            'body': '<p>A new drought early warning system in Garissa County is helping pastoralists prepare for dry seasons and protect their livestock. The system uses satellite data and ground sensors to predict drought conditions weeks in advance, giving herders time to move their animals to better grazing areas.</p><p>Since its implementation, livestock losses during dry seasons have decreased by 40%, significantly improving food security in the region.</p>',
            'is_featured': False,
            'is_visible_on_homepage': True,
        },
        {
            'title': 'Nyeri Coffee Farmers Embrace Shade-Grown Techniques',
            'subtitle': 'Traditional methods help combat climate change',
            'location': 'Nyeri',
            'body': '<p>Coffee farmers in Nyeri County are returning to traditional shade-growing techniques to combat the effects of climate change on their crops. By planting coffee under tree canopies, farmers are reducing water stress and protecting their plants from extreme temperatures.</p><p>The initiative has also created additional income streams through timber and fruit production from the shade trees.</p>',
            'is_featured': False,
            'is_visible_on_homepage': False,
        },
        {
            'title': 'Meru County Plants 2 Million Trees for Climate Action',
            'subtitle': 'Reforestation effort aims to restore degraded lands',
            'location': 'Meru',
            'body': '<p>Meru County has launched an ambitious reforestation program aimed at planting 2 million trees over the next two years. The initiative focuses on restoring degraded lands, protecting water catchment areas, and creating green jobs for local communities.</p><p>The county has partnered with schools, churches, and community groups to ensure widespread participation in the planting exercise.</p>',
            'is_featured': False,
            'is_visible_on_homepage': True,
        },
        {
            'title': 'Kakamega Forest Restoration Gains Momentum',
            'subtitle': 'Community-led efforts protect Kenya\'s only tropical rainforest',
            'location': 'Kakamega',
            'body': '<p>Community-led restoration efforts in Kakamega Forest are showing promising results in protecting Kenya\'s only tropical rainforest. Local communities have established tree nurseries and are actively participating in reforestation activities.</p><p>The forest, home to unique biodiversity, has seen a 15% increase in tree cover over the past three years thanks to these conservation efforts.</p>',
            'is_featured': True,
            'is_visible_on_homepage': True,
        },
        {
            'title': 'Malindi Beach Erosion Accelerates Due to Climate Change',
            'subtitle': 'Tourism industry faces new challenges',
            'location': 'Malindi',
            'body': '<p>Beach erosion along Malindi\'s coastline has accelerated in recent years due to climate change, posing significant challenges to the local tourism industry. Studies show that some beaches have lost up to 30 meters of shoreline in the past decade.</p><p>The Kenya Tourism Board is working with environmental experts to develop sustainable beach management practices that balance tourism with conservation.</p>',
            'is_featured': False,
            'is_visible_on_homepage': False,
        },
    ]

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Populating sample climate news articles...'))
        
        # Get or create news type
        news_type, created = NewsType.objects.get_or_create(
            name='Climate News',
        )
        if created:
            self.stdout.write(f'  Created news type: {news_type.name}')
        
        # Find or create news index page
        news_index = NewsIndexPage.objects.live().first()
        if not news_index:
            # Get the home page
            from climweb.pages.home.models import HomePage
            home_page = HomePage.objects.live().first()
            if not home_page:
                self.stdout.write(self.style.ERROR('No HomePage found. Please create one first.'))
                return
            
            # Create news index page
            news_index = NewsIndexPage(
                title='News & Updates',
                slug='news-updates',
                banner_title='News & Updates',
            )
            home_page.add_child(instance=news_index)
            news_index.save_revision().publish()
            self.stdout.write(self.style.SUCCESS('  Created NewsIndexPage: News & Updates'))
        
        created_count = 0
        for news_data in self.SAMPLE_NEWS:
            # Check if news with this title already exists
            if NewsPage.objects.filter(title=news_data['title']).exists():
                self.stdout.write(f'  Skipped (exists): {news_data["title"]}')
                continue
            
            # Create news page
            news_page = NewsPage(
                title=news_data['title'],
                subtitle=news_data['subtitle'],
                news_location=news_data['location'],
                body=news_data['body'],
                news_type=news_type,
                is_featured=news_data['is_featured'],
                is_visible_on_homepage=news_data['is_visible_on_homepage'],
                date=timezone.now(),
            )
            
            # Add as child of news index
            news_index.add_child(instance=news_page)
            news_page.save_revision().publish()
            
            created_count += 1
            self.stdout.write(f'  Created: {news_data["title"]} ({news_data["location"]})')
        
        self.stdout.write(self.style.SUCCESS(f'\nDone! Created {created_count} news articles.'))
