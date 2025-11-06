"""
Store API endpoints with filtering, search, and analytics.
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas import (
    AnalyzeStoreRequest,
    CategoryCount,
    CountryCount,
    ErrorResponse,
    ProductResponse,
    SearchFilters,
    StoreDetailResponse,
    StoreListResponse,
    StoreResponse,
    PaginationMeta,
)
from app.services.auth import get_current_user
from app.services.redis_service import RedisService
from app.services.store_service import StoreService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/trending",
    response_model=StoreListResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Server error"},
    }
)
async def get_trending_stores(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    category: Optional[str] = Query(default=None),
    country: Optional[str] = Query(default=None),
    min_revenue: Optional[int] = Query(default=None, ge=0),
    max_revenue: Optional[int] = Query(default=None, ge=0),
    min_products: Optional[int] = Query(default=None, ge=0),
    max_products: Optional[int] = Query(default=None, ge=0),
    sort_by: str = Query(default="trending_score"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get trending Shopify stores with pagination and filters.

    - **limit**: Number of stores to return (1-100, default 20)
    - **offset**: Pagination offset (default 0)
    - **category**: Filter by category (fashion, beauty, electronics, etc.)
    - **country**: Filter by country code (US, GB, CA, etc.)
    - **min_revenue**: Minimum estimated monthly revenue
    - **max_revenue**: Maximum estimated monthly revenue
    - **min_products**: Minimum number of products
    - **max_products**: Maximum number of products
    - **sort_by**: Sort field (trending_score, product_count, created_at, etc.)
    - **sort_order**: Sort order (asc or desc)

    Returns paginated list of stores with metadata.
    """
    try:
        # Build filters
        filters = SearchFilters(
            category=category,
            country=country,
            min_revenue=min_revenue,
            max_revenue=max_revenue,
            min_products=min_products,
            max_products=max_products,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # Get stores
        stores, pagination = await StoreService.get_trending_stores(
            db, limit=limit, offset=offset, filters=filters
        )

        # Convert to response models
        store_responses = [StoreResponse.model_validate(store) for store in stores]

        return StoreListResponse(
            data=store_responses,
            pagination=pagination
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting trending stores: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch trending stores"
        )


@router.get(
    "/{store_id}",
    response_model=StoreDetailResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Store not found"},
    }
)
async def get_store(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific store.

    Returns:
    - Store information
    - Recent products (top 10)
    - Category rank
    - View count

    View count is tracked for analytics.
    """
    try:
        # Get store
        store = await StoreService.get_store_by_id(db, store_id)

        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store not found"
            )

        # Track view
        await StoreService.track_store_view(store_id)

        # Get recent products
        recent_products = await StoreService.get_recent_products(db, store_id)

        # Get category rank
        category_rank = await StoreService.get_category_rank(db, store)

        # Get view count
        view_count = await StoreService.get_store_view_count(store_id)

        # Build response
        store_response = StoreDetailResponse.model_validate(store)
        store_response.recent_products = [
            ProductResponse.model_validate(p) for p in recent_products
        ]
        store_response.category_rank = category_rank
        store_response.view_count = view_count

        return store_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting store {store_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch store details"
        )


@router.post(
    "/analyze",
    response_model=StoreResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Usage limit exceeded"},
        400: {"model": ErrorResponse, "description": "Invalid domain or not Shopify"},
    }
)
async def analyze_store(
    request: AnalyzeStoreRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze a Shopify store (protected endpoint).

    Requires authentication. Counts against user's monthly search quota.

    - Checks if store exists in database
    - If exists and scraped recently (< 24h), returns cached data
    - If not exists or stale, runs scraper and saves to database
    - Increments user's searches_used_this_month

    **Note:** This endpoint may take 10-30 seconds for new stores.
    """
    try:
        # Check usage limit
        if not current_user.has_searches_remaining():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Monthly search limit reached ({current_user.searches_limit}). "
                       f"Please upgrade your subscription."
            )

        # Increment usage
        current_user.increment_search_usage()
        await db.commit()

        # Analyze store
        store = await StoreService.analyze_and_save_store(request.domain, db)

        return StoreResponse.model_validate(store)

    except ValueError as e:
        # Domain validation or not Shopify
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing store {request.domain}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze store"
        )


