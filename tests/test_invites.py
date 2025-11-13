from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.auth import get_current_user, get_current_user_optional
from app.db import get_supabase

client = TestClient(app)


class TestInvites:
    """Test invites routes and logic"""

    def setup_method(self):
        """Reset mock before each test"""
        supabase = get_supabase()
        supabase.reset()

    # // Create Invite Tests ///
    def test_create_invite_auth_user(self):
        """Ensure logged-in users can create invites"""

        # Setup valid user in mock supabase
        supabase = get_supabase()
        supabase.auth.add_user("valid_token", "user_111", "u1@example.com", "testuser")

        # Call create_invite endpoint
        response = client.post(
            "/invites/create", headers={"Authorization": "Bearer valid_token"}
        )

        # Verify invite creation succeeded
        assert response.status_code == 200
        assert response.json()["success"] == True
        assert "invite_token" in response.json()
        assert "battle_id" in response.json()
        print("Invite Token:", response.json()["invite_token"])

    def test_create_invite_invalid_token(self):
        """Test invite creation with invalid token"""
        response = client.post(
            "/invites/create", headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
        error_detail = response.json().get("detail", "")
        assert "Invalid or expired token" in error_detail

    def test_create_invite_guest_user(self):
        """Ensure guest users cannot create invites"""

        response = client.post("/invites/create")  # No auth header

        assert response.status_code == 401
        error_detail = response.json().get("detail", "")
        assert "Authorization header missing" in error_detail

    # // Accept Invite Tests ///

    def test_accept_invite_guest_user(self):
        """Test that guest users can accept invites"""
        # Setup valid inviter and invitee users in mock supabase
        supabase = get_supabase()
        supabase.auth.add_user(
            "inviter_aut_token", "user_222", "inviter@example.com", "inviter"
        )

        # Create an invite to accept
        create_response = client.post(
            "/invites/create", headers={"Authorization": "Bearer inviter_aut_token"}
        )
        assert create_response.status_code == 200
        invite_token = create_response.json()["invite_token"]
        battle_id = create_response.json()["battle_id"]
        print("Invite Token to Accept:", invite_token)

        # Accept the invite as the guest
        accept_response = client.post(f"/invites/accept/{invite_token}")
        assert accept_response.status_code == 200
        assert accept_response.json()["success"] == True
        assert accept_response.json()["battle_id"] == battle_id
        assert accept_response.json()["is_guest"] == True

    def test_battle_updated_on_guest_accept(self):
        """Test that battle is updated correctly when a guest accepts an invite"""
        # Setup valid inviter user in mock supabase
        supabase = get_supabase()
        supabase.auth.add_user(
            "inviter_token", "user_555", "inviter@example.com", "inviter"
        )

        # Create an invite to accept
        create_response = client.post(
            "/invites/create", headers={"Authorization": "Bearer inviter_token"}
        )
        assert create_response.status_code == 200
        invite_token = create_response.json()["invite_token"]
        battle_id = create_response.json()["battle_id"]

        # Accept the invite as the guest
        accept_response = client.post(f"/invites/accept/{invite_token}")
        assert accept_response.status_code == 200

        # Verify that the battle record has been updated correctly
        battles_response = (
            supabase.table("battles").select("*").eq("id", battle_id).execute()
        )
        assert battles_response.data[0]["player2_id"] is None
        assert battles_response.data[0]["player2_is_guest"] == True
        assert battles_response.data[0]["status"] == "READY"

    def test_accept_invite_auth_user(self):
        """Test that logged-in user is able to accept invite"""
        # Setup valid inviter and invitee users in mock supabase
        supabase = get_supabase()
        supabase.auth.add_user(
            "inviter_aut_token", "user_222", "inviter@example.com", "inviter"
        )
        supabase.auth.add_user(
            "invitee_aut_token", "user_333", "invitee@example.com", "invitee"
        )

        # Create an invite to accept
        create_response = client.post(
            "/invites/create", headers={"Authorization": "Bearer inviter_aut_token"}
        )
        assert create_response.status_code == 200
        invite_token = create_response.json()["invite_token"]
        battle_id = create_response.json()["battle_id"]
        print("Invite Token to Accept:", invite_token)

        # Accept the invite as the invitee
        accept_response = client.post(
            f"/invites/accept/{invite_token}",
            headers={"Authorization": "Bearer invitee_aut_token"},
        )
        assert accept_response.status_code == 200
        assert accept_response.json()["success"] == True
        assert accept_response.json()["battle_id"] == battle_id
        assert accept_response.json()["is_guest"] == False

    def test_battle_updated_on_auth_accept(self):
        """Test that battle is updated correctly when an auth user accepts an invite"""
        # Setup valid inviter and invitee users in mock supabase
        supabase = get_supabase()
        supabase.auth.add_user(
            "inviter_token", "user_666", "inviter@example.com", "inviter"
        )
        supabase.auth.add_user(
            "invitee_token", "user_777", "invitee@example.com", "invitee"
        )

        # Create an invite to accept
        create_response = client.post(
            "/invites/create", headers={"Authorization": "Bearer inviter_token"}
        )
        assert create_response.status_code == 200
        invite_token = create_response.json()["invite_token"]
        battle_id = create_response.json()["battle_id"]

        # Accept the invite as the invitee
        accept_response = client.post(
            f"/invites/accept/{invite_token}",
            headers={"Authorization": "Bearer invitee_token"},
        )
        assert accept_response.status_code == 200

        # Verify that the battle record has been updated correctly
        battles_response = (
            supabase.table("battles").select("*").eq("id", battle_id).execute()
        )
        assert battles_response.data[0]["player2_id"] == "user_777"
        assert battles_response.data[0]["player2_is_guest"] == False
        assert battles_response.data[0]["status"] == "READY"

    def test_accept_self_invite(self):
        """Test that users cannot accept their own invites"""
        # Setup valid user in mock supabase
        supabase = get_supabase()
        supabase.auth.add_user("inviter_token", "user_444", "self@example.com", "self")

        # Create an invite to accept
        create_response = client.post(
            "/invites/create", headers={"Authorization": "Bearer inviter_token"}
        )
        assert create_response.status_code == 200  # Ensure invite creation succeeded
        invite_token = create_response.json()["invite_token"]
        print("Invite Token to Accept:", invite_token)

        # Accept the invite as the inviter
        accept_response = client.post(
            f"/invites/accept/{invite_token}",
            headers={"Authorization": "Bearer inviter_token"},
        )
        assert accept_response.status_code == 400
        error_detail = accept_response.json().get("detail", "")
        assert "Cannot accept your own invite." in error_detail

    def test_accept_invite_invalid_token(self):
        """Test auth accepting invite with invalid token"""
        # Setup valid inviter and invitee users in mock supabase
        supabase = get_supabase()
        supabase.auth.add_user(
            "inviter_aut_token", "user_222", "inviter@example.com", "inviter"
        )
        supabase.auth.add_user(
            "invitee_aut_token", "user_333", "invitee@example.com", "invitee"
        )

        # Create an invite to accept
        create_response = client.post(
            "/invites/create", headers={"Authorization": "Bearer inviter_aut_token"}
        )
        assert create_response.status_code == 200

        bad_invite_token = "invalid_token"
        accept_response = client.post(
            f"/invites/accept/{bad_invite_token}",
            headers={"Authorization": "Bearer invitee_aut_token"},
        )
        assert accept_response.status_code == 404
        error_detail = accept_response.json().get("detail", "")
        assert "Could not find invite." in error_detail

    def test_accept_invite_expired(self):
        """Test accepting an expired invite"""
        # Setup valid inviter and invitee users in mock supabase
        supabase = get_supabase()
        supabase.auth.add_user(
            "inviter_aut_token", "user_222", "inviter@example.com", "inviter"
        )
        supabase.auth.add_user(
            "invitee_aut_token", "user_333", "invitee@example.com", "invitee"
        )

        # Create an invite to accept
        create_response = client.post(
            "/invites/create", headers={"Authorization": "Bearer inviter_aut_token"}
        )
        assert create_response.status_code == 200
        invite_token = create_response.json()["invite_token"]
        print("Invite Token to Accept:", invite_token)

        # Manually expire the invite in the mock supabase
        supabase.table("invites").update({"expires_at": "2000-01-01T00:00:00"}).eq(
            "invite_token", invite_token
        ).execute()

        # Accept the invite as the invitee
        accept_response = client.post(
            f"/invites/accept/{invite_token}",
            headers={"Authorization": "Bearer invitee_aut_token"},
        )

        assert accept_response.status_code == 400
        error_detail = accept_response.json().get("detail", "")
        assert "Invite has expired." in error_detail

    def test_accept_invite_concurrency_protection_two_guests(self):
        """Test that two guests trying to accept the same invite - only first succeeds"""
        # Setup valid inviter
        supabase = get_supabase()
        supabase.auth.add_user(
            "inviter_token", "user_111", "inviter@example.com", "inviter"
        )

        # Create an invite
        create_response = client.post(
            "/invites/create", headers={"Authorization": "Bearer inviter_token"}
        )
        assert create_response.status_code == 200
        invite_token = create_response.json()["invite_token"]

        # First guest accepts (should succeed)
        accept_response1 = client.post(f"/invites/accept/{invite_token}")
        assert accept_response1.status_code == 200
        assert accept_response1.json()["success"] == True
        assert accept_response1.json()["is_guest"] == True

        # Second guest tries to accept same invite (should fail due to concurrency)
        accept_response2 = client.post(f"/invites/accept/{invite_token}")
        assert accept_response2.status_code == 409
        error_detail = accept_response2.json().get("detail", "")
        assert "Invite has already been accepted by another user." in error_detail

    def test_accept_invite_concurrency_protection_guest_then_auth(self):
        """Test guest accepts first, then auth user tries - should fail"""
        # Setup users
        supabase = get_supabase()
        supabase.auth.add_user(
            "inviter_token", "user_111", "inviter@example.com", "inviter"
        )
        supabase.auth.add_user(
            "auth_user_token", "user_222", "auth@example.com", "authuser"
        )

        # Create invite
        create_response = client.post(
            "/invites/create", headers={"Authorization": "Bearer inviter_token"}
        )
        assert create_response.status_code == 200
        invite_token = create_response.json()["invite_token"]

        # Guest accepts first
        accept_response1 = client.post(f"/invites/accept/{invite_token}")
        assert accept_response1.status_code == 200
        assert accept_response1.json()["is_guest"] == True

        # Auth user tries to accept (should fail)
        accept_response2 = client.post(
            f"/invites/accept/{invite_token}",
            headers={"Authorization": "Bearer auth_user_token"},
        )
        assert accept_response2.status_code == 409
        error_detail = accept_response2.json().get("detail", "")
        assert "Invite has already been accepted by another user." in error_detail

    def test_accept_invite_concurrency_protection_auth_then_guest(self):
        """Test auth user accepts first, then guest tries - should fail"""
        # Setup users
        supabase = get_supabase()
        supabase.auth.add_user(
            "inviter_token", "user_111", "inviter@example.com", "inviter"
        )
        supabase.auth.add_user(
            "auth_user_token", "user_222", "auth@example.com", "authuser"
        )

        # Create invite
        create_response = client.post(
            "/invites/create", headers={"Authorization": "Bearer inviter_token"}
        )
        assert create_response.status_code == 200
        invite_token = create_response.json()["invite_token"]

        # Auth user accepts first
        accept_response1 = client.post(
            f"/invites/accept/{invite_token}",
            headers={"Authorization": "Bearer auth_user_token"},
        )
        assert accept_response1.status_code == 200
        assert accept_response1.json()["is_guest"] == False

        # Guest tries to accept (should fail)
        accept_response2 = client.post(f"/invites/accept/{invite_token}")
        assert accept_response2.status_code == 409
        error_detail = accept_response2.json().get("detail", "")
        assert "Invite has already been accepted by another user." in error_detail

    def test_accept_invite_concurrency_protection_two_auth_users(self):
        """Test two different auth users trying to accept same invite"""
        # Setup users
        supabase = get_supabase()
        supabase.auth.add_user(
            "inviter_token", "user_111", "inviter@example.com", "inviter"
        )
        supabase.auth.add_user(
            "auth_user1_token", "user_222", "auth1@example.com", "authuser1"
        )
        supabase.auth.add_user(
            "auth_user2_token", "user_333", "auth2@example.com", "authuser2"
        )

        # Create invite
        create_response = client.post(
            "/invites/create", headers={"Authorization": "Bearer inviter_token"}
        )
        assert create_response.status_code == 200
        invite_token = create_response.json()["invite_token"]

        # First auth user accepts
        accept_response1 = client.post(
            f"/invites/accept/{invite_token}",
            headers={"Authorization": "Bearer auth_user1_token"},
        )
        assert accept_response1.status_code == 200
        assert accept_response1.json()["is_guest"] == False

        # Second auth user tries to accept (should fail)
        accept_response2 = client.post(
            f"/invites/accept/{invite_token}",
            headers={"Authorization": "Bearer auth_user2_token"},
        )
        assert accept_response2.status_code == 409
        error_detail = accept_response2.json().get("detail", "")
        assert "Invite has already been accepted by another user." in error_detail
