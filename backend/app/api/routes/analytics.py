from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from app.api.deps import AdminUser, SessionDep, get_current_user
from app.schemas.analytics import AnalyticsOverview
from app.schemas.rules import Calibration, RulesPolicyModel, SimulationResult
from app.services.analytics_service import AnalyticsService
from app.services.rules_lab_service import RulesLabService
from app.services.rules_service import RulesPolicy

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(get_current_user)])


@router.get("/overview", response_model=AnalyticsOverview)
async def overview(session: SessionDep, since_days: int | None = Query(None, ge=1, le=3650)):
    return await AnalyticsService(session).overview(since_days)


@router.get("/rules", response_model=RulesPolicyModel)
async def current_rules():
    """The thresholds the rules engine is running with (set via RULE_* in .env)."""
    return asdict(RulesPolicy())


@router.post("/rules/simulate", response_model=SimulationResult)
async def simulate_rules(proposed: RulesPolicyModel, session: SessionDep, _: AdminUser):
    """Replay every analyzed ticket through the current and the proposed thresholds. Changes nothing."""
    return await RulesLabService(session).simulate(RulesPolicy(**proposed.model_dump()))


@router.get("/calibration", response_model=Calibration)
async def calibration(session: SessionDep):
    """How often humans agreed with Jev, by Jev's confidence."""
    return await RulesLabService(session).calibration()
