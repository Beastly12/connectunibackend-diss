from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.community_message import CommunityMessage
from app.models.community_message_attachment import CommunityMessageAttachment
from app.models.community_message_reaction import CommunityMessageReaction
from app.models.user import User


class CommunityMessageRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        community_id: int,
        sender_id: int,
        content: str | None,
        reply_to_id: int | None,
    ) -> CommunityMessage:
        message = CommunityMessage(
            community_id=community_id,
            sender_id=sender_id,
            content=content,
            reply_to_id=reply_to_id,
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_by_id(self, message_id: int) -> CommunityMessage | None:
        result = await self.db.execute(
            select(CommunityMessage)
            .options(
                selectinload(CommunityMessage.attachments),
                selectinload(CommunityMessage.reactions),
                selectinload(CommunityMessage.sender).selectinload(User.profile),
            )
            .where(CommunityMessage.id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_messages(
        self, community_id: int, page: int, limit: int
    ) -> list[CommunityMessage]:
        result = await self.db.execute(
            select(CommunityMessage)
            .options(
                selectinload(CommunityMessage.attachments),
                selectinload(CommunityMessage.reactions),
                selectinload(CommunityMessage.sender).selectinload(User.profile),
            )
            .where(CommunityMessage.community_id == community_id)
            .order_by(CommunityMessage.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_reply_to(self, reply_to_id: int) -> CommunityMessage | None:
        result = await self.db.execute(
            select(CommunityMessage)
            .options(selectinload(CommunityMessage.sender).selectinload(User.profile))
            .where(CommunityMessage.id == reply_to_id)
        )
        return result.scalar_one_or_none()

    async def add_attachment(
        self,
        message_id: int,
        file_url: str,
        file_public_id: str,
        file_name: str | None,
        file_type: str | None,
    ) -> CommunityMessageAttachment:
        attachment = CommunityMessageAttachment(
            message_id=message_id,
            file_url=file_url,
            file_public_id=file_public_id,
            file_name=file_name,
            file_type=file_type,
        )
        self.db.add(attachment)
        await self.db.commit()
        await self.db.refresh(attachment)
        return attachment

    async def toggle_reaction(
        self, message_id: int, user_id: int, emoji: str
    ) -> bool:
        """Returns True if reaction was added, False if removed."""
        existing = await self.db.execute(
            select(CommunityMessageReaction).where(
                CommunityMessageReaction.message_id == message_id,
                CommunityMessageReaction.user_id == user_id,
                CommunityMessageReaction.emoji == emoji,
            )
        )
        reaction = existing.scalar_one_or_none()

        if reaction:
            await self.db.delete(reaction)
            await self.db.commit()
            return False
        else:
            self.db.add(
                CommunityMessageReaction(
                    message_id=message_id,
                    user_id=user_id,
                    emoji=emoji,
                )
            )
            await self.db.commit()
            return True

    async def get_reaction_summary(
        self, message_id: int, current_user_id: int
    ) -> list[dict]:
        # Aggregated counts per emoji
        counts_result = await self.db.execute(
            select(
                CommunityMessageReaction.emoji,
                func.count(CommunityMessageReaction.id).label("count"),
            )
            .where(CommunityMessageReaction.message_id == message_id)
            .group_by(CommunityMessageReaction.emoji)
        )
        counts = {row.emoji: row.count for row in counts_result.all()}

        # Which emojis the current user reacted with
        user_result = await self.db.execute(
            select(CommunityMessageReaction.emoji).where(
                CommunityMessageReaction.message_id == message_id,
                CommunityMessageReaction.user_id == current_user_id,
            )
        )
        user_emojis = set(user_result.scalars().all())

        return [
            {"emoji": emoji, "count": count, "reacted_by_me": emoji in user_emojis}
            for emoji, count in counts.items()
        ]
