from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.database import AsyncSessionLocal
from app.dependencies.authDependencies import get_current_user
from app.models import User
from app.routers.auth import router as auth_router
from app.routers.event import router as event_router
from app.routers.profile import router as profile_router
from app.routers.activity import router as activity_router
from app.routers.notification import router as notification_router
from app.routers.community import router as community_router
from app.routers.community_message import router as community_message_router
from app.routers.banned_word import router as banned_word_router
from app.routers.mentorship import router as mentorship_router
from app.routers.mentor import router as mentor_router
from app.routers.role_profile import router as role_profile_router
from app.routers.dashboard import router as dashboard_router
from app.services.community_service import CommunityService


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with AsyncSessionLocal() as db:
        await CommunityService(db).ensure_global_community()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://d1hl36km7a0922.cloudfront.net",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth_router)
app.include_router(event_router)
app.include_router(profile_router)
app.include_router(activity_router)
app.include_router(notification_router)
app.include_router(community_router)
app.include_router(community_message_router)
app.include_router(banned_word_router)
app.include_router(mentorship_router)
app.include_router(mentor_router)
app.include_router(role_profile_router)
app.include_router(dashboard_router)


@app.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}
