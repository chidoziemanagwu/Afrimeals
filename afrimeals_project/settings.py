import os  
from pathlib import Path  
from dotenv import load_dotenv  
from urllib.parse import urlparse

load_dotenv()  

# Build paths inside the project like this: BASE_DIR / 'subdir'.  
BASE_DIR = Path(__file__).resolve().parent.parent  

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# SECURITY WARNING: keep the secret key used in production secret!  
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'  # Ensure boolean conversion
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-key-for-dev')  # Provide a default for development
# afrimeals_project/settings.py

# Add to your existing settings
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# In settings.py
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', '')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.onrender.com', 'afrimeals-production.up.railway.app']  

# Application definition  
INSTALLED_APPS = [  
    'django.contrib.admin',  
    'django.contrib.auth',  
    'django.contrib.contenttypes',  
    'django.contrib.sessions',  
    'django.contrib.messages',  
    'django.contrib.staticfiles',  
    'django.contrib.sites',  
    'allauth',  
    'allauth.account',  
    'allauth.socialaccount',  
    'allauth.socialaccount.providers.google',  
    'dashboard',
    'sslserver',
    'rest_framework',
]  

MIDDLEWARE = [  
    'django.middleware.security.SecurityMiddleware',  
    'whitenoise.middleware.WhiteNoiseMiddleware',  
    'django.contrib.sessions.middleware.SessionMiddleware',  
    'django.middleware.common.CommonMiddleware',  
    'django.middleware.csrf.CsrfViewMiddleware',  
    'django.contrib.auth.middleware.AuthenticationMiddleware',  
    'django.contrib.messages.middleware.MessageMiddleware',  
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  
    'allauth.account.middleware.AccountMiddleware',  
]  

ROOT_URLCONF = 'afrimeals_project.urls'  

TEMPLATES = [  
    {  
        'BACKEND': 'django.template.backends.django.DjangoTemplates',  
        'DIRS': [os.path.join(BASE_DIR, 'templates'), os.path.join(BASE_DIR, 'dashboard', 'templates')],  
        'APP_DIRS': True,  
        'OPTIONS': {  
            'context_processors': [  
                'django.template.context_processors.debug',  
                'django.template.context_processors.request',  
                'django.template.context_processors.media',  
                'django.contrib.auth.context_processors.auth',  
                'django.contrib.messages.context_processors.messages',  
            ],  
        },  
    },  
]  

WSGI_APPLICATION = 'afrimeals_project.wsgi.application'  

# In settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'afrimeals'),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [  
    {  
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',  
    },  
    {  
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',  
    },  
    {  
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',  
    },  
    {  
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',  
    },  
]  

LANGUAGE_CODE = 'en-us'  
TIME_ZONE = 'UTC'  
USE_I18N = True  
USE_TZ = True  

STATIC_URL = '/static/'  
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Ensure this matches your structure  
STATICFILES_DIRS = [  
    os.path.join(BASE_DIR, 'dashboard/static'),  
]  

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Add media directories
MEDIA_DIRS = {
    'recipes': os.path.join(MEDIA_ROOT, 'recipes'),
    'profiles': os.path.join(MEDIA_ROOT, 'profiles'),
}


# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Image validation settings
VALID_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif']
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
IMAGE_MIN_DIMENSIONS = (100, 100)  # Minimum dimensions
IMAGE_MAX_DIMENSIONS = (2000, 2000)  # Maximum dimensions


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'  

# Authentication settings  
AUTHENTICATION_BACKENDS = [  
    'django.contrib.auth.backends.ModelBackend',  
    'allauth.account.auth_backends.AuthenticationBackend',  
]  

SITE_ID = 1  
LOGIN_REDIRECT_URL = '/'  
LOGOUT_REDIRECT_URL = '/'  

SOCIALACCOUNT_PROVIDERS = {  
    'google': {  
        'SCOPE': [  
            'profile',  
            'email',  
        ],  
        'AUTH_PARAMS': {  
            'access_type': 'online',  
        },  
        'OAUTH_PKCE_ENABLED': True,  
    }  
}  

SOCIALACCOUNT_AUTO_SIGNUP = True  
SOCIALACCOUNT_LOGIN_ON_GET = True  

# In settings.py
ACCOUNT_LOGOUT_ON_GET = True  # Set to True if you want to logout immediately without confirmation
ACCOUNT_LOGOUT_REDIRECT_URL = '/'  # Redirect to home page after logout
# In settings.py
ACCOUNT_ADAPTER = 'dashboard.adapters.CustomAccountAdapter'


# Allauth settings  
ACCOUNT_EMAIL_REQUIRED = True  
ACCOUNT_USERNAME_REQUIRED = False  
ACCOUNT_AUTHENTICATION_METHOD = 'email'  
ACCOUNT_EMAIL_VERIFICATION = 'none'  

# Security settings for production  
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # For proxy servers
    CSRF_TRUSTED_ORIGINS = [
        'https://afrimeals-production.up.railway.app',
        'https://afrimeals.onrender.com',
    ]
    # New security headers
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True


# settings.py

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,  # 5 minutes default timeout
        'OPTIONS': {
            'MAX_ENTRIES': 1000,  # Maximum number of entries in cache
            'CULL_FREQUENCY': 3,  # Fraction of entries to cull when max is reached
        }
    }
}

# Cache timeouts (in seconds)
CACHE_TIMEOUTS = {
    'short': 300,        # 5 minutes
    'medium': 1800,      # 30 minutes
    'long': 3600,        # 1 hour
    'very_long': 86400,  # 24 hours
}

# Add to settings.py
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Celery task settings
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
