# app/main.py (unified-service)

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
import os
import requests
from dotenv import load_dotenv

# Import local modules
from .stt_engine import transcribe_audio, is_allowed_mime
from .config import MAX_UPLOAD_MB
from .models import TranscriptionResult
from .processor import process_query

load_dotenv()

app = FastAPI(
    title="VoiceMart Unified Service",
    version="1.0.0",
    description="Unified API combining Speech-to-Text and Query Processing for VoiceMart Shopping Assistant"
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

# Product models (defined first for type hints)
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

class VoiceUnderstandResponse(BaseModel):
    transcript: TranscriptionResult
    query: QueryResponse
    products: Optional[List[Product]] = None  # Products found based on query
    product_search_performed: bool = False  # Whether product search was performed

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
        "message": "VoiceMart Unified Service API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "stt": "/v1/stt:transcribe",
            "query": "/v1/query:process", 
            "voice_understand": "/v1/voice:understand",
            "product_search": "/v1/products:search",
            "product_details": "/v1/products:details",
            "product_categories": "/v1/products:categories"
        }
    }

@app.get("/health")
def health():
    return {"status": "ok"}

# Speech-to-Text endpoint
@app.post("/v1/stt:transcribe", response_model=TranscriptionResult)
async def stt_transcribe(file: UploadFile = File(...)):
    """
    Transcribe audio file to text.
    """
    # Basic validations
    content_type = file.content_type or ""
    if not is_allowed_mime(content_type):
        raise HTTPException(status_code=415, detail=f"Unsupported media type: {content_type}")

    contents = await file.read()
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large (> {MAX_UPLOAD_MB}MB)")

    try:
        result = transcribe_audio(contents, detect_language=True)
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Transcription failed: {str(e)}")

# Query processing endpoint
@app.post("/v1/query:process", response_model=QueryResponse)
async def query_process(req: QueryRequest):
    """
    Process text query and extract intent, entities, and actions.
    """
    result = process_query(req.text, user_id=req.user_id, locale=req.locale)
    return result

# Combined voice understanding endpoint
@app.post("/v1/voice:understand", response_model=VoiceUnderstandResponse)
async def voice_understand(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
    locale: Optional[str] = Form("en-US"),
):
    """
    Complete voice understanding: transcribe audio and process the resulting text.
    """
    # Validate audio file
    content_type = file.content_type or ""
    if not is_allowed_mime(content_type):
        raise HTTPException(status_code=415, detail=f"Unsupported media type: {content_type}")

    contents = await file.read()
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large (> {MAX_UPLOAD_MB}MB)")

    # Transcribe audio
    stt_result = transcribe_audio(contents, detect_language=True)
    transcript_text = stt_result.text or ""

    # Process the transcript
    qp_dict = process_query(transcript_text, user_id, locale)
    query_response = QueryResponse(**qp_dict)
    
    # Check if we should search for products
    products = None
    product_search_performed = False
    
    # Search for products if the intent is product-related
    if query_response.intent in ["search_product", "add_to_cart"] and transcript_text.strip():
        try:
            from .product_finder import search_products
            
            # Build search request from query processing results
            search_request = ProductSearchRequest(
                query=transcript_text,  # Use original transcript as search query
                category=qp_dict.get("slots", {}).get("category"),
                min_price=qp_dict.get("slots", {}).get("price_min"),
                max_price=qp_dict.get("slots", {}).get("price_max"),
                brand=qp_dict.get("slots", {}).get("brand"),
                limit=5  # Limit to 5 products for voice response
            )
            
            # Perform product search
            search_result = await search_products(search_request)
            products = search_result.products
            product_search_performed = True
            
        except Exception as e:
            print(f"Product search failed: {e}")
            # Continue without products if search fails
            pass

    # Return complete voice understanding results
    return VoiceUnderstandResponse(
        transcript=stt_result,
        query=query_response,
        products=products,
        product_search_performed=product_search_performed
    )

# Product search endpoint
@app.post("/v1/products:search", response_model=ProductSearchResponse)
async def search_products_endpoint(request: ProductSearchRequest):
    """
    Search for products based on query and filters.
    """
    try:
        from .product_finder import search_products
        result = await search_products(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Product search failed: {str(e)}")

# Product details endpoint
@app.post("/v1/products:details")
async def get_product_details_endpoint(product_id: str, source: str = "fakestore"):
    """
    Get detailed information about a specific product.
    """
    try:
        from .product_finder import get_product_details
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
        from .product_finder import get_categories
        categories = await get_categories()
        return {
            "categories": categories,
            "total": len(categories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")
