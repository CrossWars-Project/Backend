# app/db.py
import os
from supabase import create_client

_supabase_instance = None


def get_supabase():
    """Return either the real or mock Supabase client based on environment."""
    global _supabase_instance
    if _supabase_instance:
        return _supabase_instance

    if os.getenv("TESTING") == "1":
        print("Using MockSupabase")
        from tests.mocks.mock_supabase import MockSupabase

        _supabase_instance = MockSupabase()
    else:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("Missing Supabase credentials in environment.")
        _supabase_instance = create_client(url, key)

    return _supabase_instance
