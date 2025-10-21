# app/models.py - Product finder models

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

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
    sources: Optional[List[str]] = None  # e.g. ["amazon", "ebay", "walmart"]
    fallback: bool = True  # Whether to fall back to API-based search if web scraping yields no results

class ProductSearchResponse(BaseModel):
    products: List[Product]
    total_results: int
    query: str
    filters_applied: Dict[str, Any]

class ProductDetailsResponse(BaseModel):
    product: Product
    additional_info: Optional[Dict[str, Any]] = None
