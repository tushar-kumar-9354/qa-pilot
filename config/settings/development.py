from .base import *

DEBUG = True

# Remove debug_toolbar completely — conflicts with psycopg3
INSTALLED_APPS = [app for app in INSTALLED_APPS 
                  if app != 'debug_toolbar']

MIDDLEWARE = [m for m in MIDDLEWARE 
              if 'debug_toolbar' not in m]

CORS_ALLOW_ALL_ORIGINS = True
INTERNAL_IPS = ['127.0.0.1']
from .base import *

DEBUG = True

# Remove debug_toolbar completely — conflicts with psycopg3
INSTALLED_APPS = [app for app in INSTALLED_APPS 
                  if app != 'debug_toolbar']

MIDDLEWARE = [m for m in MIDDLEWARE 
              if 'debug_toolbar' not in m]

CORS_ALLOW_ALL_ORIGINS = True
INTERNAL_IPS = ['127.0.0.1']