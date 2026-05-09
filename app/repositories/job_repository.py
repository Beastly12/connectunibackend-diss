from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.job import Job
from app.models.job_application import JobApplication


class JobRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, posted_by: int, **data) -> Job:
        job = Job(posted_by=posted_by, **data)
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_by_id(self, job_id: int) -> Job | None:
        result = await self.db.execute(
            select(Job).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_active(self) -> list[Job]:
        result = await self.db.execute(
            select(Job)
            .where(Job.is_active == True)
            .order_by(Job.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_poster(self, user_id: int) -> list[Job]:
        result = await self.db.execute(
            select(Job)
            .where(Job.posted_by == user_id)
            .order_by(Job.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, job: Job, updates: dict) -> Job:
        for key, value in updates.items():
            setattr(job, key, value)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_application(self, job_id: int, applicant_id: int) -> JobApplication | None:
        result = await self.db.execute(
            select(JobApplication).where(
                JobApplication.job_id == job_id,
                JobApplication.applicant_id == applicant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_application(
        self,
        job_id: int,
        applicant_id: int,
        cover_letter: str | None = None,
    ) -> JobApplication:
        application = JobApplication(
            job_id=job_id,
            applicant_id=applicant_id,
            cover_letter=cover_letter,
        )
        self.db.add(application)
        await self.db.commit()
        await self.db.refresh(application)
        return application

    async def get_applications_for_job(self, job_id: int) -> list[JobApplication]:
        result = await self.db.execute(
            select(JobApplication)
            .where(JobApplication.job_id == job_id)
            .options(joinedload(JobApplication.applicant))
            .order_by(JobApplication.applied_at.desc())
        )
        return list(result.scalars().all())
