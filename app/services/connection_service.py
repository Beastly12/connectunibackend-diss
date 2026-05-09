from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.enums.connection_status import ConnectionStatus
from app.enums.notification_type import NotificationType
from app.models.connection import Connection
from app.repositories.connection_repository import ConnectionRepository
from app.services.activity_service import ActivityService
from app.services.notification_service import NotificationService


class ConnectionService:

    def __init__(self, db: AsyncSession):
        self.repo = ConnectionRepository(db)
        self.activity = ActivityService(db)
        self.notifications = NotificationService(db)

    async def send_request(self, requester_id: int, receiver_id: int) -> Connection:
        if requester_id == receiver_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot send a connection request to yourself.",
            )
        existing = await self.repo.get_connection(requester_id, receiver_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A connection with this user already exists.",
            )
        conn = await self.repo.create(requester_id=requester_id, receiver_id=receiver_id)
        try:
            await self.notifications.send(
                recipient_id=receiver_id,
                notification_type=NotificationType.CONNECTION_REQUEST,
                sender_id=requester_id,
                reference_id=conn.id,
            )
        except Exception:
            pass
        return conn

    async def accept_request(self, connection_id: int, current_user_id: int) -> Connection:
        conn = await self.repo.get_by_id(connection_id)
        if not conn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found.")
        if conn.receiver_id != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        if conn.status != ConnectionStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending connections can be accepted.",
            )
        updated = await self.repo.update_status(conn, ConnectionStatus.ACCEPTED)
        try:
            await self.notifications.send(
                recipient_id=conn.requester_id,
                notification_type=NotificationType.CONNECTION_ACCEPTED,
                sender_id=current_user_id,
                reference_id=conn.id,
            )
        except Exception:
            pass
        try:
            requester_name = conn.requester.full_name if conn.requester else "someone"
            receiver_name = conn.receiver.full_name if conn.receiver else "someone"
            await self.activity.log_connected(
                user_id=conn.requester_id,
                connected_user_id=current_user_id,
                connected_user_name=receiver_name,
            )
            await self.activity.log_connected(
                user_id=current_user_id,
                connected_user_id=conn.requester_id,
                connected_user_name=requester_name,
            )
        except Exception:
            pass
        return updated

    async def reject_request(self, connection_id: int, current_user_id: int) -> Connection:
        conn = await self.repo.get_by_id(connection_id)
        if not conn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found.")
        if conn.receiver_id != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        if conn.status != ConnectionStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending connections can be rejected.",
            )
        return await self.repo.update_status(conn, ConnectionStatus.DECLINED)

    async def remove_connection(self, connection_id: int, current_user_id: int) -> None:
        conn = await self.repo.get_by_id(connection_id)
        if not conn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found.")
        if conn.requester_id != current_user_id and conn.receiver_id != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        await self.repo.delete(conn)

    async def get_my_connections(self, user_id: int) -> list[Connection]:
        return await self.repo.get_accepted_for_user(user_id)

    async def get_pending_requests(self, user_id: int) -> list[Connection]:
        return await self.repo.get_pending_incoming(user_id)
