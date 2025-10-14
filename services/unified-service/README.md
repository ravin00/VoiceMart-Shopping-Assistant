# VoiceMart Unified Service

This is the unified service that combines Speech-to-Text and Query Processing functionality on port 8000.

## Features

- **Speech-to-Text**: Transcribe audio files to text
- **Query Processing**: Process text queries and extract intent, entities, and actions
- **Voice Understanding**: Complete pipeline from audio to structured query results

## Endpoints

- `GET /` - Service information
- `GET /health` - Health check
- `POST /v1/stt:transcribe` - Transcribe audio to text
- `POST /v1/query:process` - Process text query
- `POST /v1/voice:understand` - Complete voice understanding pipeline

## Running the Service

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python run.py
```

The service will be available at:
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Testing

You can test all functionality through the Swagger UI at http://localhost:8000/docs
