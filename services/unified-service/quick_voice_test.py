#!/usr/bin/env python3
"""
Quick test for voice-to-products integration.
Tests if the unified service automatically searches for products.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_query_processing_with_products():
    """Test if query processing triggers product search"""
    print("🔍 Testing query processing with automatic product search...")
    
    # Test queries that should trigger product search
    test_queries = [
        "find Nike shoes under $100",
        "search for laptop",
        "show me phones under $500",
        "add 2 packs of Milo to cart"
    ]
    
    for query in test_queries:
        print(f"\n📝 Testing: '{query}'")
        
        try:
            # Test query processing
            response = requests.post(f"{BASE_URL}/v1/query:process", json={
                "text": query,
                "user_id": "test_user",
                "locale": "en-US"
            })
            
            if response.status_code == 200:
                result = response.json()
                intent = result.get('intent')
                print(f"   🎯 Intent: {intent}")
                print(f"   💬 Reply: {result.get('reply')}")
                
                # Check if this should trigger product search
                if intent in ["search_product", "add_to_cart"]:
                    print("   ✅ This should trigger product search in voice understanding!")
                    print("   🔍 Test product search manually:")
                    
                    # Test product search
                    search_response = requests.post(f"{BASE_URL}/v1/products:search", json={
                        "query": query,
                        "limit": 3
                    })
                    
                    if search_response.status_code == 200:
                        search_result = search_response.json()
                        products = search_result.get('products', [])
                        print(f"      🛍️ Found {len(products)} products:")
                        for product in products[:2]:
                            print(f"         - {product.get('title', 'N/A')} (${product.get('price', 0)})")
                    else:
                        print(f"      ❌ Product search failed: {search_response.status_code}")
                else:
                    print("   ℹ️ Not a product-related intent")
            else:
                print(f"   ❌ Query processing failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Test failed: {e}")

def test_voice_understanding_structure():
    """Test the voice understanding response structure"""
    print("\n🔍 Testing voice understanding response structure...")
    
    # Test with a simple query first
    try:
        response = requests.post(f"{BASE_URL}/v1/query:process", json={
            "text": "find laptop",
            "user_id": "test_user",
            "locale": "en-US"
        })
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Query processing works!")
            print(f"   Intent: {result.get('intent')}")
            print(f"   Reply: {result.get('reply')}")
            
            # Now test the voice understanding endpoint structure
            print("\n📋 Voice understanding endpoint should return:")
            print("   - transcript: {text, language, confidence}")
            print("   - query: {intent, reply, confidence, slots}")
            print("   - products: [array of products] (if product-related intent)")
            print("   - product_search_performed: true/false")
            
            print("\n🎯 To test with audio:")
            print("   1. Go to http://localhost:8000/docs")
            print("   2. Find 'POST /v1/voice:understand'")
            print("   3. Upload an audio file")
            print("   4. Check if 'product_search_performed' is true")
            print("   5. Check if 'products' array has items")
            
        else:
            print(f"❌ Query processing failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

def main():
    """Run quick voice-to-products test"""
    print("🚀 Quick Voice-to-Products Integration Test")
    print("=" * 50)
    
    # Test if service is running
    try:
        health_response = requests.get(f"{BASE_URL}/health")
        if health_response.status_code != 200:
            print("❌ Unified service not running. Start with: python run.py")
            return
    except:
        print("❌ Cannot connect to unified service. Start with: python run.py")
        return
    
    print("✅ Unified service is running!")
    
    # Run tests
    test_query_processing_with_products()
    test_voice_understanding_structure()
    
    print("\n" + "=" * 50)
    print("🎉 Quick test completed!")
    print("\n📖 Next steps:")
    print("   1. Test with audio: http://localhost:8000/docs")
    print("   2. Run full test: python test_voice_to_products.py")

if __name__ == "__main__":
    main()
