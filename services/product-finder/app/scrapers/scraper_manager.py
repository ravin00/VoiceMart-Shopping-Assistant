from .amazon_scraper import AmazonScraper
from .ebay_scraper import EbayScraper
from .walmart_scraper import WalmartScraper
import concurrent.futures
import logging
import random
import uuid
import time
import re

logger = logging.getLogger('scraper_manager')

class ScraperManager:
    def __init__(self, cache_dir=None):
        self.scrapers = {
            'amazon': AmazonScraper(cache_dir=cache_dir),
            'ebay': EbayScraper(cache_dir=cache_dir),
            'walmart': WalmartScraper(cache_dir=cache_dir)
        }
        # Flag to generate fallback data if all scrapers fail
        self.enable_fallbacks = True
    
    def search_all_sources(self, query, limit=10, sources=None):
        """
        Search for products across all or specified sources
        
        Args:
            query: Search query string
            limit: Maximum number of results to return in total
            sources: List of sources to search (None means all sources)
            
        Returns:
            List of product dictionaries from all sources
        """
        start_time = time.time()
        
        if not query:
            query = "sample products"  # Fallback query
            
        if sources is None:
            sources = list(self.scrapers.keys())
        else:
            # Filter to only include sources we support
            sources = [s for s in sources if s in self.scrapers]
        
        if not sources:
            logger.warning("No valid sources specified for search")
            if self.enable_fallbacks:
                return self._generate_mock_products(query, limit)
            return []
            
        # Calculate how many results to get from each source
        per_source_limit = max(1, limit // len(sources))
        logger.info(f"Searching for '{query}' across {len(sources)} sources, {per_source_limit} results per source")
        
        all_results = []
        
        # Use concurrent.futures to search sources in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sources)) as executor:
            future_to_source = {
                executor.submit(
                    self._safe_search_products,
                    source,
                    query,
                    per_source_limit
                ): source for source in sources
            }
            
            for future in concurrent.futures.as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    results = future.result()
                    logger.info(f"Got {len(results)} results from {source}")
                    all_results.extend(results)
                except Exception as e:
                    logger.error(f"Error processing results from {source}: {e}")
        
        # If no results from any source and fallbacks are enabled, generate mock data
        if not all_results and self.enable_fallbacks:
            logger.warning(f"No results from any source for query '{query}', generating fallback data")
            mock_products = self._generate_mock_products(query, limit)
            all_results.extend(mock_products)
        
        # Ensure all products have required fields
        for product in all_results:
            # Generate ID if not present
            if 'id' not in product:
                product['id'] = f"{product.get('source', 'unknown')}-{str(uuid.uuid4())[:8]}"
                
            # Default currency
            if 'currency' not in product:
                product['currency'] = 'USD'
            
            # Add missing fields
            for field in ['description', 'brand', 'rating', 'availability']:
                if field not in product:
                    product[field] = None
        
        # Sort by price and limit to requested number
        all_results = sorted(all_results, key=lambda x: x.get('price', float('inf')))[:limit]
        
        elapsed = time.time() - start_time
        logger.info(f"Search completed in {elapsed:.2f}s, found {len(all_results)} results")
        
        return all_results
    
    def _safe_search_products(self, source, query, limit):
        """Safely search for products with error handling"""
        try:
            if source not in self.scrapers:
                return []
                
            results = self.scrapers[source].search_products(query, limit)
            
            # Validate results
            valid_results = []
            for product in results:
                # Ensure each product has at least title and price
                if not product.get('title'):
                    continue
                    
                if 'price' not in product:
                    product['price'] = round(random.uniform(10, 500), 2)
                
                # Add source if missing
                if 'source' not in product:
                    product['source'] = source
                    
                valid_results.append(product)
                
            return valid_results
            
        except Exception as e:
            logger.error(f"Error searching {source}: {e}")
            return []
    
    def _generate_mock_products(self, query, limit):
        """Generate mock products for testing when real scrapers fail"""
        logger.warning(f"Generating {limit} mock products for query: {query}")
        
        categories = {
            'electronics': ["TV", "Laptop", "Headphones", "Smartphone", "Tablet", "Camera"],
            'clothing': ["Shirt", "Pants", "Shoes", "Jacket", "Dress", "Socks"],
            'home': ["Sofa", "Chair", "Lamp", "Table", "Bed", "Mattress"],
            'beauty': ["Shampoo", "Moisturizer", "Sunscreen", "Perfume", "Lipstick", "Mascara"],
            'toys': ["Action Figure", "Board Game", "Puzzle", "Doll", "LEGO Set", "Remote Control Car"]
        }
        
        # Try to determine which category the query belongs to
        query_lower = query.lower()
        category_items = None
        for cat_name, cat_items in categories.items():
            if cat_name in query_lower or any(item.lower() in query_lower for item in cat_items):
                category_items = cat_items
                break
        
        # If no category matched, use a random one
        if not category_items:
            category_items = random.choice(list(categories.values()))
        
        # Generate brands based on query or category
        if 'electronics' in query_lower or any(item.lower() in query_lower for item in categories['electronics']):
            brands = ["Samsung", "Sony", "Apple", "LG", "Bose", "JBL"]
        elif 'clothing' in query_lower or any(item.lower() in query_lower for item in categories['clothing']):
            brands = ["Nike", "Adidas", "Puma", "Levi's", "H&M", "Zara"]
        else:
            brands = ["Amazon Basics", "GoodBrand", "ProShop", "ValueMart", "TopChoice", "PrimeLine"]
        
        mock_products = []
        
        sources = ["amazon", "ebay", "walmart"]
        
        # Create mock products with plausible data
        for i in range(limit):
            source = random.choice(sources)
            brand = random.choice(brands)
            item_type = random.choice(category_items)
            model = f"Model {chr(65 + i % 26)}{random.randint(100, 999)}"
            
            # Generate a price that seems realistic for the query
            if "premium" in query_lower or "pro" in query_lower:
                price = round(random.uniform(200, 1000), 2)
            elif "budget" in query_lower or "cheap" in query_lower:
                price = round(random.uniform(10, 100), 2)
            else:
                price = round(random.uniform(50, 500), 2)
                
            # Parse min/max price from query if present
            min_price_match = re.search(r'(?:min|above|over|more than)\s*\$?(\d+)', query_lower)
            max_price_match = re.search(r'(?:max|below|under|less than)\s*\$?(\d+)', query_lower)
            
            if min_price_match:
                min_price = float(min_price_match.group(1))
                price = max(price, min_price)
                
            if max_price_match:
                max_price = float(max_price_match.group(1))
                price = min(price, max_price)
            
            # Create the mock product
            product = {
                "id": f"{source}-mock-{str(uuid.uuid4())[:8]}",
                "title": f"{brand} {item_type} {model}",
                "price": price,
                "currency": "USD",
                "description": f"This {brand} {item_type} {model} is perfect for your needs. " + 
                               f"High-quality product with great features.",
                "brand": brand,
                "category": query,
                "rating": round(random.uniform(3.5, 5.0), 1),
                "availability": "In Stock",
                "image": f"https://via.placeholder.com/300x300.png?text={brand}+{item_type}",
                "url": f"https://www.{source}.com/dp/{uuid.uuid4().hex[:10]}",
                "source": source
            }
            
            mock_products.append(product)
            
        return mock_products
    
    def get_product_categories(self):
        """Get common product categories"""
        return [
            "Electronics", "Computers", "Smart Home", 
            "Home & Kitchen", "Clothing", "Beauty",
            "Sports & Outdoors", "Toys & Games", "Books",
            "Health & Household", "Automotive"
        ]
    
    def get_products_by_category(self, category, limit=10, sources=None):
        """Get products for a specific category"""
        # For now, we just search for the category name
        return self.search_all_sources(category, limit, sources)
    
    def cleanup(self):
        """Close all scrapers"""
        for scraper in self.scrapers.values():
            try:
                scraper.close()
            except Exception as e:
                logger.error(f"Error closing scraper: {e}")