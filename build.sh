#!/usr/bin/env bash  
# build.sh  
  
# Make script exit on first error  
set -o errexit  
  
# Install Python dependencies  
pip install -r requirements.txt  
  
# Collect static files  
python manage.py collectstatic --no-input  
  
# Apply database migrations  
python manage.py migrate  
  
# Create Google social application if it doesn't exist  
python manage.py shell <<EOF  
from allauth.socialaccount.models import SocialApp  
from django.contrib.sites.models import Site  
  
# Create or get the site  
site, created = Site.objects.get_or_create(domain='afrimeals.onrender.com', name='Afrimeals')  
  
# Create Google social application  
if not SocialApp.objects.filter(provider='google').exists():  
    app = SocialApp.objects.create(  
        provider='google',  
        name='Google',  
        client_id='1001374382394-fiem273li7benj9b4e8igclu5q5eu5t5.apps.googleusercontent.com',  # Replace with your actual client ID  
        secret='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',  # Replace with your actual client secret  
    )  
    app.sites.add(site)  
EOF  