#!/usr/bin/env python3
"""
Test script for the product finder service.
Run this after starting the service to test all endpoints.
"""

import requests
import json

# Service URL
BASE_URL = "http://localhost:8003"

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

def test_product_search():
    """Test product search endpoint"""
    print("\n🔍 Testing product search...")
    
    test_queries = [
        {"query": "laptop", "limit": 5},
        {"query": "shoes", "category": "men's clothing", "limit": 3},
        {"query": "phone", "min_price": 100, "max_price": 500, "limit": 3}
    ]
    
    for test in test_queries:
        try:
            response = requests.post(f"{BASE_URL}/v1/products:search", json=test)
            result = response.json()
            print(f"✅ Search: '{test['query']}'")
            print(f"   Found {result.get('total_results', 0)} products")
            for product in result.get('products', [])[:2]:  # Show first 2
                print(f"   - {product.get('title', 'N/A')} (${product.get('price', 0)})")
            print()
        except Exception as e:
            print(f"❌ Product search failed for '{test['query']}': {e}")

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

def main():
    """Run all tests"""
    print("🚀 Starting Product Finder Service Tests")
    print("=" * 50)
    
    # Test health first
    if not test_health():
        print("❌ Service is not running. Please start the service first.")
        return
    
    # Test product search
    test_product_search()
    
    # Test product details
    test_product_details()
    
    # Test categories
    test_categories()
    
    print("\n" + "=" * 50)
    print("🎉 Testing completed!")
    print("\n📖 For interactive testing, visit: http://localhost:8003/docs")

if __name__ == "__main__":
    main()
