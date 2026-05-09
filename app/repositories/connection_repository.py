from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import joinedload

from app.models.connection import Connection
from app.enums.connection_status import ConnectionStatus


class ConnectionRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_connection(self, user_a: int, user_b: int) -> Connection | None:
        result = await self.db.execute(
            select(Connection).where(
                or_(
                    and_(Connection.requester_id == user_a, Connection.receiver_id == user_b),
                    and_(Connection.requester_id == user_b, Connection.receiver_id == user_a),
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, connection_id: int) -> Connection | None:
        result = await self.db.execute(
            select(Connection)
            .where(Connection.id == connection_id)
            .options(
                joinedload(Connection.requester),
                joinedload(Connection.receiver),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, requester_id: int, receiver_id: int) -> Connection:
        conn = Connection(
            requester_id=requester_id,
            receiver_id=receiver_id,
            status=ConnectionStatus.PENDING,
        )
        self.db.add(conn)
        await self.db.commit()
        await self.db.refresh(conn)
        return conn

    async def update_status(self, connection: Connection, new_status: ConnectionStatus) -> Connection:
        connection.status = new_status
        await self.db.commit()
        await self.db.refresh(connection)
        return connection

    async def delete(self, connection: Connection) -> None:
        await self.db.delete(connection)
        await self.db.commit()

    async def get_accepted_for_user(self, user_id: int) -> list[Connection]:
        result = await self.db.execute(
            select(Connection)
            .where(
                or_(
                    Connection.requester_id == user_id,
                    Connection.receiver_id == user_id,
                ),
                Connection.status == ConnectionStatus.ACCEPTED,
            )
            .options(
                joinedload(Connection.requester),
                joinedload(Connection.receiver),
            )
            .order_by(Connection.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_pending_incoming(self, user_id: int) -> list[Connection]:
        result = await self.db.execute(
            select(Connection)
            .where(
                Connection.receiver_id == user_id,
                Connection.status == ConnectionStatus.PENDING,
            )
            .options(
                joinedload(Connection.requester),
                joinedload(Connection.receiver),
            )
            .order_by(Connection.created_at.desc())
        )
        return list(result.scalars().all())
