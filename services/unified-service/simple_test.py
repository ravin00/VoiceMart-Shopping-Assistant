#!/usr/bin/env python3
"""
Simple test to verify the product finder integration works.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.product_finder import search_products
from app.models import ProductSearchRequest
import asyncio

async def test_product_search():
    """Test the product search function directly"""
    print("🔍 Testing product search function...")
    
    try:
        # Create a search request
        request = ProductSearchRequest(
            query="laptop",
            limit=3
        )
        
        # Call the search function
        result = await search_products(request)
        
        print(f"✅ Search successful!")
        print(f"   Found {len(result.products)} products")
        print(f"   Query: {result.query}")
        print(f"   Total results: {result.total_results}")
        
        for i, product in enumerate(result.products, 1):
            print(f"   {i}. {product.title} - ${product.price}")
            print(f"      Source: {product.source}")
            print(f"      Category: {product.category}")
        
        return True
        
    except Exception as e:
        print(f"❌ Product search failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the test"""
    print("🚀 Testing Product Finder Integration")
    print("=" * 40)
    
    # Run the async test
    success = asyncio.run(test_product_search())
    
    if success:
        print("\n✅ Product finder integration is working!")
    else:
        print("\n❌ Product finder integration has issues.")
    
    print("\n" + "=" * 40)

if __name__ == "__main__":
    main()
