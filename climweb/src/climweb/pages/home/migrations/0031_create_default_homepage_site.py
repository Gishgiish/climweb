# Generated migration to ensure HomePage exists and Site is configured
from django.db import migrations
from wagtail.models import Page, Site


def create_default_homepage_and_site(apps, schema_editor):
    """
    Create a default HomePage if none exists, and configure the Wagtail Site.
    This ensures that upon deployment, there's always a valid homepage to serve.
    """
    HomePage = apps.get_model('home', 'HomePage')
    
    # Check if a HomePage already exists
    if not HomePage.objects.filter(depth__gt=1).exists():
        # Get the root page
        root_page = Page.objects.get(depth=1)
        
        # Create a default HomePage
        home_page = HomePage(
            title='Home',
            slug='home',
            hero_title='AfriClimate Center For Adaptation',
            hero_subtitle='Climate Information for Africa',
        )
        root_page.add_child(instance=home_page)
        home_page.save_revision().publish()
        print(f"Created default HomePage: {home_page.title} (id={home_page.id})")


def configure_site_for_deployment(apps, schema_editor):
    """
    Configure the Wagtail Site to use the HomePage as root.
    This runs during migration to ensure proper site configuration.
    NOTE: Port is set to 80 as placeholder; entrypoint script updates it at runtime.
    Using hostname='*' ensures it matches any hostname when port also matches.
    """
    HomePage = apps.get_model('home', 'HomePage')
    Site = apps.get_model('wagtailcore', 'Site')
    
    # Find the HomePage
    homepage = HomePage.objects.filter(depth__gt=1).first()
    
    if homepage:
        # Delete existing sites to avoid conflicts
        Site.objects.all().delete()
        
        # Create new site with hostname='*' and port=80 as placeholder
        # IMPORTANT: The entrypoint script will update this at runtime with the correct PORT
        # Using '*' as hostname ensures it matches any request when combined with correct port
        Site.objects.create(
            hostname='*',
            port=80,  # Placeholder - entrypoint will update via configure_site command
            root_page=homepage,
            is_default_site=True,
            site_name='AfriClimate Center For Adaptation',
        )
        print(f"Configured Site with homepage: {homepage.title} (id={homepage.id})")
        print("NOTE: Entrypoint script will update port at runtime based on PORT env var")
    else:
        print("WARNING: No HomePage found, Site not configured")
        print("INFO: Available pages:")
        for p in Page.objects.all().order_by('depth', 'id')[:20]:
            print(f"  id={p.id} depth={p.depth} slug={p.slug!r} title={p.title!r}")


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0030_homepage_call_to_action_button_text_2_and_more'),
        ('wagtailcore', '0094_alter_page_locale'),
    ]

    operations = [
        migrations.RunPython(create_default_homepage_and_site, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(configure_site_for_deployment, reverse_code=migrations.RunPython.noop),
    ]
