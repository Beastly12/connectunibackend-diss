from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.core.config import settings
from app.core.security import jwt
from app.dependencies.authDependencies import get_current_user
from app.enums.community_role import CommunityRole
from app.models.user import User
from app.schemas.community_schema import (
    CommunityCreate,
    CommunityResponse,
    CommunityUpdate,
    InviteResponse,
    MemberResponse,
    RoleUpdateRequest,
)
from app.services.community_service import CommunityService
from app.services.websocket_manager import ws_manager
from app.repositories.community_repository import CommunityRepository

router = APIRouter(prefix="/communities", tags=["Communities"])


def get_community_service(db: AsyncSession = Depends(get_db)) -> CommunityService:
    return CommunityService(db)


def _to_community_response(community, member_count: int) -> CommunityResponse:
    return CommunityResponse(
        id=community.id,
        name=community.name,
        description=community.description,
        type=community.type,
        university=community.university,
        is_private=community.is_private,
        is_active=community.is_active,
        cover_image_url=community.cover_image_url,
        creator_id=community.creator_id,
        member_count=member_count,
        created_at=community.created_at,
    )


# ------------------------------------------------------------------
# Community CRUD
# ------------------------------------------------------------------

@router.post("", response_model=CommunityResponse, status_code=status.HTTP_201_CREATED)
async def create_community(
    body: CommunityCreate,
    current_user: User = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    community, count = await service.create_community(
        name=body.name,
        description=body.description,
        community_type=body.type,
        university=body.university,
        is_private=body.is_private,
        creator_id=current_user.id,
    )
    return _to_community_response(community, count)


@router.get("", response_model=list[CommunityResponse])
async def list_communities(
    current_user: User = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    items = await service.list_communities(current_user.id)
    return [_to_community_response(c, count) for c, count in items]


@router.get("/me", response_model=list[CommunityResponse])
async def get_my_communities(
    current_user: User = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    items = await service.get_my_communities(current_user.id)
    return [_to_community_response(c, count) for c, count in items]


@router.get("/{community_id}", response_model=CommunityResponse)
async def get_community(
    community_id: int,
    current_user: User = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    community, count = await service.get_community(community_id, current_user.id)
    return _to_community_response(community, count)


@router.patch("/{community_id}", response_model=CommunityResponse)
async def update_community(
    community_id: int,
    body: CommunityUpdate,
    current_user: User = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    fields = body.model_dump(exclude_unset=True)
    community, count = await service.update_community(
        community_id=community_id,
        requesting_user_id=current_user.id,
        **fields,
    )
    return _to_community_response(community, count)


@router.delete("/{community_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_community(
    community_id: int,
    current_user: User = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    await service.delete_community(community_id, current_user.id)


# ------------------------------------------------------------------
# Membership
# ------------------------------------------------------------------

@router.post("/{community_id}/join", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def join_community(
    community_id: int,
    current_user: User = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    member = await service.join_community(
        community_id=community_id,
        user_id=current_user.id,
        user_university=current_user.university,
    )
    return MemberResponse(
        user_id=member.user_id,
        full_name=current_user.full_name,
        role=member.role,
        joined_at=member.joined_at,
    )


@router.delete("/{community_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_community(
    community_id: int,
    current_user: User = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    await service.leave_community(community_id, current_user.id)


@router.get("/{community_id}/members", response_model=list[MemberResponse])
async def get_members(
    community_id: int,
    current_user: User = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    members = await service.get_members(community_id, current_user.id)
    return [
        MemberResponse(
            user_id=m.user_id,
            full_name=m.user.full_name,
            role=m.role,
            joined_at=m.joined_at,
        )
        for m in members
    ]


@router.patch("/{community_id}/members/{user_id}/role", response_model=MemberResponse)
async def update_member_role(
    community_id: int,
    user_id: int,
    body: RoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
    db: AsyncSession = Depends(get_db),
):
    member = await service.update_member_role(
        community_id=community_id,
        target_user_id=user_id,
        new_role=body.role,
        requesting_user_id=current_user.id,
    )
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    return MemberResponse(
        user_id=member.user_id,
        full_name=target_user.full_name if target_user else "",
        role=member.role,
        joined_at=member.joined_at,
    )


@router.delete("/{community_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    community_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    await service.remove_member(
        community_id=community_id,
        target_user_id=user_id,
        requesting_user_id=current_user.id,
    )


# ------------------------------------------------------------------
# Invite Links
# ------------------------------------------------------------------

@router.post("/{community_id}/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    community_id: int,
    current_user: User = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    invite = await service.create_invite(community_id, current_user.id)
    return InviteResponse(
        id=invite.id,
        token=invite.token,
        community_id=invite.community_id,
        created_by=invite.created_by,
        use_count=invite.use_count,
        created_at=invite.created_at,
    )


@router.post("/join-via-invite/{token}", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def join_via_invite(
    token: str,
    current_user: User = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    member = await service.join_via_invite(
        token=token,
        user_id=current_user.id,
        user_university=current_user.university,
    )
    return MemberResponse(
        user_id=member.user_id,
        full_name=current_user.full_name,
        role=member.role,
        joined_at=member.joined_at,
    )


# ------------------------------------------------------------------
# WebSocket — Community Room
# ------------------------------------------------------------------

@router.websocket("/{community_id}/ws")
async def community_ws(community_id: int, websocket: WebSocket):
    """
    Connect: ws://.../communities/{community_id}/ws?token=<access_token>
    Receives: {"event": "new_message"|"reaction_update", "data": {...}}
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

    # Verify membership with a short-lived session that is released before
    # entering the WebSocket loop — holding it open indefinitely would exhaust
    # the connection pool with multiple concurrent users.
    async with AsyncSessionLocal() as db:
        repo = CommunityRepository(db)
        member = await repo.get_member(community_id, user_id)
        if not member:
            await websocket.close(code=4003)
            return

    await ws_manager.connect_to_community(user_id, community_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_from_community(user_id, community_id, websocket)
