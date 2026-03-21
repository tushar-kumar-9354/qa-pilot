"""
QA-PILOT — Test Runner Celery Tasks
Executes pytest programmatically and streams results.
"""
import subprocess
import tempfile
import os
from celery import shared_task
from django.utils import timezone
import structlog

logger = structlog.get_logger(__name__)


@shared_task(bind=True, max_retries=1)
def execute_test_suite_task(self, run_id: str):
    """
    Execute a test suite using pytest subprocess.
    Streams output and updates TestRun record in real time.
    """
    from apps.core.models import TestRun, BugReport

    try:
        run = TestRun.objects.select_related('suite').get(id=run_id)
    except TestRun.DoesNotExist:
        logger.error("task.execute_tests.run_not_found", run_id=run_id)
        return

    run.mark_started()
    logs = []

    try:
        # Write test code to temp file
        test_cases = run.suite.test_cases.all()
        if not test_cases.exists():
            run.mark_completed(0, 0, 0, 0, "No test cases in suite.")
            return

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='_test.py', prefix='qa_pilot_',
            dir='/tmp', delete=False
        ) as f:
            f.write("import pytest\n\n")
            for tc in test_cases:
                if tc.code:
                    f.write(f"# Test: {tc.name}\n")
                    f.write(tc.code)
                    f.write("\n\n")
            temp_path = f.name

        logs.append(f"[{timezone.now().isoformat()}] Running test suite: {run.suite.name}")
        logs.append(f"[{timezone.now().isoformat()}] Test file: {temp_path}")
        logs.append(f"[{timezone.now().isoformat()}] Cases: {test_cases.count()}")

        # Execute pytest
        result = subprocess.run(
            ["python", "-m", "pytest", temp_path, "-v", "--tb=short", "--no-header", "-q"],
            capture_output=True,
            text=True,
            timeout=300,
        )

        output = result.stdout + result.stderr
        logs.append(output)

        # Parse results
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        errors = output.count(" ERROR")
        skipped = output.count(" SKIPPED")

        full_log = "\n".join(logs)
        run.mark_completed(passed, failed, errors, skipped, full_log)

        # Create bug reports for failures
        if failed > 0 or errors > 0:
            BugReport.objects.create(
                test_run=run,
                title=f"{failed} test(s) failed in {run.suite.name}",
                description=f"Automatic bug report from test run #{str(run.id)[:8]}",
                severity=BugReport.Severity.CRITICAL if errors > 0 else BugReport.Severity.MAJOR,
                stack_trace=output[-3000:],
            )

        os.unlink(temp_path)

        logger.info(
            "task.execute_tests.done",
            run_id=run_id,
            passed=passed,
            failed=failed,
        )
        return {"passed": passed, "failed": failed, "errors": errors, "skipped": skipped}

    except subprocess.TimeoutExpired:
        run.status = TestRun.Status.FAILED
        run.logs = "Test execution timed out (300s)"
        run.save()
        logger.error("task.execute_tests.timeout", run_id=run_id)

    except Exception as exc:
        run.status = TestRun.Status.FAILED
        run.logs = str(exc)
        run.completed_at = timezone.now()
        run.save()
        logger.error("task.execute_tests.error", run_id=run_id, error=str(exc))
        self.retry(exc=exc)


@shared_task
def run_scheduled_suites():
    """Nightly task: run all active suites."""
    from apps.core.models import TestSuite, TestRun

    suites = TestSuite.objects.filter(status='active')
    triggered = []
    for suite in suites:
        run = TestRun.objects.create(
            suite=suite,
            status=TestRun.Status.PENDING,
            environment='production',
        )
        task = execute_test_suite_task.delay(str(run.id))
        run.celery_task_id = task.id
        run.save(update_fields=['celery_task_id'])
        triggered.append(str(run.id))

    logger.info("task.nightly_run.triggered", count=len(triggered))
    return {"triggered": triggered}
