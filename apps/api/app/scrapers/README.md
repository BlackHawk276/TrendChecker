# Shopify Store Scraper

Robust, production-ready scraper for Shopify stores with comprehensive error handling, rate limiting, and data extraction.

## Features

### 🔍 Store Detection
- Automatic Shopify store detection using multiple methods
- Checks `/products.json` endpoint
- Analyzes page content for Shopify indicators
- Validates Shopify CDN and headers

### 📦 Product Scraping
- Fetch all products with automatic pagination
- Extract complete product data:
  - Title, description, handle
  - Pricing (including compare-at prices)
  - Variants with SKUs
  - Images and tags
  - Vendor and product type
- Handles Shopify's 250 products/page limit

### 🏪 Store Information
- Homepage scraping for metadata
- Extract store name and description
- Logo detection (og:image, favicon)
- Social media link extraction (Instagram, Facebook, TikTok, Twitter, YouTube)
- Theme detection

### 🎯 Smart Categorization
- Automatic category detection using keyword matching
- Categories: Fashion, Beauty, Electronics, Home, Health, Sports
- Analyzes product titles, types, and tags
- Confidence scoring system

### ⚡ Rate Limiting
- 1 request per second per domain
- Prevents API abuse and bans
- Per-domain request queuing
- Respects server rate limit headers (429)

### 🛡️ Error Handling
- Exponential backoff on failures
- Automatic retries (3 attempts)
- Handles timeouts gracefully
- SSL error recovery
- Invalid JSON protection
- Comprehensive logging

### 🔄 Advanced Features
- User-Agent rotation (5 real browser UAs)
- Connection pooling for performance
- Async/await for concurrent requests
- Request/response logging
- Domain normalization

## Installation

The scraper requires these dependencies (already in requirements.txt):

```bash
pip install httpx beautifulsoup4
```

## Usage

### Basic Usage

```python
import asyncio
from app.scrapers.shopify_scraper import ShopifyScraper

async def scrape_store():
    scraper = ShopifyScraper()

    # Check if domain is Shopify
    is_shopify = await scraper.is_shopify_store("example.com")

    if is_shopify:
        # Get products
        products = await scraper.get_products("example.com")
        print(f"Found {len(products)} products")

        # Get store info
        store_info = await scraper.get_store_info("example.com")
        print(f"Store: {store_info['name']}")

    await scraper.close()

asyncio.run(scrape_store())
```

### Comprehensive Analysis

```python
from app.scrapers.shopify_scraper import ShopifyScraper

async def analyze():
    scraper = ShopifyScraper()

    # Complete analysis
    analysis = await scraper.analyze_store("gymshark.com")

    print(f"Store: {analysis['name']}")
    print(f"Category: {analysis['category']}")
    print(f"Products: {analysis['product_count']}")
    print(f"Avg Price: ${analysis['avg_price']}")
    print(f"Theme: {analysis['theme_name']}")
    print(f"Social: {analysis['social_links']}")

    await scraper.close()
```

### Get Specific Product

```python
async def get_product():
    scraper = ShopifyScraper()

    product = await scraper.get_product_details(
        "allbirds.com",
        "mens-wool-runners"  # product handle
    )

    print(f"Product: {product['title']}")
    print(f"Price: ${product['variants'][0]['price']}")

    await scraper.close()
```

## API Reference

### `ShopifyScraper`

Main scraper class with all functionality.

#### Methods

##### `async def is_shopify_store(domain: str) -> bool`

Check if a domain is a Shopify store.

**Parameters:**
- `domain` (str): Domain to check (e.g., "example.com")

**Returns:**
- `bool`: True if Shopify store, False otherwise

**Example:**
```python
is_shopify = await scraper.is_shopify_store("gymshark.com")
```

---

##### `async def get_products(domain: str, limit: int = 250) -> List[dict]`

Fetch all products from a store.

**Parameters:**
- `domain` (str): Shopify store domain
- `limit` (int): Products per page (max 250, default 250)

**Returns:**
- `List[dict]`: List of product dictionaries

