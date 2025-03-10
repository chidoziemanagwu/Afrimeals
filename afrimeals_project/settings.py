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
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-key-for-dev')
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
    'django_celery_results', 
    'csp',
    'csp_nonce'
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
    'dashboard.middleware.SecurityHeadersMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'csp.middleware.CSPMiddleware',
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
        'NAME': os.getenv('DB_NAME', 'afrimeals'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
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

CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'


# Caching configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Security headers
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'afrimeals.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'dashboard': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}


# Configure Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = (
    "'self'",
    "https://cdn.jsdelivr.net",
    "https://code.jquery.com",
    "https://js.stripe.com",
    "'unsafe-inline'",  # Remove in production if possible
)
CSP_STYLE_SRC = (
    "'self'",
    "https://cdn.jsdelivr.net",
    "https://cdnjs.cloudflare.com",
    "https://fonts.googleapis.com",
    "'unsafe-inline'",  # Required for custom scrollbar styles
)
CSP_IMG_SRC = (
    "'self'",
    "data:",
    "https://images.unsplash.com",
    "https://*.stripe.com",
)
CSP_FONT_SRC = (
    "'self'",
    "https://fonts.gstatic.com",
)