@router.get(
    "/search",
    response_model=StoreListResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid search query"},
    }
)
async def search_stores(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    category: Optional[str] = Query(default=None),
    country: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Search stores by name, domain, or description.

    - **q**: Search query (required)
    - **limit**: Number of results (1-100, default 20)
    - **offset**: Pagination offset
    - **category**: Filter by category
    - **country**: Filter by country code

    Uses fuzzy matching on store names and domains.
    Results are ranked by trending score.
    """
    try:
        # Build filters
        filters = SearchFilters(
            category=category,
            country=country
        )

        # Search stores
        stores, pagination = await StoreService.search_stores(
            db, query=q, limit=limit, offset=offset, filters=filters
        )

        # Convert to response
        store_responses = [StoreResponse.model_validate(store) for store in stores]

        return StoreListResponse(
            data=store_responses,
            pagination=pagination
        )

    except Exception as e:
        logger.error(f"Error searching stores: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )


@router.get(
    "/{store_id}/products",
    response_model=dict,  # Will contain "data" and "pagination"
    responses={
        404: {"model": ErrorResponse, "description": "Store not found"},
    }
)
async def get_store_products(
    store_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all products for a specific store.

    - **store_id**: Store UUID
    - **limit**: Number of products (1-100, default 50)
    - **offset**: Pagination offset
    - **sort_by**: Sort field (created_at, price, title, etc.)
    - **sort_order**: Sort order (asc or desc)

    Returns paginated list of products.
    """
    try:
        # Check if store exists
        store = await StoreService.get_store_by_id(db, store_id)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store not found"
            )

        # Get products
        products, pagination = await StoreService.get_store_products(
            db, store_id=store_id, limit=limit, offset=offset,
            sort_by=sort_by, sort_order=sort_order
        )

        # Convert to response
        product_responses = [ProductResponse.model_validate(p) for p in products]

        return {
            "data": product_responses,
            "pagination": pagination
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting products for store {store_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch products"
        )


@router.get(
    "/{store_id}/analytics",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Store not found"},
    }
)
async def get_store_analytics(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get analytics for a specific store (protected endpoint).

    Returns:
    - Trending score history (30 days)
    - Product count history
    - Revenue estimates over time
    - Growth metrics
    - Category comparison

    **Note:** Analytics are cached for 1 hour.
    """
    try:
        # Check if store exists
        store = await StoreService.get_store_by_id(db, store_id)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store not found"
            )

        # Check cache
        cache_key = f"analytics:{store_id}"
        cached_data = await RedisService.get_cache(cache_key)
        if cached_data:
            return cached_data

        # Generate analytics
        # TODO: Implement time-series data storage for historical analytics
        # For now, return basic metrics
        analytics = {
            "store_id": str(store_id),
            "store_name": store.name,
            "trending_score": store.trending_score,
            "product_count": store.product_count,
            "avg_price": float(store.avg_product_price) if store.avg_product_price else None,
            "estimated_monthly_revenue": store.estimated_monthly_revenue,
            "growth_rate": store.growth_rate,
            "category": store.category.value,
            "category_rank": await StoreService.get_category_rank(db, store),
            "view_count": await StoreService.get_store_view_count(store_id),
            "last_scraped": store.last_scraped_at.isoformat() if store.last_scraped_at else None,
            "note": "Historical trend data coming soon. Currently showing current metrics only."
        }

        # Cache for 1 hour
        await RedisService.set_cache(cache_key, analytics, expires_in=3600)

        return analytics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analytics for store {store_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch analytics"
        )


@router.get(
    "/categories",
    response_model=list[CategoryCount],
    responses={
        500: {"model": ErrorResponse, "description": "Server error"},
    }
)
async def get_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all categories with store counts.

    Returns list of categories with:
    - Category name
    - Store count
    - Category icon emoji

    Sorted by store count (descending).
    """
    try:
        categories = await StoreService.get_categories_with_counts(db)
        return categories

    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch categories"
        )


@router.get(
    "/countries",
    response_model=list[CountryCount],
    responses={
        500: {"model": ErrorResponse, "description": "Server error"},
    }
)
async def get_countries(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all countries with store counts.

    Returns list of countries with:
    - Country code (ISO 2-letter)
    - Country name
    - Store count
    - Country flag emoji

    Sorted by store count (descending).
    """
    try:
        countries = await StoreService.get_countries_with_counts(db)
        return countries

    except Exception as e:
        logger.error(f"Error getting countries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch countries"
        )
