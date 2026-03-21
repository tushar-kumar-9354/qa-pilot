"""
QA-PILOT — Celery Configuration
"""
import os
from celery import Celery
from celery.signals import setup_logging
import structlog

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('qa_pilot')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

logger = structlog.get_logger(__name__)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    logger.info("celery.debug_task", request=repr(self.request))


# ── Celery Beat Schedule (Periodic Tasks) ────────────────────
from celery.schedules import crontab

app.conf.beat_schedule = {
    # Scrape Wikipedia every 6 hours
    'scrape-wikipedia-tables': {
        'task': 'apps.scraper.tasks.scrape_wikipedia_task',
        'schedule': crontab(minute=0, hour='*/6'),
        'args': ('https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)',),
    },
    # Scrape Hacker News top stories every hour
    'scrape-hacker-news': {
        'task': 'apps.scraper.tasks.scrape_hacker_news_task',
        'schedule': crontab(minute=30),
    },
    # Run scheduled test suites every night at 2 AM
    'run-nightly-test-suite': {
        'task': 'apps.testrunner.tasks.run_scheduled_suites',
        'schedule': crontab(minute=0, hour=2),
    },
}
