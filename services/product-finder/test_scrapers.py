#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.scrapers.scraper_manager import ScraperManager
import json
import time

def test_individual_scrapers():
    """Test each scraper individually"""
    from app.scrapers.amazon_scraper import AmazonScraper
    from app.scrapers.ebay_scraper import EbayScraper
    from app.scrapers.walmart_scraper import WalmartScraper
    
    print("=== Testing Individual Scrapers ===")
    
    scrapers = {
        "Amazon": AmazonScraper(),
        "eBay": EbayScraper(),
        "Walmart": WalmartScraper()
    }
    
    try:
        for name, scraper in scrapers.items():
            print(f"\nTesting {name} Scraper...")
            start_time = time.time()
            results = scraper.search_products("wireless headphones", 3)
            elapsed = time.time() - start_time
            
            print(f"  Got {len(results)} results in {elapsed:.2f} seconds")
            if results:
                print(f"  First result: {json.dumps(results[0], indent=2)}")
            else:
                print("  No results found")
    finally:
        # Clean up
        for scraper in scrapers.values():
            scraper.close()

def test_scraper_manager():
    """Test the ScraperManager"""
    print("\n=== Testing Scraper Manager ===")
    
    manager = ScraperManager()
    
    try:
        print("\nTesting combined search...")
        start_time = time.time()
        results = manager.search_all_sources("wireless headphones", 6)
        elapsed = time.time() - start_time
        
        print(f"Got {len(results)} combined results in {elapsed:.2f} seconds")
        
        # Group by source
        by_source = {}
        for product in results:
            source = product.get('source', 'unknown')
            by_source.setdefault(source, []).append(product)
        
        for source, products in by_source.items():
            print(f"\nFrom {source}: {len(products)} results")
            if products:
                print(f"Example: {products[0]['title']} - ${products[0]['price']}")
    
        print("\nTesting categories...")
        categories = manager.get_product_categories()
        print(f"Available categories: {', '.join(categories[:5])}...")
        
        print("\nTesting products by category...")
        category_results = manager.get_products_by_category("Electronics", 3)
        print(f"Got {len(category_results)} results for Electronics category")
        
    finally:
        manager.cleanup()

def test_cached_client():
    """Test the CachedScraperClient"""
    from app.api_clients import CachedScraperClient
    
    print("\n=== Testing CachedScraperClient ===")
    
    client = CachedScraperClient()
    
    try:
        print("\nTesting search with cache...")
        
        # First search - should hit the web
        start_time = time.time()
        results1 = client.search_products("smart watch", 5)
        elapsed1 = time.time() - start_time
        
        print(f"Initial search: Got {len(results1)} results in {elapsed1:.2f} seconds")
        
        # Second search - should use cache
        start_time = time.time()
        results2 = client.search_products("smart watch", 5)
        elapsed2 = time.time() - start_time
        
        print(f"Cached search: Got {len(results2)} results in {elapsed2:.2f} seconds")
        print(f"Cache speedup: {elapsed1/elapsed2:.1f}x faster")
        
        # Test categories
        print("\nTesting categories...")
        categories = client.get_product_categories()
        print(f"Got {len(categories)} categories")
        print(f"Examples: {', '.join(categories[:3])}")
        
    finally:
        client.cleanup()

if __name__ == "__main__":
    test_individual_scrapers()
    test_scraper_manager()
    test_cached_client()
