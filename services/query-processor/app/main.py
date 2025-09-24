import os
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .schemas import ParseIn, ParseOut
from .processor import process_query

API_KEY = os.getenv("QP_API_KEY", "dev-key")

app = FastAPI(title="Query Processor", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/parse", response_model=ParseOut)
def parse(inp: ParseIn, x_api_key: str | None = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    result = process_query(inp.text, user_id=inp.user_id, locale=inp.locale)
    return result
