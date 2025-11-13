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


def test_update_user_stats():
    from app.main import app

    client = TestClient(app)
    # test that trying to update the stats of a user who is not in the table gives error
    res4 = client.put("/stats/update_user_stats", json={"user_id": str(uuid.uuid4())})
    assert res4.status_code == 404
    assert "User not found" in res4.json()["detail"]

    # create a new user so we can test successful updates
    res_create = client.post("/stats/create_user_stats", json=MOCK_USER)
    assert res_create.status_code == 200
    data_create = res_create.json()
    assert data_create["success"] is True

    # test successful increment of count-based stats
    res5 = client.put(
        "/stats/update_user_stats",
        json={
            "user_id": MOCK_USER["id"],
            "num_wins": 2,
            "num_solo_games": 1,
            "num_competition_games": 3,
        },
    )
    assert res5.status_code == 200
    data5 = res5.json()
    assert data5["success"] is True
    updated_data = data5["updated_data"][0]
    assert updated_data["num_wins"] >= 2
    assert updated_data["num_solo_games"] >= 1
    assert updated_data["num_competition_games"] >= 3

    # test that updating with a worse fastest time does not change it
    res6 = client.put(
        "/stats/update_user_stats",
        json={
            "user_id": MOCK_USER["id"],
            "fastest_solo_time": 100.0,  # deliberately worse
        },
    )
    assert res6.status_code == 200
    data6 = res6.json()
    # Depending on implementation, could be either "no better stats" or no update
    assert data6["success"] is False or "No better stats" in data6.get("message", "")

    # test that a better (smaller) fastest_solo_time updates correctly
    res7 = client.put(
        "/stats/update_user_stats",
        json={"user_id": MOCK_USER["id"], "fastest_solo_time": 5.0},
    )
    assert res7.status_code == 200
    data7 = res7.json()
    assert data7["success"] is True
    updated_time = data7["updated_data"][0].get("fastest_solo_time")
    assert updated_time == 5.0

    # test missing user_id gives 400 error
    res8 = client.put("/stats/update_user_stats", json={})
    assert res8.status_code == 400
    assert "Missing required field" in res8.json()["detail"]

    # test streak logic - simulate playing on consecutive days
    from datetime import datetime, timedelta

    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    today = datetime.now().isoformat()

    res9 = client.put(
        "/stats/update_user_stats",
        json={"user_id": MOCK_USER["id"], "dt_last_seen": yesterday},
    )
    assert res9.status_code == 200
    assert res9.json()["success"] is True

    # next day - should increment streak
    res10 = client.put(
        "/stats/update_user_stats",
        json={"user_id": MOCK_USER["id"], "dt_last_seen": today},
    )
    assert res10.status_code == 200
    data10 = res10.json()
    assert data10["success"] is True
    updated_streak = data10["updated_data"][0].get("streak_count")
    assert updated_streak >= 1
