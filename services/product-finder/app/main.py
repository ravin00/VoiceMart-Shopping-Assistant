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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class Product(BaseModel):
    id: str
    title: str
    price: float
    currency: str = "USD"
    image_url: Optional[str] = None
    description: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    rating: Optional[float] = None
    availability: Optional[str] = None
    url: Optional[str] = None
    source: str  # Which API provided this product

class ProductSearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    brand: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=50)

class ProductSearchResponse(BaseModel):
    products: List[Product]
    total_results: int
    query: str
    filters_applied: Dict[str, Any]

class ProductDetailsResponse(BaseModel):
    product: Product
    additional_info: Optional[Dict[str, Any]] = None

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
    Search for products across multiple APIs.
    """
    try:
        from .api_clients import search_products_unified
        result = await search_products_unified(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Product search failed: {str(e)}")

# Product details endpoint
@app.get("/v1/products:details")
async def get_product_details(product_id: str, source: str = "fakestore"):
    """
    Get detailed information about a specific product.
    """
    try:
        from .api_clients import get_product_details
        result = await get_product_details(product_id, source)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get product details: {str(e)}")

# Product categories endpoint
@app.get("/v1/products:categories")
async def get_product_categories():
    """
    Get available product categories.
    """
    try:
        from .api_clients import get_categories
        categories = await get_categories()
        return {
            "categories": categories,
            "total": len(categories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")
