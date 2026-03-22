"""
QA-PILOT — Integration Tests
Tests DB models + Django ORM pipeline.
Run: pytest tests/integration/ -v -m integration
"""
import pytest


@pytest.mark.django_db
@pytest.mark.integration
class TestUserModel:

    def test_create_user(self, django_user_model):
        """User can be created in DB."""
        user = django_user_model.objects.create_user(
            username='testqa',
            email='testqa@example.com',
            password='testpass123',
        )
        assert user.pk is not None
        assert user.email == 'testqa@example.com'

    def test_user_role_default(self, django_user_model):
        """Default role must be qa_engineer."""
        user = django_user_model.objects.create_user(
            username='testqa2',
            email='testqa2@example.com',
            password='testpass123',
        )
        assert user.role == 'qa_engineer'

    def test_superuser_is_admin(self, django_user_model):
        """Superuser must have staff access."""
        admin = django_user_model.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
        )
        assert admin.is_staff
        assert admin.is_superuser


@pytest.mark.django_db
@pytest.mark.integration
class TestTestSuiteModel:

    def test_create_test_suite(self, django_user_model):
        """TestSuite can be created and saved to DB."""
        from apps.core.models import TestSuite
        user = django_user_model.objects.create_user(
            username='qa_user', email='qa@test.com', password='pass123'
        )
        suite = TestSuite.objects.create(
            name='Integration Test Suite',
            description='Tests the DB pipeline',
            status=TestSuite.Status.ACTIVE,
            owner=user,
        )
        assert suite.pk is not None
        assert suite.name == 'Integration Test Suite'
        assert suite.status == 'active'

    def test_suite_total_cases_zero_initially(self, django_user_model):
        """New suite must have 0 test cases."""
        from apps.core.models import TestSuite
        suite = TestSuite.objects.create(name='Empty Suite', status='active')
        assert suite.total_cases == 0

    def test_suite_pass_rate_zero_with_no_runs(self, django_user_model):
        """Suite with no runs must have 0% pass rate."""
        from apps.core.models import TestSuite
        suite = TestSuite.objects.create(name='No Runs Suite', status='active')
        assert suite.pass_rate == 0


@pytest.mark.django_db
@pytest.mark.integration
class TestTestCaseModel:

    def test_create_test_case(self):
        """TestCase can be created and linked to a suite."""
        from apps.core.models import TestSuite, TestCase
        suite = TestSuite.objects.create(name='Suite A', status='active')
        tc = TestCase.objects.create(
            suite=suite,
            name='test_login_valid',
            test_type=TestCase.Type.UNIT,
            priority=TestCase.Priority.HIGH,
            code='def test_login_valid():\n    assert True',
        )
        assert tc.pk is not None
        assert tc.suite == suite
        assert tc.test_type == 'unit'

    def test_suite_total_cases_updates(self):
        """suite.total_cases must count correctly."""
        from apps.core.models import TestSuite, TestCase
        suite = TestSuite.objects.create(name='Suite B', status='active')
        TestCase.objects.create(suite=suite, name='test_1', test_type='unit', code='def test_1(): pass')
        TestCase.objects.create(suite=suite, name='test_2', test_type='api', code='def test_2(): pass')
        assert suite.total_cases == 2


@pytest.mark.django_db
@pytest.mark.integration
class TestScrapedDataModel:

    def test_create_scraper_target(self):
        """ScraperTarget can be created in DB."""
        from apps.scraper.models import ScraperTarget
        target = ScraperTarget.objects.create(
            name='Wikipedia Countries',
            url='https://en.wikipedia.org/wiki/List_of_countries',
            data_type=ScraperTarget.DataType.TABLE,
        )
        assert target.pk is not None
        assert target.is_active is True

    def test_create_scraped_data(self):
        """ScrapedData can be saved with normalized data."""
        from apps.scraper.models import ScraperTarget, ScrapedData
        target = ScraperTarget.objects.create(
            name='Test Target',
            url='https://example.com',
            data_type='table',
        )
        scraped = ScrapedData.objects.create(
            target=target,
            title='Test Data',
            raw_data={'rows': [{'country': 'India', 'population': 1428627663}]},
            normalized_data=[{'country': 'India', 'population': 1428627663}],
            data_hash='abc123',
            row_count=1,
            source_url='https://example.com',
        )
        assert scraped.pk is not None
        assert scraped.row_count == 1
        assert scraped.as_pytest_fixtures() == [{'country': 'India', 'population': 1428627663}]