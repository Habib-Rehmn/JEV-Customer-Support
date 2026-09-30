from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow
from app.models.enums import TicketPriority, TicketStatus


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), index=True)

    subject: Mapped[str] = mapped_column(String(300))
    message: Mapped[str] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(30), default=TicketStatus.NEW, index=True)
    priority: Mapped[str] = mapped_column(String(20), default=TicketPriority.NORMAL)

    final_action: Mapped[str | None] = mapped_column(String(30))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped["Customer"] = relationship(back_populates="tickets")  # noqa: F821
    order: Mapped["Order | None"] = relationship()  # noqa: F821
    jev_decisions: Mapped[list["JevDecisionRecord"]] = relationship(  # noqa: F821
        order_by="JevDecisionRecord.id.desc()"
    )

    ai_responses: Mapped[list["AIResponse"]] = relationship(  # noqa: F821
        order_by="AIResponse.id.desc()"
    )

    @property
    def latest_ai_response(self) -> "AIResponse | None":  # noqa: F821
        return self.ai_responses[0] if self.ai_responses else None

    @property
    def current_action(self) -> str | None:
        """The action the rules permitted on the latest analysis (what the agent is being asked to approve)."""
        decision = self.latest_jev_decision
        return decision.permitted_action if decision else None

    @property
    def latest_jev_decision(self) -> "JevDecisionRecord | None":  # noqa: F821
        return self.jev_decisions[0] if self.jev_decisions else None
