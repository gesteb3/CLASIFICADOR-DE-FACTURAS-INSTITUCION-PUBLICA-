from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("code", name="uq_activities_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    invoice_items = relationship("InvoiceItem", back_populates="activity")
