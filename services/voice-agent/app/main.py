# app/main.py  (voice-agent)

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from .stt_engine import transcribe_audio, is_allowed_mime
from .config import MAX_UPLOAD_MB
from .models import TranscriptionResult

# -------------------------------------------------------
# Original query-engine (kept for reference, now disabled)
# -------------------------------------------------------
# from .query_engine.processor import process_query  # <-- OLD in-process import (commented as requested)

# Pydantic / typing (unchanged)
from pydantic import BaseModel
from typing import Optional, Any, Dict

# -------------------------------------------------------
# NEW: call external query-processor over HTTP
# -------------------------------------------------------
import os, requests
from dotenv import load_dotenv

load_dotenv()  # allow QP_URL / QP_KEY to be set in .env

QP_URL = os.getenv("QP_URL", "http://localhost:8002/parse")
QP_KEY = os.getenv("QP_KEY", "dev-key")

def call_query_processor(text: str, user_id: Optional[str], locale: Optional[str]):
    """
    Send text to the standalone query-processor service and return its JSON.
    """
    payload = {"text": text, "user_id": user_id, "locale": (locale or "en-US")}
    headers = {"x-api-key": QP_KEY, "Content-Type": "application/json"}
    r = requests.post(QP_URL, json=payload, headers=headers, timeout=8)
    r.raise_for_status()
    return r.json()
# -------------------------------------------------------


app = FastAPI(
    title="VoiceMart Voice Agent",
    version="1.0.0",
    description="Speech-to-Text API for the VoiceMart Shopping Assistant"
)

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


# CORS: allow teammates / frontend to call you during dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten later to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# root endpoint
@app.get("/")
async def root():
    return {
        "message": "VoiceMart Voice Agent API",
        "docs": "/docs",
        "health": "/health",
        "stt_endpoint": "/v1/stt:transcribe"
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/v1/stt:transcribe", response_model=TranscriptionResult)
async def stt_transcribe(file: UploadFile = File(...)):
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


@app.post("/v1/query:process", response_model=QueryResponse)
async def query_process(req: QueryRequest):
    # ---------------------------
    # OLD (kept, now disabled)
    # ---------------------------
    # result = process_query(req.text, user_id=req.user_id, locale=req.locale)
    # return result

    # ---------------------------
    # NEW: delegate to query-processor service
    # ---------------------------
    qp = call_query_processor(req.text, req.user_id, req.locale)
    return qp


@app.post("/v1/voice:understand", response_model=VoiceUnderstandResponse)
async def voice_understand(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
    locale: Optional[str] = Form("en-US"),
):
    # --- reuse the same validations as your STT route ---
    content_type = file.content_type or ""
    if not is_allowed_mime(content_type):
        raise HTTPException(status_code=415, detail=f"Unsupported media type: {content_type}")

    contents = await file.read()
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large (> {MAX_UPLOAD_MB}MB)")

    # --- STT ---
    stt_result = transcribe_audio(contents, detect_language=True)  # TranscriptionResult
    transcript_text = stt_result.text or ""

    # ---------------------------
    # OLD (kept, now disabled)
    # ---------------------------
    # qp_dict = process_query(transcript_text, user_id=user_id, locale=locale)

    # ---------------------------
    # NEW: call external query-processor
    # ---------------------------
    qp_dict = call_query_processor(transcript_text, user_id, locale)

    # --- Return both ---
    return VoiceUnderstandResponse(
        transcript=stt_result,
        query=QueryResponse(**qp_dict)
    )
