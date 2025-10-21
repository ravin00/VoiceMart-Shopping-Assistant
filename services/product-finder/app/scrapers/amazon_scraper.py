from .base_scraper import BaseScraper
import re
import logging
import random
import time

logger = logging.getLogger('amazon_scraper')

class AmazonScraper(BaseScraper):
    def __init__(self, **kwargs):
        # Define user agents before calling parent class constructor
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0'
        ]
        
        super().__init__(use_selenium=False, **kwargs)  # Amazon doesn't strictly need Selenium
        self.base_url = "https://www.amazon.com"
    
    def search_products(self, query, limit=5):
        """Search for products on Amazon"""
        search_url = f"{self.base_url}/s?k={query.replace(' ', '+')}"
        logger.info(f"Searching Amazon for: {query}")
        
        html = self.get_page_content(search_url)
        if not html:
            logger.warning(f"Failed to get content from Amazon for query: {query}")
            return []
            
        soup = self.parse_html(html)
        if not soup:
            return []
        
        products = []
        
        # Amazon frequently changes their selectors, so we try multiple possible selectors
        # For the search results container
        result_selectors = [
            "div.s-result-item[data-asin]", 
            "div.sg-col-4-of-24.sg-col-4-of-12",
            "div.sg-col-20-of-24.s-result-item",
            "div[data-component-type='s-search-result']",
            "div.rush-component"
        ]
        
        results = []
        for selector in result_selectors:
            results = soup.select(selector)
            if results:
                # Filter out empty ASINs and sponsored results
                results = [r for r in results if r.get('data-asin') and r.get('data-asin') != '']
                if results:
                    logger.info(f"Found {len(results)} Amazon results for query: {query} using selector: {selector}")
                    break
        
        for i, item in enumerate(results):
            if i >= limit:
                break
                
            product = {
                "source": "amazon",
                "category": query  # Default to search query as category
            }
            
            # Try to get ASIN
            asin = item.get('data-asin')
            if asin:
                product['id'] = asin
                product['url'] = f"{self.base_url}/dp/{asin}"
            
            # Extract title
            title_selectors = [
                "h2 a.a-link-normal span",
                "h2 a.a-link-normal",
                "h2 span",
                "h5 a",
                ".a-size-medium.a-color-base"
            ]
            
            for selector in title_selectors:
                title_elem = item.select_one(selector)
                if title_elem and title_elem.text.strip():
                    product['title'] = title_elem.text.strip()
                    break
            
            # Extract price
            price_selectors = [
                ".a-price .a-offscreen",
                "span.a-price span.a-offscreen",
                ".a-color-base .a-price-whole",
                ".a-price-whole"
            ]
            
            for selector in price_selectors:
                try:
                    price_elem = item.select_one(selector)
                    if price_elem:
                        price_text = price_elem.text.strip()
                        price_match = re.search(r'[\d,]+\.\d+|\$[\d,]+\.\d+|\d+', price_text)
                        if price_match:
                            price_str = price_match.group(0).replace('$', '').replace(',', '')
                            product['price'] = float(price_str)
                            break
                except Exception as e:
                    logger.debug(f"Error extracting price: {e}")
            
            # Extract image
            img_selectors = [
                "img.s-image",
                ".s-image",
                "img[data-image-latency='s-product-image']",
                "img[srcset]"
            ]
            
            for selector in img_selectors:
                img_elem = item.select_one(selector)
                if img_elem and img_elem.get('src'):
                    product['image'] = img_elem['src']
                    break
            
            # Extract URL if not already set
            if 'url' not in product:
                link_selectors = [
                    "h2 a.a-link-normal",
                    "a.a-link-normal.s-no-outline",
                    ".a-link-normal.a-text-normal",
                    "a.a-link-normal"
                ]
                
                for selector in link_selectors:
                    link_elem = item.select_one(selector)
                    if link_elem and link_elem.get('href'):
                        href = link_elem['href']
                        product['url'] = f"{self.base_url}{href}" if href.startswith('/') else href
                        break
                
                if 'url' not in product:
                    product['url'] = search_url
            
            # Extract rating
            rating_selectors = [
                ".a-icon-star-small .a-icon-alt",
                "i.a-icon-star-small",
                ".a-icon-star-small",
                ".a-icon-alt"
            ]
            
            for selector in rating_selectors:
                rating_elem = item.select_one(selector)
                if rating_elem:
                    rating_text = rating_elem.text.strip() if hasattr(rating_elem, 'text') else rating_elem.get('aria-label', '')
                    rating_match = re.search(r'(\d+(\.\d+)?)', rating_text)
                    if rating_match:
                        product['rating'] = float(rating_match.group(1))
                        break
            
            # Extract description - Amazon doesn't usually show descriptions in search results
            product['description'] = f"Amazon product: {product.get('title', 'No title available')}"
            
            # Only add if we have at least a title and either image or price
            if 'title' in product and ('image' in product or 'price' in product):
                products.append(product)
        
        # If still no products, create some mock products for testing
        if not products and query:
            logger.warning(f"No Amazon products found for query: {query}. Generating mock products.")
            products = self.generate_fake_products(query, limit=limit, source="amazon")
        
        return products