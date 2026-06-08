from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class BudgetLine(Base):
    __tablename__ = "budget_lines"
    __table_args__ = (
        UniqueConstraint("renglon", name="uq_budget_lines_renglon"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    grupo: Mapped[int] = mapped_column(Integer, nullable=False)
    subgrupo: Mapped[int] = mapped_column(Integer, nullable=False)
    renglon: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    concepto: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    invoice_items = relationship("InvoiceItem", back_populates="budget_line")
    rules = relationship("ClassificationRule", back_populates="budget_line")
