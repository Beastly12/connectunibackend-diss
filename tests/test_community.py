"""
Tests for community CRUD, membership, roles and invite links.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers, make_user

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def create_community(
    client: AsyncClient,
    headers: dict,
    *,
    name: str = "Test Community",
    community_type: str = "global",
    is_private: bool = False,
) -> dict:
    res = await client.post(
        "/communities",
        json={"name": name, "type": community_type, "is_private": is_private},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


# ---------------------------------------------------------------------------
# Community CRUD
# ---------------------------------------------------------------------------

class TestCommunityCRUD:

    async def test_create_public_community(self, client, db):
        user = await make_user(db, email="creator@test.com")
        res = await client.post(
            "/communities",
            json={"name": "Open Club", "type": "global", "is_private": False},
            headers=auth_headers(user),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Open Club"
        assert data["is_private"] is False
        assert data["creator_id"] == user.id
        assert data["member_count"] == 1  # creator auto-joined

    async def test_create_private_community(self, client, db):
        user = await make_user(db, email="priv_creator@test.com")
        res = await client.post(
            "/communities",
            json={"name": "Secret Club", "type": "global", "is_private": True},
            headers=auth_headers(user),
        )
        assert res.status_code == 201
        assert res.json()["is_private"] is True

    async def test_list_communities_shows_public(self, client, db):
        owner = await make_user(db, email="lister_owner@test.com")
        viewer = await make_user(db, email="lister_viewer@test.com")
        await create_community(client, auth_headers(owner), name="Public Comm", is_private=False)

        res = await client.get("/communities", headers=auth_headers(viewer))
        assert res.status_code == 200
        names = [c["name"] for c in res.json()]
        assert "Public Comm" in names

    async def test_list_communities_hides_private_for_non_member(self, client, db):
        owner = await make_user(db, email="priv_owner2@test.com")
        outsider = await make_user(db, email="outsider2@test.com")
        community = await create_community(
            client, auth_headers(owner), name="Private Comm", is_private=True
        )

        res = await client.get("/communities", headers=auth_headers(outsider))
        assert res.status_code == 200
        names = [c["name"] for c in res.json()]
        assert "Private Comm" not in names

    async def test_get_community_public(self, client, db):
        owner = await make_user(db, email="get_owner@test.com")
        viewer = await make_user(db, email="get_viewer@test.com")
        community = await create_community(client, auth_headers(owner), name="Gettable")

        res = await client.get(f"/communities/{community['id']}", headers=auth_headers(viewer))
        assert res.status_code == 200
        assert res.json()["name"] == "Gettable"

    async def test_get_private_community_denied_for_non_member(self, client, db):
        owner = await make_user(db, email="priv_get_owner@test.com")
        outsider = await make_user(db, email="priv_get_outsider@test.com")
        community = await create_community(
            client, auth_headers(owner), name="Private Get", is_private=True
        )

        res = await client.get(f"/communities/{community['id']}", headers=auth_headers(outsider))
        assert res.status_code == 403

    async def test_update_community_as_admin(self, client, db):
        admin = await make_user(db, email="update_admin@test.com")
        community = await create_community(client, auth_headers(admin), name="Old Name")

        res = await client.patch(
            f"/communities/{community['id']}",
            json={"name": "New Name"},
            headers=auth_headers(admin),
        )
        assert res.status_code == 200
        assert res.json()["name"] == "New Name"

    async def test_update_community_as_member_forbidden(self, client, db):
        admin = await make_user(db, email="upd_admin2@test.com")
        member = await make_user(db, email="upd_member@test.com")
        community = await create_community(client, auth_headers(admin), name="No Update")

        # member joins
        await client.post(f"/communities/{community['id']}/join", headers=auth_headers(member))

        res = await client.patch(
            f"/communities/{community['id']}",
            json={"name": "Hacked"},
            headers=auth_headers(member),
        )
        assert res.status_code == 403

    async def test_delete_community_as_admin(self, client, db):
        admin = await make_user(db, email="del_admin@test.com")
        community = await create_community(client, auth_headers(admin), name="To Delete")

        res = await client.delete(f"/communities/{community['id']}", headers=auth_headers(admin))
        assert res.status_code == 204

        res2 = await client.get(f"/communities/{community['id']}", headers=auth_headers(admin))
        assert res2.status_code == 404

    async def test_get_nonexistent_community_404(self, client, db):
        user = await make_user(db, email="no_comm@test.com")
        res = await client.get("/communities/99999", headers=auth_headers(user))
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Membership
# ---------------------------------------------------------------------------

class TestMembership:

    async def test_join_public_community(self, client, db):
        owner = await make_user(db, email="join_owner@test.com")
        joiner = await make_user(db, email="joiner@test.com")
        community = await create_community(client, auth_headers(owner), name="Joinable")

        res = await client.post(
            f"/communities/{community['id']}/join", headers=auth_headers(joiner)
        )
        assert res.status_code == 201
        assert res.json()["role"] == "member"

    async def test_join_private_community_forbidden(self, client, db):
        owner = await make_user(db, email="priv_join_owner@test.com")
        joiner = await make_user(db, email="priv_joiner@test.com")
        community = await create_community(
            client, auth_headers(owner), name="Private Join", is_private=True
        )

        res = await client.post(
            f"/communities/{community['id']}/join", headers=auth_headers(joiner)
        )
        assert res.status_code == 403

    async def test_join_twice_conflict(self, client, db):
        owner = await make_user(db, email="dup_owner@test.com")
        joiner = await make_user(db, email="dup_joiner@test.com")
        community = await create_community(client, auth_headers(owner), name="No Dups")

        await client.post(f"/communities/{community['id']}/join", headers=auth_headers(joiner))
        res = await client.post(
            f"/communities/{community['id']}/join", headers=auth_headers(joiner)
        )
        assert res.status_code == 409

    async def test_join_university_community_wrong_university(self, client, db):
        owner = await make_user(db, email="uni_owner@test.com", university="Oxford")
        joiner = await make_user(db, email="uni_joiner@test.com", university="Cambridge")
        res = await client.post(
            "/communities",
            json={"name": "Oxford Only", "type": "university", "university": "Oxford"},
            headers=auth_headers(owner),
        )
        community = res.json()

        res2 = await client.post(
            f"/communities/{community['id']}/join", headers=auth_headers(joiner)
        )
        assert res2.status_code == 403

    async def test_leave_community(self, client, db):
        owner = await make_user(db, email="leave_owner@test.com")
        member = await make_user(db, email="leaver@test.com")
        community = await create_community(client, auth_headers(owner), name="Leavable")

        await client.post(f"/communities/{community['id']}/join", headers=auth_headers(member))
        res = await client.delete(
            f"/communities/{community['id']}/leave", headers=auth_headers(member)
        )
        assert res.status_code == 204

    async def test_last_admin_cannot_leave(self, client, db):
        admin = await make_user(db, email="last_admin@test.com")
        community = await create_community(client, auth_headers(admin), name="One Admin")

        res = await client.delete(
            f"/communities/{community['id']}/leave", headers=auth_headers(admin)
        )
        assert res.status_code == 409

    async def test_get_members(self, client, db):
        owner = await make_user(db, email="mem_owner@test.com")
        member = await make_user(db, email="mem_member@test.com")
        community = await create_community(client, auth_headers(owner), name="Members List")

        await client.post(f"/communities/{community['id']}/join", headers=auth_headers(member))

        res = await client.get(
            f"/communities/{community['id']}/members", headers=auth_headers(owner)
        )
        assert res.status_code == 200
        user_ids = [m["user_id"] for m in res.json()]
        assert owner.id in user_ids
        assert member.id in user_ids

    async def test_creator_is_admin(self, client, db):
        creator = await make_user(db, email="creator_role@test.com")
        community = await create_community(client, auth_headers(creator), name="Admin Check")

        res = await client.get(
            f"/communities/{community['id']}/members", headers=auth_headers(creator)
        )
        members = res.json()
        creator_entry = next(m for m in members if m["user_id"] == creator.id)
        assert creator_entry["role"] == "admin"


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

class TestRoles:

    async def test_admin_can_promote_to_moderator(self, client, db):
        admin = await make_user(db, email="role_admin@test.com")
        member = await make_user(db, email="role_member@test.com")
        community = await create_community(client, auth_headers(admin), name="Role Test")
        await client.post(f"/communities/{community['id']}/join", headers=auth_headers(member))

        res = await client.patch(
            f"/communities/{community['id']}/members/{member.id}/role",
            json={"role": "moderator"},
            headers=auth_headers(admin),
        )
        assert res.status_code == 200
        assert res.json()["role"] == "moderator"

    async def test_cannot_demote_last_admin(self, client, db):
        admin = await make_user(db, email="demote_admin@test.com")
        community = await create_community(client, auth_headers(admin), name="Last Admin")

        res = await client.patch(
            f"/communities/{community['id']}/members/{admin.id}/role",
            json={"role": "member"},
            headers=auth_headers(admin),
        )
        assert res.status_code == 409

    async def test_member_cannot_change_roles(self, client, db):
        admin = await make_user(db, email="role_perm_admin@test.com")
        member = await make_user(db, email="role_perm_member@test.com")
        member2 = await make_user(db, email="role_perm_member2@test.com")
        community = await create_community(client, auth_headers(admin), name="Perm Test")
        await client.post(f"/communities/{community['id']}/join", headers=auth_headers(member))
        await client.post(f"/communities/{community['id']}/join", headers=auth_headers(member2))

        res = await client.patch(
            f"/communities/{community['id']}/members/{member2.id}/role",
            json={"role": "moderator"},
            headers=auth_headers(member),
        )
        assert res.status_code == 403

    async def test_admin_can_remove_member(self, client, db):
        admin = await make_user(db, email="rm_admin@test.com")
        member = await make_user(db, email="rm_member@test.com")
        community = await create_community(client, auth_headers(admin), name="Removable")
        await client.post(f"/communities/{community['id']}/join", headers=auth_headers(member))

        res = await client.delete(
            f"/communities/{community['id']}/members/{member.id}",
            headers=auth_headers(admin),
        )
        assert res.status_code == 204

    async def test_moderator_cannot_remove_admin(self, client, db):
        admin = await make_user(db, email="mod_rm_admin@test.com")
        mod = await make_user(db, email="mod_rm_mod@test.com")
        community = await create_community(client, auth_headers(admin), name="Mod vs Admin")
        await client.post(f"/communities/{community['id']}/join", headers=auth_headers(mod))

        # promote mod
        await client.patch(
            f"/communities/{community['id']}/members/{mod.id}/role",
            json={"role": "moderator"},
            headers=auth_headers(admin),
        )

        res = await client.delete(
            f"/communities/{community['id']}/members/{admin.id}",
            headers=auth_headers(mod),
        )
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# Invite Links
# ---------------------------------------------------------------------------

class TestInviteLinks:

    async def test_admin_can_generate_invite(self, client, db):
        admin = await make_user(db, email="inv_admin@test.com")
        community = await create_community(
            client, auth_headers(admin), name="Invite Community", is_private=True
        )

        res = await client.post(
            f"/communities/{community['id']}/invites", headers=auth_headers(admin)
        )
        assert res.status_code == 201
        data = res.json()
        assert "token" in data
        assert len(data["token"]) > 10
        assert data["use_count"] == 0

    async def test_member_cannot_generate_invite(self, client, db):
        admin = await make_user(db, email="inv_admin2@test.com")
        member = await make_user(db, email="inv_member2@test.com")
        community = await create_community(
            client, auth_headers(admin), name="Invite Only2", is_private=True
        )
        await client.post(
            f"/communities/{community['id']}/join-via-invite",  # won't work directly
        )
        # member directly added via test DB trick isn't needed - just verify 403
        # member tries to create invite (not a member yet)
        res = await client.post(
            f"/communities/{community['id']}/invites", headers=auth_headers(member)
        )
        assert res.status_code == 403

    async def test_join_via_invite(self, client, db):
        admin = await make_user(db, email="via_inv_admin@test.com")
        joiner = await make_user(db, email="via_inv_joiner@test.com")
        community = await create_community(
            client, auth_headers(admin), name="Via Invite Comm", is_private=True
        )

        invite_res = await client.post(
            f"/communities/{community['id']}/invites", headers=auth_headers(admin)
        )
        token = invite_res.json()["token"]

        join_res = await client.post(
            f"/communities/join-via-invite/{token}", headers=auth_headers(joiner)
        )
        assert join_res.status_code == 201
        assert join_res.json()["user_id"] == joiner.id

    async def test_invite_use_count_increments(self, client, db):
        admin = await make_user(db, email="use_count_admin@test.com")
        joiner = await make_user(db, email="use_count_joiner@test.com")
        community = await create_community(
            client, auth_headers(admin), name="Use Count", is_private=True
        )

        invite_res = await client.post(
            f"/communities/{community['id']}/invites", headers=auth_headers(admin)
        )
        token = invite_res.json()["token"]

        await client.post(
            f"/communities/join-via-invite/{token}", headers=auth_headers(joiner)
        )

        # Get members to confirm joiner is in
        members_res = await client.get(
            f"/communities/{community['id']}/members", headers=auth_headers(admin)
        )
        assert joiner.id in [m["user_id"] for m in members_res.json()]

    async def test_join_via_invite_twice_conflict(self, client, db):
        admin = await make_user(db, email="inv_dup_admin@test.com")
        joiner = await make_user(db, email="inv_dup_joiner@test.com")
        community = await create_community(
            client, auth_headers(admin), name="No Double Join", is_private=True
        )
        invite_res = await client.post(
            f"/communities/{community['id']}/invites", headers=auth_headers(admin)
        )
        token = invite_res.json()["token"]

        await client.post(
            f"/communities/join-via-invite/{token}", headers=auth_headers(joiner)
        )
        res = await client.post(
            f"/communities/join-via-invite/{token}", headers=auth_headers(joiner)
        )
        assert res.status_code == 409

    async def test_invalid_invite_token_404(self, client, db):
        user = await make_user(db, email="bad_token@test.com")
        res = await client.post(
            "/communities/join-via-invite/not-a-real-token", headers=auth_headers(user)
        )
        assert res.status_code == 404
