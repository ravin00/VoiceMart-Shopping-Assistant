#!/usr/bin/env bash
# Run the product-finder service with web scraping capabilities

# Install required packages
echo "Installing required packages..."
pip install -r requirements.txt

# Create cache directories if they don't exist
mkdir -p app/cache/scrapes
mkdir -p app/cache/api

# Run the FastAPI app
echo "Starting Product Finder service with web scraping..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000