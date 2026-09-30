from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import SupportAction


class JevDecision(BaseModel):
    """Normalized Jev result. The rest of the app never sees BeatAPI's raw format."""

    action: SupportAction
    confidence: float
    probabilities: dict[SupportAction, float]
    billing_dispute: float | None = None
    item_damaged: float | None = None
    raw_response: dict


class JevDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    selected_action: SupportAction
    confidence: float
    refund_probability: float
    replacement_probability: float
    technical_support_probability: float
    billing_probability: float
    human_escalation_probability: float
    billing_dispute_probability: float | None
    item_damaged_probability: float | None
    permitted_action: SupportAction | None
    requires_approval: bool | None
    rule_hits: list[dict] | None
    created_at: datetime
