import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException
import time
import os
import random
import logging
import json
from urllib.parse import urlparse
import lxml  # For faster HTML parsing

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('base_scraper')

class BaseScraper:
    def __init__(self, use_selenium=True, cache_dir=None):
        self.use_selenium = use_selenium
        
        # Setup for Selenium
        self.driver = None
        self.selenium_initialized = False
        if use_selenium:
            self._setup_selenium()
        
        # Setup requests session for non-JS pages
        self.session = requests.Session()
        
        # Rotate between different user agents to avoid blocking
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0'
        ]
        
        # Set initial user agent
        self._rotate_user_agent()
        
        # Setup cache with versioning
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache')
        self.scrapes_dir = os.path.join(self.cache_dir, 'scrapes')
        os.makedirs(self.scrapes_dir, exist_ok=True)
        
        # Rate limiting with per-domain settings
        self.last_request_time = {}
        # Different delays for different domains to respect their policies
        self.min_delays = {
            'amazon.com': 5,
            'ebay.com': 3,
            'walmart.com': 4,
            'default': 3
        }
        
        # Track the number of requests to each domain
        self.request_counts = {}
        
    def _rotate_user_agent(self):
        """Rotate user agent to avoid detection"""
        user_agent = random.choice(self.user_agents)
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        return user_agent
        
    def _setup_selenium(self):
        """Initialize Selenium WebDriver with retry mechanism"""
        if self.selenium_initialized:
            return
            
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Add a realistic user agent
            user_agent = self._rotate_user_agent()
            chrome_options.add_argument(f"user-agent={user_agent}")
            
            # Add experimental options to avoid detection
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # For Mac, use chromedriver directly since sometimes webdriver_manager fails
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
            except:
                # Fallback to webdriver_manager
                self.driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=chrome_options
                )
                
            # Execute CDP commands to avoid detection
            if self.driver:
                self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    """
                })
                
            logger.info("Selenium WebDriver initialized successfully")
            self.selenium_initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {e}")
            self.driver = None
            # If we failed to initialize Selenium, we will fall back to using requests
    
    def _respect_rate_limits(self, domain):
        """Ensure we don't send requests too quickly to the same domain"""
        # Extract base domain
        base_domain = '.'.join(domain.split('.')[-2:])
        
        # Get the appropriate delay for this domain
        delay = self.min_delays.get(base_domain, self.min_delays['default'])
        
        # Track request count
        self.request_counts[base_domain] = self.request_counts.get(base_domain, 0) + 1
        
        # If we've made many requests to this domain, increase the delay
        if self.request_counts[base_domain] > 5:
            delay *= 1.5
        
        current_time = time.time()
        
        if base_domain in self.last_request_time:
            elapsed = current_time - self.last_request_time[base_domain]
            if elapsed < delay:
                sleep_time = delay - elapsed
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s for {domain}")
                time.sleep(sleep_time)
        
        # Add some randomness to appear more human-like
        time.sleep(random.uniform(1, 2))
        self.last_request_time[base_domain] = time.time()
    
    def get_page_content(self, url, use_selenium=None, cache_ttl=3600):
        """Get page content with rate limiting and caching"""
        if use_selenium is None:
            use_selenium = self.use_selenium
            
        # Extract domain for rate limiting
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Create cache filename from URL
        safe_url = url.replace('://', '_').replace('/', '_').replace('?', '_').replace('&', '_').replace('=', '_')
        cache_file = os.path.join(self.scrapes_dir, f"{safe_url[:200]}.html")
        
        # Check cache
        if os.path.exists(cache_file) and time.time() - os.path.getmtime(cache_file) < cache_ttl:
            logger.debug(f"Cache hit for {url}")
            try:
                with open(cache_file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    if content and len(content) > 500:  # Basic check if cache is valid
                        return content
            except Exception as e:
                logger.warning(f"Failed to read cache file: {e}")
        
        # Respect rate limits
        self._respect_rate_limits(domain)
        
        # Rotate user agent
        self._rotate_user_agent()
        
        content = None
        
        # Try with Selenium first if requested
        if use_selenium:
            if not self.driver:
                self._setup_selenium()
                
            if self.driver:
                try:
                    logger.info(f"Fetching {url} with Selenium")
                    self.driver.get(url)
                    # Wait longer for dynamic content
                    time.sleep(random.uniform(3, 5))
                    
                    # Scroll down a bit to trigger lazy loading
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
                    time.sleep(1)
                    
                    content = self.driver.page_source
                    
                    if not content or len(content) < 500:
                        logger.warning("Selenium returned empty or short content, falling back to requests")
                        content = None
                        
                except Exception as e:
                    logger.error(f"Error with Selenium: {e}")
                    content = None
                    # Try to recover the driver
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                    self._setup_selenium()
        
        # Fall back to requests if Selenium failed or wasn't used
        if not content:
            try:
                logger.info(f"Fetching {url} with Requests")
                response = self.session.get(
                    url, 
                    timeout=20,
                    headers={
                        'Referer': f"{parsed_url.scheme}://{parsed_url.netloc}/",
                        'Cache-Control': 'no-cache'
                    }
                )
                response.raise_for_status()
                content = response.text
            except Exception as e:
                logger.error(f"Error fetching with requests: {e}")
                # Try to return an empty HTML document as fallback
                content = "<html><body><p>Error fetching content</p></body></html>"
        
        # Cache the result if we got something useful
        if content and len(content) > 500:
            try:
                with open(cache_file, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(content)
            except Exception as e:
                logger.error(f"Failed to write cache file: {e}")
                
        return content
            
    def parse_html(self, html):
        """Parse HTML with BeautifulSoup"""
        if not html:
            return None
            
        # Try with lxml parser first (faster)
        try:
            return BeautifulSoup(html, 'lxml')
        except:
            # Fall back to html.parser
            return BeautifulSoup(html, 'html.parser')
    
    def close(self):
        """Close resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium WebDriver closed")
            except Exception as e:
                logger.error(f"Error closing Selenium: {e}")