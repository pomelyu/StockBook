import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Watchlist(Base):
    __tablename__ = "watchlist"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    stock_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="watchlist_entries")  # noqa: F821
    stock: Mapped["Stock"] = relationship("Stock", back_populates="watchlist_entries")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("user_id", "stock_id", name="uq_watchlist_user_stock"),
        Index("idx_watchlist_user", "user_id"),
    )
