# dashboard/management/commands/create_social_app.py  

import os  
from django.core.management.base import BaseCommand  
from allauth.socialaccount.models import SocialApp  
from django.contrib.sites.models import Site  

class Command(BaseCommand):  
    help = 'Create Google social application if it does not exist'  

    def handle(self, *args, **kwargs):  
        site, created = Site.objects.get_or_create(domain='afrimeals.onrender.com', name='Afrimeals')  

        if not SocialApp.objects.filter(provider='google').exists():  
            print("Creating Google social application...")  

            print("Google Client ID:", os.getenv('GOOGLE_CLIENT_ID'))  
            print("Google Client Secret:", os.getenv('GOOGLE_CLIENT_SECRET'))  
            app = SocialApp.objects.create(  
                provider='google',  
                name='Google',  
                client_id=os.getenv('GOOGLE_CLIENT_ID'),  
                secret=os.getenv('GOOGLE_CLIENT_SECRET'),  
            )  


            print("2. Google Client ID:", os.getenv('GOOGLE_CLIENT_ID'))  
            print("2. Google Client Secret:", os.getenv('GOOGLE_CLIENT_SECRET'))  
            app.sites.add(site)  
            print("Google social application created successfully.")   
        else:  
            self.stdout.write(self.style.WARNING('Google social application already exists.'))  