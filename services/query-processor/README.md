# Query Processor Service

This service extracts intents, slots, and filters from text queries.

## Run locally
```bash
cd services/query-processor
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
