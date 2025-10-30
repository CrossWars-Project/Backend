# tests/test_stats.py
import pytest
import uuid
from fastapi.testclient import TestClient

# Mock user data
MOCK_USER = {"id": str(uuid.uuid4()), "display_name": "Test User 1"}


def test_create_user_stats_creates_entry():
    from app.main import app

    client = TestClient(app)

    # if I have not yet put the user in the db, I should not find it in the db
    res = client.get(f"/stats/get_user_stats/{MOCK_USER['id']}")
    assert res.status_code == 200
    data = res.json()
    assert data["exists"] is False
    assert data["data"] == []

    # test successful post. 
    res2 = client.post("/stats/create_user_stats", json=MOCK_USER)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["success"] is True

    # check that the inserted post contains the id and display_name I inserted
    inserted = data2["data"][0]
    assert inserted["user_id"] == MOCK_USER["id"]
    assert inserted["display_name"] == MOCK_USER["display_name"]

    # test successful get. now that user is inserted, I should get back their user when I make a get request
    res3 = client.get(f"/stats/get_user_stats/{MOCK_USER['id']}")
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["exists"] is True
    assert data3["data"][0]["display_name"] == MOCK_USER["display_name"]
