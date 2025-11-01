import pytest
import asyncio
from fastapi import HTTPException
from fastapi.testclient import TestClient
import supabase
from app.main import app
from app.auth import get_current_user, get_current_user_optional
from app.db import get_supabase

client = TestClient(app)

#Testing formula 
    #def test_[function_name]_[scenario]_[expected_outcome](self):
    #Test description explaining WHY this test matters
    
    # 1. ARRANGE (Setup)
    # - Set up test data
    # - Configure mocks
    # - Prepare inputs
        #supabase = get_supabase()
        #supabase.auth.add_user("token", "user_id", "email", "username")  # Setup valid user
    
    # 2. ACT (Execute) 
    # - Call the function being tested
    # - Perform the action
 
        # For functions that should SUCCEED:
        # result = asyncio.run(get_current_user("Bearer valid_token"))

        # For functions that should FAIL:
        # with pytest.raises(HTTPException) as exc_info:
        #     asyncio.run(get_current_user("Bearer invalid_token"))

        # For HTTP endpoints:
        # response = client.get("/endpoint", headers={"Authorization": "Bearer token"})

    
    # 3. ASSERT (Verify)
    # - Check the results match expectations
    # - Verify side effects
    # - Confirm error handling
        # Success scenarios:
        #assert result["user_id"] == "expected_id"
        #assert result["email"] == "expected@email.com"

        # Failure scenarios:
        #assert exc_info.value.status_code == 401  # Correct HTTP status
        #assert "expected error message" in exc_info.value.detail

        # HTTP responses:
        #assert response.status_code == 200
        #assert response.json()["key"] == "expected_value"

class TestAuth:
    """ Test authentication functions """
    def setup_method(self):
        """Reset mock before each test"""
        supabase = get_supabase()
        supabase.reset()

    def test_get_current_user_no_header(self):
        """Test to verify security of get_current_user function"""
        with pytest.raises(HTTPException) as exc_info:
            #simulate unauth user being bassed to get user
            asyncio.run(get_current_user(None))
        
        #verify unauth user is blocked
        assert exc_info.value.status_code == 401
        assert "Authorization header missing" in exc_info.value.detail

    def test_get_current_user_bad_token(self):
        """Test to verify invalid tokens arent accepted"""

        with pytest.raises(HTTPException) as exc_info:
            #simulate invalid token being passed to get user
            asyncio.run(get_current_user("Bearer invalid_token"))
        #veryify invalid token is blocked
        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail
    def test_get_current_user_valid_token(self):
        """Ensure valid tokens are accepted and correct user info is returned"""

        #setup valid user in mock supabase
        supabase = get_supabase()
        supabase.auth.add_user("valid_token", "user_123", "test@example.com", "testuser")

        #call auth with valid token
        result = asyncio.run(get_current_user("Bearer valid_token"))

        #verify correct user info is returned
        assert result["user_id"] == "user_123"
        assert result["email"] == "test@example.com"
        assert result["username"] == "testuser"
    
    def test_get_current_user_optional_guest(self):
        """Ensure guest users are accepted in optional"""

        #call optional auth with no header
        result = asyncio.run(get_current_user_optional(None))

        #verify None is returned for guest user
        assert result is None

    def test_get_current_user_optional_auth_user(self):
        """Ensure logged in users are accepted in optional"""

        #setup valid user in mock supabase
        supabase = get_supabase()
        supabase.auth.add_user("valid_token", "user_456", "test2@example.com", "testuser2")

        result = asyncio.run(get_current_user_optional('Bearer valid_token'))

        #verify info
        assert result["user_id"] == "user_456"
        assert result["email"] == "test2@example.com"
        assert result["username"] == "testuser2"
    
    def test_get_current_user_optional_invalid_token(self):
        """Ensure invalid tokens return None in optional"""
        """Ensure users with fake auth only have guest status"""

        result = asyncio.run(get_current_user_optional('Bearer invalid_token'))

        #verify None is returned for invalid token
        assert result is None

class TokenTests:
    def setup_method(self):
        """Reset mock before each test"""
        supabase = get_supabase()
        supabase.reset()

    def test_malformed_bearer_token(self):
        """Ensure malformed bearer tokens are handled properly"""

        '''
        EDGE CASES TO TEST:
        - "Bearer" without space
        - "bearer" lowercase  
        - Multiple spaces
        - No "Bearer" prefix
        - Empty token after "Bearer"
        '''

        test_cases = [
            "Bearerbadtoken", #without space
            "bearer token111", #lowercase
            "Bearer  token111", #multiple spaces
            "token111", #no prefix
            "Bearer ", #empty token
            "" #completely empty
        ]

        for malformed_header in test_cases:
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_current_user(malformed_header))

            #malformed headers should return an error
            assert exc_info.value.status_code == 401
    def test_jwt_token(self):
        """Ensure JWT tokens are processed correctly, special characters should be accepted"""

        jwt_style_token = "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMTIzIn0.hash-signature"

        supabase = get_supabase()
        supabase.auth.add_user(jwt_style_token, "user_jwt", "jwt@example.com", "jwtuser")

        result = asyncio.run(get_current_user(f"Bearer {jwt_style_token}"))

        assert result["user_id"] == "user_jwt"

class TestSecurity:
    #TODO: add after logout test

    def test_sql_injection_in_token(self):
        """Ensure SQL injection through tokens fail"""
        evil_tokens = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "<script>alert('xss')</script>",
            "../../../etc/passwd",
            "valid_token'; SELECT * FROM users; --"
        ]

        for evil_token in evil_tokens:
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_current_user(f"Bearer {evil_token}"))

            #injection attempts should be blocked
            assert exc_info.value.status_code == 401

