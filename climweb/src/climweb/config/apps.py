from django.apps import AppConfig
import importlib
import logging

logger = logging.getLogger(__name__)


class DbEngineConfig(AppConfig):
    name = 'climweb.config'
    verbose_name = 'ClimWeb configuration'

    def ready(self):
        """Import the configured DB engine after apps are loaded.

        This avoids importing database backend internals at settings import
        time (which can run before `django.setup()` completes).
        """
        try:
            importlib.import_module('climweb.config.db_engine.base')
        except ImportError as e:
            # Don't hard-fail here; prod settings will raise if DB engine is invalid.
            logger.warning('DB engine import in AppConfig.ready() failed: %s', e, exc_info=True)
