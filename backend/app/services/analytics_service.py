from datetime import timedelta

from sqlalchemy import and_, distinct, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models import AIResponse, AuditLog, JevDecisionRecord, Ticket
from app.models.enums import SupportAction, TicketStatus
from app.schemas.analytics import AnalyticsOverview, TicketCounts

CLOSED_STATUSES = {TicketStatus.RESOLVED, TicketStatus.CLOSED}


def _rate(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def overview(self, since_days: int | None = None) -> AnalyticsOverview:
        ticket_filter = Ticket.created_at >= utcnow() - timedelta(days=since_days) if since_days else true()

        latest_decision_ids = select(func.max(JevDecisionRecord.id)).group_by(JevDecisionRecord.ticket_id)
        D = JevDecisionRecord
        rows = (await self.session.execute(
            select(Ticket.status, Ticket.final_action, D.selected_action, D.permitted_action, D.confidence)
            .outerjoin(D, and_(D.ticket_id == Ticket.id, D.id.in_(latest_decision_ids)))
            .where(ticket_filter)
        )).all()

        total = len(rows)
        decided = [r for r in rows if r.selected_action is not None]
        closed_out = [r for r in decided if r.final_action is not None]

        escalated_ever = await self.session.scalar(
            select(func.count(distinct(AuditLog.ticket_id)))
            .join(Ticket, Ticket.id == AuditLog.ticket_id)
            .where(AuditLog.event_type == "ticket_escalated", ticket_filter)
        ) or 0

        approved = (await self.session.execute(
            select(AIResponse.generated_text, AIResponse.final_text)
            .join(Ticket, Ticket.id == AIResponse.ticket_id)
            .where(AIResponse.approved.is_(True), AIResponse.generated_text.is_not(None), ticket_filter)
        )).all()

        by_category = {action.value: 0 for action in SupportAction}
        for r in decided:
            by_category[r.selected_action] += 1

        return AnalyticsOverview(
            since_days=since_days,
            tickets=TicketCounts(
                total=total,
                open=sum(r.status not in CLOSED_STATUSES for r in rows),
                escalated=sum(r.status == TicketStatus.ESCALATED for r in rows),
                resolved=sum(r.status in CLOSED_STATUSES for r in rows),
                jev_failed=sum(r.status == TicketStatus.JEV_FAILED for r in rows),
                analyzed=len(decided),
                auto_routed=sum(r.permitted_action != SupportAction.HUMAN_ESCALATION for r in decided),
            ),
            escalation_rate=_rate(escalated_ever, total),
            average_jev_confidence=(
                round(sum(r.confidence for r in decided) / len(decided), 4) if decided else None
            ),
            by_category=by_category,
            closed_out_with_decision=len(closed_out),
            human_override_rate=_rate(sum(r.final_action != r.permitted_action for r in closed_out), len(closed_out)),
            jev_human_agreement_rate=_rate(
                sum(r.final_action == r.selected_action for r in closed_out), len(closed_out)
            ),
            reply_edit_rate=_rate(sum(g != f for g, f in approved), len(approved)),
        )
