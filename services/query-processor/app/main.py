import os
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .schemas import ParseIn, ParseOut
from .processor import process_query

API_KEY = os.getenv("QP_API_KEY", "dev-key")

app = FastAPI(
    title="VoiceMart Query Processor",
    version="1.0.0",
    description="Query Processing API for the VoiceMart Shopping Assistant"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "VoiceMart Query Processor API",
        "docs": "/docs",
        "health": "/health",
        "parse_endpoint": "/parse",
        "test_endpoint": "/v1/query:process"
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/parse", response_model=ParseOut)
def parse(inp: ParseIn, x_api_key: str | None = Header(None)):
    """
    Internal API endpoint for query processing.
    Requires API key authentication.
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    result = process_query(inp.text, user_id=inp.user_id, locale=inp.locale)
    return result

@app.post("/v1/query:process", response_model=ParseOut)
def test_query_process(inp: ParseIn):
    """
    Test endpoint for query processing - mirrors the voice agent interface.
    No authentication required for testing purposes.
    """
    result = process_query(inp.text, user_id=inp.user_id, locale=inp.locale)
    return result
