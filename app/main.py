from fastapi import FastAPI, Depends
from app.routers.auth import router as auth_router
from app.routers.event import router as event_router
from app.routers.profile import router as profile_router
from app.dependencies.authDependencies import get_current_user
from app.models import User

app = FastAPI()
app.include_router(auth_router)
app.include_router(event_router)
app.include_router(profile_router)

@app.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}