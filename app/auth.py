# Authentication dependency using Supabase JWT tokens
from fastapi import Header, HTTPException, status
from db import supabase
from typing import Optional


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Verify the Supabase JWT token and return the user info.
    This will be used as a dependency in your protected routes.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    try:
        # Remove 'Bearer ' prefix from token
        token = authorization.replace("Bearer ", "").strip()

        # Verify token with Supabase
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        return {
            "user_id": user_response.user.id,
            "username": user_response.user.user_metadata.get("username"),
            "email": user_response.user.email,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )


# TODO: on the front end side, make sure to include the JWT token in the Authorization
