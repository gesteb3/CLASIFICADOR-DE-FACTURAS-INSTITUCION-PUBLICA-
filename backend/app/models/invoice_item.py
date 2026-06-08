from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    cantidad: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    precio_unitario: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    budget_line_id: Mapped[int | None] = mapped_column(ForeignKey("budget_lines.id"), nullable=True)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id"), nullable=True)
    funding_source_id: Mapped[int | None] = mapped_column(ForeignKey("funding_sources.id"), nullable=True)
    classification_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    classification_origin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estado_revision: Mapped[str] = mapped_column(String(50), default="PENDIENTE")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    invoice = relationship("Invoice", back_populates="items")
    budget_line = relationship("BudgetLine", back_populates="invoice_items")
    activity = relationship("Activity", back_populates="invoice_items")
    funding_source = relationship("FundingSource", back_populates="invoice_items")
