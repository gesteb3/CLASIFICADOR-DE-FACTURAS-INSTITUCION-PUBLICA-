from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("upload_batches.id"), nullable=True)
    serie: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    numero_dte: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    nit_emisor: Mapped[str | None] = mapped_column(String(50), nullable=True)
    proveedor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nit_receptor: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nombre_receptor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    moneda: Mapped[str] = mapped_column(String(10), default="GTQ")
    total_factura: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    pdf_path: Mapped[str] = mapped_column(String(500), nullable=False)
    estado: Mapped[str] = mapped_column(String(50), default="SUBIDA", index=True)
    queue_status: Mapped[str] = mapped_column(String(50), default="PENDIENTE")
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    processing_started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_finished_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    batch = relationship("UploadBatch", back_populates="invoices")
    uploader = relationship("User", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
