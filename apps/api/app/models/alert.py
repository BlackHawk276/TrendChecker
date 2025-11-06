"""
Alert model for user notifications and alerts.
"""
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AlertType(str, enum.Enum):
    """Alert type enum."""
    NEW_STORE = "new_store"
    PRICE_DROP = "price_drop"
    PRODUCT_ADDED = "product_added"


class Alert(Base):
    """
    Alert model for user-configured notifications.
    Allows users to set up alerts for specific events.
    """
    __tablename__ = "alerts"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Foreign keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    store_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Alert configuration
    alert_type: Mapped[AlertType] = mapped_column(
        Enum(AlertType),
        nullable=False,
        index=True
    )

    criteria: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    # Relationships
    user = relationship(
        "User",
        back_populates="alerts",
        lazy="selectin"
    )

    store = relationship(
        "Store",
        back_populates="alerts",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, type={self.alert_type}, user_id={self.user_id})>"

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "store_id": str(self.store_id) if self.store_id else None,
            "alert_type": self.alert_type.value,
            "criteria": self.criteria,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
