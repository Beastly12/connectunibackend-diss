from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload, selectinload

from app.models.community_post import CommunityPost
from app.models.post_like import PostLike
from app.models.post_comment import PostComment


class PostRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        community_id: int,
        author_id: int,
        title: str,
        content: str,
        category: str | None = None,
    ) -> CommunityPost:
        post = CommunityPost(
            community_id=community_id,
            author_id=author_id,
            title=title,
            content=content,
            category=category,
        )
        self.db.add(post)
        await self.db.commit()
        await self.db.refresh(post)
        return post

    async def get_by_id(self, post_id: int) -> CommunityPost | None:
        result = await self.db.execute(
            select(CommunityPost)
            .where(CommunityPost.id == post_id)
            .options(
                joinedload(CommunityPost.author),
                selectinload(CommunityPost.likes),
                selectinload(CommunityPost.comments),
            )
        )
        return result.scalar_one_or_none()

    async def get_for_community(
        self, community_id: int, limit: int = 20, offset: int = 0
    ) -> list[CommunityPost]:
        result = await self.db.execute(
            select(CommunityPost)
            .where(CommunityPost.community_id == community_id)
            .options(
                joinedload(CommunityPost.author),
                selectinload(CommunityPost.likes),
                selectinload(CommunityPost.comments),
            )
            .order_by(CommunityPost.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def delete(self, post: CommunityPost) -> None:
        await self.db.delete(post)
        await self.db.commit()

    async def get_like(self, post_id: int, user_id: int) -> PostLike | None:
        result = await self.db.execute(
            select(PostLike).where(
                PostLike.post_id == post_id,
                PostLike.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_like(self, post_id: int, user_id: int) -> PostLike:
        like = PostLike(post_id=post_id, user_id=user_id)
        self.db.add(like)
        await self.db.commit()
        return like

    async def remove_like(self, like: PostLike) -> None:
        await self.db.delete(like)
        await self.db.commit()

    async def add_comment(self, post_id: int, author_id: int, content: str) -> PostComment:
        comment = PostComment(post_id=post_id, author_id=author_id, content=content)
        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment)
        return comment

    async def get_comments(self, post_id: int) -> list[PostComment]:
        result = await self.db.execute(
            select(PostComment)
            .where(PostComment.post_id == post_id)
            .options(joinedload(PostComment.author))
            .order_by(PostComment.created_at.asc())
        )
        return list(result.scalars().all())
