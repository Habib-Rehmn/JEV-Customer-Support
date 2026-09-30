from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import get_logger
from app.db.base import utcnow
from app.models import AIResponse, Customer, JevDecisionRecord, Ticket
from app.models.enums import SupportAction, TicketPriority, TicketStatus
from app.repositories.customers import CustomerRepository
from app.repositories.orders import OrderRepository
from app.repositories.tickets import TicketRepository
from app.schemas.jev import JevDecision
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.services.context_builder import ContextBuilder
from app.services.jev_service import JevError, JevService
from app.services.openai_service import OpenAIError, OpenAIService
from app.services.rules_service import RuleOutcome, evaluate

logger = get_logger(__name__)


ANALYZABLE_STATUSES = {
    TicketStatus.NEW,
    TicketStatus.JEV_FAILED,
    TicketStatus.WAITING_FOR_AGENT,
    TicketStatus.ESCALATED,
}


class TicketNotFound(Exception):
    pass


class TicketNotAnalyzable(Exception):
    pass


class NoDecisionYet(Exception):
    """A reply can only be generated once the rules have permitted an action."""


class ResponseGenerationFailed(Exception):
    pass


class TicketService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.customers = CustomerRepository(session)
        self.orders = OrderRepository(session)
        self.tickets = TicketRepository(session)

    async def create(self, data: TicketCreate) -> Ticket:
        customer = await self.customers.get_by_email(data.email)
        if customer is None:
            customer = await self.customers.add(Customer(name=data.customer_name, email=data.email))

        # Only link an order that belongs to this customer; anything else is treated as unknown.
        order = await self.orders.get_by_number(data.order_number) if data.order_number else None
        if order is not None and order.customer_id != customer.id:
            order = None

        ticket = await self.tickets.add(Ticket(
            customer_id=customer.id,
            order_id=order.id if order else None,
            subject=data.subject,
            message=data.message,
        ))
        await self.tickets.log(
            ticket.id, "ticket_created",
            submitted_order_number=data.order_number, order_found=order is not None,
        )
        await self.session.commit()
        logger.info("ticket_created id=%s order_found=%s", ticket.id, order is not None)
        return ticket

    async def get(self, ticket_id: int) -> Ticket:
        ticket = await self.tickets.get(ticket_id, with_relations=True)
        if ticket is None:
            raise TicketNotFound(ticket_id)
        return ticket

    async def list(self, **filters) -> tuple[list[Ticket], int]:
        return await self.tickets.list(**filters)

    async def update(self, ticket_id: int, data: TicketUpdate) -> Ticket:
        ticket = await self.get(ticket_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        for field, value in changes.items():
            setattr(ticket, field, value)
        if changes.get("status") == TicketStatus.RESOLVED:
            ticket.resolved_at = utcnow()
        await self.tickets.log(ticket.id, "ticket_updated", **{k: str(v) for k, v in changes.items()})
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket

    async def start_analysis(self, ticket_id: int) -> Ticket:
        """Mark the ticket ANALYZING. The Jev call itself runs in the background (see analyze_ticket_job)."""
        ticket = await self.get(ticket_id)
        if ticket.status not in ANALYZABLE_STATUSES:
            raise TicketNotAnalyzable(ticket.status)
        ticket.status = TicketStatus.ANALYZING
        await self.session.commit()
        return ticket

    async def run_analysis(self, ticket_id: int, jev: JevService) -> bool:
        """Jev decision + business rules. Returns False if Jev failed (ticket is then JEV_FAILED)."""
        ticket = await self.get(ticket_id)
        context = await ContextBuilder(self.session).build(ticket)
        await self.tickets.log(ticket.id, "jev_request_started", context=context)
        await self.session.commit()

        try:
            decision = await jev.classify_ticket(context)
        except Exception as exc:
            # Never guess and never lose the ticket: it goes to a human.
            if not isinstance(exc, JevError):
                logger.exception("jev_request_failed unexpected error ticket=%s", ticket.id)
            ticket.status = TicketStatus.JEV_FAILED
            await self.tickets.log(ticket.id, "jev_request_failed", error=type(exc).__name__, detail=str(exc))
            await self.session.commit()
            logger.warning("jev_request_failed ticket=%s error=%r", ticket.id, exc)
            return False

        await self.tickets.log(
            ticket.id, "jev_request_completed", action=decision.action, confidence=decision.confidence
        )

        outcome = evaluate(decision, context)
        await self.tickets.add_decision(_decision_record(ticket.id, decision, outcome))
        for hit in outcome.hits:
            await self.tickets.log(ticket.id, "rule_triggered", **hit)
        ticket.status = outcome.status
        if outcome.escalated:
            ticket.priority = TicketPriority.HIGH
            await self.tickets.log(ticket.id, "ticket_escalated", by="rules")
        await self.session.commit()
        logger.info(
            "analysis_completed ticket=%s recommended=%s permitted=%s status=%s",
            ticket.id, decision.action, outcome.permitted_action, outcome.status,
        )
        return True

    async def generate_response(self, ticket_id: int, openai: OpenAIService) -> AIResponse:
        """Draft a reply for the permitted action. On failure the decision stays and the agent writes manually."""
        ticket = await self.get(ticket_id)
        decision = ticket.latest_jev_decision
        if decision is None or decision.permitted_action is None:
            raise NoDecisionYet(ticket.id)
        action = SupportAction(decision.permitted_action)

        await self.tickets.log(ticket.id, "openai_generation_started", action=action)
        try:
            reply = await openai.generate_reply(
                customer_name=ticket.customer.name,
                subject=ticket.subject,
                message=ticket.message,
                action=action,
                order_number=ticket.order.order_number if ticket.order else None,
            )
        except Exception as exc:
            if not isinstance(exc, OpenAIError):
                logger.exception("openai_generation_failed unexpected error ticket=%s", ticket.id)
            await self.tickets.log(ticket.id, "openai_generation_failed", error=type(exc).__name__, detail=str(exc))
            await self.session.commit()
            logger.warning("openai_generation_failed ticket=%s error=%r", ticket.id, exc)
            raise ResponseGenerationFailed(str(exc)) from exc

        response = await self.tickets.add_response(
            AIResponse(ticket_id=ticket.id, generated_text=reply.text, final_text=reply.text, model=reply.model)
        )
        await self.tickets.log(ticket.id, "openai_generation_completed", response_id=response.id, model=reply.model)
        await self.session.commit()
        logger.info("openai_generation_completed ticket=%s response=%s", ticket.id, response.id)
        return response


def _decision_record(ticket_id: int, decision: JevDecision, outcome: RuleOutcome) -> JevDecisionRecord:
    p = decision.probabilities
    return JevDecisionRecord(
        ticket_id=ticket_id,
        selected_action=decision.action,
        confidence=decision.confidence,
        refund_probability=p[SupportAction.REFUND],
        replacement_probability=p[SupportAction.REPLACEMENT],
        technical_support_probability=p[SupportAction.TECHNICAL_SUPPORT],
        billing_probability=p[SupportAction.BILLING],
        human_escalation_probability=p[SupportAction.HUMAN_ESCALATION],
        billing_dispute_probability=decision.billing_dispute,
        item_damaged_probability=decision.item_damaged,
        raw_response=decision.raw_response,
        permitted_action=outcome.permitted_action,
        requires_approval=outcome.requires_approval,
        rule_hits=outcome.hits,
    )


async def analyze_ticket_job(
    ticket_id: int, session_factory: async_sessionmaker, jev: JevService, openai: OpenAIService
) -> None:
    """Background task entry point: runs with its own DB session, after the HTTP response is sent."""
    async with session_factory() as session:
        service = TicketService(session)
        if not await service.run_analysis(ticket_id, jev):
            return
        try:
            await service.generate_response(ticket_id, openai)
        except ResponseGenerationFailed:
            pass  # already logged; the agent can regenerate or write the reply manually
