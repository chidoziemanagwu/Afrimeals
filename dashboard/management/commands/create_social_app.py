# dashboard/management/commands/create_social_app.py  

from django.core.management.base import BaseCommand  
from allauth.socialaccount.models import SocialApp  
from django.contrib.sites.models import Site  

class Command(BaseCommand):  
    help = 'Create Google social application if it does not exist'  

    def handle(self, *args, **kwargs):  
        site, created = Site.objects.get_or_create(domain='afrimeals.onrender.com', name='Afrimeals')  

        if not SocialApp.objects.filter(provider='google').exists():  
            app = SocialApp.objects.create(  
                provider='google',  
                name='Google',  
                client_id='1001374382394-fiem273li7benj9b4e8igclu5q5eu5t5.apps.googleusercontent.com',  # Replace with your actual client ID  
                secret='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',  # Replace with your actual client secret  
            )  
            app.sites.add(site)  
            self.stdout.write(self.style.SUCCESS('Successfully created Google social application.'))  
        else:  
            self.stdout.write(self.style.WARNING('Google social application already exists.'))  