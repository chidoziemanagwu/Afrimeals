import os  
from django.core.management.base import BaseCommand  
from allauth.socialaccount.models import SocialApp  
from django.contrib.sites.models import Site  

class Command(BaseCommand):  
    help = 'Create Google social application if it does not exist'  

    def handle(self, *args, **kwargs):  
        # Ensure the site exists  
        site, created = Site.objects.get_or_create(domain='afrimeals.onrender.com', defaults={'name': 'Afrimeals'})  
        if created:  
            self.stdout.write(self.style.SUCCESS(f"Site created: {site}"))  
        else:  
            self.stdout.write(self.style.SUCCESS(f"Site exists: {site}"))  

        # Check if the SocialApp exists  
        app = SocialApp.objects.filter(provider='google').first()  
        if not app:  
            # Create the SocialApp  
            app = SocialApp.objects.create(  
                provider='google',  
                name='Google',  
                client_id=os.getenv('GOOGLE_CLIENT_ID'),  
                secret=os.getenv('GOOGLE_CLIENT_SECRET'),  
            )  
            app.sites.add(site)  
            self.stdout.write(self.style.SUCCESS('Successfully created Google social application.'))  
        else:  
            self.stdout.write(self.style.WARNING('Google social application already exists.'))  

        # Verify the app is associated with the site  
        if site not in app.sites.all():  
            app.sites.add(site)  
            self.stdout.write(self.style.SUCCESS('Associated Google social application with the site.'))  