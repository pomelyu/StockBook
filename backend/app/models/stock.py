import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    market: Mapped[str] = mapped_column(String(10), nullable=False)  # "TW" | "US"
    currency: Mapped[str] = mapped_column(String(5), nullable=False)  # "TWD" | "USD"
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    price_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    track_price: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    watchlist_entries: Mapped[list["Watchlist"]] = relationship(  # noqa: F821
        "Watchlist", back_populates="stock"
    )
    transactions: Mapped[list["Transaction"]] = relationship(  # noqa: F821
        "Transaction", back_populates="stock"
    )
    dividends: Mapped[list["Dividend"]] = relationship(  # noqa: F821
        "Dividend", back_populates="stock"
    )
