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
python manage.py create_superuser