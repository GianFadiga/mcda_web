# analyzer_app/apps.py
from django.apps import AppConfig

class AnalyzerAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analyzer_app'

    def ready(self):
        import analyzer_app.signals
    