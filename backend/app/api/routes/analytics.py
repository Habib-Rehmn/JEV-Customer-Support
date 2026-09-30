from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep, get_current_user
from app.schemas.analytics import AnalyticsOverview
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(get_current_user)])


@router.get("/overview", response_model=AnalyticsOverview)
async def overview(session: SessionDep, since_days: int | None = Query(None, ge=1, le=3650)):
    return await AnalyticsService(session).overview(since_days)
