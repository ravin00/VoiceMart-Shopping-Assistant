#!/usr/bin/env python3
"""
Direct test of API functions without the web server
"""
import sys
import os
import json
import asyncio
from pathlib import Path

# Add the app directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

# Import our modules
from app.models import ProductSearchRequest
from app.api_clients import search_products_unified

async def test_api_search():
    """Test the API search function directly"""
    print("Testing API search function directly...")
    
    # Create a search request
    request = ProductSearchRequest(
        query="wireless headphones",
        category="Electronics",
        min_price=20,
        max_price=200,
        brand="Sony",
        limit=10,
        sources=["amazon", "ebay", "walmart"],
        fallback=True
    )
    
    print(f"Search request: {request.dict()}")
    
    # Call the search function
    response = await search_products_unified(request)
    
    print(f"Got {len(response.products)} products")
    
    # Print the first few products
    for i, product in enumerate(response.products[:5]):
        print(f"{i+1}. {product.title} - ${product.price} from {product.source}")
    
    # Save the response to a file
    output_dir = Path("./test_results")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "api_search_results.json"
    with open(output_file, "w") as f:
        # Convert to dict first since we can't directly serialize Pydantic models
        response_dict = response.dict()
        json.dump(response_dict, f, indent=2)
    
    print(f"Saved results to {output_file}")
    
    # Return the number of products found
    return len(response.products)

if __name__ == "__main__":
    # Run the async function
    result = asyncio.run(test_api_search())
    
    if result == 0:
        print("ERROR: No products found!")
        sys.exit(1)
    else:
        print(f"SUCCESS: Found {result} products!")
        sys.exit(0)