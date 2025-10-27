import pytest
from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

MOCK_USER = {"id": str(uuid.uuid4()), "display_name": "Test User 1"}


def test_create_user_stats_creates_entry(monkeypatch):
    """
    Test that create user stats posts a new entry to the stats table in DB and that
    the data is retrieved as expected (display name and user id match, stats are default stats)
    """
    # ensure successful post
    res = client.post("/stats/create_user_stats", json=MOCK_USER)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    inserted = data["data"][0]  # <- first item in the list
    assert inserted["user_id"] == MOCK_USER["id"]
    assert inserted["display_name"] == MOCK_USER["display_name"]

    # ensure the get behaves correctly
    res2 = client.get(f"/stats/get_user_stats/{MOCK_USER['id']}")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["exists"] is True
    assert data2["data"][0]["display_name"] == MOCK_USER["display_name"]
