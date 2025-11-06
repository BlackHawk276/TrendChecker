"""
User Router

Protected endpoints for user profile, saved stores, alerts, and usage.
All endpoints require authentication.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth import AuthService
from app.services.user_service import UserService
from app.schemas import (
    UserProfileResponse,
    UserProfileUpdate,
    SavedStoreCreate,
    SavedStoreUpdate,
    SavedStoreListResponse,
    SavedStoreResponse,
    AlertCreate,
    AlertListResponse,
    AlertResponse,
    UsageStatsResponse,
    ActivityListResponse,
    MessageResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency to get current user
get_current_user = AuthService.get_current_user


@router.get("/me", response_model=UserProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user)
) -> UserProfileResponse:
    """
    Get current user profile.

    Returns:
        - Basic user info
        - Subscription details
        - Usage statistics
        - Account dates
    """
    try:
        profile_data = await UserService.get_user_profile(current_user)
        return UserProfileResponse(**profile_data)

    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )


@router.patch("/me", response_model=UserProfileResponse)
async def update_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserProfileResponse:
    """
    Update user profile.

    Allowed fields:
    - full_name
    - avatar_url

    Returns updated user profile.
    """
    try:
        updated_user = await UserService.update_user_profile(
            user=current_user,
            full_name=profile_update.full_name,
            avatar_url=profile_update.avatar_url,
            db=db
        )

        profile_data = await UserService.get_user_profile(updated_user)
        return UserProfileResponse(**profile_data)

    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )


@router.get("/me/saved-stores", response_model=SavedStoreListResponse)
async def get_saved_stores(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="saved_at", regex="^(saved_at|trending_score)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SavedStoreListResponse:
    """
    Get user's saved/favorited stores.

    Query Parameters:
    - limit: Results per page (1-100, default 20)
    - offset: Pagination offset
    - sort_by: Sort field (saved_at or trending_score)

    Returns paginated list of saved stores with:
    - Store details
    - When saved
    - User notes
    """
    try:
        saved_stores, pagination = await UserService.get_saved_stores(
            user_id=current_user.id,
            db=db,
            limit=limit,
            offset=offset,
            sort_by=sort_by
        )

        # Format response
        data = [
            SavedStoreResponse(
                store=item["store"],
                saved_at=item["saved_at"],
                notes=item["notes"]
            )
            for item in saved_stores
        ]

        return SavedStoreListResponse(data=data, pagination=pagination)

    except Exception as e:
        logger.error(f"Error getting saved stores: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve saved stores"
        )


@router.post("/me/saved-stores", response_model=SavedStoreResponse, status_code=status.HTTP_201_CREATED)
async def save_store(
    save_request: SavedStoreCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SavedStoreResponse:
    """
    Save/favorite a store.

    Request Body:
    - store_id: UUID of store to save
    - notes: Optional notes (max 1000 chars)

    Operation is idempotent - saving an already saved store updates notes.

    Returns saved store with details.
    """
    try:
        saved_store = await UserService.save_store(
            user_id=current_user.id,
            store_id=save_request.store_id,
            notes=save_request.notes,
            db=db
        )

        # Get store details
        from sqlalchemy import select
        from app.models.store import Store

        stmt = select(Store).where(Store.id == save_request.store_id)
        result = await db.execute(stmt)
        store = result.scalar_one()

        return SavedStoreResponse(
            store=store,
            saved_at=saved_store.saved_at,
            notes=saved_store.notes
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error saving store: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save store"
        )


@router.delete("/me/saved-stores/{store_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_store(
    store_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Remove store from favorites.

    Path Parameters:
    - store_id: UUID of store to remove

    Returns 204 No Content on success.
    """
    try:
        deleted = await UserService.unsave_store(
            user_id=current_user.id,
            store_id=store_id,
            db=db
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved store not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsaving store: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unsave store"
        )


