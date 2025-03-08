#!/usr/bin/env bash  
# build.sh  

# Make script exit on first error  
set -o errexit  

# Install Python dependencies  
pip install -r requirements.txt  

# Collect static files  
python manage.py collectstatic --no-input  

# Apply database migrations  
python manage.py makemigrations 
python manage.py migrate  

# Create Google social application if it doesn't exist  
python manage.py create_superuser

# Create subscription tiers
python manage.py create_subscription_tiers