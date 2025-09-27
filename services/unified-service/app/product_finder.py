# app/product_finder.py - Product finder integration for unified service

import requests
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from .main import Product, ProductSearchRequest, ProductSearchResponse, ProductDetailsResponse
import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
FAKESTORE_API = "https://fakestoreapi.com"
EBAY_API = "https://api.ebay.com/buy/browse/v1"
WALMART_API = "https://developer.api.walmartlabs.com/v1"

# API Keys (set in .env file)
EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID", "")
WALMART_API_KEY = os.getenv("WALMART_API_KEY", "")

class FakeStoreClient:
    """FakeStore API client - Free, no authentication required"""
    
    @staticmethod
    async def search_products(request: ProductSearchRequest) -> List[Product]:
        """Search products using FakeStore API"""
        try:
            # FakeStore doesn't have search, so we'll get all products and filter
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{FAKESTORE_API}/products") as response:
                    if response.status == 200:
                        data = await response.json()
                        products = []
                        
                        for item in data:
                            # Apply filters
                            if request.category and request.category.lower() not in item.get('category', '').lower():
                                continue
                                
                            if request.min_price and item.get('price', 0) < request.min_price:
                                continue
                                
                            if request.max_price and item.get('price', 0) > request.max_price:
                                continue
                                
                            if request.brand and request.brand.lower() not in item.get('title', '').lower():
                                continue
                            
                            # Check if query matches
                            if request.query.lower() not in item.get('title', '').lower() and \
                               request.query.lower() not in item.get('description', '').lower():
                                continue
                            
                            product = Product(
                                id=str(item['id']),
                                title=item['title'],
                                price=float(item['price']),
                                currency="USD",
                                image_url=item.get('image'),
                                description=item.get('description'),
                                category=item.get('category'),
                                rating=item.get('rating', {}).get('rate'),
                                availability="in_stock",
                                url=f"{FAKESTORE_API}/products/{item['id']}",
                                source="fakestore"
                            )
                            products.append(product)
                            
                            if len(products) >= request.limit:
                                break
                        
                        return products
                    else:
                        return []
        except Exception as e:
            print(f"FakeStore API error: {e}")
            return []

    @staticmethod
    async def get_product_details(product_id: str) -> Optional[Product]:
        """Get product details from FakeStore"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{FAKESTORE_API}/products/{product_id}") as response:
                    if response.status == 200:
                        item = await response.json()
                        return Product(
                            id=str(item['id']),
                            title=item['title'],
                            price=float(item['price']),
                            currency="USD",
                            image_url=item.get('image'),
                            description=item.get('description'),
                            category=item.get('category'),
                            rating=item.get('rating', {}).get('rate'),
                            availability="in_stock",
                            url=f"{FAKESTORE_API}/products/{item['id']}",
                            source="fakestore"
                        )
                    return None
        except Exception as e:
            print(f"FakeStore details error: {e}")
            return None

class eBayClient:
    """eBay API client"""
    
    @staticmethod
    async def search_products(request: ProductSearchRequest) -> List[Product]:
        """Search products using eBay API"""
        if not EBAY_CLIENT_ID:
            return []
            
        try:
            # eBay API requires OAuth, simplified version here
            # In production, you'd implement proper OAuth flow
            headers = {
                'Authorization': f'Bearer {EBAY_CLIENT_ID}',
                'Content-Type': 'application/json'
            }
            
            params = {
                'q': request.query,
                'limit': min(request.limit, 20)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{EBAY_API}/item_summary/search", 
                                      headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        products = []
                        
                        for item in data.get('itemSummaries', []):
                            product = Product(
                                id=item.get('itemId', ''),
                                title=item.get('title', ''),
                                price=float(item.get('price', {}).get('value', 0)),
                                currency=item.get('price', {}).get('currency', 'USD'),
                                image_url=item.get('image', {}).get('imageUrl'),
                                description=item.get('shortDescription'),
                                category=item.get('categories', [{}])[0].get('categoryName'),
                                availability="available" if item.get('buyingOptions') else "unavailable",
                                url=item.get('itemWebUrl'),
                                source="ebay"
                            )
                            products.append(product)
                        
                        return products
                    return []
        except Exception as e:
            print(f"eBay API error: {e}")
            return []

class WalmartClient:
    """Walmart API client"""
    
    @staticmethod
    async def search_products(request: ProductSearchRequest) -> List[Product]:
        """Search products using Walmart API"""
        if not WALMART_API_KEY:
            return []
            
        try:
            params = {
                'query': request.query,
                'apiKey': WALMART_API_KEY,
                'numItems': min(request.limit, 25)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{WALMART_API}/search", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        products = []
                        
                        for item in data.get('items', []):
                            product = Product(
                                id=str(item.get('itemId', '')),
                                title=item.get('name', ''),
                                price=float(item.get('salePrice', item.get('msrp', 0))),
                                currency="USD",
                                image_url=item.get('mediumImage'),
                                description=item.get('shortDescription'),
                                category=item.get('categoryPath'),
                                rating=item.get('customerRating'),
                                availability="in_stock" if item.get('stock') == 'Available' else "out_of_stock",
                                url=item.get('productUrl'),
                                source="walmart"
                            )
                            products.append(product)
                        
                        return products
                    return []
        except Exception as e:
            print(f"Walmart API error: {e}")
            return []

# Unified search function
async def search_products(request: ProductSearchRequest) -> ProductSearchResponse:
    """Search products across all available APIs"""
    
    # Run searches in parallel
    tasks = [
        FakeStoreClient.search_products(request),
        eBayClient.search_products(request),
        WalmartClient.search_products(request)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Combine results
    all_products = []
    for result in results:
        if isinstance(result, list):
            all_products.extend(result)
        elif isinstance(result, Exception):
            print(f"API search error: {result}")
    
    # Remove duplicates based on title similarity
    unique_products = []
    seen_titles = set()
    
    for product in all_products:
        title_lower = product.title.lower()
        if title_lower not in seen_titles:
            seen_titles.add(title_lower)
            unique_products.append(product)
    
    # Sort by relevance (simple implementation)
    unique_products.sort(key=lambda x: (
        request.query.lower() in x.title.lower(),
        x.rating or 0
    ), reverse=True)
    
    # Limit results
    limited_products = unique_products[:request.limit]
    
    return ProductSearchResponse(
        products=limited_products,
        total_results=len(limited_products),
        query=request.query,
        filters_applied={
            "category": request.category,
            "min_price": request.min_price,
            "max_price": request.max_price,
            "brand": request.brand
        }
    )

async def get_product_details(product_id: str, source: str = "fakestore") -> ProductDetailsResponse:
    """Get detailed product information"""
    
    if source == "fakestore":
        product = await FakeStoreClient.get_product_details(product_id)
    else:
        # For other sources, you'd implement specific detail fetching
        product = None
    
    if product:
        return ProductDetailsResponse(
            product=product,
            additional_info={
                "source": source,
                "fetched_at": "2024-01-01T00:00:00Z"  # In production, use actual timestamp
            }
        )
    else:
        raise Exception(f"Product not found: {product_id}")

async def get_categories() -> List[Dict[str, Any]]:
    """Get available product categories"""
    
    # FakeStore categories
    fakestore_categories = [
        {"id": "electronics", "name": "Electronics", "source": "fakestore"},
        {"id": "jewelery", "name": "Jewelry", "source": "fakestore"},
        {"id": "men's clothing", "name": "Men's Clothing", "source": "fakestore"},
        {"id": "women's clothing", "name": "Women's Clothing", "source": "fakestore"}
    ]
    
    # You can add more categories from other APIs
    return fakestore_categories
