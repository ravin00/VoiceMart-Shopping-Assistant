import requests
import logging
import time
import random
import os
from bs4 import BeautifulSoup
import json

logger = logging.getLogger('base_scraper')

class BaseScraper:
    """Base class for web scrapers"""
    
    def __init__(self, use_selenium=False, cache_dir=None):
        """
        Initialize the base scraper
        
        Args:
            use_selenium (bool): Whether to use Selenium for JS-heavy sites
            cache_dir (str): Directory to cache scraped pages
        """
        self.use_selenium = use_selenium
        
        # Default user agents
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        # Use default cache directory if not specified
        if cache_dir is None:
            self.cache_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'cache',
                'scrapes'
            )
        else:
            self.cache_dir = cache_dir
            
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Create a session for making requests
        self.session = requests.Session()
    
    def get_page_content(self, url, force_refresh=False, cache_timeout_hours=24):
        """
        Get page content with caching support
        
        Args:
            url (str): URL to fetch
            force_refresh (bool): Force refresh the cache
            cache_timeout_hours (int): Cache timeout in hours
            
        Returns:
            str: HTML content
        """
        # Create a filename for the cache
        clean_url = url.replace('https://', '').replace('http://', '').replace('/', '_').replace('?', '_').replace('=', '_')
        cache_file = os.path.join(self.cache_dir, f"{clean_url}.html")
        
        # Check if we have a cached version
        if os.path.exists(cache_file) and not force_refresh:
            # Check if cache is still valid
            file_age_hours = (time.time() - os.path.getmtime(cache_file)) / 3600
            if file_age_hours < cache_timeout_hours:
                logger.info(f"Using cached content for {url}")
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception as e:
                    logger.error(f"Error reading cache file: {e}")
        
        # If we get here, we need to fetch the page
        logger.info(f"Fetching content for {url}")
        
        try:
            # Rotate user agents
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.google.com/'
            }
            
            # Add a delay to avoid rate limiting
            time.sleep(random.uniform(1, 3))
            
            if self.use_selenium:
                html = self._get_with_selenium(url)
            else:
                response = self.session.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                html = response.text
            
            # Save to cache
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    f.write(html)
            except Exception as e:
                logger.error(f"Error writing to cache file: {e}")
            
            return html
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _get_with_selenium(self, url):
        """
        Get page content using Selenium for JavaScript-heavy sites
        
        Note: For this to work, you need to have selenium installed
        and the appropriate webdriver (chromedriver) set up.
        
        Returns:
            str: HTML content
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            # Set up Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument(f"user-agent={random.choice(self.user_agents)}")
            
            # Set up driver
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            # Get page
            driver.get(url)
            
            # Wait for JavaScript to load
            time.sleep(5)
            
            # Get the page source
            html = driver.page_source
            
            # Close the driver
            driver.quit()
            
            return html
            
        except ImportError:
            logger.error("Selenium is not installed, falling back to requests")
            response = self.session.get(url, headers={'User-Agent': random.choice(self.user_agents)})
            return response.text
        except Exception as e:
            logger.error(f"Error with Selenium: {e}")
            return None
    
    def parse_html(self, html):
        """
        Parse HTML using BeautifulSoup
        
        Args:
            html (str): HTML content
            
        Returns:
            BeautifulSoup: Parsed HTML
        """
        if not html:
            return None
            
        try:
            return BeautifulSoup(html, 'html.parser')
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return None
    
    def search_products(self, query, limit=5):
        """
        Search for products (to be implemented by child classes)
        
        Args:
            query (str): Search query
            limit (int): Maximum number of products to return
            
        Returns:
            list: List of product dictionaries
        """
        raise NotImplementedError("Child classes must implement search_products")
        
    def generate_fake_products(self, query, limit=5, source="generic"):
        """
        Generate fake products for testing
        
        Args:
            query (str): Search query
            limit (int): Maximum number of products to return
            source (str): Source name
            
        Returns:
            list: List of fake product dictionaries
        """
        products = []
        for i in range(min(limit, 5)):
            products.append({
                "title": f"{source.title()} {query.title()} - Model {i+1}",
                "price": round(random.uniform(10, 500), 2),
                "image": f"https://placehold.co/400x400?text={source}+{i+1}",
                "url": f"https://www.{source.lower()}.com/search?q={query.replace(' ', '+')}",
                "description": f"Sample {query} product from {source}",
                "source": source.lower(),
                "category": query
            })
        return products