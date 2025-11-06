"""
Store service for business logic and database operations.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from decimal import Decimal

from sqlalchemy import select, func, or_, desc, asc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store, StoreCategory
from app.models.product import Product
from app.models.user import User
from app.schemas import (
    StoreCreate,
    StoreUpdate,
    SearchFilters,
    PaginationMeta,
    StoreAnalytics,
    CategoryCount,
    CountryCount,
)
from app.services.redis_service import RedisService
from app.scrapers.shopify_scraper import ShopifyScraper

logger = logging.getLogger(__name__)


class StoreService:
    """Service for store operations."""

    CATEGORY_ICONS = {
        "fashion": "👕",
        "beauty": "💄",
        "electronics": "📱",
        "home": "🏠",
        "health": "💊",
        "sports": "⚽",
        "other": "🏪",
    }

    @staticmethod
    async def get_trending_stores(
        db: AsyncSession,
        limit: int = 20,
        offset: int = 0,
        filters: Optional[SearchFilters] = None
    ) -> Tuple[List[Store], PaginationMeta]:
        """
        Get trending stores with pagination and filters.

        Args:
            db: Database session
            limit: Number of stores to return
            offset: Offset for pagination
            filters: Search filters

        Returns:
            Tuple of (stores list, pagination metadata)
        """
        # Build query
        query = select(Store).where(Store.is_active == True)

        # Apply filters
        if filters:
            if filters.category:
                query = query.where(Store.category == StoreCategory(filters.category))

            if filters.country:
                query = query.where(Store.country_code == filters.country)

            if filters.min_revenue is not None:
                query = query.where(Store.estimated_monthly_revenue >= filters.min_revenue)

            if filters.max_revenue is not None:
                query = query.where(Store.estimated_monthly_revenue <= filters.max_revenue)

            if filters.min_products is not None:
                query = query.where(Store.product_count >= filters.min_products)

            if filters.max_products is not None:
                query = query.where(Store.product_count <= filters.max_products)

            # Apply sorting
            sort_column = getattr(Store, filters.sort_by)
            if filters.sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            # Default: sort by trending score
            query = query.order_by(desc(Store.trending_score))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.limit(limit).offset(offset)

        # Execute query
        result = await db.execute(query)
        stores = list(result.scalars().all())

        # Create pagination metadata
        pagination = PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_next=offset + limit < total,
            has_prev=offset > 0
        )

        return stores, pagination

    @staticmethod
    async def get_store_by_id(
        db: AsyncSession,
        store_id: uuid.UUID
    ) -> Optional[Store]:
        """
        Get store by ID.

        Args:
            db: Database session
            store_id: Store UUID

        Returns:
            Store or None
        """
        result = await db.execute(
            select(Store).where(Store.id == store_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_store_by_domain(
        db: AsyncSession,
        domain: str
    ) -> Optional[Store]:
        """
        Get store by domain.

        Args:
            db: Database session
            domain: Store domain

        Returns:
            Store or None
        """
        result = await db.execute(
            select(Store).where(Store.domain == domain)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_recent_products(
        db: AsyncSession,
        store_id: uuid.UUID,
        limit: int = 10
    ) -> List[Product]:
        """
        Get recent products for a store.

        Args:
            db: Database session
            store_id: Store UUID
            limit: Number of products to return

        Returns:
            List of products
        """
        result = await db.execute(
            select(Product)
            .where(Product.store_id == store_id)
            .order_by(desc(Product.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_category_rank(
        db: AsyncSession,
        store: Store
    ) -> Optional[int]:
        """
        Get store's rank in its category.

        Args:
            db: Database session
            store: Store object

        Returns:
            Rank (1-indexed) or None
        """
        # Count stores with higher trending score in same category
        result = await db.execute(
            select(func.count())
            .select_from(Store)
            .where(
                and_(
                    Store.category == store.category,
                    Store.trending_score > store.trending_score,
                    Store.is_active == True
                )
            )
        )
        higher_count = result.scalar() or 0
        return higher_count + 1

    @staticmethod
    async def track_store_view(
        store_id: uuid.UUID
    ) -> None:
        """
        Track store view in Redis for analytics.

        Args:
            store_id: Store UUID
        """
        try:
            key = f"store:views:{store_id}"
            await RedisService.get_redis()
            redis = await RedisService.get_redis()
            await redis.incr(key)
            # Set expiration to 30 days
            await redis.expire(key, 30 * 24 * 60 * 60)
        except Exception as e:
            logger.error(f"Failed to track store view: {str(e)}")

    @staticmethod
    async def get_store_view_count(
        store_id: uuid.UUID
    ) -> int:
        """
        Get store view count from Redis.

        Args:
            store_id: Store UUID

        Returns:
            View count
        """
        try:
            key = f"store:views:{store_id}"
            redis = await RedisService.get_redis()
            count = await redis.get(key)
            return int(count) if count else 0
        except Exception:
            return 0

    @staticmethod
    async def search_stores(
        db: AsyncSession,
        query: str,
        limit: int = 20,
        offset: int = 0,
        filters: Optional[SearchFilters] = None
    ) -> Tuple[List[Store], PaginationMeta]:
        """
        Search stores by name or domain.

        Args:
            db: Database session
            query: Search query
            limit: Number of results
            offset: Offset for pagination
            filters: Additional filters

        Returns:
            Tuple of (stores, pagination)
        """
        # Build search query
        search_query = select(Store).where(
            and_(
                Store.is_active == True,
                or_(
                    Store.name.ilike(f"%{query}%"),
                    Store.domain.ilike(f"%{query}%"),
                    Store.description.ilike(f"%{query}%")
                )
            )
        )

        # Apply filters
        if filters:
            if filters.category:
                search_query = search_query.where(Store.category == StoreCategory(filters.category))
            if filters.country:
                search_query = search_query.where(Store.country_code == filters.country)

        # Get total count
        count_query = select(func.count()).select_from(search_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and sorting
        search_query = search_query.order_by(desc(Store.trending_score))
        search_query = search_query.limit(limit).offset(offset)

        # Execute
        result = await db.execute(search_query)
        stores = list(result.scalars().all())

        pagination = PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_next=offset + limit < total,
            has_prev=offset > 0
        )

        return stores, pagination

    @staticmethod
    async def get_store_products(
        db: AsyncSession,
        store_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Product], PaginationMeta]:
        """
        Get products for a store with pagination.

        Args:
            db: Database session
            store_id: Store UUID
            limit: Number of products
            offset: Offset for pagination
            sort_by: Sort field
            sort_order: Sort order (asc/desc)

        Returns:
            Tuple of (products, pagination)
        """
        # Build query
        query = select(Product).where(Product.store_id == store_id)

        # Apply sorting
        sort_column = getattr(Product, sort_by, Product.created_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Get total count
        count_query = select(func.count()).select_from(Product).where(Product.store_id == store_id)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.limit(limit).offset(offset)

        # Execute
        result = await db.execute(query)
        products = list(result.scalars().all())

        pagination = PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_next=offset + limit < total,
            has_prev=offset > 0
        )

        return products, pagination

    @staticmethod
    async def get_categories_with_counts(
        db: AsyncSession
    ) -> List[CategoryCount]:
        """
        Get all categories with store counts.

        Args:
            db: Database session

        Returns:
            List of CategoryCount objects
        """
        result = await db.execute(
            select(
                Store.category,
                func.count(Store.id).label("count")
            )
            .where(Store.is_active == True)
            .group_by(Store.category)
            .order_by(desc("count"))
        )

        categories = []
        for row in result:
            category = row[0]
            count = row[1]
            categories.append(CategoryCount(
                name=category.value if isinstance(category, StoreCategory) else category,
                count=count,
                icon=StoreService.CATEGORY_ICONS.get(
                    category.value if isinstance(category, StoreCategory) else category,
                    "🏪"
                )
            ))

        return categories

    @staticmethod
    async def get_countries_with_counts(
        db: AsyncSession
    ) -> List[CountryCount]:
        """
        Get all countries with store counts.

        Args:
            db: Database session

        Returns:
            List of CountryCount objects
        """
        result = await db.execute(
            select(
                Store.country_code,
                func.count(Store.id).label("count")
            )
            .where(
                and_(
                    Store.is_active == True,
                    Store.country_code.isnot(None)
                )
            )
            .group_by(Store.country_code)
            .order_by(desc("count"))
        )

        # Country code to name/flag mapping (top countries)
        country_data = {
            "US": ("United States", "🇺🇸"),
            "GB": ("United Kingdom", "🇬🇧"),
            "CA": ("Canada", "🇨🇦"),
            "AU": ("Australia", "🇦🇺"),
            "DE": ("Germany", "🇩🇪"),
            "FR": ("France", "🇫🇷"),
            "IT": ("Italy", "🇮🇹"),
            "ES": ("Spain", "🇪🇸"),
            "NL": ("Netherlands", "🇳🇱"),
            "SE": ("Sweden", "🇸🇪"),
            "DK": ("Denmark", "🇩🇰"),
            "NO": ("Norway", "🇳🇴"),
            "FI": ("Finland", "🇫🇮"),
            "JP": ("Japan", "🇯🇵"),
            "CN": ("China", "🇨🇳"),
            "IN": ("India", "🇮🇳"),
            "BR": ("Brazil", "🇧🇷"),
            "MX": ("Mexico", "🇲🇽"),
            "AR": ("Argentina", "🇦🇷"),
            "NZ": ("New Zealand", "🇳🇿"),
        }

        countries = []
        for row in result:
            code = row[0]
            count = row[1]
            name, flag = country_data.get(code, (code, "🌍"))
            countries.append(CountryCount(
                code=code,
                name=name,
                count=count,
                flag=flag
            ))

        return countries

    @staticmethod
    async def create_store(
        db: AsyncSession,
        store_data: StoreCreate
    ) -> Store:
        """
        Create a new store.

        Args:
            db: Database session
            store_data: Store creation data

        Returns:
            Created store
        """
        store = Store(
            id=uuid.uuid4(),
            domain=store_data.domain,
            name=store_data.name,
            description=store_data.description,
            category=StoreCategory(store_data.category),
            country_code=store_data.country_code,
            logo_url=store_data.logo_url,
            product_count=store_data.product_count,
            avg_product_price=store_data.avg_product_price,
            estimated_monthly_revenue=store_data.estimated_monthly_revenue,
            estimated_monthly_visitors=store_data.estimated_monthly_visitors,
            trending_score=store_data.trending_score,
            growth_rate=store_data.growth_rate,
            theme_name=store_data.theme_name,
            tech_stack=store_data.tech_stack,
            social_links=store_data.social_links,
            meta=store_data.meta,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_scraped_at=datetime.utcnow(),
        )

        db.add(store)
        await db.commit()
        await db.refresh(store)

        return store

    @staticmethod
    async def analyze_and_save_store(
        domain: str,
        db: AsyncSession
    ) -> Store:
        """
        Analyze a store using scraper and save to database.

        Args:
            domain: Store domain
            db: Database session

        Returns:
            Store object
        """
        logger.info(f"Analyzing and saving store: {domain}")

        # Check if store already exists
        existing_store = await StoreService.get_store_by_domain(db, domain)

        # If exists and scraped recently, return cached
        if existing_store:
            if existing_store.last_scraped_at:
                hours_since_scrape = (datetime.utcnow() - existing_store.last_scraped_at).total_seconds() / 3600
                if hours_since_scrape < 24:
                    logger.info(f"Returning cached data for {domain}")
                    return existing_store

        # Run scraper
        scraper = ShopifyScraper()
        try:
            analysis = await scraper.analyze_store(domain)
        finally:
            await scraper.close()

        if not analysis["is_shopify"]:
            raise ValueError(f"{domain} is not a Shopify store")

        # Create or update store
        if existing_store:
            # Update existing
            existing_store.name = analysis["name"] or existing_store.name
            existing_store.description = analysis["description"] or existing_store.description
            existing_store.logo_url = analysis["logo_url"] or existing_store.logo_url
            existing_store.category = StoreCategory(analysis["category"])
            existing_store.product_count = analysis["product_count"]
            existing_store.avg_product_price = analysis["avg_price"]
            existing_store.theme_name = analysis["theme_name"]
            existing_store.social_links = analysis["social_links"]
            existing_store.last_scraped_at = datetime.utcnow()
            existing_store.updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(existing_store)

            logger.info(f"Updated store: {domain}")
            return existing_store
        else:
            # Create new
            store_data = StoreCreate(
                domain=analysis["domain"],
                name=analysis["name"] or analysis["domain"],
                description=analysis["description"],
                logo_url=analysis["logo_url"],
                category=analysis["category"],
                product_count=analysis["product_count"],
                avg_product_price=analysis["avg_price"],
                theme_name=analysis["theme_name"],
                social_links=analysis["social_links"],
            )

            store = await StoreService.create_store(db, store_data)
            logger.info(f"Created new store: {domain}")

            # Save products (in background ideally)
            # For now, we'll skip this to keep the response fast
            # TODO: Queue background job to save products

            return store


# Singleton service instance
store_service = StoreService()
