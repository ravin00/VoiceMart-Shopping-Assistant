#!/usr/bin/env python3
"""
Complete test script for the unified VoiceMart service.
Tests all functionality: STT, Query Processing, and Product Search.
"""

import requests
import json
import os

# Service URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ Health check: {response.status_code} - {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_query_processing():
    """Test query processing endpoint"""
    print("\n🔍 Testing query processing...")
    
    test_queries = [
        "find Nike shoes under $100",
        "add 2 packs of Milo to cart",
        "show me the cart",
        "checkout"
    ]
    
    for query in test_queries:
        try:
            payload = {
                "text": query,
                "user_id": "test_user",
                "locale": "en-US"
            }
            response = requests.post(f"{BASE_URL}/v1/query:process", json=payload)
            result = response.json()
            print(f"✅ Query: '{query}'")
            print(f"   Intent: {result.get('intent')}")
            print(f"   Reply: {result.get('reply')}")
            print(f"   Confidence: {result.get('confidence')}")
            print()
        except Exception as e:
            print(f"❌ Query processing failed for '{query}': {e}")

def test_product_search():
    """Test product search endpoint"""
    print("🔍 Testing product search...")
    
    test_searches = [
        {"query": "laptop", "limit": 3},
        {"query": "shoes", "category": "men's clothing", "limit": 2},
        {"query": "phone", "min_price": 100, "max_price": 500, "limit": 2}
    ]
    
    for search in test_searches:
        try:
            response = requests.post(f"{BASE_URL}/v1/products:search", json=search)
            result = response.json()
            print(f"✅ Search: '{search['query']}'")
            print(f"   Found {result.get('total_results', 0)} products")
            for product in result.get('products', [])[:2]:  # Show first 2
                print(f"   - {product.get('title', 'N/A')} (${product.get('price', 0)})")
            print()
        except Exception as e:
            print(f"❌ Product search failed for '{search['query']}': {e}")

def test_product_details():
    """Test product details endpoint"""
    print("🔍 Testing product details...")
    
    try:
        # First search for a product to get an ID
        search_response = requests.post(f"{BASE_URL}/v1/products:search", json={"query": "laptop", "limit": 1})
        if search_response.status_code == 200:
            products = search_response.json().get('products', [])
            if products:
                product_id = products[0].get('id')
                print(f"✅ Getting details for product ID: {product_id}")
                
                details_response = requests.get(f"{BASE_URL}/v1/products:details?product_id={product_id}&source=fakestore")
                if details_response.status_code == 200:
                    details = details_response.json()
                    product = details.get('product', {})
                    print(f"   Title: {product.get('title', 'N/A')}")
                    print(f"   Price: ${product.get('price', 0)}")
                    print(f"   Category: {product.get('category', 'N/A')}")
                    return True
                else:
                    print(f"❌ Details request failed: {details_response.status_code}")
            else:
                print("❌ No products found to test details")
        else:
            print(f"❌ Search failed: {search_response.status_code}")
    except Exception as e:
        print(f"❌ Product details test failed: {e}")
    
    return False

def test_categories():
    """Test categories endpoint"""
    print("\n🔍 Testing categories...")
    
    try:
        response = requests.get(f"{BASE_URL}/v1/products:categories")
        if response.status_code == 200:
            result = response.json()
            categories = result.get('categories', [])
            print(f"✅ Found {len(categories)} categories:")
            for cat in categories:
                print(f"   - {cat.get('name', 'N/A')} ({cat.get('id', 'N/A')})")
            return True
        else:
            print(f"❌ Categories request failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Categories test failed: {e}")
    
    return False

def test_stt_with_sample_audio():
    """Test STT with sample audio file"""
    print("🔍 Testing Speech-to-Text...")
    
    # Check if sample audio exists
    sample_audio_path = "/Users/enithsamarasinghe/Desktop/GitHub/VoiceMart-Shopping-Assistant/services/voice-agent/sample_audio/voice1.mp3"
    
    if not os.path.exists(sample_audio_path):
        print("❌ Sample audio file not found. Please provide an audio file for testing.")
        return False
    
    try:
        with open(sample_audio_path, 'rb') as audio_file:
            files = {'file': ('voice1.mp3', audio_file, 'audio/mpeg')}
            response = requests.post(f"{BASE_URL}/v1/stt:transcribe", files=files)
            result = response.json()
            print(f"✅ STT Result:")
            print(f"   Text: {result.get('text', 'No text detected')}")
            print(f"   Language: {result.get('language', 'Unknown')}")
            print(f"   Confidence: {result.get('confidence', 'N/A')}")
            return True
    except Exception as e:
        print(f"❌ STT test failed: {e}")
        return False

def test_voice_understanding():
    """Test complete voice understanding pipeline"""
    print("\n🔍 Testing Voice Understanding...")
    
    sample_audio_path = "/Users/enithsamarasinghe/Desktop/GitHub/VoiceMart-Shopping-Assistant/services/voice-agent/sample_audio/voice1.mp3"
    
    if not os.path.exists(sample_audio_path):
        print("❌ Sample audio file not found. Skipping voice understanding test.")
        return False
    
    try:
        with open(sample_audio_path, 'rb') as audio_file:
            files = {'file': ('voice1.mp3', audio_file, 'audio/mpeg')}
            data = {
                'user_id': 'test_user',
                'locale': 'en-US'
            }
            response = requests.post(f"{BASE_URL}/v1/voice:understand", files=files, data=data)
            result = response.json()
            print(f"✅ Voice Understanding Result:")
            print(f"   Transcript: {result.get('transcript', {}).get('text', 'No text')}")
            print(f"   Intent: {result.get('query', {}).get('intent', 'Unknown')}")
            print(f"   Reply: {result.get('query', {}).get('reply', 'No reply')}")
            return True
    except Exception as e:
        print(f"❌ Voice understanding test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Complete VoiceMart Unified Service Tests")
    print("=" * 60)
    
    # Test health first
    if not test_health():
        print("❌ Service is not running. Please start the service first.")
        return
    
    # Test query processing
    test_query_processing()
    
    # Test product search
    test_product_search()
    
    # Test product details
    test_product_details()
    
    # Test categories
    test_categories()
    
    # Test STT
    test_stt_with_sample_audio()
    
    # Test voice understanding
    test_voice_understanding()
    
    print("\n" + "=" * 60)
    print("🎉 Complete testing finished!")
    print("\n📖 For interactive testing, visit: http://localhost:8000/docs")
    print("\n🔧 Available endpoints:")
    print("   - Speech-to-Text: POST /v1/stt:transcribe")
    print("   - Query Processing: POST /v1/query:process")
    print("   - Voice Understanding: POST /v1/voice:understand")
    print("   - Product Search: POST /v1/products:search")
    print("   - Product Details: GET /v1/products:details")
    print("   - Product Categories: GET /v1/products:categories")

if __name__ == "__main__":
    main()
