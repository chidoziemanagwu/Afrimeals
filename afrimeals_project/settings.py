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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'afrimeals',
        'USER': 'afrimeals_owner',
        'PASSWORD': 'fYXZqaR3g2LM',
        'HOST': 'ep-misty-pond-a5dm2536.us-east-2.aws.neon.tech',
        'PORT': '5432',  # Default PostgreSQL port
        'OPTIONS': {
            'sslmode': 'require',  # Ensure SSL is used
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

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'  

# Authentication settings  
AUTHENTICATION_BACKENDS = [  
    'django.contrib.auth.backends.ModelBackend',  
    'allauth.account.auth_backends.AuthenticationBackend',  
]  

SITE_ID = 1  
LOGIN_REDIRECT_URL = '/dashboard/'  
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