**Product Dictionary Structure:**
```python
{
    "id": 123456789,
    "title": "Product Name",
    "handle": "product-slug",
    "description": "Product description...",
    "vendor": "Brand Name",
    "product_type": "Category",
    "price": 29.99,
    "compare_at_price": 39.99,
    "tags": ["tag1", "tag2"],
    "images": [{"src": "url", "alt": "text"}],
    "variants": [{"id": 123, "price": "29.99", "sku": "ABC"}],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

---

##### `async def get_store_info(domain: str) -> dict`

Extract store information from homepage.

**Parameters:**
- `domain` (str): Shopify store domain

**Returns:**
- `dict`: Store information

**Store Info Structure:**
```python
{
    "domain": "example.com",
    "name": "Store Name",
    "description": "Store description...",
    "logo_url": "https://...",
    "social_links": {
        "instagram": "https://instagram.com/...",
        "facebook": "https://facebook.com/...",
    },
    "theme_name": "Dawn"
}
```

---

##### `async def analyze_store(domain: str) -> dict`

Comprehensive store analysis combining all data.

**Parameters:**
- `domain` (str): Shopify store domain

**Returns:**
- `dict`: Complete analysis

**Analysis Structure:**
```python
{
    "domain": "example.com",
    "is_shopify": True,
    "name": "Store Name",
    "description": "...",
    "logo_url": "...",
    "category": "fashion",
    "product_count": 150,
    "avg_price": 45.99,
    "min_price": 19.99,
    "max_price": 199.99,
    "social_links": {...},
    "theme_name": "Dawn",
    "products": [...],
    "analyzed_at": "2024-01-01T00:00:00",
    "error": None
}
```

---

##### `async def get_product_details(domain: str, handle: str) -> Optional[dict]`

Fetch detailed information for a specific product.

**Parameters:**
- `domain` (str): Shopify store domain
- `handle` (str): Product handle/slug

**Returns:**
- `Optional[dict]`: Product details or None

---

##### `async def close()`

Close the HTTP client and cleanup resources.

**Always call this when done scraping!**

```python
await scraper.close()
```

## Rate Limiting

The scraper implements intelligent rate limiting:

- **1 request per second** per domain
- Automatic detection of server rate limits (429 responses)
- Exponential backoff on rate limit errors
- Per-domain request queuing

This ensures:
- No server bans
- Respectful scraping
- Consistent performance

## Error Handling

The scraper gracefully handles:

- **Network errors**: Connection failures, timeouts
- **HTTP errors**: 404, 429, 500+ status codes
- **Invalid responses**: Malformed JSON, missing data
- **SSL errors**: Certificate validation issues
- **Rate limiting**: Server-side throttling

All errors are logged with detailed information for debugging.

## Testing

Run the test suite:

```bash
cd backend/app/scrapers
python test_scraper.py
```

Test scenarios included:
1. Basic scraping functionality
2. Full store analysis
3. Product detail fetching
4. Rate limiting verification
5. Error handling validation

## Logging

Configure logging to see scraper activity:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Log levels:
- **INFO**: Regular operations (requests, results)
- **WARNING**: Rate limiting, retries
- **ERROR**: Failures, exceptions
- **DEBUG**: Detailed request/response info

## Performance

- **Async/await**: Non-blocking concurrent requests
- **Connection pooling**: Reuses HTTP connections
- **Efficient pagination**: Fetches max products per page
- **Smart caching**: User-Agent rotation reduces detection

Expected performance:
- Store detection: ~1-2 seconds
- 100 products: ~5-10 seconds
- Full analysis (1000 products): ~30-60 seconds

## Category Detection

The scraper automatically categorizes stores using keyword matching:

| Category | Keywords |
|----------|----------|
| **Fashion** | shirt, dress, pants, shoes, clothing, apparel |
| **Beauty** | skincare, makeup, cosmetics, serum, lipstick |
| **Electronics** | phone, laptop, gadget, device, headphones |
| **Home** | furniture, decor, kitchen, table, lamp |
| **Health** | supplement, vitamin, fitness, wellness |
| **Sports** | sports, gym, athletic, outdoor, equipment |

Categories are scored based on product titles, types, and tags.

## Best Practices

1. **Always close the scraper**:
   ```python
   try:
       scraper = ShopifyScraper()
       # ... scraping code ...
   finally:
       await scraper.close()
   ```

2. **Use singleton pattern for multiple scrapes**:
   ```python
   from app.scrapers.shopify_scraper import get_scraper

   scraper = await get_scraper()  # Reuses instance
   ```

3. **Handle errors gracefully**:
   ```python
   try:
       products = await scraper.get_products(domain)
   except Exception as e:
       logger.error(f"Scraping failed: {e}")
   ```

4. **Respect rate limits** - Don't modify the delay values

5. **Monitor logs** - Check for rate limit warnings

## Integration with Database

Example integration with your models:

```python
from app.models import Store, Product
from app.scrapers.shopify_scraper import ShopifyScraper

async def save_store_to_db(domain: str, db: AsyncSession):
    scraper = ShopifyScraper()

    # Analyze store
    analysis = await scraper.analyze_store(domain)

    if not analysis["is_shopify"]:
        return None

    # Create store record
    store = Store(
        domain=analysis["domain"],
        name=analysis["name"],
        description=analysis["description"],
        category=analysis["category"],
        logo_url=analysis["logo_url"],
        product_count=analysis["product_count"],
        avg_product_price=analysis["avg_price"],
        theme_name=analysis["theme_name"],
        social_links=analysis["social_links"],
        last_scraped_at=datetime.utcnow()
    )

    db.add(store)
    await db.commit()

    # Save products
    for product_data in analysis["products"]:
        product = Product(
            store_id=store.id,
            title=product_data["title"],
            price=product_data["price"],
            # ... more fields ...
        )
        db.add(product)

    await db.commit()
    await scraper.close()

    return store
```

## Troubleshooting

### Store not detected
- Verify the domain is accessible
- Check if it's actually a Shopify store (try `/products.json` manually)
- Some stores may have access restrictions

### Rate limiting errors
- The scraper handles this automatically
- If persistent, increase `rate_limit_delay` in `__init__`

### Timeout errors
- Some stores are slow to respond
- Adjust timeout in httpx.AsyncClient initialization

### Empty product list
- Store may have no public products
- Products might be in private collections

## Limitations

- Only works with public Shopify stores
- Cannot access password-protected stores
- Cannot access draft/unpublished products
- Subject to Shopify's rate limiting
- Some stores may block scrapers

## Legal & Ethical Use

- Respect robots.txt
- Honor rate limits
- Don't overload servers
- Use responsibly for legitimate research/business purposes
- Comply with Shopify's Terms of Service

## Contributing

To add new features:
1. Add methods to `ShopifyScraper` class
2. Update tests in `test_scraper.py`
3. Document in this README
4. Ensure rate limiting is maintained

## License

Proprietary - All rights reserved
