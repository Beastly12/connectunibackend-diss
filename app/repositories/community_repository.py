import secrets

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums.community_role import CommunityRole
from app.models.community import Community
from app.models.community_member import CommunityMember
from app.models.community_invite import CommunityInvite


class CommunityRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Community CRUD
    # ------------------------------------------------------------------

    async def create(
        self,
        name: str,
        description: str | None,
        community_type: str,
        university: str | None,
        is_private: bool,
        creator_id: int,
    ) -> Community:
        community = Community(
            name=name,
            description=description,
            type=community_type,
            university=university,
            is_private=is_private,
            creator_id=creator_id,
        )
        self.db.add(community)
        await self.db.flush()  # get community.id before adding member

        # Creator is automatically admin
        member = CommunityMember(
            community_id=community.id,
            user_id=creator_id,
            role=CommunityRole.ADMIN,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(community)
        return community

    async def get_by_id(self, community_id: int) -> Community | None:
        result = await self.db.execute(
            select(Community).where(
                Community.id == community_id,
                Community.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_type(self, community_type: str) -> Community | None:
        """Return the first active community with the given type (e.g. GLOBAL)."""
        result = await self.db.execute(
            select(Community).where(
                Community.type == community_type,
                Community.is_active == True,
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def create_system(
        self,
        name: str,
        description: str | None,
        community_type: str,
    ) -> Community:
        """Create a system-owned community with no initial members."""
        community = Community(
            name=name,
            description=description,
            type=community_type,
            university=None,
            is_private=False,
            creator_id=None,
        )
        self.db.add(community)
        await self.db.commit()
        await self.db.refresh(community)
        return community

    async def get_user_memberships(self, user_id: int) -> list[tuple[Community, int]]:
        """Return all communities the user is a member of, with member counts."""
        result = await self.db.execute(
            select(Community)
            .join(CommunityMember, CommunityMember.community_id == Community.id)
            .where(CommunityMember.user_id == user_id, Community.is_active == True)
            .order_by(CommunityMember.joined_at)
        )
        communities = result.scalars().all()
        counts = []
        for c in communities:
            count = await self.get_member_count(c.id)
            counts.append((c, count))
        return counts

    async def list_visible(self, user_id: int) -> list[Community]:
        """Public communities + private communities the user belongs to."""
        # Get community IDs the user is a member of
        member_ids_result = await self.db.execute(
            select(CommunityMember.community_id).where(CommunityMember.user_id == user_id)
        )
        member_community_ids = set(member_ids_result.scalars().all())

        result = await self.db.execute(
            select(Community).where(Community.is_active == True)
        )
        all_communities = result.scalars().all()

        return [
            c for c in all_communities
            if not c.is_private or c.id in member_community_ids
        ]

    async def update(self, community: Community, **fields) -> Community:
        for key, value in fields.items():
            if value is not None:
                setattr(community, key, value)
        await self.db.commit()
        await self.db.refresh(community)
        return community

    async def delete(self, community: Community) -> None:
        community.is_active = False
        await self.db.commit()

    async def get_member_count(self, community_id: int) -> int:
        result = await self.db.execute(
            select(func.count()).where(CommunityMember.community_id == community_id)
        )
        return result.scalar_one()

    # ------------------------------------------------------------------
    # Membership
    # ------------------------------------------------------------------

    async def get_member(self, community_id: int, user_id: int) -> CommunityMember | None:
        result = await self.db.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == community_id,
                CommunityMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_members(self, community_id: int) -> list[CommunityMember]:
        result = await self.db.execute(
            select(CommunityMember)
            .options(selectinload(CommunityMember.user))
            .where(CommunityMember.community_id == community_id)
            .order_by(CommunityMember.joined_at)
        )
        return result.scalars().all()

    async def add_member(
        self,
        community_id: int,
        user_id: int,
        role: CommunityRole = CommunityRole.MEMBER,
    ) -> CommunityMember:
        member = CommunityMember(
            community_id=community_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def remove_member(self, community_id: int, user_id: int) -> None:
        await self.db.execute(
            delete(CommunityMember).where(
                CommunityMember.community_id == community_id,
                CommunityMember.user_id == user_id,
            )
        )
        await self.db.commit()

    async def update_member_role(
        self, community_id: int, user_id: int, role: CommunityRole
    ) -> CommunityMember | None:
        member = await self.get_member(community_id, user_id)
        if not member:
            return None
        member.role = role
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def count_admins(self, community_id: int) -> int:
        result = await self.db.execute(
            select(func.count()).where(
                CommunityMember.community_id == community_id,
                CommunityMember.role == CommunityRole.ADMIN,
            )
        )
        return result.scalar_one()

    # ------------------------------------------------------------------
    # Invite Links
    # ------------------------------------------------------------------

    async def create_invite(self, community_id: int, created_by: int) -> CommunityInvite:
        token = secrets.token_urlsafe(32)
        invite = CommunityInvite(
            community_id=community_id,
            created_by=created_by,
            token=token,
        )
        self.db.add(invite)
        await self.db.commit()
        await self.db.refresh(invite)
        return invite

    async def get_invite_by_token(self, token: str) -> CommunityInvite | None:
        result = await self.db.execute(
            select(CommunityInvite).where(CommunityInvite.token == token)
        )
        return result.scalar_one_or_none()

    async def increment_invite_use(self, invite: CommunityInvite) -> None:
        invite.use_count += 1
        await self.db.commit()
