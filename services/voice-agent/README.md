# Voice Agent (Speech-to-Text) — VoiceMart

FastAPI service that converts uploaded audio to text using faster-whisper.

## Run

```bash
python -m venv venv
source venv/bin/activate         # Windows: .\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
