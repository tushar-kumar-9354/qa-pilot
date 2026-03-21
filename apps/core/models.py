"""
QA-PILOT — Core Models
User, TestSuite, TestCase, TestRun, BugReport
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import structlog

logger = structlog.get_logger(__name__)


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ── User ─────────────────────────────────────────────────────
class User(AbstractUser, TimeStampedModel):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        QA_ENGINEER = 'qa_engineer', 'QA Engineer'
        VIEWER = 'viewer', 'Viewer'

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.QA_ENGINEER)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_qa_engineer(self):
        return self.role in [self.Role.ADMIN, self.Role.QA_ENGINEER]


# ── TestSuite ────────────────────────────────────────────────
class TestSuite(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        ARCHIVED = 'archived', 'Archived'
        DRAFT = 'draft', 'Draft'

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='test_suites')
    tags = models.JSONField(default=list, blank=True)
    target_url = models.URLField(blank=True, help_text="URL to test against")

    class Meta:
        db_table = 'test_suites'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def total_cases(self):
        return self.test_cases.count()

    @property
    def pass_rate(self):
        runs = self.test_runs.filter(status=TestRun.Status.COMPLETED)
        if not runs.exists():
            return 0
        passed = runs.filter(result=TestRun.Result.PASSED).count()
        return round((passed / runs.count()) * 100, 1)


# ── TestCase ─────────────────────────────────────────────────
class TestCase(TimeStampedModel):
    class Type(models.TextChoices):
        UNIT = 'unit', 'Unit Test'
        INTEGRATION = 'integration', 'Integration Test'
        E2E = 'e2e', 'End-to-End Test'
        API = 'api', 'API Test'
        PERFORMANCE = 'performance', 'Performance Test'

    class Priority(models.TextChoices):
        CRITICAL = 'critical', 'Critical'
        HIGH = 'high', 'High'
        MEDIUM = 'medium', 'Medium'
        LOW = 'low', 'Low'

    suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE, related_name='test_cases')
    name = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    test_type = models.CharField(max_length=20, choices=Type.choices, default=Type.UNIT)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    code = models.TextField(help_text="Actual pytest test code")
    expected_result = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    is_ai_generated = models.BooleanField(default=False)
    source_scraped_data = models.ForeignKey(
        'scraper.ScrapedData', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Scraped data used to generate this test"
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_test_cases')

    class Meta:
        db_table = 'test_cases'
        ordering = ['priority', 'name']

    def __str__(self):
        return f"[{self.test_type}] {self.name}"


# ── TestRun ──────────────────────────────────────────────────
class TestRun(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    class Result(models.TextChoices):
        PASSED = 'passed', 'Passed'
        FAILED = 'failed', 'Failed'
        ERROR = 'error', 'Error'
        SKIPPED = 'skipped', 'Skipped'

    suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE, related_name='test_runs')
    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='triggered_runs')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    result = models.CharField(max_length=20, choices=Result.choices, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_tests = models.IntegerField(default=0)
    passed = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    errors = models.IntegerField(default=0)
    skipped = models.IntegerField(default=0)
    logs = models.TextField(blank=True)
    report_html = models.TextField(blank=True)
    environment = models.CharField(max_length=50, default='development')
    celery_task_id = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'test_runs'
        ordering = ['-created_at']

    def __str__(self):
        return f"Run #{str(self.id)[:8]} — {self.suite.name} ({self.status})"

    @property
    def duration_seconds(self):
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def pass_rate(self):
        if self.total_tests == 0:
            return 0
        return round((self.passed / self.total_tests) * 100, 1)

    def mark_started(self):
        self.status = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
        logger.info("test_run.started", run_id=str(self.id), suite=self.suite.name)

    def mark_completed(self, passed, failed, errors, skipped, logs=""):
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.passed = passed
        self.failed = failed
        self.errors = errors
        self.skipped = skipped
        self.total_tests = passed + failed + errors + skipped
        self.logs = logs
        self.result = self.Result.PASSED if failed == 0 and errors == 0 else self.Result.FAILED
        self.save()
        logger.info("test_run.completed", run_id=str(self.id), result=self.result, pass_rate=self.pass_rate)


# ── BugReport ────────────────────────────────────────────────
class BugReport(TimeStampedModel):
    class Severity(models.TextChoices):
        BLOCKER = 'blocker', 'Blocker'
        CRITICAL = 'critical', 'Critical'
        MAJOR = 'major', 'Major'
        MINOR = 'minor', 'Minor'
        TRIVIAL = 'trivial', 'Trivial'

    class BugStatus(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In Progress'
        RESOLVED = 'resolved', 'Resolved'
        WONT_FIX = 'wont_fix', "Won't Fix"

    test_run = models.ForeignKey(TestRun, on_delete=models.CASCADE, related_name='bug_reports')
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='bug_reports', null=True)
    title = models.CharField(max_length=500)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MAJOR)
    status = models.CharField(max_length=20, choices=BugStatus.choices, default=BugStatus.OPEN)
    stack_trace = models.TextField(blank=True)
    ai_analysis = models.TextField(blank=True, help_text="AI-generated root cause analysis")
    ai_fix_suggestion = models.TextField(blank=True, help_text="AI-generated fix suggestion")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    screenshot_path = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = 'bug_reports'
        ordering = ['severity', '-created_at']

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title}"
