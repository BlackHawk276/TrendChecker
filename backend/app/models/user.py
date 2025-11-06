"""
User model for authentication and subscription management.
"""
import enum
import secrets
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Integer,
    String,
    event,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SubscriptionTier(str, enum.Enum):
    """Subscription tier enum."""
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    AGENCY = "agency"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status enum."""
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"


class User(Base):
    """
    User model for authentication and subscription management.
    Handles user accounts, subscriptions, and API access.
    """
    __tablename__ = "users"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    # Profile
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Subscription information
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier),
        nullable=False,
        default=SubscriptionTier.FREE,
        index=True
    )

    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus),
        nullable=False,
        default=SubscriptionStatus.TRIALING,
        index=True
    )

    # Stripe integration
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True
    )

    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True
    )

    # Subscription dates
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    subscription_ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Usage tracking
    searches_used_this_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    searches_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10  # Free tier default
    )

    # API access
    api_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: secrets.token_urlsafe(48)
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    saved_stores = relationship(
        "SavedStore",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    alerts = relationship(
        "Alert",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, tier={self.subscription_tier})>"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert model to dictionary.

        Args:
            include_sensitive: Whether to include sensitive fields like API key
        """
        data = {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "avatar_url": self.avatar_url,
            "subscription_tier": self.subscription_tier.value,
            "subscription_status": self.subscription_status.value,
            "trial_ends_at": self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            "subscription_ends_at": self.subscription_ends_at.isoformat() if self.subscription_ends_at else None,
            "searches_used_this_month": self.searches_used_this_month,
            "searches_limit": self.searches_limit,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }

        if include_sensitive:
            data["api_key"] = self.api_key
            data["stripe_customer_id"] = self.stripe_customer_id

        return data

    def has_searches_remaining(self) -> bool:
        """Check if user has search quota remaining."""
        return self.searches_used_this_month < self.searches_limit

    def increment_search_usage(self) -> None:
        """Increment the search usage counter."""
        self.searches_used_this_month += 1

    def reset_monthly_usage(self) -> None:
        """Reset monthly search usage counter."""
        self.searches_used_this_month = 0

    def regenerate_api_key(self) -> str:
        """Generate a new API key."""
        self.api_key = secrets.token_urlsafe(48)
        return self.api_key


# Event listener to update updated_at timestamp
@event.listens_for(User, "before_update")
def receive_before_update(mapper, connection, target):
    """Update the updated_at timestamp before each update."""
    target.updated_at = datetime.utcnow()
