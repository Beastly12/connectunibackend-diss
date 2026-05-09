from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.enums.notification_type import NotificationType
from app.models.job import Job
from app.models.job_application import JobApplication
from app.repositories.job_repository import JobRepository
from app.services.notification_service import NotificationService


class JobService:

    def __init__(self, db: AsyncSession):
        self.repo = JobRepository(db)
        self.notifications = NotificationService(db)

    async def create_job(self, posted_by: int, data: dict) -> Job:
        return await self.repo.create(posted_by=posted_by, **data)

    async def get_jobs(self) -> list[Job]:
        return await self.repo.get_active()

    async def get_my_jobs(self, user_id: int) -> list[Job]:
        return await self.repo.get_by_poster(user_id)

    async def get_job(self, job_id: int) -> Job:
        job = await self.repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
        return job

    async def update_job(self, job_id: int, user_id: int, data: dict) -> Job:
        job = await self.get_job(job_id)
        if job.posted_by != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        updates = {k: v for k, v in data.items() if v is not None}
        return await self.repo.update(job, updates)

    async def apply(
        self, job_id: int, applicant_id: int, cover_letter: str | None
    ) -> JobApplication:
        job = await self.get_job(job_id)
        if not job.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This job is no longer accepting applications.",
            )
        if job.posted_by == applicant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot apply to your own job posting.",
            )
        existing = await self.repo.get_application(job_id=job_id, applicant_id=applicant_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already applied to this job.",
            )
        application = await self.repo.create_application(
            job_id=job_id,
            applicant_id=applicant_id,
            cover_letter=cover_letter,
        )
        try:
            await self.notifications.send(
                recipient_id=job.posted_by,
                notification_type=NotificationType.JOB_APPLICATION,
                sender_id=applicant_id,
                reference_id=job_id,
            )
        except Exception:
            pass
        return application

    async def get_applications(self, job_id: int, user_id: int) -> list[JobApplication]:
        job = await self.get_job(job_id)
        if job.posted_by != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        return await self.repo.get_applications_for_job(job_id)
