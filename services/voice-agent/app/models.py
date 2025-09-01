from pydantic import BaseModel, Field
from typing import List, Optional

class TranscriptionSegment(BaseModel):
    start: float
    end: float
    text: str

class TranscriptionResult(BaseModel):
    text: str = Field(..., description="Full transcription")
    language: Optional[str] = None
    duration_sec: Optional[float] = None
    segments: Optional[List[TranscriptionSegment]] = None
