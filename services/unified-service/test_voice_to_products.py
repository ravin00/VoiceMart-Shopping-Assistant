#!/usr/bin/env python3
"""
Test script for the complete voice-to-products pipeline.
Tests voice understanding with automatic product search.
"""

import requests
import json
import os

BASE_URL = "http://localhost:8000"

def test_health():
    """Test if unified service is running"""
    print("🔍 Testing unified service health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Unified service is running!")
            return True
        else:
            print(f"❌ Service returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to unified service: {e}")
        print("   Make sure to start with: python run.py")
        return False

def test_voice_understanding_with_products():
    """Test voice understanding with automatic product search"""
    print("\n🔍 Testing voice understanding with product search...")
    
    # Check if sample audio exists
    sample_audio_path = "/Users/enithsamarasinghe/Desktop/GitHub/VoiceMart-Shopping-Assistant/services/voice-agent/sample_audio/voice1.mp3"
    
    if not os.path.exists(sample_audio_path):
        print("❌ Sample audio file not found. Creating a mock test...")
        return test_mock_voice_understanding()
    
    try:
        with open(sample_audio_path, 'rb') as audio_file:
            files = {'file': ('voice1.mp3', audio_file, 'audio/mpeg')}
            data = {
                'user_id': 'test_user',
                'locale': 'en-US'
            }
            
            print("   📤 Sending audio file for processing...")
            response = requests.post(f"{BASE_URL}/v1/voice:understand", files=files, data=data)
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Voice understanding successful!")
                
                # Show transcript
                transcript = result.get('transcript', {})
                print(f"   📝 Transcript: {transcript.get('text', 'No text')}")
                
                # Show query processing results
                query = result.get('query', {})
                print(f"   🎯 Intent: {query.get('intent', 'Unknown')}")
                print(f"   💬 Reply: {query.get('reply', 'No reply')}")
                print(f"   🎚️ Confidence: {query.get('confidence', 0)}")
                
                # Show product search results
                products = result.get('products', [])
                product_search_performed = result.get('product_search_performed', False)
                
                print(f"   🔍 Product search performed: {product_search_performed}")
                
                if products:
                    print(f"   🛍️ Found {len(products)} products:")
                    for i, product in enumerate(products, 1):
                        print(f"      {i}. {product.get('title', 'N/A')} - ${product.get('price', 0)}")
                        print(f"         Category: {product.get('category', 'N/A')}")
                        print(f"         Source: {product.get('source', 'N/A')}")
                else:
                    print("   🛍️ No products found")
                
                return True
            else:
                print(f"❌ Voice understanding failed with status {response.status_code}")
                print(f"   Error: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Voice understanding test failed: {e}")
        return False

def test_mock_voice_understanding():
    """Test voice understanding with mock data (when no audio file)"""
    print("\n🔍 Testing voice understanding with mock data...")
    
    # Test query processing first
    test_queries = [
        "find Nike shoes under $100",
        "search for laptop",
        "show me phones",
        "add 2 packs of Milo to cart"
    ]
    
    for query in test_queries:
        print(f"\n   📝 Testing query: '{query}'")
        
        try:
            # Test query processing
            query_response = requests.post(f"{BASE_URL}/v1/query:process", json={
                "text": query,
                "user_id": "test_user",
                "locale": "en-US"
            })
            
            if query_response.status_code == 200:
                query_result = query_response.json()
                print(f"      🎯 Intent: {query_result.get('intent')}")
                print(f"      💬 Reply: {query_result.get('reply')}")
                
                # If it's a product-related intent, test product search
                if query_result.get('intent') in ["search_product", "add_to_cart"]:
                    print("      🔍 This should trigger product search...")
                    
                    # Test product search separately
                    search_response = requests.post(f"{BASE_URL}/v1/products:search", json={
                        "query": query,
                        "limit": 3
                    })
                    
                    if search_response.status_code == 200:
                        search_result = search_response.json()
                        products = search_result.get('products', [])
                        print(f"      🛍️ Found {len(products)} products:")
                        for product in products[:2]:  # Show first 2
                            print(f"         - {product.get('title', 'N/A')} (${product.get('price', 0)})")
                    else:
                        print(f"      ❌ Product search failed: {search_response.status_code}")
                else:
                    print("      ℹ️ Not a product-related intent")
            else:
                print(f"      ❌ Query processing failed: {query_response.status_code}")
                
        except Exception as e:
            print(f"      ❌ Test failed: {e}")

def test_direct_product_search():
    """Test direct product search functionality"""
    print("\n🔍 Testing direct product search...")
    
    search_tests = [
        {"query": "laptop", "limit": 3},
        {"query": "shoes", "category": "men's clothing", "limit": 2},
        {"query": "phone", "min_price": 100, "max_price": 500, "limit": 2}
    ]
    
    for test in search_tests:
        try:
            print(f"   📋 Testing: {test['query']}")
            response = requests.post(f"{BASE_URL}/v1/products:search", json=test)
            
            if response.status_code == 200:
                result = response.json()
                products = result.get('products', [])
                print(f"      ✅ Found {len(products)} products")
                
                for product in products[:1]:  # Show first product
                    print(f"         - {product.get('title', 'N/A')} (${product.get('price', 0)})")
            else:
                print(f"      ❌ Search failed: {response.status_code}")
                
        except Exception as e:
            print(f"      ❌ Search test failed: {e}")

def explain_voice_to_products_flow():
    """Explain how the voice-to-products flow works"""
    print("\n📚 Voice-to-Products Flow Explanation:")
    print("=" * 50)
    print("1. 🎤 User uploads audio file")
    print("2. 🔤 Service transcribes audio to text")
    print("3. 🧠 Service processes text to extract:")
    print("   - Intent (search_product, add_to_cart, etc.)")
    print("   - Entities (brand, price, category, etc.)")
    print("   - Confidence score")
    print("4. 🔍 If intent is product-related:")
    print("   - Automatically searches for products")
    print("   - Uses extracted entities as search filters")
    print("   - Returns relevant products")
    print("5. 📦 Returns complete response with:")
    print("   - Transcript")
    print("   - Query processing results")
    print("   - Found products (if applicable)")
    print()
    print("✅ SUCCESS INDICATORS:")
    print("   - Status 200")
    print("   - 'product_search_performed': true")
    print("   - 'products' array has items")
    print("   - Products match the search criteria")

def main():
    """Run complete voice-to-products testing"""
    print("🚀 VoiceMart Voice-to-Products Pipeline Test")
    print("=" * 60)
    
    # Test health first
    if not test_health():
        print("\n❌ Cannot run tests - unified service not available")
        print("   Start with: cd services/unified-service && python run.py")
        return
    
    # Run tests
    test_voice_understanding_with_products()
    test_direct_product_search()
    
    # Explain the flow
    explain_voice_to_products_flow()
    
    print("\n" + "=" * 60)
    print("🎉 Voice-to-Products testing completed!")
    print("\n📖 For interactive testing, visit: http://localhost:8000/docs")
    print("\n🔧 Test the complete pipeline:")
    print("   1. Go to http://localhost:8000/docs")
    print("   2. Find 'POST /v1/voice:understand'")
    print("   3. Upload an audio file")
    print("   4. Check the response for products!")

if __name__ == "__main__":
    main()
