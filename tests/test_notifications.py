"""
Tests for the notifications REST API.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers, make_user
from app.enums.notification_type import NotificationType
from app.services.notification_service import NotificationService

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helper: create a notification directly via service
# ---------------------------------------------------------------------------

async def create_notification(db, recipient_id: int, sender_id: int, ref_id: int = 1):
    svc = NotificationService(db)
    return await svc.send(
        recipient_id=recipient_id,
        notification_type=NotificationType.COMMUNITY_MESSAGE,
        sender_id=sender_id,
        reference_id=ref_id,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNotifications:

    async def test_get_notifications_empty(self, client, db):
        user = await make_user(db, email="notif_empty@test.com")
        res = await client.get("/notifications", headers=auth_headers(user))
        assert res.status_code == 200
        assert res.json() == []

    async def test_get_notifications_returns_user_notifs(self, client, db):
        recipient = await make_user(db, email="notif_recip@test.com")
        sender = await make_user(db, email="notif_sender@test.com")
        other = await make_user(db, email="notif_other@test.com")

        await create_notification(db, recipient.id, sender.id)
        await create_notification(db, other.id, sender.id)  # belongs to other user

        res = await client.get("/notifications", headers=auth_headers(recipient))
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["sender_id"] == sender.id

    async def test_get_single_notification(self, client, db):
        user = await make_user(db, email="single_notif@test.com")
        sender = await make_user(db, email="single_notif_sender@test.com")
        notif = await create_notification(db, user.id, sender.id)

        res = await client.get(f"/notifications/{notif.id}", headers=auth_headers(user))
        assert res.status_code == 200
        assert res.json()["id"] == notif.id

    async def test_get_notification_wrong_user_404(self, client, db):
        owner = await make_user(db, email="notif_owner@test.com")
        thief = await make_user(db, email="notif_thief@test.com")
        sender = await make_user(db, email="notif_thief_sender@test.com")
        notif = await create_notification(db, owner.id, sender.id)

        res = await client.get(f"/notifications/{notif.id}", headers=auth_headers(thief))
        assert res.status_code == 404

    async def test_unread_count(self, client, db):
        user = await make_user(db, email="unread_count@test.com")
        sender = await make_user(db, email="unread_sender@test.com")

        await create_notification(db, user.id, sender.id)
        await create_notification(db, user.id, sender.id)

        res = await client.get("/notifications/unread-count", headers=auth_headers(user))
        assert res.status_code == 200
        assert res.json()["unread_count"] == 2

    async def test_mark_one_as_read(self, client, db):
        user = await make_user(db, email="mark_one@test.com")
        sender = await make_user(db, email="mark_one_sender@test.com")
        notif = await create_notification(db, user.id, sender.id)

        res = await client.patch(
            f"/notifications/{notif.id}/read", headers=auth_headers(user)
        )
        assert res.status_code == 200
        assert res.json()["is_read"] is True

        count_res = await client.get("/notifications/unread-count", headers=auth_headers(user))
        assert count_res.json()["unread_count"] == 0

    async def test_mark_all_as_read(self, client, db):
        user = await make_user(db, email="mark_all@test.com")
        sender = await make_user(db, email="mark_all_sender@test.com")

        await create_notification(db, user.id, sender.id)
        await create_notification(db, user.id, sender.id)
        await create_notification(db, user.id, sender.id)

        res = await client.patch("/notifications/read-all", headers=auth_headers(user))
        assert res.status_code == 204

        count_res = await client.get("/notifications/unread-count", headers=auth_headers(user))
        assert count_res.json()["unread_count"] == 0

    async def test_delete_all_notifications(self, client, db):
        user = await make_user(db, email="del_notif@test.com")
        sender = await make_user(db, email="del_notif_sender@test.com")

        await create_notification(db, user.id, sender.id)
        await create_notification(db, user.id, sender.id)

        del_res = await client.delete("/notifications", headers=auth_headers(user))
        assert del_res.status_code == 204

        list_res = await client.get("/notifications", headers=auth_headers(user))
        assert list_res.json() == []

    async def test_notification_type_field(self, client, db):
        user = await make_user(db, email="notif_type@test.com")
        sender = await make_user(db, email="notif_type_sender@test.com")
        await create_notification(db, user.id, sender.id)

        res = await client.get("/notifications", headers=auth_headers(user))
        assert res.json()[0]["type"] == NotificationType.COMMUNITY_MESSAGE

    async def test_notifications_limit_param(self, client, db):
        user = await make_user(db, email="notif_limit@test.com")
        sender = await make_user(db, email="notif_limit_sender@test.com")

        for _ in range(5):
            await create_notification(db, user.id, sender.id)

        res = await client.get(
            "/notifications", params={"limit": 3}, headers=auth_headers(user)
        )
        assert res.status_code == 200
        assert len(res.json()) == 3
