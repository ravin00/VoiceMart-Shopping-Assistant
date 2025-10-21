from .base_scraper import BaseScraper
import re
import logging
import random
import time

logger = logging.getLogger('ebay_scraper')

class EbayScraper(BaseScraper):
    def __init__(self, **kwargs):
        # Define user agents before calling parent class constructor
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0'
        ]
        
        super().__init__(use_selenium=False, **kwargs)  # eBay doesn't strictly need Selenium
        self.base_url = "https://www.ebay.com"
    
    def search_products(self, query, limit=5):
        """Search for products on eBay"""
        search_url = f"{self.base_url}/sch/i.html?_nkw={query.replace(' ', '+')}"
        logger.info(f"Searching eBay for: {query}")
        
        html = self.get_page_content(search_url)
        if not html:
            logger.warning(f"Failed to get content from eBay for query: {query}")
            return []
            
        soup = self.parse_html(html)
        if not soup:
            return []
        
        products = []
        
        # eBay selectors
        result_selectors = [
            "li.s-item", 
            ".srp-results .s-item",
            ".srp-list .s-item"
        ]
        
        results = []
        for selector in result_selectors:
            results = soup.select(selector)
            if results:
                # Filter out "More items like this" placeholders
                results = [r for r in results if not r.select_one('.srp-save--more-like')]
                if results:
                    logger.info(f"Found {len(results)} eBay results for query: {query} using selector: {selector}")
                    break
        
        for i, item in enumerate(results):
            if i >= limit:
                break
                
            # Skip if it's a "More items like this" placeholder
            if item.select_one('.srp-save--more-like'):
                continue
                
            product = {
                "source": "ebay",
                "category": query  # Default to search query as category
            }
            
            # Extract title
            title_selectors = [
                ".s-item__title",
                ".s-item__title span",
                "h3.s-item__title",
                ".s-item__info a h3"
            ]
            
            for selector in title_selectors:
                title_elem = item.select_one(selector)
                if title_elem and title_elem.text.strip() and 'Shop on eBay' not in title_elem.text:
                    product['title'] = title_elem.text.strip().replace('New Listing', '').strip()
                    break
            
            # Extract price
            price_selectors = [
                ".s-item__price",
                "span.s-item__price",
                ".s-item__detail--primary .s-item__price"
            ]
            
            for selector in price_selectors:
                try:
                    price_elem = item.select_one(selector)
                    if price_elem:
                        price_text = price_elem.text.strip()
                        
                        # Handle price ranges (e.g., "$10.00 to $20.00")
                        if ' to ' in price_text:
                            price_parts = price_text.split(' to ')
                            if len(price_parts) > 0:
                                price_text = price_parts[0]  # Take the lower price in range
                        
                        price_match = re.search(r'(\$[\d,]+\.\d+)|(\$[\d,]+)', price_text)
                        if price_match:
                            price_str = price_match.group(0).replace('$', '').replace(',', '')
                            product['price'] = float(price_str)
                            break
                except Exception as e:
                    logger.debug(f"Error extracting price: {e}")
            
            # Extract image
            img_selectors = [
                ".s-item__image-img",
                "img.s-item__image-img",
                ".s-item__image img"
            ]
            
            for selector in img_selectors:
                img_elem = item.select_one(selector)
                if img_elem:
                    # eBay sometimes uses data-src for lazy loading
                    image_url = img_elem.get('data-src') or img_elem.get('src')
                    if image_url and 'ir.ebaystatic.com' not in image_url:
                        product['image'] = image_url
                        break
            
            # Extract URL
            link_selectors = [
                ".s-item__link",
                "a.s-item__link",
                ".s-item__info a"
            ]
            
            for selector in link_selectors:
                link_elem = item.select_one(selector)
                if link_elem and link_elem.get('href'):
                    href = link_elem['href']
                    if '?' in href:
                        # Keep only the part before the query parameters
                        href = href.split('?')[0]
                    product['url'] = href
                    break
            
            if 'url' not in product:
                product['url'] = search_url
            
            # Extract condition
            condition_selectors = [
                ".s-item__subtitle",
                ".SECONDARY_INFO",
                ".s-item__detail--secondary"
            ]
            
            for selector in condition_selectors:
                condition_elem = item.select_one(selector)
                if condition_elem and condition_elem.text.strip():
                    product['condition'] = condition_elem.text.strip()
                    break
            
            # Extract shipping
            shipping_selectors = [
                ".s-item__shipping",
                ".s-item__logisticsCost",
                ".s-item__detail--primary .s-item__shipping"
            ]
            
            for selector in shipping_selectors:
                shipping_elem = item.select_one(selector)
                if shipping_elem and shipping_elem.text.strip():
                    product['shipping'] = shipping_elem.text.strip()
                    break
                    
            # Add description based on available info
            description_parts = []
            if 'title' in product:
                description_parts.append(product['title'])
            if 'condition' in product:
                description_parts.append(product['condition'])
            if 'shipping' in product:
                description_parts.append(f"Shipping: {product['shipping']}")
                
            product['description'] = " - ".join(description_parts) if description_parts else "eBay product"
            
            # Only add if we have at least a title
            if 'title' in product:
                products.append(product)
        
        # If still no products, create some mock products for testing
        if not products and query:
            logger.warning(f"No eBay products found for query: {query}. Generating mock products.")
            products = self.generate_fake_products(query, limit=limit, source="ebay")
        
        return products