# app/models.py - Data models for unified service

from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List

# Transcription models
class TranscriptionSegment(BaseModel):
    start: float
    end: float
    text: str

class TranscriptionResult(BaseModel):
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    duration: Optional[float] = None
    segments: Optional[List[TranscriptionSegment]] = None

# Query processing models
class QueryRequest(BaseModel):
    text: str
    user_id: Optional[str] = None
    locale: Optional[str] = "en-US"

class QueryResponse(BaseModel):
    intent: str
    confidence: float
    slots: Dict[str, Any]
    reply: str
    action: Dict[str, Any]
    user_id: Optional[str] = None
    locale: Optional[str] = "en-US"

# Product models
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

# Voice understanding response
class VoiceUnderstandResponse(BaseModel):
    transcript: TranscriptionResult
    query: QueryResponse
    products: Optional[List[Product]] = None  # Products found based on query
    product_search_performed: bool = False  # Whether product search was performed