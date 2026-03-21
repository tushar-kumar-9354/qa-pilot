"""
QA-PILOT — E2E Selenium Tests
Tests the full browser UI flows on your running Django app.
Run: pytest tests/e2e/ -v -m e2e
"""
import pytest
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException


BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def driver():
    """Headless Chrome driver fixture for all E2E tests."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    d = webdriver.Chrome(options=options)
    d.implicitly_wait(10)
    yield d
    d.quit()


@pytest.fixture(scope="module")
def wait(driver):
    return WebDriverWait(driver, 15)


# ──────────────────────────────────────────────────────────
# Page Load Tests
# ──────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestPageLoads:

    def test_homepage_loads(self, driver, wait):
        """Dashboard home page must load successfully."""
        driver.get(BASE_URL + "/")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        assert driver.title != ""

    def test_dashboard_has_sidebar(self, driver, wait):
        """Dashboard must have a visible sidebar."""
        driver.get(BASE_URL + "/")
        sidebar = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "sidebar")))
        assert sidebar.is_displayed()

    def test_logo_text_visible(self, driver, wait):
        """QA-Pilot logo must be visible in sidebar."""
        driver.get(BASE_URL + "/")
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "logo-text")))

    def test_admin_login_page_loads(self, driver, wait):
        """Django admin login page must load."""
        driver.get(BASE_URL + "/admin/login/")
        wait.until(EC.presence_of_element_located((By.ID, "id_username")))
        assert "Log in" in driver.title or "Django" in driver.title

    def test_api_docs_loads(self, driver, wait):
        """FastAPI Swagger docs must load."""
        driver.get("http://localhost:8001/docs")
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "swagger-ui")))


# ──────────────────────────────────────────────────────────
# Admin Login Flow
# ──────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestAdminFlow:

    def test_admin_login_with_valid_credentials(self, driver, wait):
        """Admin must be able to log in with correct credentials."""
        driver.get(BASE_URL + "/admin/login/")
        wait.until(EC.presence_of_element_located((By.ID, "id_username")))

        driver.find_element(By.ID, "id_username").send_keys("admin")
        driver.find_element(By.ID, "id_password").send_keys("admin123")
        driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

        wait.until(EC.url_changes(BASE_URL + "/admin/login/"))
        assert "/admin/" in driver.current_url

    def test_admin_shows_app_models(self, driver, wait):
        """After login, admin must show QA-Pilot models."""
        driver.get(BASE_URL + "/admin/")
        body = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        content = body.text.lower()
        # At least one of our apps should be visible
        assert any(word in content for word in ["test", "scraper", "user", "core"])


# ──────────────────────────────────────────────────────────
# Navigation Tests
# ──────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestNavigation:

    def test_all_nav_links_present(self, driver, wait):
        """All sidebar nav items must be present."""
        driver.get(BASE_URL + "/")
        nav_texts = ["Dashboard", "Test Suites", "Test Runs", "Web Scraper", "AI Assistant"]
        body_text = driver.find_element(By.TAG_NAME, "body").text
        for nav_text in nav_texts:
            assert nav_text in body_text, f"Nav item '{nav_text}' not found"

    def test_stat_cards_present(self, driver, wait):
        """Dashboard must display stat cards."""
        driver.get(BASE_URL + "/")
        cards = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "stat-card")))
        assert len(cards) >= 3, "Expected at least 3 stat cards"

    def test_live_badge_visible(self, driver, wait):
        """Live badge must be visible in topbar."""
        driver.get(BASE_URL + "/")
        badge = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "live-badge")))
        assert badge.is_displayed()
        assert "LIVE" in badge.text
