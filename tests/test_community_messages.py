"""
Tests for community messaging, reactions, and banned words.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers, make_user

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def create_community(client, headers, *, name="Msg Test", is_private=False) -> dict:
    res = await client.post(
        "/communities",
        json={"name": name, "type": "global", "is_private": is_private},
        headers=headers,
    )
    assert res.status_code == 201
    return res.json()


async def send_message(client, community_id: int, headers: dict, content: str) -> dict:
    res = await client.post(
        f"/communities/{community_id}/messages",
        data={"content": content},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


# ---------------------------------------------------------------------------
# Sending messages
# ---------------------------------------------------------------------------

class TestSendMessage:

    async def test_send_text_message(self, client, db):
        owner = await make_user(db, email="msg_owner@test.com")
        community = await create_community(client, auth_headers(owner), name="Send Test")

        res = await client.post(
            f"/communities/{community['id']}/messages",
            data={"content": "Hello world"},
            headers=auth_headers(owner),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["content"] == "Hello world"
        assert data["sender_id"] == owner.id
        assert data["reply_to"] is None
        assert data["attachments"] == []
        assert data["reactions"] == []

    async def test_send_message_no_content_no_files_fails(self, client, db):
        owner = await make_user(db, email="empty_msg@test.com")
        community = await create_community(client, auth_headers(owner), name="Empty Msg")

        res = await client.post(
            f"/communities/{community['id']}/messages",
            data={},
            headers=auth_headers(owner),
        )
        assert res.status_code == 422

    async def test_non_member_cannot_send(self, client, db):
        owner = await make_user(db, email="nm_owner@test.com")
        outsider = await make_user(db, email="nm_outsider@test.com")
        community = await create_community(client, auth_headers(owner), name="Members Only Msg")

        res = await client.post(
            f"/communities/{community['id']}/messages",
            data={"content": "Intruder!"},
            headers=auth_headers(outsider),
        )
        assert res.status_code == 403

    async def test_send_reply_message(self, client, db):
        owner = await make_user(db, email="reply_owner@test.com")
        community = await create_community(client, auth_headers(owner), name="Reply Test")

        original = await send_message(client, community["id"], auth_headers(owner), "Original")
        original_id = original["id"]

        res = await client.post(
            f"/communities/{community['id']}/messages",
            data={"content": "Reply here", "reply_to_id": str(original_id)},
            headers=auth_headers(owner),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["reply_to_id"] == original_id
        assert data["reply_to"]["id"] == original_id
        assert data["reply_to"]["content"] == "Original"

    async def test_reply_to_wrong_community_message_fails(self, client, db):
        owner = await make_user(db, email="wrong_reply_owner@test.com")
        comm1 = await create_community(client, auth_headers(owner), name="Comm Alpha")
        comm2 = await create_community(client, auth_headers(owner), name="Comm Beta")

        msg = await send_message(client, comm1["id"], auth_headers(owner), "In comm1")

        res = await client.post(
            f"/communities/{comm2['id']}/messages",
            data={"content": "Bad reply", "reply_to_id": str(msg["id"])},
            headers=auth_headers(owner),
        )
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Fetching messages (pagination)
# ---------------------------------------------------------------------------

class TestGetMessages:

    async def test_get_messages_returns_list(self, client, db):
        owner = await make_user(db, email="get_msg_owner@test.com")
        community = await create_community(client, auth_headers(owner), name="Get Msgs")

        for i in range(3):
            await send_message(client, community["id"], auth_headers(owner), f"Msg {i}")

        res = await client.get(
            f"/communities/{community['id']}/messages",
            params={"page": 1, "limit": 10},
            headers=auth_headers(owner),
        )
        assert res.status_code == 200
        assert len(res.json()) == 3

    async def test_get_messages_pagination(self, client, db):
        owner = await make_user(db, email="pag_owner@test.com")
        community = await create_community(client, auth_headers(owner), name="Paginated")

        for i in range(5):
            await send_message(client, community["id"], auth_headers(owner), f"Pag {i}")

        page1 = await client.get(
            f"/communities/{community['id']}/messages",
            params={"page": 1, "limit": 3},
            headers=auth_headers(owner),
        )
        page2 = await client.get(
            f"/communities/{community['id']}/messages",
            params={"page": 2, "limit": 3},
            headers=auth_headers(owner),
        )
        assert len(page1.json()) == 3
        assert len(page2.json()) == 2

    async def test_private_community_messages_hidden_for_non_member(self, client, db):
        owner = await make_user(db, email="priv_msg_owner@test.com")
        outsider = await make_user(db, email="priv_msg_outsider@test.com")
        community = await create_community(
            client, auth_headers(owner), name="Private Msgs", is_private=True
        )
        await send_message(client, community["id"], auth_headers(owner), "Secret")

        res = await client.get(
            f"/communities/{community['id']}/messages",
            headers=auth_headers(outsider),
        )
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# Reactions
# ---------------------------------------------------------------------------

class TestReactions:

    async def test_add_reaction(self, client, db):
        owner = await make_user(db, email="react_owner@test.com")
        community = await create_community(client, auth_headers(owner), name="React Test")
        msg = await send_message(client, community["id"], auth_headers(owner), "React me")

        res = await client.post(
            f"/communities/{community['id']}/messages/{msg['id']}/reactions",
            json={"emoji": "👍"},
            headers=auth_headers(owner),
        )
        assert res.status_code == 200
        reactions = res.json()
        assert len(reactions) == 1
        assert reactions[0]["emoji"] == "👍"
        assert reactions[0]["count"] == 1
        assert reactions[0]["reacted_by_me"] is True

    async def test_toggle_removes_existing_reaction(self, client, db):
        owner = await make_user(db, email="toggle_owner@test.com")
        community = await create_community(client, auth_headers(owner), name="Toggle Test")
        msg = await send_message(client, community["id"], auth_headers(owner), "Toggle me")

        # Add reaction
        await client.post(
            f"/communities/{community['id']}/messages/{msg['id']}/reactions",
            json={"emoji": "❤️"},
            headers=auth_headers(owner),
        )
        # Toggle off
        res = await client.post(
            f"/communities/{community['id']}/messages/{msg['id']}/reactions",
            json={"emoji": "❤️"},
            headers=auth_headers(owner),
        )
        assert res.status_code == 200
        assert res.json() == []

    async def test_multiple_users_same_emoji(self, client, db):
        owner = await make_user(db, email="multi_react_owner@test.com")
        other = await make_user(db, email="multi_react_other@test.com")
        community = await create_community(client, auth_headers(owner), name="Multi React")
        await client.post(f"/communities/{community['id']}/join", headers=auth_headers(other))
        msg = await send_message(client, community["id"], auth_headers(owner), "Popular")

        await client.post(
            f"/communities/{community['id']}/messages/{msg['id']}/reactions",
            json={"emoji": "🔥"},
            headers=auth_headers(owner),
        )
        res = await client.post(
            f"/communities/{community['id']}/messages/{msg['id']}/reactions",
            json={"emoji": "🔥"},
            headers=auth_headers(other),
        )
        reactions = res.json()
        fire = next(r for r in reactions if r["emoji"] == "🔥")
        assert fire["count"] == 2
        assert fire["reacted_by_me"] is True  # current user is `other`

    async def test_reaction_shows_reacted_by_me_false_for_other_user(self, client, db):
        owner = await make_user(db, email="rby_owner@test.com")
        viewer = await make_user(db, email="rby_viewer@test.com")
        community = await create_community(client, auth_headers(owner), name="RBM Test")
        await client.post(f"/communities/{community['id']}/join", headers=auth_headers(viewer))
        msg = await send_message(client, community["id"], auth_headers(owner), "Test RBM")

        # owner reacts
        await client.post(
            f"/communities/{community['id']}/messages/{msg['id']}/reactions",
            json={"emoji": "😮"},
            headers=auth_headers(owner),
        )

        # viewer fetches messages
        res = await client.get(
            f"/communities/{community['id']}/messages",
            headers=auth_headers(viewer),
        )
        msg_data = next(m for m in res.json() if m["id"] == msg["id"])
        reaction = next(r for r in msg_data["reactions"] if r["emoji"] == "😮")
        assert reaction["reacted_by_me"] is False

    async def test_non_member_cannot_react(self, client, db):
        owner = await make_user(db, email="nm_react_owner@test.com")
        outsider = await make_user(db, email="nm_react_outsider@test.com")
        community = await create_community(client, auth_headers(owner), name="No React")
        msg = await send_message(client, community["id"], auth_headers(owner), "Can't react")

        res = await client.post(
            f"/communities/{community['id']}/messages/{msg['id']}/reactions",
            json={"emoji": "👍"},
            headers=auth_headers(outsider),
        )
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# Banned words
# ---------------------------------------------------------------------------

class TestBannedWords:

    async def test_message_with_banned_word_rejected(self, client, db):
        admin = await make_user(db, email="bw_admin@test.com")
        community = await create_community(client, auth_headers(admin), name="Moderated")

        # Add a banned word
        await client.post(
            "/admin/banned-words",
            json={"word": "badword"},
            headers=auth_headers(admin),
        )

        res = await client.post(
            f"/communities/{community['id']}/messages",
            data={"content": "This contains badword in it"},
            headers=auth_headers(admin),
        )
        assert res.status_code == 422

    async def test_banned_word_check_is_case_insensitive(self, client, db):
        admin = await make_user(db, email="bw_case_admin@test.com")
        community = await create_community(client, auth_headers(admin), name="Case Test")

        await client.post(
            "/admin/banned-words",
            json={"word": "spam"},
            headers=auth_headers(admin),
        )

        res = await client.post(
            f"/communities/{community['id']}/messages",
            data={"content": "This is SPAM content"},
            headers=auth_headers(admin),
        )
        assert res.status_code == 422

    async def test_clean_message_is_allowed(self, client, db):
        admin = await make_user(db, email="bw_clean_admin@test.com")
        community = await create_community(client, auth_headers(admin), name="Clean Test")

        await client.post(
            "/admin/banned-words",
            json={"word": "forbidden"},
            headers=auth_headers(admin),
        )

        res = await client.post(
            f"/communities/{community['id']}/messages",
            data={"content": "This is a perfectly fine message"},
            headers=auth_headers(admin),
        )
        assert res.status_code == 201

    async def test_list_banned_words(self, client, db):
        admin = await make_user(db, email="bw_list_admin@test.com")
        await client.post(
            "/admin/banned-words",
            json={"word": "listword"},
            headers=auth_headers(admin),
        )
        res = await client.get("/admin/banned-words", headers=auth_headers(admin))
        assert res.status_code == 200
        assert "listword" in res.json()

    async def test_remove_banned_word(self, client, db):
        admin = await make_user(db, email="bw_rm_admin@test.com")
        community = await create_community(client, auth_headers(admin), name="Remove BW")

        await client.post(
            "/admin/banned-words",
            json={"word": "temporary"},
            headers=auth_headers(admin),
        )
        await client.delete(
            "/admin/banned-words/temporary", headers=auth_headers(admin)
        )

        # Message should now be allowed
        res = await client.post(
            f"/communities/{community['id']}/messages",
            data={"content": "This is temporary content"},
            headers=auth_headers(admin),
        )
        assert res.status_code == 201
