from pydantic import BaseModel, Field


class TicketCounts(BaseModel):
    total: int
    open: int = Field(description="Not RESOLVED or CLOSED")
    escalated: int = Field(description="Currently ESCALATED")
    resolved: int = Field(description="RESOLVED or CLOSED")
    jev_failed: int
    overdue: int = Field(description="Awaiting a reply past their priority's response-time target")
    analyzed: int = Field(description="Has a Jev decision")
    auto_routed: int = Field(description="Analyzed and not escalated by the rules")


class AnalyticsOverview(BaseModel):
    since_days: int | None = Field(description="Only tickets created in the last N days; null = all time")
    tickets: TicketCounts
    escalation_rate: float | None = Field(description="Tickets ever escalated (rules or agent) / all tickets")
    average_jev_confidence: float | None = Field(description="Mean confidence of each ticket's latest decision")
    by_category: dict[str, int] = Field(description="Jev's recommended action per analyzed ticket")
    closed_out_with_decision: int = Field(
        description="Tickets with a Jev decision and a human final_action (denominator of the two rates below)"
    )
    human_override_rate: float | None = Field(description="final_action != the rules' permitted action")
    jev_human_agreement_rate: float | None = Field(description="final_action == Jev's recommended action")
    reply_edit_rate: float | None = Field(description="Approved AI replies the agent edited before sending")
