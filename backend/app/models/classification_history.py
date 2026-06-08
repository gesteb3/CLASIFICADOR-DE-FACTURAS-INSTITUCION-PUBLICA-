from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ClassificationHistory(Base):
    __tablename__ = "classification_history"
    __table_args__ = (
        UniqueConstraint("normalized_description", name="uq_classification_history_description"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    normalized_description: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    budget_line_id: Mapped[int] = mapped_column(ForeignKey("budget_lines.id"), nullable=False)
    times_used: Mapped[int] = mapped_column(Integer, default=1)
    last_used_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
