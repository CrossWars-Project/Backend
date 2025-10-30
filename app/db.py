import os
from supabase import create_client

"""
this is a factory which returns a mock supabase for testing or the real supabase for production
"""


def get_supabase():
    """Return either the real or mock Supabase client based on environment."""
    if os.getenv("TESTING") == "1":
        print("Using MockSupabase")
        from tests.mocks.mock_supabase import MockSupabase

        return MockSupabase()
    else:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("Missing Supabase credentials in environment.")
        return create_client(url, key)


supabase = get_supabase()
