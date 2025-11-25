# tests/test_battles.py
from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.db import get_supabase

client = TestClient(app)

# ═══════════════════════════════════════════════════════════
# FIXTURES - Reusable Setup
# ═══════════════════════════════════════════════════════════


@pytest.fixture
def setup_battle():
    """
    Sets up a complete battle scenario with two users.

    Returns both players' auth info and a battle they're both in.
    This is the "happy path" setup - everything is valid.
    """
    supabase = get_supabase()
    supabase.reset()  # Clear previous test data

    # Create two test users in auth
    player1_token = "player1_token_abc"
    player1_id = "player1_user_id"
    supabase.auth.add_user(player1_token, player1_id, "player1@test.com", "player1")

    player2_token = "player2_token_xyz"
    player2_id = "player2_user_id"
    supabase.auth.add_user(player2_token, player2_id, "player2@test.com", "player2")

    # Create a battle with both players
    battle_data = {
        "id": "test_battle_123",
        "player1_id": player1_id,
        "player2_id": player2_id,
        "player2_is_guest": False,
        "status": "READY",
        "player1_ready": False,
        "player2_ready": False,
        "puzzle_date": "2024-01-01",
        "created_at": "2024-01-01T00:00:00Z",
    }

    supabase.table("battles").insert(battle_data).execute()

    return {
        "battle_id": "test_battle_123",
        "player1": {
            "token": player1_token,
            "id": player1_id,
            "headers": {"Authorization": f"Bearer {player1_token}"},
        },
        "player2": {
            "token": player2_token,
            "id": player2_id,
            "headers": {"Authorization": f"Bearer {player2_token}"},
        },
    }


@pytest.fixture
def setup_guest_battle():
    """
    Sets up a battle with player1 (logged in) and player2 (guest).

    Used for testing guest-specific scenarios.
    """
    supabase = get_supabase()
    supabase.reset()

    # Create player1
    player1_token = "player1_token_abc"
    player1_id = "player1_user_id"
    supabase.auth.add_user(player1_token, player1_id, "player1@test.com", "player1")

    # Create battle with guest as player2
    battle_data = {
        "id": "guest_battle_123",
        "player1_id": player1_id,
        "player2_id": None,  # Guest has no ID
        "player2_is_guest": True,
        "status": "READY",
        "player1_ready": False,
        "player2_ready": False,
        "puzzle_date": "2024-01-01",
        "created_at": "2024-01-01T00:00:00Z",
    }

    supabase.table("battles").insert(battle_data).execute()

    return {
        "battle_id": "guest_battle_123",
        "player1": {
            "token": player1_token,
            "id": player1_id,
            "headers": {"Authorization": f"Bearer {player1_token}"},
        },
    }


# ═══════════════════════════════════════════════════════════
# READY ROUTE TESTS
# ═══════════════════════════════════════════════════════════


def test_player1_marks_ready_success(setup_battle):
    """Player 1 successfully marks themselves as ready."""
    setup = setup_battle

    # Player 1 marks ready
    response = client.post(
        f"/api/battles/{setup['battle_id']}/ready", headers=setup["player1"]["headers"]
    )

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert "player1" in json_response["message"]

    supabase = get_supabase()
    battle_response = (
        supabase.table("battles").select("*").eq("id", setup["battle_id"]).execute()
    )

    battle = battle_response.data[0]

    assert battle["player1_ready"] is True
    assert battle["player2_ready"] is False  # Player 2 hasn't marked yet


def test_player2_marks_ready_success(setup_battle):
    """Player 2 successfully marks themselves as ready."""
    setup = setup_battle

    # Player 2 marks ready
    response = client.post(
        f"/api/battles/{setup['battle_id']}/ready", headers=setup["player2"]["headers"]
    )

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert "player2" in json_response["message"]

    supabase = get_supabase()
    battle_response = (
        supabase.table("battles").select("*").eq("id", setup["battle_id"]).execute()
    )

    battle = battle_response.data[0]

    assert battle["player1_ready"] is False
    assert battle["player2_ready"] is True


