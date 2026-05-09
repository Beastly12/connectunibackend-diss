from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.authDependencies import get_current_user
from app.models.user import User
from app.schemas.job_schema import (
    JobCreate,
    JobUpdate,
    JobApplicationCreate,
    JobResponse,
    JobApplicationResponse,
)
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def get_service(db: AsyncSession = Depends(get_db)) -> JobService:
    return JobService(db)


def _to_application_response(app) -> JobApplicationResponse:
    return JobApplicationResponse(
        id=app.id,
        job_id=app.job_id,
        applicant_id=app.applicant_id,
        applicant_name=app.applicant.full_name if app.applicant else None,
        cover_letter=app.cover_letter,
        status=app.status,
        applied_at=app.applied_at,
    )


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_service),
):
    return await service.get_jobs()


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    body: JobCreate,
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_service),
):
    return await service.create_job(
        posted_by=current_user.id,
        data=body.model_dump(exclude_none=True),
    )


@router.get("/mine", response_model=list[JobResponse])
async def get_my_jobs(
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_service),
):
    return await service.get_my_jobs(user_id=current_user.id)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_service),
):
    return await service.get_job(job_id)


@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    body: JobUpdate,
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_service),
):
    return await service.update_job(
        job_id=job_id,
        user_id=current_user.id,
        data=body.model_dump(exclude_unset=True),
    )


@router.post(
    "/{job_id}/apply",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def apply_to_job(
    job_id: int,
    body: JobApplicationCreate,
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_service),
):
    application = await service.apply(
        job_id=job_id,
        applicant_id=current_user.id,
        cover_letter=body.cover_letter,
    )
    return JobApplicationResponse(
        id=application.id,
        job_id=application.job_id,
        applicant_id=application.applicant_id,
        applicant_name=current_user.full_name,
        cover_letter=application.cover_letter,
        status=application.status,
        applied_at=application.applied_at,
    )


@router.get("/{job_id}/applications", response_model=list[JobApplicationResponse])
async def get_applications(
    job_id: int,
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_service),
):
    applications = await service.get_applications(
        job_id=job_id,
        user_id=current_user.id,
    )
    return [_to_application_response(a) for a in applications]