@router.patch("/me/saved-stores/{store_id}", response_model=SavedStoreResponse)
async def update_saved_store_notes(
    store_id: UUID,
    update_request: SavedStoreUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SavedStoreResponse:
    """
    Update notes for a saved store.

    Path Parameters:
    - store_id: UUID of saved store

    Request Body:
    - notes: Updated notes (max 1000 chars)

    Returns updated saved store.
    """
    try:
        saved_store = await UserService.update_saved_store_notes(
            user_id=current_user.id,
            store_id=store_id,
            notes=update_request.notes,
            db=db
        )

        if not saved_store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved store not found"
            )

        # Get store details
        from sqlalchemy import select
        from app.models.store import Store

        stmt = select(Store).where(Store.id == store_id)
        result = await db.execute(stmt)
        store = result.scalar_one()

        return SavedStoreResponse(
            store=store,
            saved_at=saved_store.saved_at,
            notes=saved_store.notes
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating saved store notes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update saved store notes"
        )


@router.get("/me/alerts", response_model=AlertListResponse)
async def get_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> AlertListResponse:
    """
    Get user's active alerts.

    Returns all alert configurations for the user.
    """
    try:
        alerts = await UserService.get_user_alerts(
            user_id=current_user.id,
            db=db
        )

        return AlertListResponse(
            data=[
                AlertResponse(
                    id=alert.id,
                    user_id=alert.user_id,
                    alert_type=alert.alert_type.value,
                    criteria=alert.criteria,
                    store_id=alert.store_id,
                    is_active=alert.is_active,
                    created_at=alert.created_at
                )
                for alert in alerts
            ],
            total=len(alerts)
        )

    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alerts"
        )


@router.post("/me/alerts", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_request: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> AlertResponse:
    """
    Create new alert.

    Alert Types:
    - new_store: Notify when stores matching criteria are added
    - price_drop: Notify when saved store products drop in price (requires store_id)
    - trending: Notify when saved store trending score increases (requires store_id)

    Request Body:
    - alert_type: Type of alert
    - criteria: Alert criteria configuration (optional)
      * category: Filter by category
      * min_products: Minimum product count
      * min_trending_score: Minimum trending score
      * keywords: Keywords to match in store name/description
    - store_id: Required for price_drop and trending alerts

    Returns created alert.
    """
    try:
        criteria_dict = alert_request.criteria.dict() if alert_request.criteria else None

        alert = await UserService.create_alert(
            user_id=current_user.id,
            alert_type=alert_request.alert_type,
            criteria=criteria_dict,
            store_id=alert_request.store_id,
            db=db
        )

        return AlertResponse(
            id=alert.id,
            user_id=alert.user_id,
            alert_type=alert.alert_type.value,
            criteria=alert.criteria,
            store_id=alert.store_id,
            is_active=alert.is_active,
            created_at=alert.created_at
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create alert"
        )


@router.delete("/me/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete an alert.

    Path Parameters:
    - alert_id: UUID of alert to delete

    Authorization check ensures users can only delete their own alerts.

    Returns 204 No Content on success.
    """
    try:
        deleted = await UserService.delete_alert(
            user_id=current_user.id,
            alert_id=alert_id,
            db=db
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found or unauthorized"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete alert"
        )


@router.get("/me/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UsageStatsResponse:
    """
    Get detailed usage statistics.

    Returns:
    - Searches used this month
    - Searches remaining
    - Reset date
    - Historical usage (last 6 months)
    - Most searched categories
    """
    try:
        usage_stats = await UserService.get_usage_stats(
            user=current_user,
            db=db
        )

        return UsageStatsResponse(**usage_stats)

    except Exception as e:
        logger.error(f"Error getting usage stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage statistics"
        )


@router.get("/me/recent-activity", response_model=ActivityListResponse)
async def get_recent_activity(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
) -> ActivityListResponse:
    """
    Get recent user activity.

    Query Parameters:
    - limit: Maximum activities to return (1-100, default 50)

    Returns:
    - Recent searches
    - Store views
    - Saved stores
    - Store analyses

    Activities include timestamps and store information.
    """
    try:
        activities = await UserService.get_recent_activity(
            user_id=current_user.id,
            limit=limit
        )

        return ActivityListResponse(
            data=activities,
            total=len(activities)
        )

    except Exception as e:
        logger.error(f"Error getting recent activity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recent activity"
        )
