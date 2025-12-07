# tests/test_stats.py
from datetime import datetime, timedelta
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


@pytest.fixture(autouse=True)
def clear_overrides():
    """
    Ensure dependency overrides are cleared before and after each test to avoid
    leaking mocked auth between tests.
    """
    from app.main import app

    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


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


def test_create_user_stats_when_stats_already_exist_returns_existing_row():
    from app.main import app
    from app.auth import get_current_user

    # 1. Mock authentication for our test user
    test_user_id = MOCK_USER["id"]
    app.dependency_overrides[get_current_user] = lambda: _make_auth_user_for_mock(
        test_user_id, MOCK_USER["display_name"]
    )

    client = TestClient(app)

    # 2. First create call → should insert successfully
    res1 = client.post("/stats/create_user_stats", json=MOCK_USER)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["success"] is True

    # Normalize data1["data"] into a dict
    initial_row = data1["data"]
    if isinstance(initial_row, list):  # backend sometimes wraps in list?
        initial_row = initial_row[0]

    # 3. Second create call → SHOULD NOT ERROR, SHOULD RETURN EXISTING ROW
    res2 = client.post("/stats/create_user_stats", json=MOCK_USER)
    assert res2.status_code == 200
    data2 = res2.json()

    assert data2["success"] is True
    assert "already" in data2.get("message", "").lower()

    # Normalize result again
    returned_row = data2["data"]
    if isinstance(returned_row, list):
        returned_row = returned_row[0]

    # Validate same user
    assert returned_row["user_id"] == initial_row["user_id"]
    assert returned_row["display_name"] == initial_row["display_name"]

    # Ensure no duplicates exist
    res3 = client.get(f"/stats/get_user_stats/{test_user_id}")
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["exists"] is True

    # Should contain *exactly* 1 row
    rows = data3["data"]
    assert isinstance(rows, list)
    assert len(rows) == 1


def test_update_user_stats_user_not_found_for_authenticated_user():
    from app.main import app
    from app.auth import get_current_user

    # Use a different auth user id that has no stats row -> should return 404
    random_user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: _make_auth_user_for_mock(
        random_user_id, "NoStatsUser"
    )

    client = TestClient(app)

    res = client.put("/stats/update_user_stats", json={"num_wins_battle": 1})
    assert res.status_code == 404
    assert "User not found" in res.json()["detail"]


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

    # Increment counts and set a fastest solo time
    res5 = client.put(
        "/stats/update_user_stats",
        json={
            "num_solo_games": 1,
            "fastest_solo_time": 70,
        },
    )
    assert res5.status_code == 200
    data5 = res5.json()
    assert data5["success"] is True
    updated_data = data5["updated_data"][0]
    assert updated_data.get("num_solo_games", 0) >= 1
    # If backend wrote the fastest time, it should equal 70
    assert updated_data.get("fastest_solo_time") == 70

    # Updating with a worse fastest time should not change it
    res6 = client.put(
        "/stats/update_user_stats",
        json={
            "fastest_solo_time": 100.0,  # worse
        },
    )
    assert res6.status_code == 200
    data6 = res6.json()
    # backend returns success False + message when nothing better to update
    assert data6.get("success") is False or "No better stats" in data6.get(
        "message", ""
    )

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

    # Test solo streak logic using dt_last_seen_solo
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    today = datetime.now().isoformat()

    res9 = client.put("/stats/update_user_stats", json={"dt_last_seen_solo": yesterday})
    assert res9.status_code == 200
    assert res9.json()["success"] is True

    res10 = client.put("/stats/update_user_stats", json={"dt_last_seen_solo": today})
    assert res10.status_code == 200
    data10 = res10.json()
    assert data10["success"] is True
    updated_streak = data10["updated_data"][0].get("streak_count_solo")
    assert updated_streak is not None and updated_streak >= 1


def test_unauthenticated_requests_are_rejected_with_401():
    from app.main import app

    # Ensure no auth override -> dependency will look for Authorization header and fail
    app.dependency_overrides.clear()
    client = TestClient(app)

    # calling create endpoint without auth should return 401
    res = client.post("/stats/create_user_stats", json=MOCK_USER)
    assert res.status_code == 401

    # calling update endpoint without auth should return 401
    res2 = client.put("/stats/update_user_stats", json={"num_wins_battle": 1})
    assert res2.status_code == 401


# -------------------------------------------------
# STREAK UPDATE TESTS
# -------------------------------------------------


def test_streak_increment_and_no_increment_same_day_solo():
    from app.main import app
    from app.auth import get_current_user

    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: _make_auth_user_for_mock(
        user_id, "SoloTester"
    )
    client = TestClient(app)

    client.post("/stats/create_user_stats", json={"id": user_id})

    today = datetime.utcnow().isoformat()

    # First play → streak = 1
    r1 = client.put("/stats/update_user_stats", json={"dt_last_seen_solo": today})
    assert r1.status_code == 200
    assert r1.json()["updated_data"][0]["streak_count_solo"] == 1

    # Same day play → streak should NOT increment
    r2 = client.put("/stats/update_user_stats", json={"dt_last_seen_solo": today})
    assert r2.status_code == 200

    streak = r2.json()["updated_data"][0]["streak_count_solo"]
    assert streak == 1


def test_streak_resets_after_two_days_solo():
    from app.main import app
    from app.auth import get_current_user

    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: _make_auth_user_for_mock(
        user_id, "ResetTesterS"
    )
    client = TestClient(app)

    client.post("/stats/create_user_stats", json={"id": user_id})

    two_days_ago = (datetime.utcnow() - timedelta(days=2)).date().isoformat()

    # Insert last_seen manually via update
    client.put("/stats/update_user_stats", json={"dt_last_seen_solo": two_days_ago})

    # GET route should detect >=2 days gap AND reset streak
    get_res = client.get(f"/stats/get_user_stats/{user_id}")
    assert get_res.status_code == 200
    row = get_res.json()["data"][0]
    assert row["streak_count_solo"] == 0
