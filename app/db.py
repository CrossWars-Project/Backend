# connect to supabase and centralize client creation
# things are simple here to allow for easy testing overrides
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from fastapi import Depends

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # secure, backend-only
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

supabase_service: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
# grant admin privileges for backend operations including testing


def get_supaabase_client(user_token: str | None = None) -> Client:
    # helpful for integration tests
    """Returns a Supabase client. If a user token is provided, it creates a client with that token for user-specific operations."""
    key = SUPABASE_ANON_KEY or SUPABASE_SERVICE_KEY
    client = create_client(SUPABASE_URL, key)
    if user_token:
        client.auth.set_auth(user_token)
    return client


def get_supabase_client_dep(authorization: str | None = None) -> Client:
    """Dependency function to get a Supabase client with optional user authorization token."""
    # allows us to add correct and valid user to routes that need it
    user_token = None
    # TODO: might need changed based on header form to get just the token
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer":
            user_token = token
    return get_supaabase_client(user_token)


supabase = supabase_service
