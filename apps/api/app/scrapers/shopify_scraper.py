"""
Robust Shopify store scraper with rate limiting and error handling.
"""
import asyncio
import logging
import re
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)


class ShopifyScraper:
    """
    Robust scraper for Shopify stores with rate limiting and error handling.
    """

    # List of real browser User-Agents for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    # Category keywords for classification
    CATEGORY_KEYWORDS = {
        "fashion": [
            "shirt", "dress", "pants", "jeans", "jacket", "coat", "hoodie",
            "sweater", "shoes", "sneakers", "boots", "clothing", "apparel",
            "fashion", "style", "outfit", "wear", "tee", "denim", "blazer"
        ],
        "beauty": [
            "skincare", "makeup", "cosmetics", "beauty", "serum", "cream",
            "moisturizer", "cleanser", "lipstick", "foundation", "mascara",
            "perfume", "fragrance", "nail", "hair", "shampoo", "conditioner"
        ],
        "electronics": [
            "phone", "laptop", "computer", "tablet", "headphones", "speaker",
            "camera", "gadget", "electronic", "device", "tech", "wireless",
            "bluetooth", "charger", "cable", "monitor", "keyboard", "mouse"
        ],
        "home": [
            "furniture", "decor", "home", "kitchen", "bedroom", "living",
            "table", "chair", "sofa", "bed", "lamp", "rug", "curtain",
            "pillow", "blanket", "storage", "organization", "cookware"
        ],
        "health": [
            "supplement", "vitamin", "protein", "fitness", "health", "wellness",
            "nutrition", "organic", "natural", "herbal", "remedy", "therapy",
            "medical", "healthcare", "dietary", "probiotic", "omega"
        ],
        "sports": [
            "sports", "fitness", "gym", "workout", "exercise", "athletic",
            "training", "running", "yoga", "cycling", "swimming", "outdoor",
            "camping", "hiking", "equipment", "gear", "activewear"
        ]
    }

    def __init__(self):
        """Initialize the Shopify scraper with httpx client."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
        self.current_ua_index = 0
        self.request_timestamps: Dict[str, List[float]] = {}  # Domain -> timestamps
        self.rate_limit_delay = 1.0  # 1 second between requests per domain

    def _get_user_agent(self) -> str:
        """
        Get next user agent from rotation.

        Returns:
            User agent string
        """
        ua = self.USER_AGENTS[self.current_ua_index]
        self.current_ua_index = (self.current_ua_index + 1) % len(self.USER_AGENTS)
        return ua

    async def _rate_limit(self, domain: str) -> None:
        """
        Implement rate limiting per domain (1 req/sec).

        Args:
            domain: Domain to rate limit
        """
        current_time = asyncio.get_event_loop().time()

        if domain not in self.request_timestamps:
            self.request_timestamps[domain] = []

        # Clean old timestamps (older than 1 second)
        self.request_timestamps[domain] = [
            ts for ts in self.request_timestamps[domain]
            if current_time - ts < self.rate_limit_delay
        ]

        # If there were requests in the last second, wait
        if self.request_timestamps[domain]:
            last_request = self.request_timestamps[domain][-1]
            time_since_last = current_time - last_request
            if time_since_last < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - time_since_last
                logger.debug(f"Rate limiting {domain}: sleeping {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)

        # Record this request
        self.request_timestamps[domain].append(asyncio.get_event_loop().time())

    async def _make_request(
        self,
        url: str,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[httpx.Response]:
        """
        Make HTTP request with retry logic and exponential backoff.

        Args:
            url: URL to request
            max_retries: Maximum number of retry attempts
            retry_delay: Initial retry delay in seconds

        Returns:
            Response object or None on failure
        """
        domain = urlparse(url).netloc

        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                await self._rate_limit(domain)

                # Make request
                headers = {"User-Agent": self._get_user_agent()}
                response = await self.client.get(url, headers=headers)

                # Handle rate limiting from server
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", retry_delay * (2 ** attempt)))
                    logger.warning(f"Rate limited by {domain}, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                # Return successful responses
                if response.status_code in [200, 201]:
                    return response

                # Handle client errors (don't retry)
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    logger.error(f"Client error {response.status_code} for {url}")
                    return None

                # Retry on server errors
                if response.status_code >= 500:
                    logger.warning(f"Server error {response.status_code} for {url}, attempt {attempt + 1}/{max_retries}")
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue

                return response

            except httpx.TimeoutException:
                logger.warning(f"Timeout for {url}, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                return None

            except httpx.ConnectError:
                logger.error(f"Connection error for {url}")
                return None

            except Exception as e:
                logger.error(f"Unexpected error for {url}: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                return None

        logger.error(f"Max retries exceeded for {url}")
        return None

    def _normalize_domain(self, domain: str) -> str:
        """
        Normalize domain name.

        Args:
            domain: Domain to normalize

        Returns:
            Normalized domain without protocol
        """
        # Remove protocol
        domain = re.sub(r'^https?://', '', domain)
        # Remove trailing slash
        domain = domain.rstrip('/')
        # Remove www.
        domain = re.sub(r'^www\.', '', domain)
        return domain

    async def is_shopify_store(self, domain: str) -> bool:
        """
        Check if a domain is a Shopify store.

        Args:
            domain: Domain to check

        Returns:
            True if it's a Shopify store, False otherwise
        """
        domain = self._normalize_domain(domain)
        logger.info(f"Checking if {domain} is a Shopify store")

        try:
            # Method 1: Check /products.json endpoint
            products_url = f"https://{domain}/products.json?limit=1"
            response = await self._make_request(products_url)

            if response and response.status_code == 200:
                try:
                    data = response.json()
                    if "products" in data:
                        logger.info(f"{domain} is a Shopify store (products.json exists)")
                        return True
                except Exception:
                    pass

            # Method 2: Check homepage for Shopify indicators
            homepage_url = f"https://{domain}"
            response = await self._make_request(homepage_url)

            if response and response.status_code == 200:
                content = response.text

                # Check for Shopify CDN
                if "cdn.shopify.com" in content:
                    logger.info(f"{domain} is a Shopify store (Shopify CDN found)")
                    return True

                # Check for Shopify meta tags
                if 'name="shopify-' in content or 'Shopify.theme' in content:
                    logger.info(f"{domain} is a Shopify store (Shopify meta tags found)")
                    return True

                # Check headers
                if "x-shopify-stage" in response.headers or "x-shopify-shop-api-call-limit" in response.headers:
                    logger.info(f"{domain} is a Shopify store (Shopify headers found)")
                    return True

            logger.info(f"{domain} is not a Shopify store")
            return False

        except Exception as e:
            logger.error(f"Error checking if {domain} is Shopify store: {str(e)}")
            return False

    async def get_products(self, domain: str, limit: int = 250) -> List[dict]:
        """
        Fetch all products from a Shopify store.

        Args:
            domain: Shopify store domain
            limit: Products per page (max 250)

        Returns:
            List of product dictionaries
        """
        domain = self._normalize_domain(domain)
        logger.info(f"Fetching products from {domain}")

        all_products = []
        page = 1
        limit = min(limit, 250)  # Shopify max

        try:
            while True:
                url = f"https://{domain}/products.json?limit={limit}&page={page}"
                response = await self._make_request(url)

                if not response or response.status_code != 200:
                    break

                try:
                    data = response.json()
                    products = data.get("products", [])

                    if not products:
                        break

                    # Parse products
                    for product in products:
                        parsed_product = {
                            "id": product.get("id"),
                            "title": product.get("title"),
                            "handle": product.get("handle"),
                            "description": product.get("body_html", ""),
                            "vendor": product.get("vendor"),
                            "product_type": product.get("product_type"),
                            "created_at": product.get("created_at"),
                            "updated_at": product.get("updated_at"),
                            "published_at": product.get("published_at"),
                            "tags": product.get("tags", "").split(", ") if product.get("tags") else [],
                            "variants": [],
                            "images": [],
                            "price": None,
                            "compare_at_price": None,
                        }

                        # Parse variants
                        for variant in product.get("variants", []):
                            parsed_product["variants"].append({
                                "id": variant.get("id"),
                                "title": variant.get("title"),
                                "price": variant.get("price"),
                                "compare_at_price": variant.get("compare_at_price"),
                                "available": variant.get("available"),
                                "sku": variant.get("sku"),
                            })

                            # Set main product price from first variant
                            if not parsed_product["price"] and variant.get("price"):
                                parsed_product["price"] = float(variant["price"])
                            if not parsed_product["compare_at_price"] and variant.get("compare_at_price"):
                                parsed_product["compare_at_price"] = float(variant["compare_at_price"])

                        # Parse images
                        for image in product.get("images", []):
                            parsed_product["images"].append({
                                "id": image.get("id"),
                                "src": image.get("src"),
                                "alt": image.get("alt"),
                            })

                        # Set main image
                        if parsed_product["images"]:
                            parsed_product["image_url"] = parsed_product["images"][0]["src"]
                        else:
                            parsed_product["image_url"] = None

                        all_products.append(parsed_product)

                    logger.info(f"Fetched page {page} with {len(products)} products from {domain}")

                    # Check if there are more pages
                    if len(products) < limit:
                        break

                    page += 1

                except Exception as e:
                    logger.error(f"Error parsing products from {domain}: {str(e)}")
                    break

            logger.info(f"Total products fetched from {domain}: {len(all_products)}")
            return all_products

        except Exception as e:
            logger.error(f"Error fetching products from {domain}: {str(e)}")
            return []

    async def get_store_info(self, domain: str) -> dict:
        """
        Scrape store information from homepage.

        Args:
            domain: Shopify store domain

        Returns:
            Dictionary with store information
        """
        domain = self._normalize_domain(domain)
        logger.info(f"Fetching store info from {domain}")

        store_info = {
            "domain": domain,
            "name": None,
            "description": None,
            "logo_url": None,
            "social_links": {},
            "theme_name": None,
        }

        try:
            url = f"https://{domain}"
            response = await self._make_request(url)

            if not response or response.status_code != 200:
                return store_info

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract store name
            title_tag = soup.find("title")
            if title_tag:
                store_info["name"] = title_tag.get_text().strip()

            # Extract description from meta tags
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                store_info["description"] = meta_desc.get("content", "").strip()

            # Extract logo from og:image or favicon
            og_image = soup.find("meta", attrs={"property": "og:image"})
            if og_image:
                store_info["logo_url"] = og_image.get("content")
            else:
                favicon = soup.find("link", attrs={"rel": "icon"})
                if favicon:
                    store_info["logo_url"] = favicon.get("href")

            # Extract social links
            social_patterns = {
                "instagram": r"instagram\.com/([a-zA-Z0-9._]+)",
                "facebook": r"facebook\.com/([a-zA-Z0-9.]+)",
                "twitter": r"twitter\.com/([a-zA-Z0-9_]+)",
                "tiktok": r"tiktok\.com/@([a-zA-Z0-9._]+)",
                "youtube": r"youtube\.com/(c/|channel/|user/)?([a-zA-Z0-9_-]+)",
            }

            page_text = response.text
            for platform, pattern in social_patterns.items():
                matches = re.findall(pattern, page_text)
                if matches:
                    # Get the first match
                    username = matches[0] if isinstance(matches[0], str) else matches[0][-1]
                    store_info["social_links"][platform] = f"https://{platform}.com/{username}"

            # Try to detect theme name
            theme_match = re.search(r'Shopify\.theme\s*=\s*{[^}]*"name"\s*:\s*"([^"]+)"', response.text)
            if theme_match:
                store_info["theme_name"] = theme_match.group(1)

            logger.info(f"Store info fetched for {domain}")
            return store_info

        except Exception as e:
            logger.error(f"Error fetching store info from {domain}: {str(e)}")
            return store_info

    def _categorize_store(self, products: List[dict]) -> str:
        """
        Categorize store based on products using keyword matching.

        Args:
            products: List of product dictionaries

        Returns:
            Category name
        """
        if not products:
            return "other"

        # Count category keywords in product titles and tags
        category_scores = {category: 0 for category in self.CATEGORY_KEYWORDS}

        for product in products:
            # Combine title, type, and tags
            text = " ".join([
                product.get("title", ""),
                product.get("product_type", ""),
                " ".join(product.get("tags", []))
            ]).lower()

            # Score each category
            for category, keywords in self.CATEGORY_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in text:
                        category_scores[category] += 1

        # Get category with highest score
        if sum(category_scores.values()) == 0:
            return "other"

        best_category = max(category_scores.items(), key=lambda x: x[1])[0]
        logger.info(f"Store categorized as '{best_category}' with scores: {category_scores}")
        return best_category

    def _calculate_avg_price(self, products: List[dict]) -> Optional[float]:
        """
        Calculate average product price.

        Args:
            products: List of product dictionaries

        Returns:
            Average price or None
        """
        if not products:
            return None

        prices = []
        for product in products:
            if product.get("price"):
                prices.append(float(product["price"]))

        if not prices:
            return None

        return round(sum(prices) / len(prices), 2)

    async def get_product_details(self, domain: str, handle: str) -> Optional[dict]:
        """
        Fetch detailed product information.

        Args:
            domain: Shopify store domain
            handle: Product handle (slug)

        Returns:
            Product dictionary or None
        """
        domain = self._normalize_domain(domain)
        logger.info(f"Fetching product details for {handle} from {domain}")

        try:
            url = f"https://{domain}/products/{handle}.json"
            response = await self._make_request(url)

            if not response or response.status_code != 200:
                return None

            data = response.json()
            product = data.get("product", {})

            logger.info(f"Product details fetched for {handle}")
            return product

        except Exception as e:
            logger.error(f"Error fetching product details for {handle}: {str(e)}")
            return None

    async def analyze_store(self, domain: str) -> dict:
        """
        Perform comprehensive store analysis.

        Args:
            domain: Shopify store domain

        Returns:
            Dictionary with complete store analysis
        """
        domain = self._normalize_domain(domain)
        logger.info(f"Starting comprehensive analysis of {domain}")

        analysis = {
            "domain": domain,
            "is_shopify": False,
            "name": None,
            "description": None,
            "logo_url": None,
            "category": "other",
            "product_count": 0,
            "avg_price": None,
            "min_price": None,
            "max_price": None,
            "social_links": {},
            "theme_name": None,
            "products": [],
            "analyzed_at": datetime.utcnow().isoformat(),
            "error": None,
        }

        try:
            # Check if it's a Shopify store
            is_shopify = await self.is_shopify_store(domain)
            analysis["is_shopify"] = is_shopify

            if not is_shopify:
                analysis["error"] = "Not a Shopify store"
                return analysis

            # Fetch store info and products concurrently
            store_info_task = asyncio.create_task(self.get_store_info(domain))
            products_task = asyncio.create_task(self.get_products(domain))

            store_info, products = await asyncio.gather(store_info_task, products_task)

            # Update analysis with store info
            analysis.update({
                "name": store_info.get("name"),
                "description": store_info.get("description"),
                "logo_url": store_info.get("logo_url"),
                "social_links": store_info.get("social_links", {}),
                "theme_name": store_info.get("theme_name"),
            })

            # Update analysis with product data
            analysis["products"] = products
            analysis["product_count"] = len(products)

            if products:
                # Categorize store
                analysis["category"] = self._categorize_store(products)

                # Calculate price statistics
                prices = [float(p["price"]) for p in products if p.get("price")]
                if prices:
                    analysis["avg_price"] = round(sum(prices) / len(prices), 2)
                    analysis["min_price"] = round(min(prices), 2)
                    analysis["max_price"] = round(max(prices), 2)

            logger.info(f"Analysis complete for {domain}: {analysis['product_count']} products, category: {analysis['category']}")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing store {domain}: {str(e)}")
            analysis["error"] = str(e)
            return analysis

    async def close(self):
        """Close the httpx client."""
        await self.client.aclose()


# Singleton instance
_scraper_instance = None


async def get_scraper() -> ShopifyScraper:
    """
    Get or create scraper instance.

    Returns:
        ShopifyScraper instance
    """
    global _scraper_instance
    if _scraper_instance is None:
        _scraper_instance = ShopifyScraper()
    return _scraper_instance
