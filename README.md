# VoiceMart-Shopping-Assistant
Voice Shopping Assistant - Voice to Text Agent, Query Processor, Product Finder

# After cloning the repo:
# Go to the service folder
cd VoiceMart-Shopping-Assistant/services/voice-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate    # macOS/Linux
# OR
.\venv\Scripts\Activate.ps1 # Windows (PowerShell)

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install FFmpeg (one time only)
# macOS:
brew install ffmpeg
# Ubuntu/Debian:
sudo apt update && sudo apt install -y ffmpeg
# Windows: Download FFmpeg and add to PATH.

# Run the service
uvicorn app.main:app --reload --port 8001
# Test in browser
# Open: http://127.0.0.1:8001/docs
# Try POST /v1/stt:transcribe → upload a short .wav or .mp3 file.

![WhatsApp Image 2025-09-28 at 15 43 17](https://github.com/user-attachments/assets/d61e81d9-a6a6-4bb0-80b0-65c3e70d1696)
