# dashboard/management/commands/create_social_app.py  

from django.core.management.base import BaseCommand  
from allauth.socialaccount.models import SocialApp  
from django.contrib.sites.models import Site  
import os  

class Command(BaseCommand):  
    help = 'Create Google social application if it does not exist'  

    def handle(self, *args, **kwargs):  
        site, created = Site.objects.get_or_create(domain='afrimeals.onrender.com', name='Afrimeals')  

        if not SocialApp.objects.filter(provider='google').exists():  
            app = SocialApp.objects.create(  
                provider='google',  
                name='Google',  
                client_id=os.getenv('GOOGLE_CLIENT_ID'),  # Use environment variable  
                secret=os.getenv('GOOGLE_CLIENT_SECRET'),  # Use environment variable  
            )  
            app.sites.add(site)  
            self.stdout.write(self.style.SUCCESS('Successfully created Google social application.'))  
        else:  
            self.stdout.write(self.style.WARNING('Google social application already exists.'))  