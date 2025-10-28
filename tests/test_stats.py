import pytest
import uuid
from tests.mocks.mock_supabase import mock_supabase

# Mock user data
MOCK_USER = {"id": str(uuid.uuid4()), "display_name": "Test User 1"}


def test_create_user_stats_creates_entry(mock_supabase):
    # import is here so that we use the mocked supabase instead of the real one. must import
    # main after we have already mocked supabase.
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # make sure we do not get a user that has not yer been added to the table
    res = client.get(f"/stats/get_user_stats/{MOCK_USER['id']}")
    assert res.status_code == 200
    data = res.json()
    assert data["exists"] is False
    assert data["data"] == []

    # Test POST /stats/create_user_stats, make sure we are inserting a new user as expected
    res2 = client.post("/stats/create_user_stats", json=MOCK_USER)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["success"] is True
    # Inserted row is first in the list
    inserted = data2["data"][0]
    assert inserted["user_id"] == MOCK_USER["id"]
    assert inserted["display_name"] == MOCK_USER["display_name"]

    # Test GET /stats/get_user_stats/{user_id}, make sure we are retrieving the user we just added
    res3 = client.get(f"/stats/get_user_stats/{MOCK_USER['id']}")
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["exists"] is True
    assert data3["data"][0]["display_name"] == MOCK_USER["display_name"]
