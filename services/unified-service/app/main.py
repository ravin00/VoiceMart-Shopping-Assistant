# app/main.py (unified-service)

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any, Dict
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

class VoiceUnderstandResponse(BaseModel):
    transcript: TranscriptionResult
    query: QueryResponse

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
            "voice_understand": "/v1/voice:understand"
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

    # Return both transcription and query processing results
    return VoiceUnderstandResponse(
        transcript=stt_result,
        query=QueryResponse(**qp_dict)
    )
