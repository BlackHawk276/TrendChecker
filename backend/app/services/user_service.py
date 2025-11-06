"""
User Service

Business logic for user operations including:
- Profile management
- Saved stores
- Alerts
- Usage tracking
- Activity logging
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from uuid import UUID
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.store import Store
from app.models.saved_store import SavedStore
from app.models.alert import Alert, AlertType
from app.services.redis_service import RedisService
from app.schemas import PaginationMeta

logger = logging.getLogger(__name__)


class UserService:
    """
    Service for user-related operations.
    """

    @staticmethod
    async def get_user_profile(user: User) -> Dict:
        """
        Get detailed user profile with computed fields.

        Args:
            user: User model instance

        Returns:
            Dictionary with profile data including searches_remaining
        """
        searches_remaining = user.searches_limit - user.searches_used_this_month

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "subscription_tier": user.subscription_tier.value,
            "subscription_status": user.subscription_status.value,
            "trial_ends_at": user.trial_ends_at,
            "subscription_ends_at": user.subscription_ends_at,
            "searches_used_this_month": user.searches_used_this_month,
            "searches_limit": user.searches_limit,
            "searches_remaining": searches_remaining,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
            "last_login_at": user.last_login_at,
            "api_key": user.api_key,
        }

    @staticmethod
    async def update_user_profile(
        user: User,
        full_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        db: AsyncSession = None
    ) -> User:
        """
        Update user profile.

        Args:
            user: User model instance
            full_name: New full name
            avatar_url: New avatar URL
            db: Database session

        Returns:
            Updated user
        """
        if full_name is not None:
            user.full_name = full_name

        if avatar_url is not None:
            user.avatar_url = avatar_url

        user.updated_at = datetime.utcnow()

        if db:
            await db.commit()
            await db.refresh(user)

        return user

    @staticmethod
    async def get_saved_stores(
        user_id: UUID,
        db: AsyncSession,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "saved_at"
    ) -> Tuple[List[Dict], PaginationMeta]:
        """
        Get user's saved stores with pagination.

        Args:
            user_id: User UUID
            db: Database session
            limit: Results per page
            offset: Pagination offset
            sort_by: Sort field (saved_at or trending_score)

        Returns:
            Tuple of (saved stores list, pagination metadata)
        """
        # Count total saved stores
        count_stmt = select(func.count()).select_from(SavedStore).where(
            SavedStore.user_id == user_id
        )
        result = await db.execute(count_stmt)
        total = result.scalar_one()

        # Build query for saved stores
        stmt = (
            select(SavedStore, Store)
            .join(Store, SavedStore.store_id == Store.id)
            .where(SavedStore.user_id == user_id)
        )

        # Apply sorting
        if sort_by == "trending_score":
            stmt = stmt.order_by(desc(Store.trending_score))
        else:
            stmt = stmt.order_by(desc(SavedStore.saved_at))

        stmt = stmt.limit(limit).offset(offset)

        result = await db.execute(stmt)
        rows = result.all()

        # Format response
        saved_stores = []
        for saved_store, store in rows:
            saved_stores.append({
                "store": store,
                "saved_at": saved_store.saved_at,
                "notes": saved_store.notes,
            })

        # Pagination metadata
        pagination = PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_next=offset + limit < total,
            has_prev=offset > 0,
        )

        return saved_stores, pagination

    @staticmethod
    async def save_store(
        user_id: UUID,
        store_id: UUID,
        notes: Optional[str],
        db: AsyncSession
    ) -> SavedStore:
        """
        Save a store to user's favorites.

        Args:
            user_id: User UUID
            store_id: Store UUID
            notes: Optional notes
            db: Database session

        Returns:
            SavedStore instance

        Raises:
            ValueError: If store doesn't exist
        """
        # Check if store exists
        stmt = select(Store).where(Store.id == store_id)
        result = await db.execute(stmt)
        store = result.scalar_one_or_none()

        if not store:
            raise ValueError("Store not found")

        # Check if already saved
        stmt = select(SavedStore).where(
            and_(
                SavedStore.user_id == user_id,
                SavedStore.store_id == store_id
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update notes if provided
            if notes is not None:
                existing.notes = notes
                await db.commit()
                await db.refresh(existing)
            return existing

        # Create new saved store
        saved_store = SavedStore(
            user_id=user_id,
            store_id=store_id,
            notes=notes,
            saved_at=datetime.utcnow()
        )

        db.add(saved_store)
        await db.commit()
        await db.refresh(saved_store)

        # Log activity
        await UserService.log_activity(
            user_id=user_id,
            activity_type="save",
            description=f"Saved store: {store.domain}",
            store_domain=store.domain
        )

        return saved_store

    @staticmethod
    async def unsave_store(
        user_id: UUID,
        store_id: UUID,
        db: AsyncSession
    ) -> bool:
        """
        Remove store from user's favorites.

        Args:
            user_id: User UUID
            store_id: Store UUID
            db: Database session

        Returns:
            True if deleted, False if not found
        """
        stmt = select(SavedStore).where(
            and_(
                SavedStore.user_id == user_id,
                SavedStore.store_id == store_id
            )
        )
        result = await db.execute(stmt)
        saved_store = result.scalar_one_or_none()

        if not saved_store:
            return False

        await db.delete(saved_store)
        await db.commit()

        return True

    @staticmethod
    async def update_saved_store_notes(
        user_id: UUID,
        store_id: UUID,
        notes: Optional[str],
        db: AsyncSession
    ) -> Optional[SavedStore]:
        """
        Update notes for a saved store.

        Args:
            user_id: User UUID
            store_id: Store UUID
            notes: New notes
            db: Database session

        Returns:
            Updated SavedStore or None if not found
        """
        stmt = select(SavedStore).where(
            and_(
                SavedStore.user_id == user_id,
                SavedStore.store_id == store_id
            )
        )
        result = await db.execute(stmt)
        saved_store = result.scalar_one_or_none()

        if not saved_store:
            return None

        saved_store.notes = notes
        await db.commit()
        await db.refresh(saved_store)

        return saved_store

    @staticmethod
    async def get_user_alerts(
        user_id: UUID,
        db: AsyncSession
    ) -> List[Alert]:
        """
        Get all alerts for a user.

        Args:
            user_id: User UUID
            db: Database session

        Returns:
            List of Alert instances
        """
        stmt = select(Alert).where(
            Alert.user_id == user_id
        ).order_by(desc(Alert.created_at))

        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def create_alert(
        user_id: UUID,
        alert_type: str,
        criteria: Optional[Dict],
        store_id: Optional[UUID],
        db: AsyncSession
    ) -> Alert:
        """
        Create a new alert for the user.

        Args:
            user_id: User UUID
            alert_type: Type of alert (new_store, price_drop, trending)
            criteria: Alert criteria configuration
            store_id: Optional store ID for store-specific alerts
            db: Database session

        Returns:
            Created Alert instance

        Raises:
            ValueError: If validation fails
        """
        # Validate alert type
        try:
            alert_type_enum = AlertType(alert_type)
        except ValueError:
            raise ValueError(f"Invalid alert type: {alert_type}")

        # Validate store-specific alerts
        if alert_type in ["price_drop", "trending"] and not store_id:
            raise ValueError(f"{alert_type} alerts require a store_id")

        if store_id:
            # Check if store exists
            stmt = select(Store).where(Store.id == store_id)
            result = await db.execute(stmt)
            store = result.scalar_one_or_none()

            if not store:
                raise ValueError("Store not found")

        # Create alert
        alert = Alert(
            user_id=user_id,
            alert_type=alert_type_enum,
            criteria=criteria,
            store_id=store_id,
            is_active=True,
            created_at=datetime.utcnow()
        )

        db.add(alert)
        await db.commit()
        await db.refresh(alert)

        logger.info(f"Created alert {alert.id} for user {user_id}: {alert_type}")

        return alert

    @staticmethod
    async def delete_alert(
        user_id: UUID,
        alert_id: UUID,
        db: AsyncSession
    ) -> bool:
        """
        Delete an alert.

        Args:
            user_id: User UUID
            alert_id: Alert UUID
            db: Database session

        Returns:
            True if deleted, False if not found or unauthorized
        """
        stmt = select(Alert).where(
            and_(
                Alert.id == alert_id,
                Alert.user_id == user_id  # Authorization check
            )
        )
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()

        if not alert:
            return False

        await db.delete(alert)
        await db.commit()

        return True

    @staticmethod
    async def get_usage_stats(
        user: User,
        db: AsyncSession
    ) -> Dict:
        """
        Get detailed usage statistics for a user.

        Args:
            user: User model instance
            db: Database session

        Returns:
            Dictionary with usage statistics
        """
        # Calculate current month stats
        searches_remaining = user.searches_limit - user.searches_used_this_month
        usage_percentage = (user.searches_used_this_month / user.searches_limit * 100) if user.searches_limit > 0 else 0

        # Calculate reset date (first day of next month)
        today = datetime.utcnow()
        if today.month == 12:
            reset_date = datetime(today.year + 1, 1, 1)
        else:
            reset_date = datetime(today.year, today.month + 1, 1)

        # Get historical usage from Redis
        history = await UserService._get_usage_history(user.id)

        # Get category breakdown from Redis
        category_breakdown = await UserService._get_category_usage(user.id)

        return {
            "searches_used_this_month": user.searches_used_this_month,
            "searches_remaining": searches_remaining,
            "searches_limit": user.searches_limit,
            "reset_date": reset_date,
            "usage_percentage": round(usage_percentage, 2),
            "history": history,
            "category_breakdown": category_breakdown,
        }

    @staticmethod
    async def _get_usage_history(user_id: UUID) -> List[Dict]:
        """
        Get usage history for the last 6 months from Redis.

        Args:
            user_id: User UUID

        Returns:
            List of monthly usage records
        """
        history = []

        try:
            redis_client = await RedisService.get_redis()

            # Get last 6 months
            today = datetime.utcnow()
            for i in range(6):
                month_date = today - timedelta(days=30 * i)
                month_key = month_date.strftime("%Y-%m")

                cache_key = f"usage_history:{user_id}:{month_key}"
                usage_data = await redis_client.hgetall(cache_key)

                if usage_data:
                    history.append({
                        "month": month_key,
                        "searches_used": int(usage_data.get(b"searches_used", 0)),
                        "searches_limit": int(usage_data.get(b"searches_limit", 0)),
                    })
                else:
                    # No data for this month
                    history.append({
                        "month": month_key,
                        "searches_used": 0,
                        "searches_limit": 0,
                    })

        except Exception as e:
            logger.error(f"Error getting usage history: {str(e)}")

        return history

    @staticmethod
    async def _get_category_usage(user_id: UUID) -> List[Dict]:
        """
        Get category usage breakdown from Redis.

        Args:
            user_id: User UUID

        Returns:
            List of category usage statistics
        """
        category_breakdown = []

        try:
            redis_client = await RedisService.get_redis()

            cache_key = f"category_usage:{user_id}"
            category_data = await redis_client.hgetall(cache_key)

            if category_data:
                total_searches = sum(int(count) for count in category_data.values())

                for category_bytes, count_bytes in category_data.items():
                    category = category_bytes.decode('utf-8')
                    count = int(count_bytes)
                    percentage = (count / total_searches * 100) if total_searches > 0 else 0

                    category_breakdown.append({
                        "category": category,
                        "search_count": count,
                        "percentage": round(percentage, 2),
                    })

                # Sort by count descending
                category_breakdown.sort(key=lambda x: x["search_count"], reverse=True)

        except Exception as e:
            logger.error(f"Error getting category usage: {str(e)}")

        return category_breakdown

    @staticmethod
    async def track_category_usage(user_id: UUID, category: str) -> None:
        """
        Track category usage in Redis.

        Args:
            user_id: User UUID
            category: Category name
        """
        try:
            redis_client = await RedisService.get_redis()

            cache_key = f"category_usage:{user_id}"
            await redis_client.hincrby(cache_key, category, 1)

            # Set expiration to 1 year
            await redis_client.expire(cache_key, 31536000)

        except Exception as e:
            logger.error(f"Error tracking category usage: {str(e)}")

    @staticmethod
    async def log_activity(
        user_id: UUID,
        activity_type: str,
        description: str,
        store_domain: Optional[str] = None
    ) -> None:
        """
        Log user activity to Redis.

        Args:
            user_id: User UUID
            activity_type: Type of activity (search, view, save, analyze)
            description: Activity description
            store_domain: Optional store domain
        """
        try:
            redis_client = await RedisService.get_redis()

            activity_data = {
                "activity_type": activity_type,
                "description": description,
                "store_domain": store_domain or "",
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Store in Redis list (latest first)
            cache_key = f"user_activity:{user_id}"
            await redis_client.lpush(cache_key, str(activity_data))

            # Keep only last 100 activities
            await redis_client.ltrim(cache_key, 0, 99)

            # Set expiration to 90 days
            await redis_client.expire(cache_key, 7776000)

        except Exception as e:
            logger.error(f"Error logging activity: {str(e)}")

    @staticmethod
    async def get_recent_activity(
        user_id: UUID,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get recent user activity from Redis.

        Args:
            user_id: User UUID
            limit: Maximum number of activities to return

        Returns:
            List of activity records
        """
        activities = []

        try:
            redis_client = await RedisService.get_redis()

            cache_key = f"user_activity:{user_id}"
            activity_strings = await redis_client.lrange(cache_key, 0, limit - 1)

            for activity_str in activity_strings:
                # Parse activity data
                import ast
                activity_data = ast.literal_eval(activity_str.decode('utf-8'))

                activities.append({
                    "activity_type": activity_data.get("activity_type"),
                    "description": activity_data.get("description"),
                    "store_domain": activity_data.get("store_domain") or None,
                    "timestamp": datetime.fromisoformat(activity_data.get("timestamp")),
                })

        except Exception as e:
            logger.error(f"Error getting recent activity: {str(e)}")

        return activities

    @staticmethod
    async def check_and_increment_usage(
        user: User,
        db: AsyncSession
    ) -> bool:
        """
        Check if user has remaining searches and increment usage.

        Args:
            user: User model instance
            db: Database session

        Returns:
            True if usage incremented, False if limit reached

        Raises:
            ValueError: If user has exceeded their limit
        """
        if user.searches_used_this_month >= user.searches_limit:
            raise ValueError(
                f"Search limit exceeded. You've used {user.searches_used_this_month} "
                f"of {user.searches_limit} searches this month."
            )

        user.searches_used_this_month += 1
        user.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user)

        # Update usage history in Redis
        today = datetime.utcnow()
        month_key = today.strftime("%Y-%m")
        cache_key = f"usage_history:{user.id}:{month_key}"

        try:
            redis_client = await RedisService.get_redis()
            await redis_client.hset(
                cache_key,
                mapping={
                    "searches_used": str(user.searches_used_this_month),
                    "searches_limit": str(user.searches_limit),
                }
            )
            # Expire after 1 year
            await redis_client.expire(cache_key, 31536000)

        except Exception as e:
            logger.error(f"Error updating usage history: {str(e)}")

        return True
