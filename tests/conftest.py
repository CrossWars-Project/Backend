import pytest

@pytest.fixture(autouse=True)
def set_testing_env(monkeypatch):
    """
    Automatically set TESTING=1 for all tests so that the
    Supabase factory loads the mock client instead of the real one. See app/db.py for why this logic matters.
    """
    monkeypatch.setenv("TESTING", "1")
