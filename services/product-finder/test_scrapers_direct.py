#!/usr/bin/env python3
"""
Test script for web scraper implementation.
This tests the web scraping functionality specifically by directly importing the scrapers.
"""

import os
import sys
import json
import logging
import time
from pathlib import Path

# Add the app directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_scrapers')

# Try to import our scrapers
try:
    # Import from the app.scrapers module
    from app.scrapers import AmazonScraper, EbayScraper, WalmartScraper, ScraperManager
    SCRAPERS_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import scrapers: {e}")
    SCRAPERS_AVAILABLE = False

def save_results(query, products, filename):
    """Save search results to a JSON file"""
    cache_dir = Path(os.path.join(os.path.dirname(__file__), "app", "cache", "test"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = cache_dir / filename
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "query": query,
            "products": products,
            "count": len(products),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(products)} products to {output_file}")

def test_amazon_scraper(query="wireless headphones", limit=5):
    """Test Amazon scraper"""
    logger.info(f"Testing Amazon scraper with query: {query}")
    
    try:
        scraper = AmazonScraper()
        start_time = time.time()
        products = scraper.search_products(query, limit)
        duration = time.time() - start_time
        
        logger.info(f"Found {len(products)} Amazon products in {duration:.2f} seconds")
        
        # Save results
        save_results(query, products, f"amazon_{query.replace(' ', '_')}.json")
        
        # Print results
        for i, product in enumerate(products, 1):
            print(f"{i}. {product.get('title', 'N/A')} - ${product.get('price', 'N/A')}")
            print(f"   URL: {product.get('url', 'N/A')}")
            
        return products
    except Exception as e:
        logger.error(f"Amazon scraper error: {e}")
        return []

def test_ebay_scraper(query="wireless headphones", limit=5):
    """Test eBay scraper"""
    logger.info(f"Testing eBay scraper with query: {query}")
    
    try:
        scraper = EbayScraper()
        start_time = time.time()
        products = scraper.search_products(query, limit)
        duration = time.time() - start_time
        
        logger.info(f"Found {len(products)} eBay products in {duration:.2f} seconds")
        
        # Save results
        save_results(query, products, f"ebay_{query.replace(' ', '_')}.json")
        
        # Print results
        for i, product in enumerate(products, 1):
            print(f"{i}. {product.get('title', 'N/A')} - ${product.get('price', 'N/A')}")
            print(f"   URL: {product.get('url', 'N/A')}")
            
        return products
    except Exception as e:
        logger.error(f"eBay scraper error: {e}")
        return []

def test_walmart_scraper(query="wireless headphones", limit=5):
    """Test Walmart scraper"""
    logger.info(f"Testing Walmart scraper with query: {query}")
    
    try:
        scraper = WalmartScraper()
        start_time = time.time()
        products = scraper.search_products(query, limit)
        duration = time.time() - start_time
        
        logger.info(f"Found {len(products)} Walmart products in {duration:.2f} seconds")
        
        # Save results
        save_results(query, products, f"walmart_{query.replace(' ', '_')}.json")
        
        # Print results
        for i, product in enumerate(products, 1):
            print(f"{i}. {product.get('title', 'N/A')} - ${product.get('price', 'N/A')}")
            print(f"   URL: {product.get('url', 'N/A')}")
            
        return products
    except Exception as e:
        logger.error(f"Walmart scraper error: {e}")
        return []

def test_scraper_manager(query="wireless headphones", limit=5):
    """Test ScraperManager with all scrapers"""
    logger.info(f"Testing ScraperManager with query: {query}")
    
    try:
        # Create scrapers
        amazon = AmazonScraper()
        ebay = EbayScraper()
        walmart = WalmartScraper()
        
        # Create manager and add scrapers
        manager = ScraperManager()
        manager.add_scraper(amazon)
        manager.add_scraper(ebay)
        manager.add_scraper(walmart)
        
        # Search products
        start_time = time.time()
        products = manager.search_products(query, limit, parallel=True)
        duration = time.time() - start_time
        
        logger.info(f"Found {len(products)} total products in {duration:.2f} seconds")
        
        # Group by source
        by_source = {}
        for product in products:
            source = product.get('source', 'unknown')
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(product)
        
        # Print summary
        for source, items in by_source.items():
            logger.info(f"- {source.title()}: {len(items)} products")
        
        # Save results
        save_results(query, products, f"all_{query.replace(' ', '_')}.json")
        
        return products
    except Exception as e:
        logger.error(f"ScraperManager error: {e}")
        return []

def main():
    """Main function to run all tests"""
    if not SCRAPERS_AVAILABLE:
        print("ERROR: Scrapers are not available. Make sure you have implemented:")
        print("- app/scrapers/base_scraper.py")
        print("- app/scrapers/amazon_scraper.py")
        print("- app/scrapers/ebay_scraper.py")
        print("- app/scrapers/walmart_scraper.py")
        print("- app/scrapers/scraper_manager.py")
        print("- app/scrapers/__init__.py")
        return
    
    # Parse command line arguments
    query = "wireless headphones"
    limit = 5
    
    if len(sys.argv) > 1:
        query = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            limit = int(sys.argv[2])
        except ValueError:
            print(f"Invalid limit: {sys.argv[2]}. Using default: {limit}")
    
    # Run individual scraper tests
    print("\n===== Testing Amazon Scraper =====")
    test_amazon_scraper(query, limit)
    
    print("\n===== Testing eBay Scraper =====")
    test_ebay_scraper(query, limit)
    
    print("\n===== Testing Walmart Scraper =====")
    test_walmart_scraper(query, limit)
    
    print("\n===== Testing Scraper Manager (All Scrapers) =====")
    test_scraper_manager(query, limit)
    
    print("\nAll tests completed! Check the app/cache/test directory for results.")

if __name__ == "__main__":
    main()