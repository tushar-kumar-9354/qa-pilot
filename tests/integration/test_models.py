"""
QA-PILOT — Unit Tests for Core Models
Tests: User, TestSuite, TestCase, TestRun, BugReport

Run with:
    python manage.py test apps.core.tests
or:
    pytest apps/core/tests/test_core_models.py -v
"""
import uuid
from django.test import TestCase
from django.utils import timezone
from apps.core.models import User, TestSuite, TestCase as TC, TestRun, BugReport


# ── Helpers ───────────────────────────────────────────────────

def make_user(email="qa@example.com", role=User.Role.QA_ENGINEER):
    return User.objects.create_user(
        username=email.split("@")[0],
        email=email,
        password="TestPass123!",
        role=role,
    )

def make_suite(owner=None, name="Login Suite", status=TestSuite.Status.ACTIVE):
    return TestSuite.objects.create(
        name=name,
        description="Tests for login flow",
        status=status,
        owner=owner,
        tags=["auth", "smoke"],
        target_url="https://example.com",
    )

def make_test_case(suite, name="test_login_passes", priority=TC.Priority.HIGH):
    return TC.objects.create(
        suite=suite,
        name=name,
        test_type=TC.Type.UNIT,
        priority=priority,
        code="def test_login_passes():\n    assert 1 + 1 == 2\n",
        expected_result="Test passes without errors",
    )

def make_run(suite, status=TestRun.Status.PENDING):
    return TestRun.objects.create(
        suite=suite,
        status=status,
        environment="development",
    )


# ═══════════════════════════════════════════════════════════════
# 1. User model — role helpers
# ═══════════════════════════════════════════════════════════════
class UserRoleTest(TestCase):
    """TC-01: is_admin and is_qa_engineer properties work correctly."""

    def test_admin_role_flags(self):
        """Admin user has both is_admin and is_qa_engineer True."""
        admin = make_user("admin@qa.com", role=User.Role.ADMIN)
        self.assertTrue(admin.is_admin)
        self.assertTrue(admin.is_qa_engineer)

    def test_qa_engineer_role_flags(self):
        """QA Engineer is NOT admin but IS qa_engineer."""
        eng = make_user("eng@qa.com", role=User.Role.QA_ENGINEER)
        self.assertFalse(eng.is_admin)
        self.assertTrue(eng.is_qa_engineer)

    def test_viewer_role_flags(self):
        """Viewer is neither admin nor qa_engineer."""
        viewer = make_user("view@qa.com", role=User.Role.VIEWER)
        self.assertFalse(viewer.is_admin)
        self.assertFalse(viewer.is_qa_engineer)


# ═══════════════════════════════════════════════════════════════
# 2. User model — email as USERNAME_FIELD
# ═══════════════════════════════════════════════════════════════
class UserEmailTest(TestCase):
    """TC-02: User authenticates by email, not username."""

    def test_email_is_unique(self):
        """Creating two users with the same email raises IntegrityError."""
        from django.db import IntegrityError
        make_user("dup@qa.com")
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username="dup2",
                email="dup@qa.com",
                password="pass",
            )

    def test_str_representation(self):
        """__str__ includes email and role."""
        user = make_user("str@qa.com", role=User.Role.ADMIN)
        self.assertIn("str@qa.com", str(user))
        self.assertIn("admin", str(user))


# ═══════════════════════════════════════════════════════════════
# 3. TestSuite — total_cases property
# ═══════════════════════════════════════════════════════════════
class TestSuiteTotalCasesTest(TestCase):
    """TC-03: total_cases counts related TestCase objects correctly."""

    def test_empty_suite_has_zero_cases(self):
        """A brand-new suite with no cases returns 0."""
        suite = make_suite()
        self.assertEqual(suite.total_cases, 0)

    def test_total_cases_increments_on_add(self):
        """Adding cases increases total_cases."""
        suite = make_suite()
        make_test_case(suite, "test_a")
        make_test_case(suite, "test_b")
        make_test_case(suite, "test_c")
        self.assertEqual(suite.total_cases, 3)


# ═══════════════════════════════════════════════════════════════
# 4. TestSuite — pass_rate property
# ═══════════════════════════════════════════════════════════════
class TestSuitePassRateTest(TestCase):
    """TC-04: pass_rate calculates correctly from completed runs."""

    def setUp(self):
        self.suite = make_suite()

    def test_pass_rate_no_runs_returns_zero(self):
        """Suite with no completed runs returns pass_rate of 0."""
        self.assertEqual(self.suite.pass_rate, 0)

    def test_pass_rate_all_passed(self):
        """Suite where all completed runs passed returns 100.0."""
        for _ in range(3):
            run = make_run(self.suite)
            run.mark_completed(5, 0, 0, 0)
        self.assertEqual(self.suite.pass_rate, 100.0)

    def test_pass_rate_mixed_results(self):
        """Suite with 1 passed and 1 failed run returns 50.0."""
        run1 = make_run(self.suite)
        run1.mark_completed(5, 0, 0, 0)   # passed
        run2 = make_run(self.suite)
        run2.mark_completed(3, 2, 0, 0)   # failed
        self.assertEqual(self.suite.pass_rate, 50.0)


