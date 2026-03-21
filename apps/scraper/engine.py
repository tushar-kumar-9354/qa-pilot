"""
QA-PILOT — Selenium Web Scraper Engine
Scrapes real-world data from websites and stores as test fixtures.
"""
import time
import random
import hashlib
import json
from typing import Optional
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import pandas as pd
import structlog

from django.conf import settings

logger = structlog.get_logger(__name__)


class ScraperEngine:
    """
    Production-grade Selenium scraper with:
    - Headless Chrome
    - Anti-bot measures (rotating UA, random delays)
    - Retry logic
    - Multiple extraction strategies (table, list, article, custom)
    """

    def __init__(self):
        self.config = settings.SCRAPER_CONFIG
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None

    def _build_driver(self) -> webdriver.Chrome:
        """Build Chrome driver with production options."""
        ua = UserAgent()
        options = Options()

        if self.config['HEADLESS']:
            options.add_argument('--headless=new')

        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(f'--user-agent={ua.random}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')

        try:
            service = Service('/usr/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=options)
        except Exception:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

        # Remove automation detection signals
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": ua.random})
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        return driver

    def __enter__(self):
        self.driver = self._build_driver()
        self.wait = WebDriverWait(self.driver, self.config['TIMEOUT'])
        logger.info("scraper.driver_started")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()
            logger.info("scraper.driver_stopped")

    def _random_delay(self):
        """Human-like random delay between actions."""
        delay = random.uniform(self.config['DELAY_MIN'], self.config['DELAY_MAX'])
        time.sleep(delay)

    def _navigate(self, url: str) -> bool:
        """Navigate to URL with retry logic."""
        for attempt in range(self.config['MAX_RETRIES']):
            try:
                self.driver.get(url)
                self._random_delay()
                logger.info("scraper.navigated", url=url, attempt=attempt + 1)
                return True
            except WebDriverException as e:
                logger.warning("scraper.navigation_failed", url=url, attempt=attempt + 1, error=str(e))
                if attempt < self.config['MAX_RETRIES'] - 1:
                    time.sleep(2 ** attempt)
        return False

    def scrape_table(self, url: str, table_index: int = 0, css_selector: str = None) -> dict:
        """
        Extract HTML tables as structured data.
        Perfect for: Wikipedia data, government stats, sports tables.
        Returns data usable as pytest parametrize fixtures.
        """
        if not self._navigate(url):
            return {'error': 'Failed to navigate', 'url': url}

        try:
            # Wait for tables to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'table')))
            self._random_delay()

            soup = BeautifulSoup(self.driver.page_source, 'lxml')

            if css_selector:
                tables = soup.select(css_selector)
            else:
                tables = soup.find_all('table', class_=lambda x: x and 'wikitable' in x) or soup.find_all('table')

            if not tables or table_index >= len(tables):
                return {'error': 'No tables found', 'url': url}

            table = tables[table_index]
            rows = []
            headers = []

            # Extract headers
            header_row = table.find('tr')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]

            # Extract data rows
            for tr in table.find_all('tr')[1:]:
                cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if cells and len(cells) == len(headers):
                    rows.append(dict(zip(headers, cells)))

            result = {
                'url': url,
                'scraped_at': datetime.utcnow().isoformat(),
                'headers': headers,
                'rows': rows,
                'row_count': len(rows),
                'column_count': len(headers),
                'title': soup.find('title').get_text(strip=True) if soup.find('title') else '',
            }

            logger.info("scraper.table_extracted", url=url, rows=len(rows), columns=len(headers))
            return result

        except TimeoutException:
            logger.error("scraper.timeout", url=url)
            return {'error': 'Timeout waiting for table', 'url': url}
        except Exception as e:
            logger.error("scraper.table_error", url=url, error=str(e))
            return {'error': str(e), 'url': url}

    def scrape_article(self, url: str) -> dict:
        """
        Extract article content (title, text, links, metadata).
        Good for: Hacker News, news sites, documentation pages.
        """
        if not self._navigate(url):
            return {'error': 'Failed to navigate', 'url': url}

        try:
            soup = BeautifulSoup(self.driver.page_source, 'lxml')

            title = soup.find('title')
            h1 = soup.find('h1')
            paragraphs = soup.find_all('p')
            links = soup.find_all('a', href=True)

            result = {
                'url': url,
                'scraped_at': datetime.utcnow().isoformat(),
                'title': (h1 or title).get_text(strip=True) if (h1 or title) else '',
                'meta_title': title.get_text(strip=True) if title else '',
                'paragraphs': [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)],
                'links': [
                    {'text': a.get_text(strip=True), 'href': a['href']}
                    for a in links[:50]
                ],
                'word_count': sum(len(p.get_text().split()) for p in paragraphs),
            }

            logger.info("scraper.article_extracted", url=url, word_count=result['word_count'])
            return result

        except Exception as e:
            logger.error("scraper.article_error", url=url, error=str(e))
            return {'error': str(e), 'url': url}

    def scrape_hacker_news(self) -> dict:
        """
        Scrape Hacker News top stories.
        Provides real structured data for API testing fixtures.
        """
        url = 'https://news.ycombinator.com/'
        if not self._navigate(url):
            return {'error': 'Failed to reach Hacker News', 'url': url}

        try:
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'athing')))
            soup = BeautifulSoup(self.driver.page_source, 'lxml')

            stories = []
            items = soup.find_all('tr', class_='athing')

            for item in items[:30]:
                title_cell = item.find('td', class_='title')
                if not title_cell:
                    continue

                anchor = title_cell.find('a', class_='storylink') or title_cell.find('a')
                if not anchor:
                    continue

                # Get subtext (score, author, time)
                subtext_row = item.find_next_sibling('tr')
                score = ''
                author = ''
                if subtext_row:
                    score_el = subtext_row.find('span', class_='score')
                    author_el = subtext_row.find('a', class_='hnuser')
                    score = score_el.get_text(strip=True) if score_el else '0 points'
                    author = author_el.get_text(strip=True) if author_el else 'unknown'

                stories.append({
                    'id': item.get('id', ''),
                    'title': anchor.get_text(strip=True),
                    'url': anchor.get('href', ''),
                    'score': score,
                    'author': author,
                })

            result = {
                'url': url,
                'scraped_at': datetime.utcnow().isoformat(),
                'stories': stories,
                'row_count': len(stories),
                'title': 'Hacker News Top Stories',
            }

            logger.info("scraper.hn_extracted", stories=len(stories))
            return result

        except Exception as e:
            logger.error("scraper.hn_error", error=str(e))
            return {'error': str(e), 'url': url}

    @staticmethod
    def compute_hash(data: dict) -> str:
        """SHA256 hash to detect duplicate scraped data."""
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def normalize_table_data(raw_data: dict) -> list:
        """
        Clean and normalize scraped table data.
        Strips whitespace, handles numeric strings, removes empty rows.
        """
        rows = raw_data.get('rows', [])
        normalized = []

        for row in rows:
            clean_row = {}
            for key, value in row.items():
                clean_key = key.strip().lower().replace(' ', '_').replace('.', '').replace(',', '')
                clean_value = value.strip() if isinstance(value, str) else value
                # Try to convert numeric strings
                if clean_value:
                    try:
                        clean_value = int(clean_value.replace(',', '').replace('%', ''))
                    except ValueError:
                        try:
                            clean_value = float(clean_value.replace(',', ''))
                        except ValueError:
                            pass
                clean_row[clean_key] = clean_value

            if any(v for v in clean_row.values()):
                normalized.append(clean_row)

        return normalized
