# dashboard/apps.py
from django.apps import AppConfig
import os
from django.conf import settings


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

    def ready(self):
        import dashboard.signals
        # Create media directories
        media_root = settings.MEDIA_ROOT
        recipes_dir = os.path.join(media_root, 'recipes')
        os.makedirs(recipes_dir, exist_ok=True)