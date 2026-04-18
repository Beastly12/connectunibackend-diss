from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.authDependencies import get_current_user
from app.models.user import User
from app.schemas.mentorship_schema import DashboardStatsResponse
from app.services.mentorship_service import MentorshipService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_mentorship_service(db: AsyncSession = Depends(get_db)) -> MentorshipService:
    return MentorshipService(db)


@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
    summary="Combined dashboard stats for the authenticated user",
)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """
    Returns a combined stats snapshot for the authenticated user's dashboard:
    - messages_unread: count of unread messages
      (TODO: integrate with direct messaging system — currently returns 0)
    - upcoming_events: count of upcoming registered events
      (TODO: integrate with events system — currently returns 0)
    - upcoming_sessions: up to 5 future UPCOMING mentorship sessions the user
      is a participant in, ordered by scheduled_at ascending.
    """
    return await service.get_dashboard_stats(current_user.id)