# ═══════════════════════════════════════════════════════════════
# 5. TestCase — default field values
# ═══════════════════════════════════════════════════════════════
class TestCaseDefaultsTest(TestCase):
    """TC-05: TestCase defaults are set correctly on creation."""

    def test_is_ai_generated_defaults_false(self):
        """New test cases are not AI-generated by default."""
        suite = make_suite()
        tc = make_test_case(suite)
        self.assertFalse(tc.is_ai_generated)

    def test_tags_default_to_empty_list(self):
        """Tags field defaults to an empty list."""
        suite = make_suite()
        tc = make_test_case(suite)
        self.assertEqual(tc.tags, [])

    def test_str_representation(self):
        """__str__ includes test type and name."""
        suite = make_suite()
        tc = make_test_case(suite, "test_checkout_flow")
        self.assertIn("unit", str(tc))
        self.assertIn("test_checkout_flow", str(tc))


# ═══════════════════════════════════════════════════════════════
# 6. TestRun — mark_started
# ═══════════════════════════════════════════════════════════════
class TestRunMarkStartedTest(TestCase):
    """TC-06: mark_started sets status to RUNNING and stamps started_at."""

    def test_mark_started_sets_status_and_timestamp(self):
        """After mark_started, status is RUNNING and started_at is set."""
        suite = make_suite()
        run = make_run(suite)
        self.assertIsNone(run.started_at)
        run.mark_started()
        run.refresh_from_db()
        self.assertEqual(run.status, TestRun.Status.RUNNING)
        self.assertIsNotNone(run.started_at)


# ═══════════════════════════════════════════════════════════════
# 7. TestRun — mark_completed
# ═══════════════════════════════════════════════════════════════
class TestRunMarkCompletedTest(TestCase):
    """TC-07: mark_completed records counts and determines result correctly."""

    def setUp(self):
        self.suite = make_suite()
        self.run = make_run(self.suite)

    def test_all_passed_result_is_passed(self):
        """Run with 0 failures and 0 errors gets result PASSED."""
        self.run.mark_completed(10, 0, 0, 0)
        self.assertEqual(self.run.result, TestRun.Result.PASSED)
        self.assertEqual(self.run.total_tests, 10)

    def test_any_failure_result_is_failed(self):
        """Run with 1+ failures gets result FAILED."""
        self.run.mark_completed(8, 2, 0, 0)
        self.assertEqual(self.run.result, TestRun.Result.FAILED)

    def test_any_error_result_is_failed(self):
        """Run with 1+ errors gets result FAILED."""
        self.run.mark_completed(9, 0, 1, 0)
        self.assertEqual(self.run.result, TestRun.Result.FAILED)

    def test_total_tests_is_sum_of_all(self):
        """total_tests = passed + failed + errors + skipped."""
        self.run.mark_completed(3, 2, 1, 4)
        self.assertEqual(self.run.total_tests, 10)


# ═══════════════════════════════════════════════════════════════
# 8. TestRun — pass_rate property
# ═══════════════════════════════════════════════════════════════
class TestRunPassRateTest(TestCase):
    """TC-08: TestRun.pass_rate calculates correctly."""

    def setUp(self):
        self.suite = make_suite()

    def test_pass_rate_zero_when_no_tests(self):
        """pass_rate is 0 when total_tests is 0."""
        run = make_run(self.suite)
        self.assertEqual(run.pass_rate, 0)

    def test_pass_rate_correct_percentage(self):
        """pass_rate = (passed / total) * 100, rounded to 1 decimal."""
        run = make_run(self.suite)
        run.mark_completed(7, 3, 0, 0)  # 7/10 = 70.0
        self.assertEqual(run.pass_rate, 70.0)


# ═══════════════════════════════════════════════════════════════
# 9. TestRun — duration_seconds property
# ═══════════════════════════════════════════════════════════════
class TestRunDurationTest(TestCase):
    """TC-09: duration_seconds returns None until run completes."""

    def test_duration_none_before_completion(self):
        """duration_seconds is None when started_at or completed_at is missing."""
        suite = make_suite()
        run = make_run(suite)
        self.assertIsNone(run.duration_seconds)

    def test_duration_positive_after_completion(self):
        """duration_seconds is a positive number after mark_completed."""
        suite = make_suite()
        run = make_run(suite)
        run.mark_started()
        run.mark_completed(5, 0, 0, 0)
        self.assertIsNotNone(run.duration_seconds)
        self.assertGreaterEqual(run.duration_seconds, 0)


# ═══════════════════════════════════════════════════════════════
# 10. BugReport — cascade delete with TestRun
# ═══════════════════════════════════════════════════════════════
class BugReportCascadeTest(TestCase):
    """TC-10: Deleting a TestRun cascades and deletes its BugReports."""

    def test_bug_report_deleted_when_run_deleted(self):
        """BugReport is removed from DB when its TestRun is deleted."""
        user = make_user()
        suite = make_suite(owner=user)
        run = make_run(suite)
        tc = make_test_case(suite)

        bug = BugReport.objects.create(
            test_run=run,
            test_case=tc,
            title="Login button missing",
            description="The login button is not rendered on /login.",
            severity=BugReport.Severity.CRITICAL,
        )
        bug_id = bug.id

        run.delete()
        self.assertFalse(BugReport.objects.filter(id=bug_id).exists())