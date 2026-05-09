from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.enums.notification_type import NotificationType
from app.models.community_post import CommunityPost
from app.models.post_comment import PostComment
from app.repositories.community_repository import CommunityRepository
from app.repositories.post_repository import PostRepository
from app.services.activity_service import ActivityService
from app.services.notification_service import NotificationService


def _post_to_dict(post: CommunityPost) -> dict:
    return {
        "id": post.id,
        "community_id": post.community_id,
        "author_id": post.author_id,
        "author_name": post.author.full_name if post.author else "",
        "title": post.title,
        "content": post.content,
        "category": post.category,
        "image_url": post.image_url,
        "like_count": len(post.likes),
        "comment_count": len(post.comments),
        "created_at": post.created_at,
    }


def _comment_to_dict(comment: PostComment) -> dict:
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "author_id": comment.author_id,
        "author_name": comment.author.full_name if comment.author else "",
        "content": comment.content,
        "created_at": comment.created_at,
    }


class PostService:

    def __init__(self, db: AsyncSession):
        self.repo = PostRepository(db)
        self.community_repo = CommunityRepository(db)
        self.activity = ActivityService(db)
        self.notifications = NotificationService(db)

    async def create_post(
        self,
        community_id: int,
        author_id: int,
        title: str,
        content: str,
        category: str | None = None,
    ) -> dict:
        member = await self.community_repo.get_member(community_id, author_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a community member to post.",
            )
        post = await self.repo.create(
            community_id=community_id,
            author_id=author_id,
            title=title,
            content=content,
            category=category,
        )
        # Reload with relationships
        post = await self.repo.get_by_id(post.id)
        try:
            await self.activity.log_created_post(
                user_id=author_id,
                post_id=post.id,
                post_title=title,
            )
        except Exception:
            pass
        return _post_to_dict(post)

    async def get_posts(
        self,
        community_id: int,
        requesting_user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        member = await self.community_repo.get_member(community_id, requesting_user_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a community member to view posts.",
            )
        posts = await self.repo.get_for_community(community_id, limit=limit, offset=offset)
        return [_post_to_dict(p) for p in posts]

    async def delete_post(self, community_id: int, post_id: int, user_id: int) -> None:
        post = await self.repo.get_by_id(post_id)
        if not post or post.community_id != community_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
        if post.author_id != user_id:
            member = await self.community_repo.get_member(community_id, user_id)
            if not member or member.role not in ("admin", "moderator"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        await self.repo.delete(post)

    async def toggle_like(self, community_id: int, post_id: int, user_id: int) -> dict:
        post = await self.repo.get_by_id(post_id)
        if not post or post.community_id != community_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
        existing = await self.repo.get_like(post_id=post_id, user_id=user_id)
        if existing:
            await self.repo.remove_like(existing)
            liked = False
        else:
            await self.repo.add_like(post_id=post_id, user_id=user_id)
            liked = True
            if post.author_id != user_id:
                try:
                    await self.notifications.send(
                        recipient_id=post.author_id,
                        notification_type=NotificationType.POST_LIKE,
                        sender_id=user_id,
                        reference_id=post_id,
                    )
                except Exception:
                    pass
        # Reload to get accurate count
        post = await self.repo.get_by_id(post_id)
        return {"liked": liked, "like_count": len(post.likes)}

    async def add_comment(
        self, community_id: int, post_id: int, author_id: int, content: str
    ) -> dict:
        post = await self.repo.get_by_id(post_id)
        if not post or post.community_id != community_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
        comment = await self.repo.add_comment(
            post_id=post_id, author_id=author_id, content=content
        )
        if post.author_id != author_id:
            try:
                await self.notifications.send(
                    recipient_id=post.author_id,
                    notification_type=NotificationType.POST_COMMENT,
                    sender_id=author_id,
                    reference_id=post_id,
                )
            except Exception:
                pass
        # Reload comment with author
        comments = await self.repo.get_comments(post_id)
        loaded = next((c for c in comments if c.id == comment.id), comment)
        return _comment_to_dict(loaded)

    async def get_comments(
        self, community_id: int, post_id: int, requesting_user_id: int
    ) -> list[dict]:
        post = await self.repo.get_by_id(post_id)
        if not post or post.community_id != community_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
        comments = await self.repo.get_comments(post_id)
        return [_comment_to_dict(c) for c in comments]
