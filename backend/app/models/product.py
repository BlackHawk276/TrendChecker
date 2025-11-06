"""
Product model for e-commerce products.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    event,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    """
    Product model representing individual products from e-commerce stores.
    Tracks product information, pricing, and availability over time.
    """
    __tablename__ = "products"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Foreign key to store
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Basic information
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Pricing
    price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        index=True
    )

    compare_at_price: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD"
    )

    # Images
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    images: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Product categorization
    tags: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        index=True  # GIN index for array searches
    )

    vendor: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    product_type: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    handle: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    # Tracking timestamps
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    # Availability
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True
    )

    variant_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1
    )

    # Standard timestamps
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

    # Relationships
    store = relationship(
        "Store",
        back_populates="products",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, title={self.title}, price={self.price})>"

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "store_id": str(self.store_id),
            "title": self.title,
            "description": self.description,
            "price": float(self.price),
            "compare_at_price": float(self.compare_at_price) if self.compare_at_price else None,
            "currency": self.currency,
            "image_url": self.image_url,
            "images": self.images,
            "tags": self.tags,
            "vendor": self.vendor,
            "product_type": self.product_type,
            "handle": self.handle,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "is_available": self.is_available,
            "variant_count": self.variant_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def discount_percentage(self) -> Optional[float]:
        """Calculate discount percentage if compare_at_price is set."""
        if self.compare_at_price and self.compare_at_price > self.price:
            return ((self.compare_at_price - self.price) / self.compare_at_price) * 100
        return None


# Event listener to update updated_at timestamp
@event.listens_for(Product, "before_update")
def receive_before_update(mapper, connection, target):
    """Update the updated_at timestamp before each update."""
    target.updated_at = datetime.utcnow()
