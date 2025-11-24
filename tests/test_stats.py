# tests/test_stats.py
import pytest
import uuid
from fastapi.testclient import TestClient

# Mock user data
MOCK_USER = {"id": str(uuid.uuid4()), "display_name": "Test User 1"}


def _make_auth_user_for_mock(mock_id: str, display_name: str = "Test User"):
    """
    return the shape of current_user returned by app.auth.get_current_user
    (adjust fields as needed by your auth implementation)
    """
    return {
        "user_id": mock_id,
        "username": display_name,
        "email": f"{mock_id[:8]}@example.com",
    }


def test_create_user_stats_creates_entry_and_gets_saved():
    from app.main import app
    from app.auth import get_current_user

    # Override auth to return our MOCK_USER
    app.dependency_overrides[get_current_user] = lambda: _make_auth_user_for_mock(
        MOCK_USER["id"], MOCK_USER["display_name"]
    )

    client = TestClient(app)

    # Ensure no existing stats for this mock user
    res = client.get(f"/stats/get_user_stats/{MOCK_USER['id']}")
    assert res.status_code == 200
    data = res.json()
    assert data["exists"] is False

    # Create stats (authenticated)
    res2 = client.post("/stats/create_user_stats", json=MOCK_USER)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["success"] is True

    inserted = data2["data"][0]
    assert inserted["user_id"] == MOCK_USER["id"]
    # display name from body or fallback to username should be present
    assert inserted["display_name"] == MOCK_USER["display_name"]

    # Now a GET should show the record exists
    res3 = client.get(f"/stats/get_user_stats/{MOCK_USER['id']}")
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["exists"] is True
    assert data3["data"][0]["display_name"] == MOCK_USER["display_name"]

    # Clear overrides after test
    app.dependency_overrides.clear()


def test_update_user_stats_user_not_found_for_authenticated_user():
    from app.main import app
    from app.auth import get_current_user

    # Use a different auth user id that has no stats row -> should return 404
    random_user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: _make_auth_user_for_mock(
        random_user_id, "NoStatsUser"
    )

    client = TestClient(app)

    res = client.put("/stats/update_user_stats", json={"num_wins": 1})
    assert res.status_code == 404
    assert "User not found" in res.json()["detail"]

    app.dependency_overrides.clear()


def test_update_user_stats_successful_updates_and_times_logic():
    from app.main import app
    from app.auth import get_current_user
    from datetime import datetime, timedelta

    # Ensure auth is our MOCK_USER
    app.dependency_overrides[get_current_user] = lambda: _make_auth_user_for_mock(
        MOCK_USER["id"], MOCK_USER["display_name"]
    )

    client = TestClient(app)

    # Make sure user exists
    res_create = client.post("/stats/create_user_stats", json=MOCK_USER)
    assert res_create.status_code == 200
    assert res_create.json()["success"] is True

    # Increment counts and set a fastest time
    res5 = client.put(
        "/stats/update_user_stats",
        json={
            "num_wins": 2,
            "num_solo_games": 1,
            "num_competition_games": 3,
            "fastest_solo_time": 70,
        },
    )
    assert res5.status_code == 200
    data5 = res5.json()
    assert data5["success"] is True
    updated_data = data5["updated_data"][0]
    assert updated_data["num_wins"] >= 2
    assert updated_data["num_solo_games"] >= 1
    assert updated_data["num_competition_games"] >= 3
    assert updated_data["fastest_solo_time"] == 70

    # Updating with a worse fastest time should not change it
    res6 = client.put(
        "/stats/update_user_stats",
        json={
            "fastest_solo_time": 100.0,  # worse
        },
    )
    assert res6.status_code == 200
    data6 = res6.json()
    assert data6["success"] is False or "No better stats" in data6.get("message", "")

    # A better (smaller) fastest time should update
    res7 = client.put(
        "/stats/update_user_stats",
        json={"fastest_solo_time": 5.0},
    )
    assert res7.status_code == 200
    data7 = res7.json()
    assert data7["success"] is True
    updated_time = data7["updated_data"][0].get("fastest_solo_time")
    assert updated_time == 5.0

    # Test streak logic
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    today = datetime.now().isoformat()

    res9 = client.put("/stats/update_user_stats", json={"dt_last_seen": yesterday})
    assert res9.status_code == 200
    assert res9.json()["success"] is True

    res10 = client.put("/stats/update_user_stats", json={"dt_last_seen": today})
    assert res10.status_code == 200
    data10 = res10.json()
    assert data10["success"] is True
    updated_streak = data10["updated_data"][0].get("streak_count")
    assert updated_streak >= 1

    app.dependency_overrides.clear()


def test_unauthenticated_requests_are_rejected_with_401():
    from app.main import app

    # Ensure no auth override -> dependency will look for Authorization header and fail
    app.dependency_overrides.clear()
    client = TestClient(app)

    # calling create endpoint without auth should return 401
    res = client.post("/stats/create_user_stats", json=MOCK_USER)
    assert res.status_code == 401

    # calling update endpoint without auth should return 401
    res2 = client.put("/stats/update_user_stats", json={"num_wins": 1})
    assert res2.status_code == 401
