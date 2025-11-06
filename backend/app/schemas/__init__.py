"""
Pydantic schemas for authentication and user management.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# Request schemas
class UserRegisterRequest(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserLoginRequest(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh."""
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    """Schema for email verification."""
    verification_token: str


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Schema for password reset."""
    reset_token: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class ChangePasswordRequest(BaseModel):
    """Schema for password change."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


# Response schemas
class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    """Schema for user response."""
    id: UUID
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    subscription_tier: str
    subscription_status: str
    trial_ends_at: Optional[datetime]
    subscription_ends_at: Optional[datetime]
    searches_used_this_month: int
    searches_limit: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Schema for authentication response with user and tokens."""
    user: UserResponse
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    detail: Optional[str] = None


# Store and Product schemas
class ProductBase(BaseModel):
    """Base product schema."""
    title: str
    description: Optional[str] = None
    price: float
    compare_at_price: Optional[float] = None
    currency: str = "USD"
    image_url: Optional[str] = None
    vendor: Optional[str] = None
    product_type: Optional[str] = None
    handle: Optional[str] = None
    is_available: bool = True


class ProductCreate(ProductBase):
    """Schema for creating a product."""
    store_id: UUID
    tags: Optional[list[str]] = []
    images: Optional[dict] = None
    first_seen: datetime
    last_seen: datetime


class ProductResponse(ProductBase):
    """Schema for product response."""
    id: UUID
    store_id: UUID
    tags: Optional[list[str]] = []
    first_seen: datetime
    last_seen: datetime
    variant_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StoreBase(BaseModel):
    """Base store schema."""
    domain: str
    name: str
    description: Optional[str] = None
    category: str = "other"
    country_code: Optional[str] = None
    logo_url: Optional[str] = None


class StoreCreate(StoreBase):
    """Schema for creating a store."""
    product_count: int = 0
    avg_product_price: Optional[float] = None
    estimated_monthly_revenue: Optional[int] = None
    estimated_monthly_visitors: Optional[int] = None
    trending_score: float = 0.0
    growth_rate: Optional[float] = None
    theme_name: Optional[str] = None
    tech_stack: Optional[dict] = None
    social_links: Optional[dict] = None
    meta: Optional[dict] = None


class StoreUpdate(BaseModel):
    """Schema for updating a store."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    logo_url: Optional[str] = None
    product_count: Optional[int] = None
    avg_product_price: Optional[float] = None
    estimated_monthly_revenue: Optional[int] = None
    estimated_monthly_visitors: Optional[int] = None
    trending_score: Optional[float] = None
    growth_rate: Optional[float] = None
    last_scraped_at: Optional[datetime] = None


class StoreResponse(StoreBase):
    """Schema for store response."""
    id: UUID
    product_count: int
    avg_product_price: Optional[float]
    estimated_monthly_revenue: Optional[int]
    estimated_monthly_visitors: Optional[int]
    trending_score: float
    growth_rate: Optional[float]
    is_active: bool
    is_verified: bool
    theme_name: Optional[str]
    social_links: Optional[dict]
    created_at: datetime
    updated_at: datetime
    last_scraped_at: Optional[datetime]

    class Config:
        from_attributes = True


class StoreDetailResponse(StoreResponse):
    """Detailed store response with products."""
    recent_products: list[ProductResponse] = []
    category_rank: Optional[int] = None
    view_count: int = 0


class AnalyzeStoreRequest(BaseModel):
    """Schema for store analysis request."""
    domain: str = Field(..., min_length=1, max_length=255)

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Validate and normalize domain."""
        # Remove protocol and trailing slash
        import re
        v = re.sub(r'^https?://', '', v)
        v = v.rstrip('/')
        v = re.sub(r'^www\.', '', v)
        return v.lower()


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    total: int
    limit: int
    offset: int
    has_next: bool
    has_prev: bool


class StoreListResponse(BaseModel):
    """Paginated store list response."""
    data: list[StoreResponse]
    pagination: PaginationMeta


class CategoryCount(BaseModel):
    """Category with count."""
    name: str
    count: int
    icon: str


class CountryCount(BaseModel):
    """Country with store count."""
    code: str
    name: str
    count: int
    flag: str


class StoreAnalytics(BaseModel):
    """Store analytics response."""
    store_id: UUID
    trending_history: list[dict]  # [{date, score}]
    product_count_history: list[dict]
    revenue_history: list[dict]
    growth_metrics: dict
    category_comparison: dict


class SearchFilters(BaseModel):
    """Search filter parameters."""
    category: Optional[str] = None
    country: Optional[str] = None
    min_revenue: Optional[int] = None
    max_revenue: Optional[int] = None
    min_products: Optional[int] = None
    max_products: Optional[int] = None
    sort_by: str = "trending_score"
    sort_order: str = "desc"

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        """Validate sort_by field."""
        allowed = ["trending_score", "product_count", "avg_product_price",
                   "estimated_monthly_revenue", "created_at", "updated_at"]
        if v not in allowed:
            raise ValueError(f"sort_by must be one of: {', '.join(allowed)}")
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        """Validate sort_order field."""
        if v not in ["asc", "desc"]:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v
