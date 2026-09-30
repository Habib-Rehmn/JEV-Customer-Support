from pydantic import BaseModel, Field

from app.models.enums import SupportAction


class RulesPolicyModel(BaseModel):
    """Business-rule thresholds (mirrors services.rules_service.RulesPolicy)."""

    min_confidence: float = Field(ge=0, le=1)
    refund_approval_limit: float = Field(ge=0)
    max_refunds_30_days: int = Field(ge=1)
    replacement_window_days: int = Field(ge=0)
    auto_replacement_limit: float = Field(ge=0)
    signal_threshold: float = Field(ge=0, le=1)


class SimulatedOutcome(BaseModel):
    outcome: str = Field(description="escalated | needs_approval | pre_approved")
    permitted_action: SupportAction
    rules: list[str]


class ChangedTicket(BaseModel):
    ticket_id: int
    subject: str
    recommended_action: SupportAction
    current: SimulatedOutcome
    proposed: SimulatedOutcome


class SimulationResult(BaseModel):
    current_policy: RulesPolicyModel
    proposed_policy: RulesPolicyModel
    replayed: int = Field(description="Tickets with a Jev decision and the context it was made on")
    skipped: int = Field(description="Analyzed tickets that couldn't be replayed (missing context)")
    current: dict[str, int] = Field(description="Outcome counts under the current rules")
    proposed: dict[str, int] = Field(description="Outcome counts under the proposed rules")
    changed: list[ChangedTicket]


class CalibrationBucket(BaseModel):
    label: str
    min: float
    max: float
    decisions: int = Field(description="Latest Jev decisions with confidence in this range")
    closed_out: int = Field(description="Of those, tickets with a human final action")
    agreement_rate: float | None = Field(description="final action == Jev's recommendation, among closed_out")


class Calibration(BaseModel):
    min_confidence: float = Field(description="Current escalation threshold, for reference")
    buckets: list[CalibrationBucket]
