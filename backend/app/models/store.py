"""
Store model for e-commerce stores being tracked.
"""
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    Integer,
    Numeric,
    String,
    Text,
    event,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StoreCategory(str, enum.Enum):
    """Store category enum."""
    FASHION = "fashion"
    BEAUTY = "beauty"
    ELECTRONICS = "electronics"
    HOME = "home"
    HEALTH = "health"
    SPORTS = "sports"
    OTHER = "other"


class Store(Base):
    """
    Store model representing an e-commerce store.
    Tracks store metadata, performance metrics, and technology information.
    """
    __tablename__ = "stores"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Basic information
    domain: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    category: Mapped[StoreCategory] = mapped_column(
        Enum(StoreCategory),
        nullable=False,
        default=StoreCategory.OTHER,
        index=True
    )

    country_code: Mapped[Optional[str]] = mapped_column(
        String(2),
        nullable=True,
        index=True
    )

    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

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

    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Metrics
    product_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    avg_product_price: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )

    estimated_monthly_revenue: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    estimated_monthly_visitors: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    trending_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        index=True  # Indexed for sorting by trending
    )

    growth_rate: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )

    # Status flags
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

    # Technology information
    theme_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tech_stack: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    social_links: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Flexible metadata (renamed from 'metadata' to 'meta' to avoid SQLAlchemy reserved attribute)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    products = relationship(
        "Product",
        back_populates="store",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    saved_by_users = relationship(
        "SavedStore",
        back_populates="store",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    alerts = relationship(
        "Alert",
        back_populates="store",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Store(id={self.id}, domain={self.domain}, name={self.name})>"

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "domain": self.domain,
            "name": self.name,
            "description": self.description,
            "category": self.category.value if self.category else None,
            "country_code": self.country_code,
            "logo_url": self.logo_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_scraped_at": self.last_scraped_at.isoformat() if self.last_scraped_at else None,
            "product_count": self.product_count,
            "avg_product_price": float(self.avg_product_price) if self.avg_product_price else None,
            "estimated_monthly_revenue": self.estimated_monthly_revenue,
            "estimated_monthly_visitors": self.estimated_monthly_visitors,
            "trending_score": self.trending_score,
            "growth_rate": self.growth_rate,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "theme_name": self.theme_name,
            "tech_stack": self.tech_stack,
            "social_links": self.social_links,
            "meta": self.meta,
        }


# Event listener to update updated_at timestamp
@event.listens_for(Store, "before_update")
def receive_before_update(mapper, connection, target):
    """Update the updated_at timestamp before each update."""
    target.updated_at = datetime.utcnow()
