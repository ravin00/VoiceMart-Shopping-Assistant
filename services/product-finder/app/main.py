# app/main.py (product-finder)

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="VoiceMart Product Finder",
    version="1.0.0",
    description="Product search and discovery API for VoiceMart Shopping Assistant"
)

# Initialize scraper client
from .api_clients import CachedScraperClient
scraper_client = CachedScraperClient()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models (import from dedicated models module to avoid duplication)
from .models import (
    Product,
    ProductSearchRequest,
    ProductSearchResponse,
    ProductDetailsResponse,
)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "VoiceMart Product Finder API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "search": "/v1/products:search",
            "details": "/v1/products:details",
            "categories": "/v1/products:categories"
        }
    }

@app.get("/health")
def health():
    return {"status": "ok"}

# Product search endpoint
@app.post("/v1/products:search", response_model=ProductSearchResponse)
async def search_products(request: ProductSearchRequest):
    """
    Search for products across multiple sources using web scraping.
    """
    try:
        # Convert the request to scraper parameters
        results = scraper_client.search_products(
            query=request.query,
            limit=request.limit
        )
        
        # Convert the results to the expected response format
        products = []
        for item in results:
            products.append(Product(
                id=f"{item.get('source', 'unknown')}_{len(products)}",
                title=item.get('title', 'Unknown Title'),
                price=item.get('price', 0.0),
                currency="USD",
                image_url=item.get('image'),
                description=item.get('description', ''),
                category=item.get('category', ''),
                availability="in_stock",
                url=item.get('url', ''),
                source=item.get('source', 'unknown')
            ))
            
        return ProductSearchResponse(
            products=products,
            total_results=len(products),
            query=request.query,
            filters_applied={
                "category": request.category,
                "min_price": request.min_price,
                "max_price": request.max_price,
                "brand": request.brand
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Product search failed: {str(e)}")

# Alias without colon to avoid %3A encoding issues in some clients
@app.post("/v1/products/search", response_model=ProductSearchResponse)
async def search_products_alias(request: ProductSearchRequest):
    """
    Search for products across multiple sources using web scraping.
    """
    return await search_products(request)

# Product details endpoint
@app.get("/v1/products:details")
async def get_product_details(product_id: str, source: str = "amazon"):
    """
    Get detailed information about a specific product.
    
    Note: Full product details require visiting the product URL directly,
    this endpoint returns basic information based on search results.
    """
    try:
        # For now, just search for the product ID
        results = scraper_client.search_products(product_id, limit=1, sources=[source] if source else None)
        
        if not results:
            raise HTTPException(status_code=404, detail=f"Product not found: {product_id}")
            
        item = results[0]
        product = Product(
            id=product_id,
            title=item.get('title', 'Unknown Title'),
            price=item.get('price', 0.0),
            currency="USD",
            image_url=item.get('image'),
            description=item.get('description', ''),
            category=item.get('category', ''),
            availability="in_stock",
            url=item.get('url', ''),
            source=item.get('source', 'unknown')
        )
        
        return {
            "product": product,
            "additional_info": {
                "source": source,
                "note": "Limited information available through search results"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get product details: {str(e)}")

# Alias without colon
@app.get("/v1/products/details")
async def get_product_details_alias(product_id: str, source: str = "amazon"):
    """
    Get detailed information about a specific product.
    """
    return await get_product_details(product_id, source)

# Product categories endpoint
@app.get("/v1/products:categories")
async def get_product_categories():
    """
    Get available product categories.
    """
    try:
        categories = scraper_client.get_product_categories()
        return {
            "categories": [{"id": cat.lower().replace(' ', '_'), 
                           "name": cat, 
                           "source": "scrapers"} for cat in categories],
            "total": len(categories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")

# Alias without colon
@app.get("/v1/products/categories")
async def get_product_categories_alias():
    """
    Get available product categories.
    """
    return await get_product_categories()


# Web Scraping Endpoints

@app.get("/v1/scraped/search")
async def scraped_search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Maximum number of results"),
    sources: Optional[str] = Query(None, description="Comma-separated list of sources (amazon,ebay,walmart)")
):
    """Search for products across multiple e-commerce sites using web scraping"""
    if not q:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    source_list = sources.split(",") if sources else None
    
    try:
        results = scraper_client.search_products(q, limit, source_list)
        return {"products": results, "query": q, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching products: {str(e)}")

@app.get("/v1/scraped/categories")
async def scraped_categories():
    """Get available product categories from scrapers"""
    try:
        categories = scraper_client.get_product_categories()
        return {"categories": categories, "count": len(categories)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")

@app.get("/v1/scraped/category/{category}")
async def scraped_products_by_category(
    category: str,
    limit: int = Query(10, description="Maximum number of results"),
    sources: Optional[str] = Query(None, description="Comma-separated list of sources (amazon,ebay,walmart)")
):
    """Get products for a specific category using web scraping"""
    source_list = sources.split(",") if sources else None
    
    try:
        results = scraper_client.get_products_by_category(category, limit, source_list)
        return {"products": results, "category": category, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching products by category: {str(e)}")

# Clean up resources on shutdown
@app.on_event("shutdown")
def shutdown_event():
    """Clean up resources when the application shuts down"""
    scraper_client.cleanup()
