from django.apps import AppConfig
import importlib
import logging

logger = logging.getLogger(__name__)


class DbEngineConfig(AppConfig):
    name = 'climweb.config'
    verbose_name = 'ClimWeb configuration'

    def ready(self):
        """Perform a lightweight validation of the DB engine after apps are ready.

        This avoids doing the check during module import time (which can run
        before django.setup()). We attempt to import the real PostGIS backend
        and validate it exposes the expected attributes.
        """
        try:
            # Import our proxy wrapper module (safe) and the real postgis backend
            mod = importlib.import_module('climweb.config.db_engine.base')
            DBWrapper = getattr(mod, 'DatabaseWrapper', None)

            postgis_mod = importlib.import_module('django.contrib.gis.db.backends.postgis.base')
            PostGISDB = getattr(postgis_mod, 'DatabaseWrapper', None)

            if PostGISDB is None or not hasattr(PostGISDB, 'geo_db_type'):
                raise RuntimeError("PostGIS DatabaseWrapper does not expose 'geo_db_type'.")

        except Exception as e:
            # Log explicitly so deploy logs show the cause; do not raise here
            # because settings-level checks (prod.py) will still perform
            # an explicit ImproperlyConfigured if needed.
            logger.warning('DB engine validation in AppConfig.ready() failed: %s', e, exc_info=True)
