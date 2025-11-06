"""
Trending Score Calculation Service

Calculates intelligent 0-100 trending scores for e-commerce stores based on:
- Growth velocity (35%)
- Recency bonus (25%)
- Product engagement (20%)
- Category momentum (10%)
- Traffic estimation (10%)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store, StoreCategory
from app.models.product import Product
from app.services.redis_service import RedisService
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class TrendingService:
    """
    Service for calculating intelligent trending scores for stores.

    The trending score is a 0-100 value that indicates how "hot" or trending
    a store is based on multiple weighted factors.
    """

    # Category multipliers for revenue estimation
    CATEGORY_MULTIPLIERS = {
        StoreCategory.FASHION: 1.2,
        StoreCategory.BEAUTY: 1.5,
        StoreCategory.ELECTRONICS: 0.8,
        StoreCategory.HOME: 1.0,
        StoreCategory.HEALTH: 1.3,
        StoreCategory.SPORTS: 0.9,
        StoreCategory.OTHER: 1.0,
    }

    # Weight distribution for scoring factors
    WEIGHTS = {
        "growth": 0.35,
        "recency": 0.25,
        "engagement": 0.20,
        "category": 0.10,
        "traffic": 0.10,
    }

    # Cache TTL for category averages (6 hours)
    CATEGORY_CACHE_TTL = 21600

    @classmethod
    async def calculate_trending_score(cls, store: Store, db: AsyncSession) -> float:
        """
        Calculate comprehensive trending score for a store.

        Args:
            store: Store model instance
            db: Database session

        Returns:
            Float between 0-100 representing trending score
        """
        try:
            # Calculate individual factor scores
            growth_score = await cls._calculate_growth_score(store, db)
            recency_score = cls._calculate_recency_score(store)
            engagement_score = await cls._calculate_engagement_score(store, db)
            category_score = await cls._calculate_category_score(store, db)
            traffic_score = cls._calculate_traffic_score(store)

            # Apply weighted formula
            trending_score = (
                growth_score * cls.WEIGHTS["growth"] +
                recency_score * cls.WEIGHTS["recency"] +
                engagement_score * cls.WEIGHTS["engagement"] +
                category_score * cls.WEIGHTS["category"] +
                traffic_score * cls.WEIGHTS["traffic"]
            )

            # Ensure score is between 0-100
            trending_score = max(0.0, min(100.0, trending_score))

            logger.info(
                f"Calculated trending score for {store.domain}: {trending_score:.2f} "
                f"(growth={growth_score:.1f}, recency={recency_score:.1f}, "
                f"engagement={engagement_score:.1f}, category={category_score:.1f}, "
                f"traffic={traffic_score:.1f})"
            )

            return round(trending_score, 2)

        except Exception as e:
            logger.error(f"Error calculating trending score for {store.domain}: {str(e)}")
            return 0.0

    @classmethod
    async def _calculate_growth_score(cls, store: Store, db: AsyncSession) -> float:
        """
        Calculate growth velocity score (0-100) based on product count growth.

        Weight: 35%

        Growth Rate Scoring:
        - >50% growth: 100 points
        - 20-50%: 70 points
        - 5-20%: 40 points
        - 0-5%: 20 points
        - Negative: 0 points
        """
        try:
            growth_rate = await cls.calculate_growth_rate(store, db)

            if growth_rate is None:
                # New store or no historical data - give moderate score
                return 50.0

            # Score based on growth rate brackets
            if growth_rate >= 50:
                return 100.0
            elif growth_rate >= 20:
                # Linear interpolation between 70-100
                return 70.0 + ((growth_rate - 20) / 30) * 30
            elif growth_rate >= 5:
                # Linear interpolation between 40-70
                return 40.0 + ((growth_rate - 5) / 15) * 30
            elif growth_rate >= 0:
                # Linear interpolation between 20-40
                return 20.0 + (growth_rate / 5) * 20
            else:
                # Negative growth - penalize based on decline
                if growth_rate <= -20:
                    return 0.0
                else:
                    # Linear decay from 20 to 0
                    return max(0.0, 20.0 + growth_rate)

        except Exception as e:
            logger.error(f"Error calculating growth score for {store.domain}: {str(e)}")
            return 0.0

    @classmethod
    def _calculate_recency_score(cls, store: Store) -> float:
        """
        Calculate recency bonus score (0-100) based on store age.

        Weight: 25%

        Scoring:
        - Stores < 30 days: 90-100 points
        - Stores < 90 days: 70-90 points
        - Stores < 180 days: 50-70 points
        - Stores > 1 year: decay gradually to 0
        """
        try:
            days_since_created = (datetime.utcnow() - store.created_at).days

            # Formula: max(0, 100 - (days_since_created / 365 * 50))
            # This gives stores a year to decay from 100 to 50, then continues
            base_score = 100 - (days_since_created / 365 * 50)

            # Apply bonus for very new stores
            if days_since_created <= 30:
                # Extra boost for stores under 30 days
                bonus = (30 - days_since_created) / 30 * 10
                return min(100.0, base_score + bonus)

            return max(0.0, min(100.0, base_score))

        except Exception as e:
            logger.error(f"Error calculating recency score for {store.domain}: {str(e)}")
            return 0.0

    @classmethod
    async def _calculate_engagement_score(cls, store: Store, db: AsyncSession) -> float:
        """
        Calculate product engagement score (0-100).

        Weight: 20%

        Based on:
        - Product availability ratio (40%)
        - Price range optimization (30%) - $30-$150 sweet spot
        - Product diversity (30%) - unique titles
        """
        try:
            # Get store products
            stmt = select(Product).where(Product.store_id == store.id).limit(250)
            result = await db.execute(stmt)
            products = result.scalars().all()

            if not products:
                return 0.0

            # 1. Availability ratio (40 points)
            available_count = sum(1 for p in products if p.available)
            availability_ratio = available_count / len(products)
            availability_score = availability_ratio * 40

            # 2. Price range optimization (30 points)
            # Sweet spot is $30-$150 (higher conversion rates)
            prices = [p.price for p in products if p.price is not None]

            if prices:
                avg_price = sum(prices) / len(prices)

                if 30 <= avg_price <= 150:
                    # Perfect range
                    price_score = 30.0
                elif 15 <= avg_price < 30:
                    # Below sweet spot - still good
                    price_score = 20.0 + ((avg_price - 15) / 15) * 10
                elif 150 < avg_price <= 300:
                    # Above sweet spot - still good
                    price_score = 20.0 + ((300 - avg_price) / 150) * 10
                else:
                    # Too low or too high
                    price_score = 10.0
            else:
                price_score = 0.0

            # 3. Product diversity (30 points)
            # More unique titles = better diversity
            unique_titles = len(set(p.title.lower() for p in products if p.title))
            diversity_ratio = unique_titles / len(products)
            diversity_score = diversity_ratio * 30

            total_engagement = availability_score + price_score + diversity_score

            return min(100.0, total_engagement)

        except Exception as e:
            logger.error(f"Error calculating engagement score for {store.domain}: {str(e)}")
            return 0.0

    @classmethod
    async def _calculate_category_score(cls, store: Store, db: AsyncSession) -> float:
        """
        Calculate category momentum score (0-100).

        Weight: 10%

        Compares store performance to category average.
        Stores outperforming their category get bonus points.
        """
        try:
            category_avg = await cls.get_category_average(store.category, db)

            if category_avg == 0:
                return 50.0  # No category data, give neutral score

            # Calculate preliminary score (without category component to avoid recursion)
            prelim_score = (
                await cls._calculate_growth_score(store, db) * 0.389 +  # 35/90
                cls._calculate_recency_score(store) * 0.278 +  # 25/90
                await cls._calculate_engagement_score(store, db) * 0.222 +  # 20/90
                cls._calculate_traffic_score(store) * 0.111  # 10/90
            )

            # Compare to category average
            if prelim_score > category_avg:
                # Outperforming category
                ratio = prelim_score / category_avg
                return min(100.0, ratio * 50)
            else:
                # Underperforming category
                ratio = prelim_score / category_avg
                return ratio * 50

        except Exception as e:
            logger.error(f"Error calculating category score for {store.domain}: {str(e)}")
            return 50.0

    @classmethod
    def _calculate_traffic_score(cls, store: Store) -> float:
        """
        Calculate traffic estimation score (0-100).

        Weight: 10%

        Scoring based on estimated monthly visitors:
        - >1M: 100 points
        - 500K-1M: 80 points
        - 100K-500K: 60 points
        - 10K-100K: 40 points
        - <10K: 20 points
        """
        try:
            # Check if we have traffic data
            if store.estimated_monthly_visitors is None:
                # No traffic data, estimate from product count and trending score
                # This is a fallback estimation
                if store.product_count > 1000:
                    return 60.0
                elif store.product_count > 500:
                    return 50.0
                elif store.product_count > 100:
                    return 40.0
                else:
                    return 30.0

            visitors = store.estimated_monthly_visitors

            if visitors >= 1_000_000:
                return 100.0
            elif visitors >= 500_000:
                # Linear interpolation between 80-100
                return 80.0 + ((visitors - 500_000) / 500_000) * 20
            elif visitors >= 100_000:
                # Linear interpolation between 60-80
                return 60.0 + ((visitors - 100_000) / 400_000) * 20
            elif visitors >= 10_000:
                # Linear interpolation between 40-60
                return 40.0 + ((visitors - 10_000) / 90_000) * 20
            else:
                # Linear interpolation between 0-40
                return min(40.0, (visitors / 10_000) * 40)

        except Exception as e:
            logger.error(f"Error calculating traffic score for {store.domain}: {str(e)}")
            return 0.0

    @classmethod
    async def calculate_growth_rate(cls, store: Store, db: AsyncSession) -> Optional[float]:
        """
        Calculate product count growth rate over time.

        Compares current product count to historical values:
        - Checks 7 days ago and 30 days ago
        - Returns percentage growth

        Args:
            store: Store model instance
            db: Database session

        Returns:
            Percentage growth rate or None if no historical data
        """
        try:
            # Check if we have historical data stored
            # For now, we'll use a simplified approach based on last_scraped_at

            if store.last_scraped_at is None:
                return None

            days_since_scraped = (datetime.utcnow() - store.last_scraped_at).days

            if days_since_scraped < 7:
                # Too recent to calculate growth
                return None

            # Try to get historical product count from Redis cache
            cache_key = f"store_history:{store.id}"
            redis_client = await RedisService.get_redis()

            historical_data = await redis_client.hgetall(cache_key)

            if not historical_data:
                # No historical data, store current count for future
                await redis_client.hset(
                    cache_key,
                    mapping={
                        "product_count": str(store.product_count),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                await redis_client.expire(cache_key, 86400 * 90)  # 90 days
                return None

            # Calculate growth rate
            previous_count = int(historical_data.get(b"product_count", 0))
            current_count = store.product_count

            if previous_count == 0:
                return 100.0 if current_count > 0 else 0.0

            growth_rate = ((current_count - previous_count) / previous_count) * 100

            # Update historical data
            await redis_client.hset(
                cache_key,
                mapping={
                    "product_count": str(current_count),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            return round(growth_rate, 2)

        except Exception as e:
            logger.error(f"Error calculating growth rate for {store.domain}: {str(e)}")
            return None

    @classmethod
    async def get_category_average(cls, category: StoreCategory, db: AsyncSession) -> float:
        """
        Get average trending score for a category.

        Cached for 6 hours to improve performance.

        Args:
            category: Store category enum
            db: Database session

        Returns:
            Average trending score for category
        """
        try:
            # Check cache first
            cache_key = f"category_avg:{category.value}"
            redis_client = await RedisService.get_redis()

            cached_value = await redis_client.get(cache_key)
            if cached_value:
                return float(cached_value)

            # Calculate average from database
            stmt = select(func.avg(Store.trending_score)).where(
                and_(
                    Store.category == category,
                    Store.is_active == True,
                    Store.trending_score > 0
                )
            )
            result = await db.execute(stmt)
            avg_score = result.scalar_one_or_none()

            if avg_score is None:
                avg_score = 50.0  # Default if no stores in category

            # Cache for 6 hours
            await redis_client.setex(cache_key, cls.CATEGORY_CACHE_TTL, str(avg_score))

            return float(avg_score)

        except Exception as e:
            logger.error(f"Error getting category average for {category}: {str(e)}")
            return 50.0

    @classmethod
    async def estimate_revenue(cls, store: Store, db: AsyncSession) -> int:
        """
        Estimate monthly revenue for a store.

        Formula: product_count * avg_price * 30 * 0.05
        Assumptions:
        - 5% conversion rate (industry standard for e-commerce)
        - 30 orders per month per product (conservative estimate)

        Adjusted by category multipliers:
        - Fashion: 1.2x
        - Beauty: 1.5x
        - Electronics: 0.8x
        - Home: 1.0x
        - Health: 1.3x
        - Sports: 0.9x

        Args:
            store: Store model instance
            db: Database session

        Returns:
            Estimated monthly revenue in USD
        """
        try:
            # Get average product price
            avg_price = store.avg_product_price or 0

            if avg_price == 0:
                # Calculate from products
                stmt = select(func.avg(Product.price)).where(
                    and_(
                        Product.store_id == store.id,
                        Product.price.isnot(None),
                        Product.price > 0
                    )
                )
                result = await db.execute(stmt)
                avg_price = result.scalar_one_or_none() or 50.0  # Default $50

            # Base calculation
            # Formula: products * avg_price * orders_per_month_per_product * conversion_rate
            product_count = store.product_count or 0
            orders_per_product = 30
            conversion_rate = 0.05

            base_revenue = product_count * avg_price * orders_per_product * conversion_rate

            # Apply category multiplier
            category_multiplier = cls.CATEGORY_MULTIPLIERS.get(store.category, 1.0)
            estimated_revenue = base_revenue * category_multiplier

            return int(estimated_revenue)

        except Exception as e:
            logger.error(f"Error estimating revenue for {store.domain}: {str(e)}")
            return 0

    @classmethod
    async def batch_calculate_trending_scores(
        cls,
        limit: Optional[int] = None,
        only_active: bool = True
    ) -> Dict[str, int]:
        """
        Calculate trending scores for all stores in batch.

        Args:
            limit: Optional limit on number of stores to process
            only_active: Only process active stores

        Returns:
            Dictionary with statistics:
            - total: Total stores processed
            - updated: Stores with updated scores
            - errors: Stores with errors
        """
        stats = {
            "total": 0,
            "updated": 0,
            "errors": 0,
            "score_changes": [],
        }

        try:
            async with AsyncSessionLocal() as db:
                # Build query
                stmt = select(Store)

                if only_active:
                    stmt = stmt.where(Store.is_active == True)

                if limit:
                    stmt = stmt.limit(limit)

                # Order by last update to prioritize stale data
                stmt = stmt.order_by(Store.updated_at.asc())

                result = await db.execute(stmt)
                stores = result.scalars().all()

                stats["total"] = len(stores)

                # Process each store
                for store in stores:
                    try:
                        old_score = store.trending_score
                        new_score = await cls.calculate_trending_score(store, db)

                        # Update store
                        store.trending_score = new_score
                        store.updated_at = datetime.utcnow()

                        # Track score change
                        score_change = new_score - old_score
                        if abs(score_change) > 5:  # Only log significant changes
                            stats["score_changes"].append({
                                "domain": store.domain,
                                "old_score": old_score,
                                "new_score": new_score,
                                "change": score_change,
                            })

                        stats["updated"] += 1

                    except Exception as e:
                        logger.error(f"Error processing store {store.domain}: {str(e)}")
                        stats["errors"] += 1

                # Commit all changes
                await db.commit()

                logger.info(
                    f"Batch calculation complete: {stats['updated']} stores updated, "
                    f"{stats['errors']} errors"
                )

        except Exception as e:
            logger.error(f"Error in batch calculation: {str(e)}")
            stats["errors"] = stats["total"]

        return stats

    @classmethod
    async def get_trending_stores_by_score(
        cls,
        db: AsyncSession,
        min_score: float = 70.0,
        limit: int = 20
    ) -> List[Store]:
        """
        Get stores with high trending scores.

        Args:
            db: Database session
            min_score: Minimum trending score threshold
            limit: Maximum number of stores to return

        Returns:
            List of trending stores
        """
        try:
            stmt = (
                select(Store)
                .where(
                    and_(
                        Store.is_active == True,
                        Store.trending_score >= min_score
                    )
                )
                .order_by(Store.trending_score.desc())
                .limit(limit)
            )

            result = await db.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error getting trending stores: {str(e)}")
            return []