def test_both_players_mark_ready(setup_battle):
    """Both players can mark ready in sequence.

    - Player 1 marks ready first
    - Player 2 marks ready second

    """
    setup = setup_battle

    # Player 1 marks ready
    response1 = client.post(
        f"/api/battles/{setup['battle_id']}/ready", headers=setup["player1"]["headers"]
    )
    assert response1.status_code == 200

    # Player 2 marks ready
    response2 = client.post(
        f"/api/battles/{setup['battle_id']}/ready", headers=setup["player2"]["headers"]
    )
    assert response2.status_code == 200

    supabase = get_supabase()
    battle_response = (
        supabase.table("battles").select("*").eq("id", setup["battle_id"]).execute()
    )
    battle = battle_response.data[0]

    assert battle["player1_ready"] is True
    assert battle["player2_ready"] is True


def test_guest_marks_ready_success(setup_guest_battle):
    """Guest (player 2) can mark themselves ready."""
    setup = setup_guest_battle

    # Guest marks ready (no auth header)
    response = client.post(
        f"/api/battles/{setup['battle_id']}/ready"
        # No headers = guest (unauthenticated)
    )

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert "player2" in json_response["message"]

    supabase = get_supabase()
    battle_response = (
        supabase.table("battles").select("*").eq("id", setup["battle_id"]).execute()
    )
    battle = battle_response.data[0]

    assert battle["player2_ready"] is True


def test_non_player_cannot_mark_ready(setup_battle):
    """User not in the battle can't mark ready."""
    setup = setup_battle
    supabase = get_supabase()

    # Create a third user (not in the battle)
    intruder_token = "intruder_token"
    intruder_id = "intruder_user_id"
    supabase.auth.add_user(intruder_token, intruder_id, "intruder@test.com")

    # Intruder tries to mark ready
    response = client.post(
        f"/api/battles/{setup['battle_id']}/ready",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )

    # Request is rejected
    assert response.status_code == 403
    assert "not part of this battle" in response.json()["detail"].lower()

    battle_response = (
        supabase.table("battles").select("*").eq("id", setup["battle_id"]).execute()
    )
    battle = battle_response.data[0]

    assert battle["player1_ready"] is False
    assert battle["player2_ready"] is False


