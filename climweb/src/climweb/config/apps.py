from django.apps import AppConfig


class DbEngineConfig(AppConfig):
    name = 'climweb.config'
    verbose_name = 'ClimWeb configuration'

    def ready(self):
        pass
