from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.notification_type import NotificationType
from app.models.community_message import CommunityMessage
from app.repositories.community_message_repository import CommunityMessageRepository
from app.repositories.community_repository import CommunityRepository
from app.schemas.community_message_schema import (
    AttachmentResponse,
    CommunityMessageResponse,
    MessageReplyResponse,
    ReactionSummary,
    SenderSummary,
)
from app.services.banned_word_service import BannedWordService
from app.services.image_service import ImageService
from app.services.notification_service import NotificationService
from app.services.websocket_manager import ws_manager


class CommunityMessageService:

    def __init__(self, db: AsyncSession):
        self.repo = CommunityMessageRepository(db)
        self.community_repo = CommunityRepository(db)
        self.notification_service = NotificationService(db)
        self.banned_word_service = BannedWordService(db)
        self.image_service = ImageService()

    # ------------------------------------------------------------------
    # Send message
    # ------------------------------------------------------------------

    async def send_message(
        self,
        community_id: int,
        sender_id: int,
        content: str | None,
        reply_to_id: int | None,
        files: list[UploadFile],
    ) -> CommunityMessageResponse:
        # Must have text or at least one file
        if not content and not files:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A message must contain text or at least one file attachment.",
            )

        # Verify community exists and user is a member
        community = await self.community_repo.get_by_id(community_id)
        if not community:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found.")

        member = await self.community_repo.get_member(community_id, sender_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a member to send messages.",
            )

        # Banned word check
        if content:
            hit = await self.banned_word_service.check(content)
            if hit:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Message contains a banned word.",
                )

        # Validate reply_to exists in same community
        if reply_to_id:
            reply_msg = await self.repo.get_by_id(reply_to_id)
            if not reply_msg or reply_msg.community_id != community_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Reply target message not found.",
                )

        # Upload files first — so if an upload fails we don't commit a message
        # row that will never get its attachments.
        uploaded_files = []
        for file in files:
            uploaded = await self.image_service.upload(file, image_type="message_image")
            uploaded_files.append(
                {
                    "url": uploaded["url"],
                    "public_id": uploaded["public_id"],
                    "name": file.filename,
                    "type": file.content_type,
                }
            )

        message = await self.repo.create(
            community_id=community_id,
            sender_id=sender_id,
            content=content,
            reply_to_id=reply_to_id,
        )

        for uf in uploaded_files:
            await self.repo.add_attachment(
                message_id=message.id,
                file_url=uf["url"],
                file_public_id=uf["public_id"],
                file_name=uf["name"],
                file_type=uf["type"],
            )

        # Reload with attachments and reactions
        message = await self.repo.get_by_id(message.id)
        response = await self._build_response(message, current_user_id=sender_id)

        # Broadcast to community room
        await ws_manager.broadcast_to_community(
            community_id,
            {"event": "new_message", "data": response.model_dump(mode="json")},
        )

        # Notify community members (new message)
        await self._notify_members(
            community_id=community_id,
            sender_id=sender_id,
            notification_type=NotificationType.COMMUNITY_MESSAGE,
            reference_id=message.id,
        )

        # Notify original message author on reply
        if reply_to_id:
            original = await self.repo.get_reply_to(reply_to_id)
            if original and original.sender_id and original.sender_id != sender_id:
                try:
                    await self.notification_service.send(
                        recipient_id=original.sender_id,
                        notification_type=NotificationType.MESSAGE_REPLY,
                        sender_id=sender_id,
                        reference_id=message.id,
                    )
                except Exception:
                    pass

        return response

    # ------------------------------------------------------------------
    # Get messages (paginated)
    # ------------------------------------------------------------------

    async def get_messages(
        self,
        community_id: int,
        requesting_user_id: int,
        page: int,
        limit: int,
    ) -> list[CommunityMessageResponse]:
        community = await self.community_repo.get_by_id(community_id)
        if not community:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found.")

        if community.is_private:
            member = await self.community_repo.get_member(community_id, requesting_user_id)
            if not member:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Members only.")

        messages = await self.repo.get_messages(community_id, page=page, limit=limit)
        return [await self._build_response(m, current_user_id=requesting_user_id) for m in messages]

    # ------------------------------------------------------------------
    # Reactions
    # ------------------------------------------------------------------

    async def toggle_reaction(
        self,
        community_id: int,
        message_id: int,
        emoji: str,
        user_id: int,
    ) -> list[ReactionSummary]:
        message = await self.repo.get_by_id(message_id)
        if not message or message.community_id != community_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")

        member = await self.community_repo.get_member(community_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Members only.")

        added = await self.repo.toggle_reaction(message_id, user_id, emoji)
        summary_data = await self.repo.get_reaction_summary(message_id, user_id)
        summary = [ReactionSummary(**r) for r in summary_data]

        # Broadcast reaction update to community room
        await ws_manager.broadcast_to_community(
            community_id,
            {
                "event": "reaction_update",
                "data": {
                    "message_id": message_id,
                    "reactions": [r.model_dump() for r in summary],
                },
            },
        )

        # Notify message author when a new reaction is added
        if added and message.sender_id and message.sender_id != user_id:
            try:
                await self.notification_service.send(
                    recipient_id=message.sender_id,
                    notification_type=NotificationType.MESSAGE_REACTION,
                    sender_id=user_id,
                    reference_id=message_id,
                )
            except Exception:
                pass

        return summary

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _build_response(
        self, message: CommunityMessage, current_user_id: int
    ) -> CommunityMessageResponse:
        # Reaction summary
        summary_data = await self.repo.get_reaction_summary(message.id, current_user_id)
        reactions = [ReactionSummary(**r) for r in summary_data]

        # Attachments
        attachments = [
            AttachmentResponse.model_validate(a) for a in message.attachments
        ]

        # Reply-to
        reply_to = None
        if message.reply_to_id:
            parent = await self.repo.get_reply_to(message.reply_to_id)
            if parent:
                reply_to = MessageReplyResponse.model_validate(parent)

        sender = SenderSummary.model_validate(message.sender) if message.sender else None

        return CommunityMessageResponse(
            id=message.id,
            community_id=message.community_id,
            sender_id=message.sender_id,
            sender=sender,
            content=message.content,
            reply_to_id=message.reply_to_id,
            reply_to=reply_to,
            attachments=attachments,
            reactions=reactions,
            created_at=message.created_at,
        )

    async def _notify_members(
        self,
        community_id: int,
        sender_id: int,
        notification_type: NotificationType,
        reference_id: int,
    ) -> None:
        members = await self.community_repo.get_members(community_id)
        for member in members:
            if member.user_id == sender_id:
                continue
            try:
                await self.notification_service.send(
                    recipient_id=member.user_id,
                    notification_type=notification_type,
                    sender_id=sender_id,
                    reference_id=reference_id,
                )
            except Exception:
                pass
