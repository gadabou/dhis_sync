"""
Settings de production pour DHIS2 Sync

Ce fichier hérite de settings.py et remplace certains paramètres
pour l'environnement de production.
"""

from .settings import *
from decouple import config, Csv
import os

# SECURITY SETTINGS
# =================

# Load SECRET_KEY from environment
SECRET_KEY = config('SECRET_KEY', default='django-insecure-&a&_#5u*6$wahn0m#$lh(0b%^=8*%u=rhu9%1^%thzr7we(_*e')

# DEBUG must be False in production
DEBUG = config('DEBUG', default=False, cast=bool)

# Allowed hosts for production
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# CSRF Configuration
# Django 4+ requires explicit trusted origins for CSRF protection
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:4999',
    'http://127.0.0.1:4999',
    'http://localhost',
    'http://127.0.0.1',
]

# Add custom domain if configured
CUSTOM_DOMAIN = config('CUSTOM_DOMAIN', default=None)
if CUSTOM_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f'http://{CUSTOM_DOMAIN}')
    CSRF_TRUSTED_ORIGINS.append(f'https://{CUSTOM_DOMAIN}')

# HTTPS settings (uncomment when SSL is configured)
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_BROWSER_XSS_FILTER = True
# SECURE_CONTENT_TYPE_NOSNIFF = True
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# DATABASE CONFIGURATION
# ======================

# Support for Docker environment variables
if config('POSTGRES_HOST', default=None):
    # PostgreSQL configuration (Docker)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('POSTGRES_DB', default='dhis2sync'),
            'USER': config('POSTGRES_USER', default='dhis2user'),
            'PASSWORD': config('POSTGRES_PASSWORD', default=''),
            'HOST': config('POSTGRES_HOST', default='db'),
            'PORT': config('POSTGRES_PORT', default='5432'),
            'CONN_MAX_AGE': 600,  # Connection pooling
        }
    }
elif config('DATABASE_URL', default=None):
    # DATABASE_URL format: postgresql://user:password@host:port/dbname
    database_url = config('DATABASE_URL')
    if database_url.startswith('postgresql://'):
        import dj_database_url
        DATABASES = {
            'default': dj_database_url.config(default=database_url)
        }
    else:
        # SQLite from DATABASE_URL
        db_path = database_url.replace('sqlite:///', '')
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / db_path if not os.path.isabs(db_path) else db_path,
            }
        }
else:
    # SQLite (default)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# STATIC FILES (CSS, JavaScript, Images)
# ======================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Use WhiteNoise for serving static files in production
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# MEDIA FILES
# ===========

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# CELERY CONFIGURATION
# ====================

CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max per task

# REDIS CACHE
# ===========

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('CELERY_BROKER_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# SESSION CONFIGURATION
# =====================

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# EMAIL CONFIGURATION
# ===================

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.example.org')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)

# LOGGING CONFIGURATION
# =====================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'dhis_app': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# PERFORMANCE OPTIMIZATIONS
# =========================

# Disable Django Debug Toolbar in production
if 'debug_toolbar' in INSTALLED_APPS:
    INSTALLED_APPS.remove('debug_toolbar')

if 'debug_toolbar.middleware.DebugToolbarMiddleware' in MIDDLEWARE:
    MIDDLEWARE.remove('debug_toolbar.middleware.DebugToolbarMiddleware')

# Security middleware
MIDDLEWARE.insert(0, 'django.middleware.security.SecurityMiddleware')

print("Production settings loaded successfully!")
print(f"DEBUG: {DEBUG}")
print(f"ALLOWED_HOSTS: {ALLOWED_HOSTS}")
print(f"Database: {DATABASES['default']['ENGINE']}")
