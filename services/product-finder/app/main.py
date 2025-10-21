# app/main.py (product-finder)

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import requests
import os
import logging
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
    Search for products across multiple APIs.
    """
    try:
        logger = logging.getLogger("api")
        logger.info(f"Received search request: {request.dict()}")
        from .api_clients import search_products_unified
        result = await search_products_unified(request)
        logger.info(f"Search returned {len(result.products)} products")
        return result
    except Exception as e:
        logger.error(f"Product search failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Product search failed: {str(e)}")

# Alias without colon to avoid %3A encoding issues in some clients
@app.post("/v1/products/search", response_model=ProductSearchResponse)
async def search_products_alias(request: ProductSearchRequest):
    try:
        logger = logging.getLogger("api")
        logger.info(f"Received search request at alias endpoint: {request.dict()}")
        from .api_clients import search_products_unified
        result = await search_products_unified(request)
        logger.info(f"Search returned {len(result.products)} products")
        return result
    except Exception as e:
        logger.error(f"Product search failed: {str(e)}", exc_info=True)
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

# Alias without colon
@app.get("/v1/products/details")
async def get_product_details_alias(product_id: str, source: str = "fakestore"):
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

# Alias without colon
@app.get("/v1/products/categories")
async def get_product_categories_alias():
    try:
        from .api_clients import get_categories
        categories = await get_categories()
        return {
            "categories": categories,
            "total": len(categories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")










