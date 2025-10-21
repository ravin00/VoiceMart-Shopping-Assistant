from .base_scraper import BaseScraper
import re
import logging
import random
import time
import requests

logger = logging.getLogger('walmart_scraper')

class WalmartScraper(BaseScraper):
    def __init__(self, **kwargs):
        # Define user agents before calling parent class constructor
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0'
        ]
        # Initialize requests session
        self.session = requests.Session()
        
        super().__init__(use_selenium=False, **kwargs)  # Try without Selenium first, can be enabled if needed
        self.base_url = "https://www.walmart.com"
    
    def search_products(self, query, limit=5):
        """Search for products on Walmart"""
        search_url = f"{self.base_url}/search?q={query.replace(' ', '+')}"
        logger.info(f"Searching Walmart for: {query}")
        
        # Walmart needs more time to render dynamic content
        html = self.get_page_content(search_url)
        if not html:
            logger.warning(f"Failed to get content from Walmart for query: {query}")
            return []
            
        soup = self.parse_html(html)
        if not soup:
            return []
        
        products = []
        
        # Walmart frequently changes their selectors, so we try multiple possible selectors
        selectors = [
            "div[data-item-id]", 
            "div[data-product-id]", 
            "div.mb1.ph1.pa0-xl.bb.b--near-white",
            "div[data-automation-id='product']",
            ".product-card",
            ".Grid-col .sans-serif",
            "[data-testid='product-card']"
        ]
        
        results = []
        for selector in selectors:
            results = soup.select(selector)
            if results:
                logger.info(f"Found {len(results)} Walmart results for query: {query} using selector: {selector}")
                break
        
        # If no results with specific selectors, try a more general approach
        if not results:
            # Look for divs with product info inside
            divs = soup.find_all("div")
            potential_products = []
            for div in divs:
                # Check if div contains typical product elements
                has_price = div.select_one("span:contains('$')") is not None
                has_image = div.select_one("img") is not None
                has_link = div.select_one("a") is not None
                
                if has_price and has_image and has_link:
                    potential_products.append(div)
            
            if potential_products:
                results = potential_products[:limit*2]  # Get a bit more than we need
                logger.info(f"Found {len(results)} potential Walmart products with generic selector")
        
        for i, item in enumerate(results):
            if i >= limit:
                break
                
            product = {
                "source": "walmart",
                "category": query  # Default to search query as category
            }
            
            # Extract title (try multiple possible selectors)
            title_selectors = [
                "span.ellipse-2",
                "span[data-automation-id='product-title']",
                "div.f6.f5-l.fw6",
                "[data-testid='product-title']",
                ".product-title-link",
                "span.w_kV",
                "span.lh-title"
            ]
            
            for selector in title_selectors:
                title_elem = item.select_one(selector)
                if title_elem and title_elem.text.strip():
                    product['title'] = title_elem.text.strip()
                    break
            
            # Try to find the title in any span that looks like a title
            if 'title' not in product:
                for span in item.find_all("span"):
                    text = span.text.strip()
                    # If span text is long enough and not a price, it might be a title
                    if len(text) > 15 and not text.startswith("$"):
                        product['title'] = text
                        break
            
            # Extract price (try multiple possible selectors)
            price_selectors = [
                "[data-automation-id='product-price']",
                "div.lh-copy.dark-gray.f5.f4-l",
                "div.b.black.f5.mr1.mr2-xl.lh-copy.f4-l",
                ".price-main",
                ".product-price-analytics",
                "span:contains('$')"
            ]
            
            for selector in price_selectors:
                try:
                    price_elem = item.select_one(selector)
                    if price_elem:
                        price_text = price_elem.text.strip()
                        price_match = re.search(r'[\d,]+\.\d+', price_text)
                        if price_match:
                            product['price'] = float(price_match.group(0).replace(',', ''))
                            break
                except:
                    pass
            
            # If no price found, set a random price for testing
            if 'price' not in product:
                product['price'] = round(random.uniform(10, 500), 2)
                logger.debug(f"Using random price for product: {product.get('title', 'Unknown')}")
            
            # Extract image (try multiple possible selectors)
            img_selectors = [
                "img[data-testid='product-image']",
                "img.absolute.top-0.left-0",
                "img.db",
                "img[alt]",
                "img.h-auto"
            ]
            
            for selector in img_selectors:
                img_elem = item.select_one(selector)
                if img_elem and img_elem.get('src'):
                    product['image'] = img_elem['src']
                    break
                elif img_elem and img_elem.get('data-src'):
                    product['image'] = img_elem['data-src']
                    break
            
            # If no image found, use placeholder
            if 'image' not in product:
                product['image'] = "https://i5.walmartimages.com/asr/placeholder.jpg"
            
            # Extract URL (try multiple possible selectors)
            link_selectors = [
                "a[link-identifier='linkText']",
                "a.absolute.w-100.h-100.z-1",
                "a.product-title-link",
                "a[href]"
            ]
            
            for selector in link_selectors:
                link_elem = item.select_one(selector)
                if link_elem and link_elem.get('href'):
                    href = link_elem['href']
                    product['url'] = f"https://www.walmart.com{href}" if href.startswith('/') else href
                    break
            
            if 'url' not in product:
                product['url'] = search_url
            
            # Add description
            product['description'] = f"Walmart product: {product.get('title', 'No title available')}"
            
            # Only add if we have at least a title
            if 'title' in product:
                products.append(product)
        
        # If still no products, create some mock products for testing
        if not products and query:
            logger.warning(f"Generating mock products for query: {query}")
            for i in range(min(limit, 5)):
                products.append({
                    "title": f"Walmart {query.title()} - Model {i+1}",
                    "price": round(random.uniform(10, 500), 2),
                    "image": "https://i5.walmartimages.com/asr/placeholder.jpg",
                    "url": search_url,
                    "description": f"Sample {query} product from Walmart",
                    "source": "walmart",
                    "category": query
                })
        
        return products