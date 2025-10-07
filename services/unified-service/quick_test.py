#!/usr/bin/env python3
"""
Quick test to verify the unified service is working.
"""

import requests
import json

def test_service():
    """Test the unified service"""
    base_url = "http://localhost:8000"
    
    print("🔍 Testing unified service...")
    
    # Test health
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            print("✅ Service is running!")
        else:
            print("❌ Service not responding")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to service: {e}")
        return False
    
    # Test product search
    try:
        print("\n🔍 Testing product search...")
        search_data = {
            "query": "laptop",
            "limit": 3
        }
        
        response = requests.post(f"{base_url}/v1/products:search", json=search_data)
        print(f"Product search status: {response.status_code}")
        
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

if __name__ == "__main__":
    print("🚀 Quick Unified Service Test")
    print("=" * 40)
    
    success = test_service()
    
    if success:
        print("\n✅ All tests passed! The unified service is working correctly.")
        print("\n🎉 Product finder integration is now working!")
        print("\nYou can now:")
        print("   - Use /v1/voice:understand for voice-to-products")
        print("   - Use /v1/products:search for direct product search")
        print("   - Visit http://localhost:8000/docs for interactive testing")
    else:
        print("\n❌ Some tests failed. Check the service logs.")
    
    print("\n" + "=" * 40)
