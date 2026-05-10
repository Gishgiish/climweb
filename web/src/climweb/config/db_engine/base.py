# Adapted from https://forum.djangoproject.com/t/django-db-utils-interfaceerror-connection-already-closed-when-updating-from-django-3-0-to-3-1/12708/21

"""Lazy-loading DatabaseWrapper wrapper for PostGIS.

Importing Django's GIS backend at module import time can trigger app
registry access before Django is fully initialised (django.setup()).
This wrapper defers importing and instantiating the real
`django.contrib.gis.db.backends.postgis.base.DatabaseWrapper` until
it's actually needed at runtime.

The wrapper forwards attribute access to the real backend instance and
handles `InterfaceError` during cursor creation by closing old
connections and retrying.
"""
from psycopg2 import InterfaceError


class DatabaseWrapper:
    """Proxy DatabaseWrapper that lazily instantiates the real PostGIS wrapper.

    Django will import this module and instantiate `DatabaseWrapper` with
    connection settings. Instead of importing the PostGIS backend at module
    import time (which may access app registry), we store the init args and
    defer creating the real wrapper until first use.
    """

    def __init__(self, *args, **kwargs):
        self._real = None
        self._real_args = args
        self._real_kwargs = kwargs

    # Expose a class-level marker expected by settings checks that validate
    # the configured backend implements GeoDjango/PostGIS operations.
    geo_db_type = 'postgis'

    def _ensure_real(self):
        if self._real is None:
            # Import inside runtime context to avoid touching Django app
            # registry during settings import / django.setup().
            from django.contrib.gis.db.backends.postgis.base import DatabaseWrapper as _Real

            # Instantiate the real backend wrapper and keep a reference.
            self._real = _Real(*self._real_args, **self._real_kwargs)

    def create_cursor(self, name=None):
        try:
            self._ensure_real()
            return self._real.create_cursor(name=name)
        except InterfaceError:
            # Attempt to recover like the adapted upstream implementation:
            import django.db

            django.db.close_old_connections()
            # Ensure the real backend is (re)connected and retry
            self._ensure_real()
            return self._real.create_cursor(name=name)

    def __getattr__(self, item):
        # Delegate any other attributes to the real backend instance.
        self._ensure_real()
        return getattr(self._real, item)

