from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.auth import get_current_user, get_current_user_optional
from app.db import get_supabase

client = TestClient(app)

class TestAuth:
    """Tests for authentication"""
    '''TODO:
        [] test supabase setup
        [] test get_current_user with valid token
        [] test get_current_user with invalid token
        [] test get_current_user_optional
    '''