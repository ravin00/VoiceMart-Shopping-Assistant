import logging
import concurrent.futures
import time

logger = logging.getLogger('scraper_manager')

class ScraperManager:
    """
    Manages multiple scrapers and combines their results
    """
    
    def __init__(self, scrapers=None):
        """
        Initialize the scraper manager
        
        Args:
            scrapers (list): List of scraper instances
        """
        self.scrapers = scrapers or []
        
    def add_scraper(self, scraper):
        """
        Add a scraper to the manager
        
        Args:
            scraper: Scraper instance
        """
        self.scrapers.append(scraper)
        
    def search_products(self, query, limit=5, sources=None, parallel=True):
        """
        Search for products across all scrapers
        
        Args:
            query (str): Search query
            limit (int): Maximum number of products to return per source
            sources (list): List of source names to search (e.g., ['amazon', 'ebay'])
            parallel (bool): Whether to run scraper searches in parallel
            
        Returns:
            list: Combined list of products from all scrapers
        """
        if not query:
            return []
        
        results = []
        start_time = time.time()
        
        # Filter scrapers by source if specified
        active_scrapers = []
        for scraper in self.scrapers:
            source_name = scraper.__class__.__name__.lower().replace('scraper', '')
            if sources is None or source_name in sources:
                active_scrapers.append(scraper)
        
        if not active_scrapers:
            logger.warning(f"No scrapers available for query: {query}")
            return []
        
        if parallel:
            # Use ThreadPoolExecutor for parallel execution
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(active_scrapers)) as executor:
                # Submit scraper tasks
                future_to_scraper = {
                    executor.submit(scraper.search_products, query, limit): scraper 
                    for scraper in active_scrapers
                }
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_scraper):
                    scraper = future_to_scraper[future]
                    try:
                        products = future.result()
                        # Normalize product fields
                        for product in products:
                            self._normalize_product_fields(product)
                        logger.info(f"Got {len(products)} products from {scraper.__class__.__name__}")
                        results.extend(products)
                    except Exception as e:
                        logger.error(f"Error from {scraper.__class__.__name__}: {e}")
        else:
            # Run scrapers sequentially
            for scraper in active_scrapers:
                try:
                    products = scraper.search_products(query, limit)
                    # Normalize product fields
                    for product in products:
                        self._normalize_product_fields(product)
                    logger.info(f"Got {len(products)} products from {scraper.__class__.__name__}")
                    results.extend(products)
                except Exception as e:
                    logger.error(f"Error from {scraper.__class__.__name__}: {e}")
        
        duration = time.time() - start_time
        logger.info(f"Search completed in {duration:.2f}s with {len(results)} total results")
        
        return results
    
    def search_by_category(self, category, limit=5, sources=None):
        """
        Search for products by category
        
        Args:
            category (str): Category name
            limit (int): Maximum number of products to return per source
            sources (list): List of source names to search
            
        Returns:
            list: Combined list of products from all scrapers
        """
        # For now, just use the category as a search query
        return self.search_products(category, limit, sources)
    
    def _normalize_product_fields(self, product):
        """
        Normalize product fields to match expected API model
        
        Args:
            product (dict): Product dictionary to normalize
        """
        # Handle image field normalization (some scrapers use 'image', API expects 'image_url')
        if 'image' in product and 'image_url' not in product:
            product['image_url'] = product['image']
        
        # Ensure all required fields exist
        required_fields = ['id', 'title', 'price', 'source', 'url']
        for field in required_fields:
            if field not in product:
                if field == 'id' and 'url' in product:
                    # Generate an ID from the URL if not available
                    product['id'] = str(hash(product['url']))
                elif field == 'price':
                    product[field] = 0.0
                else:
                    product[field] = f"Unknown {field}"
        
        # Convert price to float if it's a string
        if isinstance(product.get('price'), str):
            try:
                product['price'] = float(product['price'].replace('$', '').replace(',', ''))
            except (ValueError, AttributeError):
                product['price'] = 0.0
        
        # Ensure price is a float
        if not isinstance(product.get('price'), float):
            try:
                product['price'] = float(product.get('price', 0))
            except (ValueError, TypeError):
                product['price'] = 0.0
                
        return product

    def get_product_details(self, product_url, source=None):
        """
        Get detailed information for a specific product
        
        Args:
            product_url (str): URL of the product
            source (str): Name of the source
            
        Returns:
            dict: Product details
        """
        # This is a placeholder - in a real implementation, you'd
        # determine the appropriate scraper and fetch detailed product info
        
        # Find the appropriate scraper
        for scraper in self.scrapers:
            scraper_source = scraper.__class__.__name__.lower().replace('scraper', '')
            if source is None or scraper_source == source:
                # Check if the URL belongs to this scraper
                if scraper.base_url in product_url:
                    # Here you would implement a method to get detailed product info
                    # For now, just return a placeholder
                    return {
                        "url": product_url,
                        "source": scraper_source,
                        "details": "Product details would go here"
                    }
        
        return None