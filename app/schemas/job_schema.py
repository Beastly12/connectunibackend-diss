from pydantic import BaseModel
from datetime import datetime


class JobCreate(BaseModel):
    title: str
    company: str
    location: str | None = None
    description: str | None = None
    requirements: str | None = None
    job_type: str | None = None


class JobUpdate(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    description: str | None = None
    requirements: str | None = None
    job_type: str | None = None
    is_active: bool | None = None


class JobApplicationCreate(BaseModel):
    cover_letter: str | None = None


class JobResponse(BaseModel):
    id: int
    posted_by: int
    title: str
    company: str
    location: str | None
    description: str | None
    requirements: str | None
    job_type: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class JobApplicationResponse(BaseModel):
    id: int
    job_id: int
    applicant_id: int
    applicant_name: str | None = None
    cover_letter: str | None
    status: str
    applied_at: datetime

    model_config = {"from_attributes": True}
