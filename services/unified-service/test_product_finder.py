#!/usr/bin/env python3
"""
Simple test script to verify product finder integration in unified service.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test if service is running"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            print("✅ Service is running")
            return True
        else:
            print("❌ Service not responding properly")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to service: {e}")
        return False

def test_product_search():
    """Test product search endpoint"""
    print("\n🔍 Testing product search...")
    
    try:
        search_data = {
            "query": "laptop",
            "limit": 3
        }
        
        response = requests.post(f"{BASE_URL}/v1/products:search", json=search_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            products = result.get('products', [])
            print(f"✅ Found {len(products)} products")
            
            for i, product in enumerate(products, 1):
                print(f"   {i}. {product.get('title', 'N/A')} - ${product.get('price', 0)}")
                print(f"      Source: {product.get('source', 'N/A')}")
            
            return True
        else:
            print(f"❌ Product search failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Product search test failed: {e}")
        return False

def test_query_processing():
    """Test query processing"""
    print("\n🔍 Testing query processing...")
    
    try:
        query_data = {
            "text": "find Nike shoes under $100",
            "user_id": "test_user",
            "locale": "en-US"
        }
        
        response = requests.post(f"{BASE_URL}/v1/query:process", json=query_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Query processed successfully")
            print(f"   Intent: {result.get('intent', 'N/A')}")
            print(f"   Reply: {result.get('reply', 'N/A')}")
            print(f"   Confidence: {result.get('confidence', 0)}")
            return True
        else:
            print(f"❌ Query processing failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Query processing test failed: {e}")
        return False

def main():
    """Run tests"""
    print("🚀 Testing VoiceMart Unified Service Product Finder Integration")
    print("=" * 60)
    
    # Test health
    if not test_health():
        print("\n❌ Service is not running. Please start it first:")
        print("   python run.py")
        return
    
    # Test query processing
    test_query_processing()
    
    # Test product search
    test_product_search()
    
    print("\n" + "=" * 60)
    print("🎉 Testing completed!")

if __name__ == "__main__":
    main()
