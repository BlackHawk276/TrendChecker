"""
Test script for Shopify scraper.
Run this to test scraping functionality.
"""
import asyncio
import json
import logging

from shopify_scraper import ShopifyScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def test_basic_scraping():
    """Test basic scraping functionality."""
    scraper = ShopifyScraper()

    # Test domains (known Shopify stores)
    test_domains = [
        "gymshark.com",  # Fitness apparel
        "allbirds.com",  # Sustainable shoes
        "kylie cosmetics.com",  # Beauty
    ]

    for domain in test_domains:
        print(f"\n{'='*60}")
        print(f"Testing: {domain}")
        print(f"{'='*60}\n")

        # Check if it's a Shopify store
        is_shopify = await scraper.is_shopify_store(domain)
        print(f"Is Shopify store: {is_shopify}")

        if is_shopify:
            # Get store info
            print("\nFetching store info...")
            store_info = await scraper.get_store_info(domain)
            print(f"Store Name: {store_info.get('name')}")
            print(f"Description: {store_info.get('description')[:100] if store_info.get('description') else 'N/A'}...")
            print(f"Logo: {store_info.get('logo_url')}")
            print(f"Theme: {store_info.get('theme_name')}")
            print(f"Social Links: {store_info.get('social_links')}")

            # Get products (limited to first page for testing)
            print("\nFetching products...")
            products = await scraper.get_products(domain, limit=10)
            print(f"Total products fetched: {len(products)}")

            if products:
                print("\nFirst 3 products:")
                for i, product in enumerate(products[:3], 1):
                    print(f"\n{i}. {product.get('title')}")
                    print(f"   Price: ${product.get('price')}")
                    print(f"   Vendor: {product.get('vendor')}")
                    print(f"   Tags: {', '.join(product.get('tags', [])[:5])}")

        print("\n" + "="*60)

    await scraper.close()


async def test_full_analysis():
    """Test comprehensive store analysis."""
    scraper = ShopifyScraper()

    # Test with a known Shopify store
    domain = "allbirds.com"

    print(f"\n{'='*60}")
    print(f"Full Analysis: {domain}")
    print(f"{'='*60}\n")

    analysis = await scraper.analyze_store(domain)

    # Print analysis results
    print(json.dumps({
        "domain": analysis["domain"],
        "is_shopify": analysis["is_shopify"],
        "name": analysis["name"],
        "category": analysis["category"],
        "product_count": analysis["product_count"],
        "avg_price": analysis["avg_price"],
        "min_price": analysis["min_price"],
        "max_price": analysis["max_price"],
        "theme_name": analysis["theme_name"],
        "social_links": analysis["social_links"],
        "error": analysis["error"],
    }, indent=2))

    await scraper.close()


async def test_product_details():
    """Test fetching specific product details."""
    scraper = ShopifyScraper()

    domain = "allbirds.com"
    handle = "mens-wool-runners"  # Example product handle

    print(f"\n{'='*60}")
    print(f"Product Details: {domain}/products/{handle}")
    print(f"{'='*60}\n")

    product = await scraper.get_product_details(domain, handle)

    if product:
        print(f"Title: {product.get('title')}")
        print(f"Type: {product.get('product_type')}")
        print(f"Vendor: {product.get('vendor')}")
        print(f"Variants: {len(product.get('variants', []))}")
        print(f"Images: {len(product.get('images', []))}")
    else:
        print("Product not found or error occurred")

    await scraper.close()


async def test_rate_limiting():
    """Test rate limiting functionality."""
    scraper = ShopifyScraper()

    domain = "allbirds.com"

    print(f"\n{'='*60}")
    print(f"Rate Limiting Test: Making 5 requests to {domain}")
    print(f"{'='*60}\n")

    import time
    start_time = time.time()

    for i in range(5):
        print(f"Request {i+1}...", end=" ")
        is_shopify = await scraper.is_shopify_store(domain)
        print(f"Complete (Shopify: {is_shopify})")

    elapsed = time.time() - start_time
    print(f"\nTotal time: {elapsed:.2f}s")
    print(f"Average time per request: {elapsed/5:.2f}s")
    print(f"Rate limiting is working correctly!" if elapsed >= 4 else "Warning: Rate limiting may not be working")

    await scraper.close()


async def test_error_handling():
    """Test error handling with invalid domains."""
    scraper = ShopifyScraper()

    test_cases = [
        ("invalid-domain-that-does-not-exist.com", "Non-existent domain"),
        ("google.com", "Non-Shopify store"),
        ("", "Empty domain"),
    ]

    print(f"\n{'='*60}")
    print("Error Handling Tests")
    print(f"{'='*60}\n")

    for domain, description in test_cases:
        print(f"Testing: {description} ({domain})")
        try:
            is_shopify = await scraper.is_shopify_store(domain)
            print(f"  Result: Is Shopify = {is_shopify}")
        except Exception as e:
            print(f"  Exception caught: {type(e).__name__}: {str(e)}")
        print()

    await scraper.close()


async def main():
    """Run all tests."""
    print("="*60)
    print("SHOPIFY SCRAPER TEST SUITE")
    print("="*60)

    # Uncomment the tests you want to run:

    # Test 1: Basic scraping
    # await test_basic_scraping()

    # Test 2: Full analysis
    await test_full_analysis()

    # Test 3: Product details
    # await test_product_details()

    # Test 4: Rate limiting
    # await test_rate_limiting()

    # Test 5: Error handling
    # await test_error_handling()

    print("\n" + "="*60)
    print("TESTS COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
