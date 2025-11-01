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
    
    def test_create_invite_auth_user(self):
        """Ensure logged-in users can create invites"""

        #Setup valid user in mock supabase
        supabase = get_supabase()
        supabase.auth.add_user("valid_token", "user_111", "u1@example.com", "testuser")

        # Call create_invite endpoint
        response = client.post("/invites/create", headers={"Authorization": "Bearer valid_token"})

        # Verify invite creation succeeded
        assert response.status_code == 200
        assert response.json()["success"] == True
        print("Invite Token:", response.json()["invite_token"])

    def test_create_invite_invalid_token(self):
        """Test invite creation with invalid token"""
        response = client.post(
            "/invites/create", 
            headers={"Authorization": "Bearer invalid_token"}
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
    
