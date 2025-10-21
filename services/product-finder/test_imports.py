#!/usr/bin/env python3
"""
Simple test to verify that our imports work correctly.
"""

import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import core libraries
print("Testing core library imports...")
try:
    import requests
    print("✅ requests")
    
    import aiohttp
    print("✅ aiohttp")
    
    import bs4
    from bs4 import BeautifulSoup
    print("✅ BeautifulSoup4")
    
    import selenium
    from selenium import webdriver
    print("✅ selenium")
    
    from webdriver_manager.chrome import ChromeDriverManager
    print("✅ webdriver_manager")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Try to import our modules
print("\nTesting our module imports...")
try:
    from app.scrapers.base_scraper import BaseScraper
    print("✅ base_scraper")
    
    from app.scrapers.amazon_scraper import AmazonScraper
    print("✅ amazon_scraper")
    
    from app.scrapers.ebay_scraper import EbayScraper
    print("✅ ebay_scraper")
    
    from app.scrapers.walmart_scraper import WalmartScraper
    print("✅ walmart_scraper")
    
    from app.scrapers.scraper_manager import ScraperManager
    print("✅ scraper_manager")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

print("\n✅ All imports successful!")