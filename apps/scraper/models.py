"""
QA-PILOT — Scraper Models
ScraperTarget, ScrapedData, ScraperRun
"""
import uuid
from django.db import models
import structlog

logger = structlog.get_logger(__name__)


class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ScraperTarget(TimeStampedModel):
    """Defines a URL target with scraping configuration."""
    class DataType(models.TextChoices):
        TABLE = 'table', 'HTML Table'
        LIST = 'list', 'HTML List'
        FORM = 'form', 'HTML Form'
        ARTICLE = 'article', 'Article Content'
        API = 'api', 'JSON API'
        CUSTOM = 'custom', 'Custom Selector'

    name = models.CharField(max_length=255, unique=True)
    url = models.URLField(max_length=2000)
    data_type = models.CharField(max_length=20, choices=DataType.choices, default=DataType.TABLE)
    css_selector = models.CharField(max_length=500, blank=True, help_text="CSS selector for target element")
    xpath_selector = models.CharField(max_length=500, blank=True, help_text="XPath for target element")
    is_active = models.BooleanField(default=True)
    requires_js = models.BooleanField(default=True, help_text="Use Selenium (True) or requests (False)")
    description = models.TextField(blank=True, help_text="What data this target provides for testing")
    last_scraped_at = models.DateTimeField(null=True, blank=True)
    total_records_scraped = models.IntegerField(default=0)

    class Meta:
        db_table = 'scraper_targets'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.url[:50]}...)"


class ScraperRun(TimeStampedModel):
    """Tracks each individual scraping run."""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        PARTIAL = 'partial', 'Partial Success'

    target = models.ForeignKey(ScraperTarget, on_delete=models.CASCADE, related_name='runs')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    started_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    records_scraped = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True)
    triggered_by = models.CharField(max_length=100, default='scheduler')

    class Meta:
        db_table = 'scraper_runs'
        ordering = ['-created_at']

    def __str__(self):
        return f"Run for {self.target.name} — {self.status}"

    @property
    def duration_seconds(self):
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class ScrapedData(TimeStampedModel):
    """
    Stores normalized data scraped from targets.
    This data is used as test fixtures across all testing types.
    """
    class DataStatus(models.TextChoices):
        RAW = 'raw', 'Raw'
        VALIDATED = 'validated', 'Validated'
        USED_IN_TESTS = 'used_in_tests', 'Used in Tests'
        STALE = 'stale', 'Stale'

    target = models.ForeignKey(ScraperTarget, on_delete=models.CASCADE, related_name='scraped_data')
    scraper_run = models.ForeignKey(ScraperRun, on_delete=models.CASCADE, related_name='scraped_records', null=True)
    title = models.CharField(max_length=500, blank=True)
    raw_data = models.JSONField(help_text="Raw scraped data as JSON")
    normalized_data = models.JSONField(null=True, blank=True, help_text="Cleaned/normalized version")
    data_hash = models.CharField(max_length=64, blank=True, help_text="SHA256 hash to detect duplicates")
    status = models.CharField(max_length=20, choices=DataStatus.choices, default=DataStatus.RAW)
    row_count = models.IntegerField(default=0)
    column_count = models.IntegerField(default=0)
    source_url = models.URLField(max_length=2000, blank=True)

    class Meta:
        db_table = 'scraped_data'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['data_hash']),
            models.Index(fields=['target', 'status']),
        ]

    def __str__(self):
        return f"{self.title or 'Scraped'} from {self.target.name} ({self.row_count} rows)"

    def as_pytest_fixtures(self):
        """
        Returns scraped data formatted as pytest parametrize args.
        Use this to drive test cases with real-world data.
        """
        if not self.normalized_data:
            return []
        if isinstance(self.normalized_data, list):
            return self.normalized_data
        return [self.normalized_data]
