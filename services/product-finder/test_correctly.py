#!/usr/bin/env python3
"""
Correct testing script for product finder service.
This shows you exactly what to expect and how to interpret results.
"""

import requests
import json

BASE_URL = "http://localhost:8003"

def test_health():
    """Test if service is running"""
    print("🔍 Testing if service is running...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Service is running!")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Service returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to service: {e}")
        print("   Make sure to start the service with: python run.py")
        return False

def test_simple_search():
    """Test a simple product search"""
    print("\n🔍 Testing simple product search...")
    
    # Correct JSON format
    search_data = {
        "query": "laptop",
        "limit": 3
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/products:search", json=search_data)
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Search successful!")
            print(f"   Found {result.get('total_results', 0)} products")
            print(f"   Query: {result.get('query', 'N/A')}")
            
            # Show first product if any
            products = result.get('products', [])
            if products:
                first_product = products[0]
                print(f"   First product:")
                print(f"     - Title: {first_product.get('title', 'N/A')}")
                print(f"     - Price: ${first_product.get('price', 0)}")
                print(f"     - Category: {first_product.get('category', 'N/A')}")
                print(f"     - Source: {first_product.get('source', 'N/A')}")
            else:
                print("   No products found (this might be normal)")
            
            return True
        else:
            print(f"❌ Search failed with status {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Search test failed: {e}")
        return False

def test_search_with_filters():
    """Test search with filters"""
    print("\n🔍 Testing search with filters...")
    
    # Correct JSON format with proper escaping
    search_data = {
        "query": "shoes",
        "category": "men's clothing",  # No extra escaping needed in Python
        "min_price": 10,
        "max_price": 100,
        "limit": 2
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/products:search", json=search_data)
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Filtered search successful!")
            print(f"   Found {result.get('total_results', 0)} products")
            print(f"   Filters applied: {result.get('filters_applied', {})}")
            
            # Show products
            products = result.get('products', [])
            for i, product in enumerate(products, 1):
                print(f"   Product {i}:")
                print(f"     - {product.get('title', 'N/A')} (${product.get('price', 0)})")
            
            return True
        else:
            print(f"❌ Filtered search failed with status {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Filtered search test failed: {e}")
        return False

def test_categories():
    """Test categories endpoint"""
    print("\n🔍 Testing categories...")
    
    try:
        response = requests.get(f"{BASE_URL}/v1/products:categories")
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            categories = result.get('categories', [])
            print("✅ Categories retrieved successfully!")
            print(f"   Found {len(categories)} categories:")
            
            for cat in categories:
                print(f"     - {cat.get('name', 'N/A')} (ID: {cat.get('id', 'N/A')})")
            
            return True
        else:
            print(f"❌ Categories failed with status {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Categories test failed: {e}")
        return False

def interpret_results():
    """Explain what the results mean"""
    print("\n📚 How to interpret your results:")
    print("=" * 50)
    print("✅ GOOD SIGNS:")
    print("   - Status Code 200 = Success")
    print("   - 'products' array has items = Products found")
    print("   - 'total_results' > 0 = Search worked")
    print("   - No error messages = Everything OK")
    print()
    print("❌ BAD SIGNS:")
    print("   - Status Code 422 = JSON format error")
    print("   - Status Code 500 = Server error")
    print("   - Empty 'products' array = No products found")
    print("   - Error messages = Something went wrong")
    print()
    print("🔧 COMMON ISSUES:")
    print("   - JSON format errors (check quotes and commas)")
    print("   - Service not running (start with: python run.py)")
    print("   - Wrong endpoint URL")
    print("   - Network connection issues")

def main():
    """Run all tests and explain results"""
    print("🚀 Product Finder Service - Correct Testing")
    print("=" * 50)
    
    # Run tests
    health_ok = test_health()
    
    if health_ok:
        test_simple_search()
        test_search_with_filters()
        test_categories()
    else:
        print("\n❌ Cannot run tests - service not available")
        print("   Start the service with: python run.py")
    
    # Explain results
    interpret_results()
    
    print("\n" + "=" * 50)
    print("🎉 Testing completed!")
    print("\n📖 For interactive testing, visit: http://localhost:8003/docs")

if __name__ == "__main__":
    main()
