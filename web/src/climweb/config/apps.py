from django.apps import AppConfig
import importlib
import logging

logger = logging.getLogger(__name__)


class DbEngineConfig(AppConfig):
    name = 'climweb.config'
    verbose_name = 'ClimWeb configuration'

    def ready(self):
        """Validate the configured DB engine after apps are loaded.

        This avoids importing database backend internals at settings import
        time (which can run before `django.setup()` completes) and provides
        a post-startup validation point.
        """
        try:
            mod = importlib.import_module('climweb.config.db_engine.base')
            DBWrapper = getattr(mod, 'DatabaseWrapper', None)

            # Check the real PostGIS backend provides expected attributes
            postgis_mod = importlib.import_module('django.contrib.gis.db.backends.postgis.base')
            PostGISDB = getattr(postgis_mod, 'DatabaseWrapper', None)

            if PostGISDB is None or not hasattr(PostGISDB, 'geo_db_type'):
                raise RuntimeError("PostGIS DatabaseWrapper missing 'geo_db_type'")
        except Exception as e:
            # Don't hard-fail here; prod settings will raise if DB engine is invalid.
            logger.warning('DB engine validation in AppConfig.ready() failed: %s', e, exc_info=True)
