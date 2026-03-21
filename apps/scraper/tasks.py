"""
QA-PILOT — Scraper Celery Tasks
Async & scheduled scraping tasks
"""
from celery import shared_task
from django.utils import timezone
import structlog

logger = structlog.get_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_wikipedia_task(self, url: str, table_index: int = 0):
    """
    Celery task: Scrape a Wikipedia table and store as ScrapedData.
    These records are used as pytest parametrize fixtures in unit & integration tests.
    """
    from apps.scraper.models import ScraperTarget, ScraperRun, ScrapedData
    from apps.scraper.engine import ScraperEngine

    logger.info("task.scrape_wikipedia.start", url=url)

    # Get or create scraper target
    target, _ = ScraperTarget.objects.get_or_create(
        url=url,
        defaults={
            'name': f'Wikipedia: {url.split("/")[-1].replace("_", " ")}',
            'data_type': ScraperTarget.DataType.TABLE,
            'requires_js': True,
        }
    )

    # Create run record
    run = ScraperRun.objects.create(
        target=target,
        status=ScraperRun.Status.RUNNING,
        started_at=timezone.now(),
        celery_task_id=self.request.id or '',
        triggered_by='celery_beat',
    )

    try:
        with ScraperEngine() as scraper:
            raw_data = scraper.scrape_table(url, table_index)

        if 'error' in raw_data:
            run.status = ScraperRun.Status.FAILED
            run.error_message = raw_data['error']
            run.completed_at = timezone.now()
            run.save()
            return {'status': 'failed', 'error': raw_data['error']}

        # Normalize data
        normalized = ScraperEngine.normalize_table_data(raw_data)
        data_hash = ScraperEngine.compute_hash(raw_data)

        # Skip if duplicate
        if ScrapedData.objects.filter(data_hash=data_hash).exists():
            logger.info("task.scrape_wikipedia.duplicate_skipped", hash=data_hash)
            run.status = ScraperRun.Status.SUCCESS
            run.completed_at = timezone.now()
            run.save()
            return {'status': 'skipped', 'reason': 'duplicate'}

        # Save scraped data
        scraped = ScrapedData.objects.create(
            target=target,
            scraper_run=run,
            title=raw_data.get('title', ''),
            raw_data=raw_data,
            normalized_data=normalized,
            data_hash=data_hash,
            row_count=raw_data.get('row_count', 0),
            column_count=raw_data.get('column_count', 0),
            source_url=url,
            status=ScrapedData.DataStatus.VALIDATED,
        )

        # Update run
        run.status = ScraperRun.Status.SUCCESS
        run.records_scraped = raw_data.get('row_count', 0)
        run.completed_at = timezone.now()
        run.save()

        # Update target
        target.last_scraped_at = timezone.now()
        target.total_records_scraped += raw_data.get('row_count', 0)
        target.save()

        logger.info(
            "task.scrape_wikipedia.success",
            url=url,
            rows=raw_data.get('row_count', 0),
            scraped_id=str(scraped.id)
        )
        return {
            'status': 'success',
            'scraped_id': str(scraped.id),
            'rows': raw_data.get('row_count', 0),
        }

    except Exception as exc:
        logger.error("task.scrape_wikipedia.error", url=url, error=str(exc))
        run.status = ScraperRun.Status.FAILED
        run.error_message = str(exc)
        run.completed_at = timezone.now()
        run.save()
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def scrape_hacker_news_task(self):
    """
    Celery task: Scrape Hacker News top stories.
    Used as API testing fixtures (real titles, real URLs, real data).
    """
    from apps.scraper.models import ScraperTarget, ScraperRun, ScrapedData
    from apps.scraper.engine import ScraperEngine

    url = 'https://news.ycombinator.com/'
    logger.info("task.scrape_hn.start")

    target, _ = ScraperTarget.objects.get_or_create(
        name='Hacker News Top Stories',
        defaults={
            'url': url,
            'data_type': ScraperTarget.DataType.LIST,
            'requires_js': True,
            'description': 'Real news stories used as API test fixtures',
        }
    )

    run = ScraperRun.objects.create(
        target=target,
        status=ScraperRun.Status.RUNNING,
        started_at=timezone.now(),
        celery_task_id=self.request.id or '',
        triggered_by='celery_beat',
    )

    try:
        with ScraperEngine() as scraper:
            raw_data = scraper.scrape_hacker_news()

        if 'error' in raw_data:
            run.status = ScraperRun.Status.FAILED
            run.error_message = raw_data['error']
            run.completed_at = timezone.now()
            run.save()
            return {'status': 'failed'}

        data_hash = ScraperEngine.compute_hash(raw_data)

        ScrapedData.objects.create(
            target=target,
            scraper_run=run,
            title='Hacker News Stories',
            raw_data=raw_data,
            normalized_data=raw_data.get('stories', []),
            data_hash=data_hash,
            row_count=raw_data.get('row_count', 0),
            source_url=url,
            status=ScrapedData.DataStatus.VALIDATED,
        )

        run.status = ScraperRun.Status.SUCCESS
        run.records_scraped = raw_data.get('row_count', 0)
        run.completed_at = timezone.now()
        run.save()

        logger.info("task.scrape_hn.success", stories=raw_data.get('row_count', 0))
        return {'status': 'success', 'stories': raw_data.get('row_count', 0)}

    except Exception as exc:
        logger.error("task.scrape_hn.error", error=str(exc))
        run.status = ScraperRun.Status.FAILED
        run.error_message = str(exc)
        run.completed_at = timezone.now()
        run.save()
        self.retry(exc=exc)


@shared_task
def scrape_custom_url_task(url: str, data_type: str = 'table', css_selector: str = ''):
    """
    On-demand scraping task — triggered from dashboard UI.
    """
    from apps.scraper.models import ScraperTarget, ScraperRun, ScrapedData
    from apps.scraper.engine import ScraperEngine

    logger.info("task.scrape_custom.start", url=url, data_type=data_type)

    target, _ = ScraperTarget.objects.get_or_create(
        url=url,
        defaults={
            'name': f'Custom: {url[:80]}',
            'data_type': data_type,
            'css_selector': css_selector,
            'requires_js': True,
        }
    )

    run = ScraperRun.objects.create(
        target=target,
        status=ScraperRun.Status.RUNNING,
        started_at=timezone.now(),
        triggered_by='manual',
    )

    try:
        with ScraperEngine() as scraper:
            if data_type == 'table':
                raw_data = scraper.scrape_table(url, css_selector=css_selector or None)
            else:
                raw_data = scraper.scrape_article(url)

        normalized = ScraperEngine.normalize_table_data(raw_data) if data_type == 'table' else raw_data
        data_hash = ScraperEngine.compute_hash(raw_data)

        scraped = ScrapedData.objects.create(
            target=target,
            scraper_run=run,
            title=raw_data.get('title', ''),
            raw_data=raw_data,
            normalized_data=normalized,
            data_hash=data_hash,
            row_count=raw_data.get('row_count', len(normalized) if isinstance(normalized, list) else 1),
            source_url=url,
            status=ScrapedData.DataStatus.VALIDATED,
        )

        run.status = ScraperRun.Status.SUCCESS
        run.completed_at = timezone.now()
        run.save()

        return {'status': 'success', 'scraped_id': str(scraped.id)}

    except Exception as exc:
        run.status = ScraperRun.Status.FAILED
        run.error_message = str(exc)
        run.completed_at = timezone.now()
        run.save()
        return {'status': 'failed', 'error': str(exc)}
