import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    market: Mapped[str] = mapped_column(String(5), nullable=False)  # "TW" or "US"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="accounts")  # noqa: F821
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="account")  # noqa: F821
    dividends: Mapped[list["Dividend"]] = relationship("Dividend", back_populates="account")  # noqa: F821
