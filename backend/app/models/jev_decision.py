from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class JevDecisionRecord(Base):
    __tablename__ = "jev_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)

    selected_action: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[float] = mapped_column(Float)

    refund_probability: Mapped[float] = mapped_column(Float)
    replacement_probability: Mapped[float] = mapped_column(Float)
    technical_support_probability: Mapped[float] = mapped_column(Float)
    billing_probability: Mapped[float] = mapped_column(Float)
    human_escalation_probability: Mapped[float] = mapped_column(Float)

    # Extra yes/no signals asked in the same Jev request.
    billing_dispute_probability: Mapped[float | None] = mapped_column(Float)
    item_damaged_probability: Mapped[float | None] = mapped_column(Float)

    raw_response: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
