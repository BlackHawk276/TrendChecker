"""
SavedStore association model for user saved stores.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SavedStore(Base):
    """
    Association table for users saving stores to their collection.
    Allows users to bookmark stores for later reference.
    """
    __tablename__ = "saved_stores"

    # Composite primary key
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )

    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        primary_key=True
    )

    # Metadata
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Relationships
    user = relationship(
        "User",
        back_populates="saved_stores",
        lazy="selectin"
    )

    store = relationship(
        "Store",
        back_populates="saved_by_users",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<SavedStore(user_id={self.user_id}, store_id={self.store_id})>"

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "user_id": str(self.user_id),
            "store_id": str(self.store_id),
            "saved_at": self.saved_at.isoformat() if self.saved_at else None,
            "notes": self.notes,
        }
