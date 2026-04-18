from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import jwt
from app.core.config import settings
from app.dependencies.authDependencies import get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService
from app.services.websocket_manager import ws_manager
from app.schemas.notification_schema import NotificationResponse, UnreadCountResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_notification_service(db: AsyncSession = Depends(get_db)) -> NotificationService:
    return NotificationService(db)


@router.get(
    "",
    response_model=list[NotificationResponse],
    summary="Get the authenticated user's notifications",
)
async def get_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    return await service.get_notifications(user_id=current_user.id, limit=limit)


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get the count of unread notifications",
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    count = await service.get_unread_count(user_id=current_user.id)
    return UnreadCountResponse(unread_count=count)


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Get a single notification",
)
async def get_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    notification = await service.get_notification(
        notification_id=notification_id, user_id=current_user.id
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.patch(
    "/read-all",
    status_code=204,
    summary="Mark all notifications as read",
)
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    await service.mark_all_as_read(user_id=current_user.id)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark a single notification as read",
)
async def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    updated = await service.mark_one_as_read(
        notification_id=notification_id, user_id=current_user.id
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification = await service.get_notification(
        notification_id=notification_id, user_id=current_user.id
    )
    return notification


@router.delete(
    "",
    status_code=204,
    summary="Delete all notifications",
)
async def delete_all_notifications(
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    await service.delete_all(user_id=current_user.id)


@router.websocket("/ws")
async def notifications_ws(websocket: WebSocket):
    """
    Connect with: ws://.../notifications/ws?token=<access_token>
    Receives JSON: {"event": "notification", "data": {...}}
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        if payload.get("type") != "access":
            raise ValueError("wrong token type")
        user_id: int = payload["uid"]
    except Exception:
        await websocket.close(code=4001)
        return

    await ws_manager.connect(user_id, websocket)
    try:
        while True:
            # Keep the connection alive; client pings are ignored
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id, websocket)
