"""Verify environment and Django DATABASES['default'] for PostGIS/GeoDjango.

Run as: python -m climweb.scripts.verify_db
Exit codes:
 - 0: OK
 - 2: Engine not PostGIS/GeoDjango
 - 3: DB connection failed
 - 4: PostGIS extension missing
 - 1: unexpected error
"""
import os
import sys
import json
import traceback

DJANGO_SETTINGS = os.environ.get('DJANGO_SETTINGS_MODULE', 'climweb.config.settings.prod')

REQUIRED_ENVS = ['DATABASE_URL', 'SECRET_KEY']
OPTIONAL_ENVS = [
    'DJANGO_SUPERUSER_USERNAME',
    'DJANGO_SUPERUSER_EMAIL',
    'DJANGO_SUPERUSER_PASSWORD',
    'RAILWAY_PUBLIC_DOMAIN',
]

def check_envs():
    missing = [v for v in REQUIRED_ENVS if not os.environ.get(v)]
    if missing:
        print('ERROR: Missing required environment variables:', missing)
        return False
    present_optional = {v: bool(os.environ.get(v)) for v in OPTIONAL_ENVS}
    print('Optional env presence:', present_optional)
    return True

def check_django_and_engine():
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', DJANGO_SETTINGS)
    django.setup()
    from django.conf import settings
    cfg = dict(settings.DATABASES.get('default', {}))
    cfg.pop('PASSWORD', None)
    cfg.pop('USER', None)
    print('SANITIZED_DATABASE:', json.dumps(cfg))

    engine = (cfg.get('ENGINE') or '')
    if not any(k in engine for k in ('postgis', 'gis', 'climweb.config.db_engine')):
        print('\nERROR: DATABASE ENGINE does not appear to be a PostGIS/GeoDjango backend.')
        print('Detected ENGINE:', engine)
        return 2, None
    print('DB engine looks good:', engine)
    return 0, engine

def check_postgis_available():
    # Attempt to run a simple PostGIS query to verify extension is present
    try:
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute("SELECT PostGIS_Version();")
            row = cur.fetchone()
            print('PostGIS_Version():', row)
            if not row:
                print('ERROR: PostGIS version query returned no rows')
                return 4
            return 0
    except Exception as e:
        print('ERROR: Could not run PostGIS version check:', e)
        traceback.print_exc()
        return 3

def main():
    try:
        if not check_envs():
            sys.exit(1)

        code, engine = check_django_and_engine()
        if code != 0:
            sys.exit(code)

        # Check DB/PostGIS availability
        pg_code = check_postgis_available()
        if pg_code != 0:
            sys.exit(pg_code)

        # Optionally check native GDAL/GEOS availability
        try:
            from django.contrib.gis import geos, gdal
            print('GEOS version:', getattr(geos, 'geos_version', None))
            print('GDAL available:', hasattr(gdal, '__version__'))
        except Exception:
            print('Warning: could not import django.contrib.gis geos/gdal modules')

        print('All checks passed')
        sys.exit(0)
    except Exception as e:
        print('Unexpected error in verify_db:', e)
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
