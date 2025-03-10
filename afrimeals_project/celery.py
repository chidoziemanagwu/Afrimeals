import os
from celery import Celery

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afrimeals_project.settings')

# Create Celery app
app = Celery('afrimeals')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()