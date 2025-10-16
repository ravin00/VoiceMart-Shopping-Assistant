#!/usr/bin/env bash

# Colors for better output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== VoiceMart Product Finder with Web Scraping ===${NC}"

echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt

echo -e "${YELLOW}Running test_scrapers.py to verify scrapers...${NC}"
python test_scrapers.py

echo -e "${YELLOW}Starting Product Finder service...${NC}"
echo -e "${GREEN}Swagger UI will be available at: http://localhost:8000/docs${NC}"
echo -e "${GREEN}ReDoc will be available at: http://localhost:8000/redoc${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the service${NC}"

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000