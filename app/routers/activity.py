from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.authDependencies import get_current_user
from app.models.user import User
from app.services.activity_service import ActivityService
from app.schemas.activity_schema import ActivityResponse

router = APIRouter(prefix="/activity", tags=["Activity"])


def get_activity_service(db: AsyncSession = Depends(get_db)) -> ActivityService:
    return ActivityService(db)


@router.get(
    "/me",
    response_model=list[ActivityResponse],
    summary="Get the authenticated user's recent activity",
)
async def get_my_activity(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: ActivityService = Depends(get_activity_service),
):
    return await service.get_recent_activity(user_id=current_user.id, limit=limit)


@router.get(
    "/me/{activity_type}",
    response_model=list[ActivityResponse],
    summary="Get the authenticated user's recent activity filtered by type",
)
async def get_my_activity_by_type(
    activity_type: str,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: ActivityService = Depends(get_activity_service),
):
    return await service.get_activity_by_type(
        user_id=current_user.id,
        activity_type=activity_type,
        limit=limit,
    )