def test_mark_ready_invalid_battle_id(setup_battle):
    """Can't mark ready for non-existent battle."""
    setup = setup_battle

    # Try to mark ready for fake battle
    response = client.post(
        "/api/battles/fake_battle_id_999/ready", headers=setup["player1"]["headers"]
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_cannot_mark_ready_when_in_progress(setup_battle):
    """Can't mark ready after game has started."""
    setup = setup_battle
    supabase = get_supabase()

    # Change battle status to IN_PROGRESS
    supabase.table("battles").update({"status": "IN_PROGRESS"}).eq(
        "id", setup["battle_id"]
    ).execute()

    # Try to mark ready
    response = client.post(
        f"/api/battles/{setup['battle_id']}/ready", headers=setup["player1"]["headers"]
    )

    assert response.status_code == 400
    assert "not in a joinable state" in response.json()["detail"].lower()


def test_cannot_mark_ready_when_completed(setup_battle):
    """Can't mark ready after game is over."""
    setup = setup_battle
    supabase = get_supabase()

    # Change battle status to COMPLETED
    supabase.table("battles").update({"status": "COMPLETED"}).eq(
        "id", setup["battle_id"]
    ).execute()

    # Try to mark ready
    response = client.post(
        f"/api/battles/{setup['battle_id']}/ready", headers=setup["player1"]["headers"]
    )

    assert response.status_code == 400
    assert "not in a joinable state" in response.json()["detail"].lower()


def test_guest_cannot_mark_ready_in_non_guest_battle(setup_battle):
    """Guest can't mark ready in battle where player2 is not a guest."""
    setup = setup_battle

    # Guest tries to mark ready (no auth header)
    response = client.post(
        f"/api/battles/{setup['battle_id']}/ready"
        # No headers = guest
    )

    assert response.status_code == 403
    assert "not a guest" in response.json()["detail"].lower()


def test_mark_ready_no_auth_token(setup_battle):
    """What happens when no auth AND not a guest battle?"""
    setup = setup_battle

    # No auth header, regular battle
    response = client.post(f"/api/battles/{setup['battle_id']}/ready")

    # Rejected (this is a non-guest battle)
    assert response.status_code == 403


# ═══════════════════════════════════════════════════════════
# START ROUTE TESTS
# ═══════════════════════════════════════════════════════════


def test_start_battle_success_both_players_ready(setup_battle):
    """Successfully start battle when both players are ready."""
    setup = setup_battle
    supabase = get_supabase()

    # Mark both players as ready first
    supabase.table("battles").update({"player1_ready": True, "player2_ready": True}).eq(
        "id", setup["battle_id"]
    ).execute()

    # Player 1 starts the battle
    response = client.post(
        f"/api/battles/{setup['battle_id']}/start", headers=setup["player1"]["headers"]
    )

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert json_response["message"] == "Battle started"
    assert "started_at" in json_response
    assert json_response["already_started"] is False

    # Verify database was updated
    battle_response = (
        supabase.table("battles").select("*").eq("id", setup["battle_id"]).execute()
    )
    battle = battle_response.data[0]
    assert battle["status"] == "IN_PROGRESS"
    assert battle["started_at"] is not None


def test_start_battle_player2_can_start(setup_battle):
    """Player 2 can also start the battle."""
    setup = setup_battle
    supabase = get_supabase()

    # Mark both players as ready
    supabase.table("battles").update({"player1_ready": True, "player2_ready": True}).eq(
        "id", setup["battle_id"]
    ).execute()

    # Player 2 starts the battle
    response = client.post(
        f"/api/battles/{setup['battle_id']}/start", headers=setup["player2"]["headers"]
    )

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert json_response["already_started"] is False


def test_start_battle_guest_can_start(setup_guest_battle):
    """Guest player can start the battle."""
    setup = setup_guest_battle
    supabase = get_supabase()

    # Mark both players as ready
    supabase.table("battles").update({"player1_ready": True, "player2_ready": True}).eq(
        "id", setup["battle_id"]
    ).execute()

    # Guest starts the battle (no auth header)
    response = client.post(f"/api/battles/{setup['battle_id']}/start")

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True


def test_start_battle_fails_when_neither_ready(setup_battle):
    """Cannot start battle when neither player is ready."""
    setup = setup_battle

    # Try to start without marking ready
    response = client.post(
        f"/api/battles/{setup['battle_id']}/start", headers=setup["player1"]["headers"]
    )

    assert response.status_code == 400
    assert "both players must be ready" in response.json()["detail"].lower()


def test_start_battle_fails_when_only_player1_ready(setup_battle):
    """Cannot start battle when only player 1 is ready."""
    setup = setup_battle
    supabase = get_supabase()

    # Only player 1 ready
    supabase.table("battles").update(
        {"player1_ready": True, "player2_ready": False}
    ).eq("id", setup["battle_id"]).execute()

    response = client.post(
        f"/api/battles/{setup['battle_id']}/start", headers=setup["player1"]["headers"]
    )

    assert response.status_code == 400
    assert "both players must be ready" in response.json()["detail"].lower()


def test_start_battle_fails_when_only_player2_ready(setup_battle):
    """Cannot start battle when only player 2 is ready."""
    setup = setup_battle
    supabase = get_supabase()

    # Only player 2 ready
    supabase.table("battles").update(
        {"player1_ready": False, "player2_ready": True}
    ).eq("id", setup["battle_id"]).execute()

    response = client.post(
        f"/api/battles/{setup['battle_id']}/start", headers=setup["player2"]["headers"]
    )

    assert response.status_code == 400
    assert "both players must be ready" in response.json()["detail"].lower()


def test_start_battle_non_player_cannot_start(setup_battle):
    """User not in the battle cannot start it."""
    setup = setup_battle
    supabase = get_supabase()

    # Mark both players ready
    supabase.table("battles").update({"player1_ready": True, "player2_ready": True}).eq(
        "id", setup["battle_id"]
    ).execute()

    # Create an intruder
    intruder_token = "intruder_token"
    intruder_id = "intruder_user_id"
    supabase.auth.add_user(intruder_token, intruder_id, "intruder@test.com")

    # Intruder tries to start
    response = client.post(
        f"/api/battles/{setup['battle_id']}/start",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )

    assert response.status_code == 403
    assert "not part of this battle" in response.json()["detail"].lower()


def test_start_battle_invalid_battle_id(setup_battle):
    """Cannot start a non-existent battle."""
    setup = setup_battle

    response = client.post(
        "/api/battles/fake_battle_id_999/start", headers=setup["player1"]["headers"]
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_start_battle_idempotent_already_in_progress(setup_battle):
    """Starting an already-started battle is idempotent."""
    setup = setup_battle
    supabase = get_supabase()

    # Set up battle as already started
    test_started_at = "2024-01-01T12:00:00Z"
    supabase.table("battles").update(
        {
            "player1_ready": True,
            "player2_ready": True,
            "status": "IN_PROGRESS",
            "started_at": test_started_at,
        }
    ).eq("id", setup["battle_id"]).execute()

    # Try to start again
    response = client.post(
        f"/api/battles/{setup['battle_id']}/start", headers=setup["player1"]["headers"]
    )

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert json_response["already_started"] is True
    assert json_response["started_at"] == test_started_at


def test_start_battle_fails_from_waiting_status(setup_battle):
    """Cannot start battle from WAITING status."""
    setup = setup_battle
    supabase = get_supabase()

    # Change to WAITING status (but mark both ready)
    supabase.table("battles").update(
        {"player1_ready": True, "player2_ready": True, "status": "WAITING"}
    ).eq("id", setup["battle_id"]).execute()

    response = client.post(
        f"/api/battles/{setup['battle_id']}/start", headers=setup["player1"]["headers"]
    )

    assert response.status_code == 400
    assert "not in a startable state" in response.json()["detail"].lower()


def test_start_battle_fails_from_completed_status(setup_battle):
    """Cannot start an already completed battle."""
    setup = setup_battle
    supabase = get_supabase()

    # Change to COMPLETED status
    supabase.table("battles").update(
        {"player1_ready": True, "player2_ready": True, "status": "COMPLETED"}
    ).eq("id", setup["battle_id"]).execute()

    response = client.post(
        f"/api/battles/{setup['battle_id']}/start", headers=setup["player1"]["headers"]
    )

    assert response.status_code == 400
    assert "not in a startable state" in response.json()["detail"].lower()


def test_start_battle_guest_denied_for_non_guest_battle(setup_battle):
    """Guest cannot start a non-guest battle."""
    setup = setup_battle
    supabase = get_supabase()

    # Mark both ready
    supabase.table("battles").update({"player1_ready": True, "player2_ready": True}).eq(
        "id", setup["battle_id"]
    ).execute()

    # Guest tries to start (no auth header)
    response = client.post(f"/api/battles/{setup['battle_id']}/start")

    assert response.status_code == 403
    assert "guest access denied" in response.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════
# COMPLETE ROUTE TESTS
# ═══════════════════════════════════════════════════════════


def test_player1_completes_battle_wins(setup_battle):
    """Player 1 completes the battle and is marked as winner."""
    setup = setup_battle
    supabase = get_supabase()

    # Set battle to IN_PROGRESS
    supabase.table("battles").update({"status": "IN_PROGRESS"}).eq(
        "id", setup["battle_id"]
    ).execute()

    # Player 1 marks complete
    response = client.post(
        f"/api/battles/{setup['battle_id']}/complete",
        headers=setup["player1"]["headers"],
    )

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert json_response["winner_id"] == setup["player1"]["id"]

    # Verify database update
    battle_response = (
        supabase.table("battles").select("*").eq("id", setup["battle_id"]).execute()
    )
    battle = battle_response.data[0]

    assert battle["status"] == "COMPLETED"
    assert battle["winner_id"] == setup["player1"]["id"]
    assert battle["player1_completed_at"] is not None


def test_player2_completes_battle_wins(setup_battle):
    """Player 2 completes the battle and is marked as winner."""
    setup = setup_battle
    supabase = get_supabase()

    # Set battle to IN_PROGRESS
    supabase.table("battles").update({"status": "IN_PROGRESS"}).eq(
        "id", setup["battle_id"]
    ).execute()

    # Player 2 marks complete
    response = client.post(
        f"/api/battles/{setup['battle_id']}/complete",
        headers=setup["player2"]["headers"],
    )

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert json_response["winner_id"] == setup["player2"]["id"]

    # Verify database update
    battle_response = (
        supabase.table("battles").select("*").eq("id", setup["battle_id"]).execute()
    )
    battle = battle_response.data[0]

    assert battle["status"] == "COMPLETED"
    assert battle["winner_id"] == setup["player2"]["id"]
    assert battle["player2_completed_at"] is not None


def test_complete_battle_non_player_cannot_complete(setup_battle):
    """User not in the battle cannot mark it complete."""
    setup = setup_battle
    supabase = get_supabase()

    # Set battle to IN_PROGRESS
    supabase.table("battles").update({"status": "IN_PROGRESS"}).eq(
        "id", setup["battle_id"]
    ).execute()

    # Create an intruder
    intruder_token = "intruder_token"
    intruder_id = "intruder_user_id"
    supabase.auth.add_user(intruder_token, intruder_id, "intruder@example.com")
    # Intruder tries to complete
    response = client.post(
        f"/api/battles/{setup['battle_id']}/complete",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert response.status_code == 403
    assert "not part of this battle" in response.json()["detail"].lower()


def test_player2_guest_completes_battle_wins(setup_guest_battle):
    """Guest player (player 2) completes the battle and is marked as winner."""
    setup = setup_guest_battle
    supabase = get_supabase()

    # Set battle to IN_PROGRESS
    supabase.table("battles").update({"status": "IN_PROGRESS"}).eq(
        "id", setup["battle_id"]
    ).execute()

    # Guest marks complete (no auth header)
    response = client.post(f"/api/battles/{setup['battle_id']}/complete")

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert json_response["winner_id"] is None  # Guest has no user ID

    # Verify database update
    battle_response = (
        supabase.table("battles").select("*").eq("id", setup["battle_id"]).execute()
    )
    battle = battle_response.data[0]

    assert battle["status"] == "COMPLETED"
    assert battle["winner_id"] is None
    assert battle["player2_completed_at"] is not None


def test_already_completed(setup_battle):
    """Completing an already completed battle is idempotent."""
    setup = setup_guest_battle
    supabase = get_supabase()

    # Set battle to COMPLETED
    supabase.table("battles").update(
        {
            "status": "COMPLETED",
            "winner_id": setup["player1"]["id"],
            "player1_completed_at": "2024-01-01T12:00:00Z",
        }
    ).eq("id", setup["battle_id"]).execute()

    # Player 2 tries to complete
    response = client.post(
        f"/api/battles/{setup['battle_id']}/complete",
        headers=setup["player2"]["headers"],
    )

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert json_response["winner_id"] == setup["player1"]["id"]
