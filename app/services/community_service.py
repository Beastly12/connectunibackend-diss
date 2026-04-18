from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.community_role import CommunityRole
from app.enums.community_type import CommunityType
from app.enums.notification_type import NotificationType
from app.models.community import Community
from app.models.community_member import CommunityMember
from app.models.community_invite import CommunityInvite
from app.repositories.community_repository import CommunityRepository
from app.services.notification_service import NotificationService


GLOBAL_COMMUNITY_NAME = "ConnectUni Global"
GLOBAL_COMMUNITY_DESCRIPTION = (
    "The shared feed for every ConnectUni user. "
    "Share updates, ask questions, and connect with the whole community."
)


class CommunityService:

    def __init__(self, db: AsyncSession):
        self.repo = CommunityRepository(db)
        self.notification_service = NotificationService(db)

    # ------------------------------------------------------------------
    # System / startup helpers
    # ------------------------------------------------------------------

    async def get_global_community(self) -> Community | None:
        return await self.repo.get_by_type(CommunityType.GLOBAL)

    async def ensure_global_community(self) -> Community:
        """Idempotent: create the global community if it doesn't exist yet."""
        existing = await self.repo.get_by_type(CommunityType.GLOBAL)
        if existing:
            return existing
        return await self.repo.create_system(
            name=GLOBAL_COMMUNITY_NAME,
            description=GLOBAL_COMMUNITY_DESCRIPTION,
            community_type=CommunityType.GLOBAL,
        )

    async def add_to_global_community(self, user_id: int) -> None:
        """Add a user to the global community. No-op if already a member."""
        community = await self.repo.get_by_type(CommunityType.GLOBAL)
        if not community:
            return
        existing = await self.repo.get_member(community.id, user_id)
        if not existing:
            await self.repo.add_member(community.id, user_id, role=CommunityRole.MEMBER)

    # ------------------------------------------------------------------
    # Community CRUD
    # ------------------------------------------------------------------

    async def create_community(
        self,
        name: str,
        description: str | None,
        community_type: str,
        university: str | None,
        is_private: bool,
        creator_id: int,
    ) -> tuple[Community, int]:
        community = await self.repo.create(
            name=name,
            description=description,
            community_type=community_type,
            university=university,
            is_private=is_private,
            creator_id=creator_id,
        )
        member_count = await self.repo.get_member_count(community.id)
        return community, member_count

    async def get_community(
        self, community_id: int, requesting_user_id: int
    ) -> tuple[Community, int]:
        community = await self._get_or_404(community_id)
        await self._assert_can_view(community, requesting_user_id)
        member_count = await self.repo.get_member_count(community.id)
        return community, member_count

    async def get_my_communities(self, user_id: int) -> list[tuple[Community, int]]:
        return await self.repo.get_user_memberships(user_id)

    async def list_communities(self, user_id: int) -> list[tuple[Community, int]]:
        communities = await self.repo.list_visible(user_id)
        result = []
        for c in communities:
            count = await self.repo.get_member_count(c.id)
            result.append((c, count))
        return result

    async def update_community(
        self,
        community_id: int,
        requesting_user_id: int,
        **fields,
    ) -> tuple[Community, int]:
        community = await self._get_or_404(community_id)
        await self._assert_role(community_id, requesting_user_id, CommunityRole.ADMIN)
        community = await self.repo.update(community, **fields)
        member_count = await self.repo.get_member_count(community.id)
        return community, member_count

    async def delete_community(self, community_id: int, requesting_user_id: int) -> None:
        await self._get_or_404(community_id)
        await self._assert_role(community_id, requesting_user_id, CommunityRole.ADMIN)
        community = await self.repo.get_by_id(community_id)
        await self.repo.delete(community)

    # ------------------------------------------------------------------
    # Membership
    # ------------------------------------------------------------------

    async def join_community(self, community_id: int, user_id: int, user_university: str) -> CommunityMember:
        community = await self._get_or_404(community_id)

        if community.is_private:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This community is private. Use an invite link to join.",
            )

        if community.type == CommunityType.UNIVERSITY and community.university:
            if community.university.lower() != user_university.lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This community is restricted to a specific university.",
                )

        existing = await self.repo.get_member(community_id, user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already a member of this community.",
            )

        return await self.repo.add_member(community_id, user_id)

    async def leave_community(self, community_id: int, user_id: int) -> None:
        await self._get_or_404(community_id)
        member = await self.repo.get_member(community_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not a member.")

        if member.role == CommunityRole.ADMIN:
            admin_count = await self.repo.count_admins(community_id)
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="You are the last admin. Assign another admin before leaving.",
                )

        await self.repo.remove_member(community_id, user_id)

    async def get_members(self, community_id: int, requesting_user_id: int) -> list[CommunityMember]:
        community = await self._get_or_404(community_id)
        if community.is_private:
            await self._assert_is_member(community_id, requesting_user_id)
        return await self.repo.get_members(community_id)

    async def update_member_role(
        self,
        community_id: int,
        target_user_id: int,
        new_role: CommunityRole,
        requesting_user_id: int,
    ) -> CommunityMember:
        await self._get_or_404(community_id)
        await self._assert_role(community_id, requesting_user_id, CommunityRole.ADMIN)

        target = await self.repo.get_member(community_id, target_user_id)
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")

        # Protect last admin
        if target.role == CommunityRole.ADMIN and new_role != CommunityRole.ADMIN:
            admin_count = await self.repo.count_admins(community_id)
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot demote the last admin.",
                )

        updated = await self.repo.update_member_role(community_id, target_user_id, new_role)
        return updated

    async def remove_member(
        self,
        community_id: int,
        target_user_id: int,
        requesting_user_id: int,
    ) -> None:
        if target_user_id == requesting_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot remove yourself. Use the leave endpoint instead.",
            )
        await self._get_or_404(community_id)
        requester = await self.repo.get_member(community_id, requesting_user_id)
        if not requester or requester.role not in (CommunityRole.ADMIN, CommunityRole.MODERATOR):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")

        target = await self.repo.get_member(community_id, target_user_id)
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")

        # Moderators cannot remove admins
        if target.role == CommunityRole.ADMIN and requester.role != CommunityRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Moderators cannot remove admins.",
            )

        await self.repo.remove_member(community_id, target_user_id)

    # ------------------------------------------------------------------
    # Invite Links
    # ------------------------------------------------------------------

    async def create_invite(self, community_id: int, requesting_user_id: int) -> CommunityInvite:
        await self._get_or_404(community_id)
        requester = await self.repo.get_member(community_id, requesting_user_id)
        if not requester or requester.role not in (CommunityRole.ADMIN, CommunityRole.MODERATOR):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")
        return await self.repo.create_invite(community_id, requesting_user_id)

    async def join_via_invite(self, token: str, user_id: int, user_university: str) -> CommunityMember:
        invite = await self.repo.get_invite_by_token(token)
        if not invite:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite token.")

        community = await self.repo.get_by_id(invite.community_id)
        if not community:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community no longer exists.")

        if community.type == CommunityType.UNIVERSITY and community.university:
            if community.university.lower() != user_university.lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This community is restricted to a specific university.",
                )

        existing = await self.repo.get_member(invite.community_id, user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already a member of this community.",
            )

        member = await self.repo.add_member(invite.community_id, user_id)
        await self.repo.increment_invite_use(invite)

        # Notify the user they were added
        try:
            await self.notification_service.send(
                recipient_id=user_id,
                notification_type=NotificationType.COMMUNITY_ADDED,
                sender_id=invite.created_by,
                reference_id=invite.community_id,
            )
        except Exception:
            pass

        return member

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_or_404(self, community_id: int) -> Community:
        community = await self.repo.get_by_id(community_id)
        if not community:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found.")
        return community

    async def _assert_can_view(self, community: Community, user_id: int) -> None:
        if community.is_private:
            member = await self.repo.get_member(community.id, user_id)
            if not member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This community is private.",
                )

    async def _assert_is_member(self, community_id: int, user_id: int) -> None:
        member = await self.repo.get_member(community_id, user_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Members only.",
            )

    async def _assert_role(
        self, community_id: int, user_id: int, minimum_role: CommunityRole
    ) -> None:
        member = await self.repo.get_member(community_id, user_id)
        hierarchy = {
            CommunityRole.ADMIN: 3,
            CommunityRole.MODERATOR: 2,
            CommunityRole.MEMBER: 1,
        }
        if not member or hierarchy.get(member.role, 0) < hierarchy[minimum_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
