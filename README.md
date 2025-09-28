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

System Diagram
![WhatsApp Image 2025-09-28 at 15 43 17](https://github.com/user-attachments/assets/d61e81d9-a6a6-4bb0-80b0-65c3e70d1696)

Sequence Diagram
![WhatsApp Image 2025-09-28 at 15 43 17](https://github.com/user-attachments/assets/bb778df8-ff6b-409f-a93d-01d3bb0648d3)

1. Pricing Plans (in LKR)
Plan	Features	Price (LKR)
Basic (SME)	1000 queries/month, Sinhala/English, basic reports	Rs. 5,000 / mo
Standard	10,000 queries, multi-language, API integration	Rs. 25,000 / mo
Enterprise	Unlimited queries, SLA, advanced analytics	Rs. 100,000 / mo
Integration	Custom setup + training for enterprise deployment	Rs. 200,000 one-off

👉 The plans are structured for SMEs, mid-sized businesses, and large enterprises.

2. Target Market

Large retailers (Keells, Cargills, Glomark)

Online marketplaces (Kapruka, Wasi.lk)

SMEs with Shopify/WooCommerce shops

Regional expansion potential (Tamil Nadu, Maldives)

3. Revenue Model

SaaS (monthly subscriptions)

One-time enterprise integration fees

Custom enterprise SLAs and analytics dashboards

4. Value Proposition

Voice-based shopping → faster, easier experience

Accessible for non-tech-savvy customers

Sinhala + English support (Tamil in future)

Competitive advantage for AI-driven e-commerce

5. Cost Considerations (Monthly, in LKR)

Cloud hosting / infra → Rs. 25,000

STT compute costs → Rs. 40,000

Developer salaries (small team) → Rs. 300,000

Marketing & Sales → Rs. 100,000

Admin & Legal → Rs. 35,000
Total ~ Rs. 500,000 / month

6. Revenue Projection (First Year)

Months 1–3: 3 SMEs + 1 Enterprise → ~Rs. 350,000

Month 6: 10 SMEs + 3 Enterprises → ~Rs. 1,300,000

Month 12: 25 SMEs + 5 Enterprises → ~Rs. 3,250,000

👉 Break-even in ~6–7 months.
👉 Year 1 profit ~ Rs. 3–3.5 Million.

