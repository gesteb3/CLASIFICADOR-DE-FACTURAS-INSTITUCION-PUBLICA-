from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ClassificationRule(Base):
    __tablename__ = "classification_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    budget_line_id: Mapped[int] = mapped_column(ForeignKey("budget_lines.id"), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=50)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    budget_line = relationship("BudgetLine", back_populates="rules")
