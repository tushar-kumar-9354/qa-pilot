from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = config('DJANGO_SECRET_KEY', default='ci-key')
DEBUG = True
ALLOWED_HOSTS = ['*']
INSTALLED_APPS = [
    'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes',
    'django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles',
    'rest_framework','rest_framework_simplejwt','corsheaders','django_filters',
    'apps.core','apps.scraper','apps.testrunner','apps.agents',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'apps.core.middleware.StructuredLoggingMiddleware',
]
ROOT_URLCONF = 'config.urls'
AUTH_USER_MODEL = 'core.User'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'frontend'/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'test_db.sqlite3'}}
CELERY_TASK_ALWAYS_EAGER = True
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
GEMINI_MODEL = config('GEMINI_MODEL', default='gemini-2.0-flash')
SCRAPER_CONFIG = {'HEADLESS':True,'TIMEOUT':30,'MAX_RETRIES':3,'DELAY_MIN':1.0,'DELAY_MAX':3.0}
STATIC_URL = '/static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES':['rest_framework_simplejwt.authentication.JWTAuthentication']}
from datetime import timedelta
SIMPLE_JWT = {'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60)}
import structlog
structlog.configure(processors=[structlog.stdlib.add_log_level,structlog.stdlib.ProcessorFormatter.wrap_for_formatter],wrapper_class=structlog.stdlib.BoundLogger,context_class=dict,logger_factory=structlog.stdlib.LoggerFactory())
LOGGING = {'version':1,'disable_existing_loggers':False,'handlers':{'console':{'class':'logging.StreamHandler'}},'root':{'handlers':['console'],'level':'WARNING'}}