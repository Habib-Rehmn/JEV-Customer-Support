"""Replay stored Jev decisions through the business rules, and measure how well Jev's confidence is calibrated.

Nothing here calls Jev: it reuses each ticket's stored answer and the exact context Jev was given.
"""
from dataclasses import asdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import AuditLog, JevDecisionRecord, Ticket
from app.services.jev_service import JevError, parse_response
from app.services.rules_service import RuleOutcome, RulesPolicy, evaluate

logger = get_logger(__name__)

OUTCOMES = ("escalated", "needs_approval", "pre_approved")
BUCKETS = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 0.95), (0.95, 1.0)]


def _classify(outcome: RuleOutcome) -> str:
    if outcome.escalated:
        return "escalated"
    return "needs_approval" if outcome.requires_approval else "pre_approved"


def _summary(outcome: RuleOutcome) -> dict:
    return {
        "outcome": _classify(outcome),
        "permitted_action": outcome.permitted_action,
        "rules": [hit["rule"] for hit in outcome.hits],
    }


class RulesLabService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _latest_decisions(self):
        latest_ids = select(func.max(JevDecisionRecord.id)).group_by(JevDecisionRecord.ticket_id)
        rows = await self.session.execute(
            select(Ticket.id, Ticket.subject, Ticket.final_action, JevDecisionRecord)
            .join(JevDecisionRecord, JevDecisionRecord.ticket_id == Ticket.id)
            .where(JevDecisionRecord.id.in_(latest_ids))
            .order_by(Ticket.id)
        )
        return rows.all()

    async def _latest_contexts(self) -> dict[int, dict]:
        """The context sent to Jev on each ticket's most recent analysis."""
        latest_ids = (
            select(func.max(AuditLog.id))
            .where(AuditLog.event_type == "jev_request_started")
            .group_by(AuditLog.ticket_id)
        )
        rows = await self.session.execute(
            select(AuditLog.ticket_id, AuditLog.event_data).where(AuditLog.id.in_(latest_ids))
        )
        return {ticket_id: data.get("context") for ticket_id, data in rows if data.get("context")}

    async def simulate(self, proposed: RulesPolicy) -> dict:
        current = RulesPolicy()
        contexts = await self._latest_contexts()
        counts = {"current": dict.fromkeys(OUTCOMES, 0), "proposed": dict.fromkeys(OUTCOMES, 0)}
        changed, replayed, skipped = [], 0, 0

        for ticket_id, subject, _, record in await self._latest_decisions():
            context = contexts.get(ticket_id)
            try:
                decision = parse_response(record.raw_response)
            except JevError:
                decision = None
            if context is None or decision is None:
                skipped += 1
                continue

            replayed += 1
            now, then = evaluate(decision, context, current), evaluate(decision, context, proposed)
            counts["current"][_classify(now)] += 1
            counts["proposed"][_classify(then)] += 1
            if _summary(now) != _summary(then):
                changed.append({
                    "ticket_id": ticket_id,
                    "subject": subject,
                    "recommended_action": decision.action,
                    "current": _summary(now),
                    "proposed": _summary(then),
                })

        logger.info("rules_simulated replayed=%s changed=%s", replayed, len(changed))
        return {
            "current_policy": asdict(current),
            "proposed_policy": asdict(proposed),
            "replayed": replayed,
            "skipped": skipped,
            "current": counts["current"],
            "proposed": counts["proposed"],
            "changed": changed,
        }

    async def calibration(self) -> dict:
        rows = await self._latest_decisions()
        buckets = []
        for i, (low, high) in enumerate(BUCKETS):
            last = i == len(BUCKETS) - 1
            in_bucket = [r for r in rows if low <= r[3].confidence < high or (last and r[3].confidence == high)]
            closed = [r for r in in_bucket if r[2] is not None]
            agreed = sum(r[2] == r[3].selected_action for r in closed)
            buckets.append({
                "label": f"{low:.2f}–{high:.2f}",
                "min": low,
                "max": high,
                "decisions": len(in_bucket),
                "closed_out": len(closed),
                "agreement_rate": round(agreed / len(closed), 4) if closed else None,
            })
        return {"min_confidence": RulesPolicy().min_confidence, "buckets": buckets}
