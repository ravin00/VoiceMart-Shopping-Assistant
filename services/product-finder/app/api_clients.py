# app/api_clients.py - Product API integrations using web scraping

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from .models import Product, ProductSearchRequest, ProductSearchResponse, ProductDetailsResponse
from .scrapers.scraper_manager import ScraperManager

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('api_clients')

# New implementation using web scraping instead of fake APIs

class CachedScraperClient:
    """Client for managing product data using web scrapers with caching"""
    
    def __init__(self):
        cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        
        # API cache (for processed results)
        self.api_cache_dir = os.path.join(cache_dir, 'api')
        os.makedirs(self.api_cache_dir, exist_ok=True)
        
        # Raw scrape cache is managed by the scraper_manager
        self.scraper_manager = ScraperManager(cache_dir=os.path.join(cache_dir, 'scrapes'))
        self.cache_ttl = 3600  # 1 hour cache validity
        
        logger.info("CachedScraperClient initialized")
    
    def _get_cache_key(self, operation, params):
        """Generate a cache key from operation and params"""
        # Convert params to a stable string format
        params_str = "_".join(f"{k}_{v}" for k, v in sorted(params.items()) if v is not None)
        return f"{operation}_{params_str}.json"
    
    def _get_from_cache(self, operation, params):
        """Get results from cache if valid"""
        cache_key = self._get_cache_key(operation, params)
        cache_path = os.path.join(self.api_cache_dir, cache_key)
        
        if os.path.exists(cache_path):
            # Check if cache is expired
            if time.time() - os.path.getmtime(cache_path) < self.cache_ttl:
                try:
                    with open(cache_path, 'r') as f:
                        logger.info(f"Cache hit for {operation}")
                        return json.load(f)
                except Exception as e:
                    logger.error(f"Error reading cache: {e}")
                    # If reading cache fails, continue to fetch new data
                    
        return None
    
    def _save_to_cache(self, operation, params, data):
        """Save results to cache"""
        cache_key = self._get_cache_key(operation, params)
        cache_path = os.path.join(self.api_cache_dir, cache_key)
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f)
                logger.info(f"Saved to cache: {operation}")
        except Exception as e:
            logger.error(f"Error writing to cache: {e}")
            # Silently fail on cache write error
    
    def search_products(self, query, limit=10, sources=None):
        """Search for products matching query"""
        # Try cache first
        cache_params = {'query': query, 'limit': limit, 'sources': ','.join(sources) if sources else 'all'}
        cached_results = self._get_from_cache('search', cache_params)
        if cached_results:
            return cached_results
        
        logger.info(f"Searching for '{query}' across sources: {sources or 'all'}")
        
        # Perform the search
        results = self.scraper_manager.search_all_sources(query, limit, sources)
        
        # Cache the results
        self._save_to_cache('search', cache_params, results)
        
        logger.info(f"Found {len(results)} results for '{query}'")
        return results
    
    def get_product_categories(self):
        """Get product categories"""
        # Try cache first
        cached_results = self._get_from_cache('categories', {})
        if cached_results:
            return cached_results
        
        # Get categories
        logger.info("Fetching product categories")
        categories = self.scraper_manager.get_product_categories()
        
        # Cache the results
        self._save_to_cache('categories', {}, categories)
        
        logger.info(f"Found {len(categories)} categories")
        return categories
    
    def get_products_by_category(self, category, limit=10, sources=None):
        """Get products by category"""
        # Try cache first
        cache_params = {'category': category, 'limit': limit, 'sources': ','.join(sources) if sources else 'all'}
        cached_results = self._get_from_cache('category', cache_params)
        if cached_results:
            return cached_results
        
        # Get products for category
        logger.info(f"Searching category '{category}' across sources: {sources or 'all'}")
        results = self.scraper_manager.get_products_by_category(category, limit, sources)
        
        # Cache the results
        self._save_to_cache('category', cache_params, results)
        
        logger.info(f"Found {len(results)} products in category '{category}'")
        return results
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up CachedScraperClient resources")
        self.scraper_manager.cleanup()


class CachedScraperClient:
    """Client for managing product data using web scrapers with caching"""
    
    def __init__(self):
        cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        
        # API cache (for processed results)
        self.api_cache_dir = os.path.join(cache_dir, 'api')
        os.makedirs(self.api_cache_dir, exist_ok=True)
        
        # Raw scrape cache is managed by the scraper_manager
        self.scraper_manager = ScraperManager(cache_dir=os.path.join(cache_dir, 'scrapes'))
        self.cache_ttl = 3600  # 1 hour cache validity
    
    def _get_cache_key(self, operation, params):
        """Generate a cache key from operation and params"""
        # Convert params to a stable string format
        params_str = "_".join(f"{k}_{v}" for k, v in sorted(params.items()) if v is not None)
        return f"{operation}_{params_str}.json"
    
    def _get_from_cache(self, operation, params):
        """Get results from cache if valid"""
        cache_key = self._get_cache_key(operation, params)
        cache_path = os.path.join(self.api_cache_dir, cache_key)
        
        if os.path.exists(cache_path):
            # Check if cache is expired
            if time.time() - os.path.getmtime(cache_path) < self.cache_ttl:
                try:
                    with open(cache_path, 'r') as f:
                        return json.load(f)
                except Exception:
                    pass  # If reading cache fails, continue to fetch new data
                    
        return None
    
    def _save_to_cache(self, operation, params, data):
        """Save results to cache"""
        cache_key = self._get_cache_key(operation, params)
        cache_path = os.path.join(self.api_cache_dir, cache_key)
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass  # Silently fail on cache write error
    
    def search_products(self, query, limit=10, sources=None):
        """Search for products matching query"""
        # Try cache first
        cache_params = {'query': query, 'limit': limit, 'sources': ','.join(sources) if sources else 'all'}
        cached_results = self._get_from_cache('search', cache_params)
        if cached_results:
            return cached_results
        
        # Perform the search
        results = self.scraper_manager.search_all_sources(query, limit, sources)
        
        # Cache the results
        self._save_to_cache('search', cache_params, results)
        
        return results
    
    def get_product_categories(self):
        """Get product categories"""
        # Try cache first
        cached_results = self._get_from_cache('categories', {})
        if cached_results:
            return cached_results
        
        # Get categories
        categories = self.scraper_manager.get_product_categories()
        
        # Cache the results
        self._save_to_cache('categories', {}, categories)
        
        return categories
    
    def get_products_by_category(self, category, limit=10, sources=None):
        """Get products by category"""
        # Try cache first
        cache_params = {'category': category, 'limit': limit, 'sources': ','.join(sources) if sources else 'all'}
        cached_results = self._get_from_cache('category', cache_params)
        if cached_results:
            return cached_results
        
        # Get products for category
        results = self.scraper_manager.get_products_by_category(category, limit, sources)
        
        # Cache the results
        self._save_to_cache('category', cache_params, results)
        
        return results
    
    def cleanup(self):
        """Clean up resources"""
        self.scraper_manager.cleanup()
