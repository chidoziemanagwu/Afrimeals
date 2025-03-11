# dashboard/management/commands/create_superuser.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.google.provider import GoogleProvider
from django.contrib.sites.models import Site
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Create a superuser and add Google social application'

    def handle(self, *args, **kwargs):
        # Create superuser from environment variables
        User = get_user_model()
        username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'doxzy')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'ghostfrancis2@gmail.com')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'doxzy')

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'Superuser {username} created successfully.'))
        else:
            self.stdout.write(self.style.WARNING(f'Superuser {username} already exists.'))

        # Add Google Social App using environment variables
        site = Site.objects.get_current()
        google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

        if not google_client_id or not google_client_secret:
            self.stdout.write(self.style.ERROR('Google OAuth credentials not found in environment variables.'))
            return

        social_app, created = SocialApp.objects.get_or_create(
            provider=GoogleProvider.id,
            name='Google',
            defaults={
                'client_id': google_client_id,
                'secret': google_client_secret,
            }
        )
        social_app.sites.add(site)

        if created:
            self.stdout.write(self.style.SUCCESS('Google Social App created successfully.'))
        else:
            self.stdout.write(self.style.WARNING('Google Social App already exists.'))