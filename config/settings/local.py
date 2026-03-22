from .base import *
from pathlib import Path
import os

DEBUG = True
ALLOWED_HOSTS = ['*']

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── Database ─────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'qa_pilot',
        'USER': 'postgres',
        'PASSWORD': '12345',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# ── No Redis needed locally ──────────────────────────────────
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

INSTALLED_APPS = [app for app in INSTALLED_APPS
                  if app not in ['django_celery_beat', 'django_celery_results', 'debug_toolbar']]

MIDDLEWARE = [m for m in MIDDLEWARE if 'debug_toolbar' not in m]
CORS_ALLOW_ALL_ORIGINS = True

# ── Templates ────────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'frontend' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ── Static files ─────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'frontend' / 'static']

# ── Gemini AI — reads from .env ──────────────────────────────
from decouple import config
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
GEMINI_MODEL = config('GEMINI_MODEL', default='gemini-2.5-flash')

# ── Simple logging ────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
}

# Disable debug toolbar SQL panel (conflicts with psycopg3)
DEBUG_TOOLBAR_CONFIG = {
    'DISABLE_PANELS': ['debug_toolbar.panels.sql.SQLPanel'],
    'SHOW_TOOLBAR_CALLBACK': lambda request: False,  # Fully disable toolbar
}