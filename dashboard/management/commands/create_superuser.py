from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from allauth.socialaccount.models import SocialApp, SocialToken, SocialLogin
from allauth.socialaccount.providers.google.provider import GoogleProvider
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = 'Create a superuser and add Google social application'

    def handle(self, *args, **kwargs):
        # Create superuser
        User = get_user_model()
        username = 'doxzy'
        email = 'doxzy@example.com'
        password = 'doxzy'

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'Superuser {username} created successfully.'))
        else:
            self.stdout.write(self.style.WARNING(f'Superuser {username} already exists.'))

        # Add Google Social App
        site = Site.objects.get_current()
        google_client_id = '1001374382394-fiem273li7benj9b4e8igclu5q5eu5t5.apps.googleusercontent.com'
        google_client_secret = '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'

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