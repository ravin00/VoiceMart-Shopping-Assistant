#!/usr/bin/env python3
# test_scrapers.py - Test the web scrapers

import os
import sys
import json
import logging
from pathlib import Path

# Add the app directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from scrapers import AmazonScraper, EbayScraper, WalmartScraper, ScraperManager

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_scrapers')

def save_results(query, products, filename):
    """Save search results to a JSON file"""
    cache_dir = Path(os.path.join(os.path.dirname(__file__), "app/cache/api"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = cache_dir / filename
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "query": query,
            "products": products,
            "count": len(products)
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(products)} products to {output_file}")

def test_individual_scrapers():
    """Test each scraper individually"""
    # Test queries
    queries = [
        "wireless headphones", 
        "smart watch"
    ]
    
    # Initialize scrapers
    amazon_scraper = AmazonScraper()
    ebay_scraper = EbayScraper()
    walmart_scraper = WalmartScraper()
    
    # Test Amazon scraper
    for query in queries:
        logger.info(f"Testing Amazon scraper with query: {query}")
        products = amazon_scraper.search_products(query, limit=5)
        save_results(query, products, f"search_amazon_query_{query.replace(' ', '_')}_limit_5.json")
    
    # Test eBay scraper
    for query in queries:
        logger.info(f"Testing eBay scraper with query: {query}")
        products = ebay_scraper.search_products(query, limit=5)
        save_results(query, products, f"search_ebay_query_{query.replace(' ', '_')}_limit_5.json")
    
    # Test Walmart scraper
    for query in queries:
        logger.info(f"Testing Walmart scraper with query: {query}")
        products = walmart_scraper.search_products(query, limit=5)
        save_results(query, products, f"search_walmart_query_{query.replace(' ', '_')}_limit_5.json")

def test_scraper_manager():
    """Test the scraper manager with all scrapers"""
    # Initialize scrapers
    amazon_scraper = AmazonScraper()
    ebay_scraper = EbayScraper()
    walmart_scraper = WalmartScraper()
    
    # Create scraper manager and add scrapers
    manager = ScraperManager()
    manager.add_scraper(amazon_scraper)
    manager.add_scraper(ebay_scraper)
    manager.add_scraper(walmart_scraper)
    
    # Test queries
    test_cases = [
        {"query": "wireless headphones", "limit": 5, "sources": ["amazon", "ebay", "walmart"]},
        {"query": "smart watch", "limit": 5, "sources": ["amazon", "ebay", "walmart"]},
        {"query": "electronics", "limit": 5, "sources": ["amazon", "ebay", "walmart"]},
        {"query": "smartphone", "limit": 5, "sources": ["amazon", "ebay", "walmart"]},
        {"query": "laptop", "limit": 5, "sources": ["amazon", "ebay", "walmart"]},
    ]
    
    for case in test_cases:
        query = case["query"]
        limit = case["limit"]
        sources = case["sources"]
        
        logger.info(f"Testing ScraperManager with query: {query}, sources: {sources}")
        products = manager.search_products(query, limit=limit, sources=sources)
        
        sources_str = "_".join(sources)
        save_results(query, products, 
                     f"search_limit_{limit}_query_{query.replace(' ', '_')}_sources_{sources_str}.json")

if __name__ == "__main__":
    # Check if specific test is requested
    if len(sys.argv) > 1 and sys.argv[1] == "individual":
        test_individual_scrapers()
    else:
        # Run all tests by default
        test_individual_scrapers()
        test_scraper_manager()
    
    logger.info("All tests completed successfully!")