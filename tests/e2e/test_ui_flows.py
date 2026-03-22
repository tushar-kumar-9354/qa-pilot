"""
QA-PILOT — E2E Tests (Selenium + Chrome headless)
Tests full browser UI flows against running Django server.
Run: pytest tests/e2e/ -v -m e2e
"""
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def driver():
    """Headless Chrome driver for all E2E tests."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # Try system chromedriver first (CI), then fallback
    try:
        service = Service('/usr/bin/chromedriver')
        d = webdriver.Chrome(service=service, options=options)
    except Exception:
        d = webdriver.Chrome(options=options)

    d.implicitly_wait(10)
    yield d
    d.quit()


@pytest.fixture
def wait(driver):
    return WebDriverWait(driver, 15)


@pytest.mark.e2e
class TestPageLoads:

    def test_homepage_loads(self, driver, wait):
        """Dashboard home page must load with 200."""
        driver.get(BASE_URL + "/")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        assert driver.title != ""

    def test_dashboard_has_sidebar(self, driver, wait):
        """Dashboard must have a visible sidebar."""
        driver.get(BASE_URL + "/")
        sidebar = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "sidebar")))
        assert sidebar.is_displayed()

    def test_logo_visible(self, driver, wait):
        """QA-Pilot logo must be visible."""
        driver.get(BASE_URL + "/")
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "logo-text")))

    def test_stat_cards_present(self, driver, wait):
        """At least 3 stat cards must be visible."""
        driver.get(BASE_URL + "/")
        cards = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "stat-card")))
        assert len(cards) >= 3

    def test_live_badge_visible(self, driver, wait):
        """LIVE badge must be visible in topbar."""
        driver.get(BASE_URL + "/")
        badge = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "live-badge")))
        assert "LIVE" in badge.text


@pytest.mark.e2e
class TestNavigation:

    def test_suites_page_loads(self, driver, wait):
        """Test Suites page must load."""
        driver.get(BASE_URL + "/suites/")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        assert driver.current_url.endswith("/suites/")

    def test_runs_page_loads(self, driver, wait):
        """Test Runs page must load."""
        driver.get(BASE_URL + "/runs/")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        assert driver.current_url.endswith("/runs/")

    def test_scraper_page_loads(self, driver, wait):
        """Scraper page must load."""
        driver.get(BASE_URL + "/scraper/")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        assert driver.current_url.endswith("/scraper/")

    def test_ai_chat_page_loads(self, driver, wait):
        """AI Chat page must load."""
        driver.get(BASE_URL + "/agents/chat/")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        assert driver.current_url.endswith("/agents/chat/")


@pytest.mark.e2e
class TestAdminPanel:

    def test_admin_login_page_loads(self, driver, wait):
        """Django admin login page must load."""
        driver.get(BASE_URL + "/admin/login/")
        wait.until(EC.presence_of_element_located((By.ID, "id_username")))
        assert "login" in driver.current_url.lower()

    def test_admin_has_username_field(self, driver, wait):
        """Admin login must have username input."""
        driver.get(BASE_URL + "/admin/login/")
        field = wait.until(EC.presence_of_element_located((By.ID, "id_username")))
        assert field.is_displayed()

    def test_admin_has_password_field(self, driver, wait):
        """Admin login must have password input."""
        driver.get(BASE_URL + "/admin/login/")
        field = wait.until(EC.presence_of_element_located((By.ID, "id_password")))
        assert field.is_displayed()