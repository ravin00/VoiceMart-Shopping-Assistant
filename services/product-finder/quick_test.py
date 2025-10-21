#!/usr/bin/env python3
"""
Quick test script for product finder service.
Run this to test all functionality quickly.
"""

import requests
import json

# Set base URL
# Use port 8000 for web scraper testing
# Use port 8003 for original API testing
BASE_URL = "http://localhost:8000"  # Change to 8003 to test the original API

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ Health: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Health failed: {e}")
        return False

def test_search_scenarios():
    """Test different search scenarios"""
    print("\n🔍 Testing product search scenarios...")
    
    scenarios = [
        {
            "name": "Basic Laptop Search",
            "data": {"query": "laptop", "limit": 3}
        },
        {
            "name": "Electronics with Price Filter",
            "data": {"query": "phone", "category": "electronics", "min_price": 100, "max_price": 500, "limit": 2}
        },
        {
            "name": "Clothing Search",
            "data": {"query": "shirt", "category": "men's clothing", "limit": 2}
        },
        {
            "name": "Jewelry Search",
            "data": {"query": "ring", "category": "jewelery", "limit": 1}
        }
    ]
    
    for scenario in scenarios:
        try:
            print(f"\n📋 {scenario['name']}:")
            response = requests.post(f"{BASE_URL}/v1/products:search", json=scenario['data'])
            result = response.json()
            
            print(f"   Query: {scenario['data']['query']}")
            print(f"   Found: {result.get('total_results', 0)} products")
            
            for i, product in enumerate(result.get('products', [])[:2], 1):
                print(f"   {i}. {product.get('title', 'N/A')} - ${product.get('price', 0)}")
                
        except Exception as e:
            print(f"❌ {scenario['name']} failed: {e}")

def test_product_details():
    """Test product details"""
    print("\n🔍 Testing product details...")
    
    try:
        # First search for a product
        search_response = requests.post(f"{BASE_URL}/v1/products:search", json={"query": "laptop", "limit": 1})
        if search_response.status_code == 200:
            products = search_response.json().get('products', [])
            if products:
                product_id = products[0].get('id')
                print(f"   Getting details for product ID: {product_id}")
                
                details_response = requests.get(f"{BASE_URL}/v1/products:details?product_id={product_id}&source=fakestore")
                if details_response.status_code == 200:
                    details = details_response.json()
                    product = details.get('product', {})
                    print(f"   ✅ Title: {product.get('title', 'N/A')}")
                    print(f"   ✅ Price: ${product.get('price', 0)}")
                    print(f"   ✅ Category: {product.get('category', 'N/A')}")
                    print(f"   ✅ Description: {product.get('description', 'N/A')[:100]}...")
                    return True
                else:
                    print(f"   ❌ Details request failed: {details_response.status_code}")
            else:
                print("   ❌ No products found")
        else:
            print(f"   ❌ Search failed: {search_response.status_code}")
    except Exception as e:
        print(f"   ❌ Details test failed: {e}")
    
    return False

def test_categories():
    """Test categories endpoint"""
    print("\n🔍 Testing categories...")
    
    try:
        response = requests.get(f"{BASE_URL}/v1/products:categories")
        if response.status_code == 200:
            result = response.json()
            categories = result.get('categories', [])
            print(f"   ✅ Found {len(categories)} categories:")
            for cat in categories:
                print(f"      - {cat.get('name', 'N/A')} ({cat.get('id', 'N/A')})")
            return True
        else:
            print(f"   ❌ Categories failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Categories test failed: {e}")
    
    return False

def test_edge_cases():
    """Test edge cases"""
    print("\n🔍 Testing edge cases...")
    
    edge_cases = [
        {"name": "Empty Query", "data": {"query": "", "limit": 1}},
        {"name": "Very High Price", "data": {"query": "laptop", "min_price": 10000, "limit": 1}},
        {"name": "Non-existent Category", "data": {"query": "laptop", "category": "non-existent", "limit": 1}},
        {"name": "Large Limit", "data": {"query": "laptop", "limit": 50}}
    ]
    
    for case in edge_cases:
        try:
            print(f"   📋 {case['name']}:")
            response = requests.post(f"{BASE_URL}/v1/products:search", json=case['data'])
            result = response.json()
            print(f"      Found: {result.get('total_results', 0)} products")
        except Exception as e:
            print(f"      ❌ Failed: {e}")

def main():
    """Run all tests"""
    print("🚀 Product Finder Service - Quick Test Suite")
    print("=" * 50)
    
    # Test health first
    if not test_health():
        print("❌ Service not running. Start with: python run.py")
        return
    
    # Run all tests
    test_search_scenarios()
    test_product_details()
    test_categories()
    test_edge_cases()
    
    print("\n" + "=" * 50)
    print("🎉 Quick testing completed!")
    print("\n📖 For interactive testing, visit: http://localhost:8003/docs")
    print("\n🔧 Available endpoints:")
    print("   - Health: GET /health")
    print("   - Search: POST /v1/products:search")
    print("   - Details: GET /v1/products:details")
    print("   - Categories: GET /v1/products:categories")

if __name__ == "__main__":
    main()
