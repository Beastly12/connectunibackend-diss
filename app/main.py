from fastapi import FastAPI, Depends
from app.routers.auth import router as auth_router
from app.dependencies.authDependencies import get_current_user
from app.models import User

app = FastAPI()
app.include_router(auth_router)

@app.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}