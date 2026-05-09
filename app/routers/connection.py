from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.authDependencies import get_current_user
from app.models.connection import Connection
from app.models.user import User
from app.schemas.connection_schema import ConnectionResponse
from app.services.connection_service import ConnectionService

router = APIRouter(prefix="/connections", tags=["Connections"])


def get_service(db: AsyncSession = Depends(get_db)) -> ConnectionService:
    return ConnectionService(db)


def _to_response(conn: Connection) -> ConnectionResponse:
    return ConnectionResponse(
        id=conn.id,
        requester_id=conn.requester_id,
        requester_name=conn.requester.full_name if conn.requester else None,
        receiver_id=conn.receiver_id,
        receiver_name=conn.receiver.full_name if conn.receiver else None,
        status=conn.status,
        created_at=conn.created_at,
    )


@router.post(
    "/request/{receiver_id}",
    response_model=ConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_request(
    receiver_id: int,
    current_user: User = Depends(get_current_user),
    service: ConnectionService = Depends(get_service),
):
    conn = await service.send_request(
        requester_id=current_user.id,
        receiver_id=receiver_id,
    )
    return ConnectionResponse(
        id=conn.id,
        requester_id=conn.requester_id,
        requester_name=current_user.full_name,
        receiver_id=conn.receiver_id,
        receiver_name=None,
        status=conn.status,
        created_at=conn.created_at,
    )


@router.post("/{connection_id}/accept", response_model=ConnectionResponse)
async def accept_request(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    service: ConnectionService = Depends(get_service),
):
    conn = await service.accept_request(
        connection_id=connection_id,
        current_user_id=current_user.id,
    )
    return _to_response(conn)


@router.post("/{connection_id}/reject", response_model=ConnectionResponse)
async def reject_request(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    service: ConnectionService = Depends(get_service),
):
    conn = await service.reject_request(
        connection_id=connection_id,
        current_user_id=current_user.id,
    )
    return _to_response(conn)


@router.get("", response_model=list[ConnectionResponse])
async def get_my_connections(
    current_user: User = Depends(get_current_user),
    service: ConnectionService = Depends(get_service),
):
    connections = await service.get_my_connections(user_id=current_user.id)
    return [_to_response(c) for c in connections]


@router.get("/pending", response_model=list[ConnectionResponse])
async def get_pending_requests(
    current_user: User = Depends(get_current_user),
    service: ConnectionService = Depends(get_service),
):
    connections = await service.get_pending_requests(user_id=current_user.id)
    return [_to_response(c) for c in connections]


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    service: ConnectionService = Depends(get_service),
):
    await service.remove_connection(
        connection_id=connection_id,
        current_user_id=current_user.id,
    )
