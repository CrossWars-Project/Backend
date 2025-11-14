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
        "created_at": "2024-01-01T00:00:00Z"
    }
    
    supabase.table("battles").insert(battle_data).execute()
    
    return {
        "battle_id": "test_battle_123",
        "player1": {
            "token": player1_token,
            "id": player1_id,
            "headers": {"Authorization": f"Bearer {player1_token}"}
        },
        "player2": {
            "token": player2_token,
            "id": player2_id,
            "headers": {"Authorization": f"Bearer {player2_token}"}
        }
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
        "created_at": "2024-01-01T00:00:00Z"
    }
    
    supabase.table("battles").insert(battle_data).execute()
    
    return {
        "battle_id": "guest_battle_123",
        "player1": {
            "token": player1_token,
            "id": player1_id,
            "headers": {"Authorization": f"Bearer {player1_token}"}
        }
    }



def test_player1_marks_ready_success(setup_battle):
    """Player 1 successfully marks themselves as ready. """
    setup = setup_battle
    
    # Player 1 marks ready
    response = client.post(
        f"/api/battles/{setup['battle_id']}/ready",
        headers=setup["player1"]["headers"]
    )
    
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert "player1" in json_response["message"]
    
    supabase = get_supabase()
    battle_response = (
        supabase.table("battles")
        .select("*")
        .eq("id", setup["battle_id"])
        .execute()
    )

    battle = battle_response.data[0]
    
    assert battle["player1_ready"] is True
    assert battle["player2_ready"] is False  # Player 2 hasn't marked yet

def test_player2_marks_ready_success(setup_battle):
    """Player 2 successfully marks themselves as ready.    """
    setup = setup_battle
    
    #Player 2 marks ready
    response = client.post(
        f"/api/battles/{setup['battle_id']}/ready",
        headers=setup["player2"]["headers"]
    )
    
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert "player2" in json_response["message"]
    
   
    supabase = get_supabase()
    battle_response = (
        supabase.table("battles")\
        .select("*")\
        .eq("id", setup["battle_id"])\
        .execute()
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
    
    #Player 1 marks ready
    response1 = client.post(
        f"/api/battles/{setup['battle_id']}/ready",
        headers=setup["player1"]["headers"]
    )
    assert response1.status_code == 200
    
    #Player 2 marks ready
    response2 = client.post(
        f"/api/battles/{setup['battle_id']}/ready",
        headers=setup["player2"]["headers"]
    )
    assert response2.status_code == 200
   
    supabase = get_supabase()
    battle_response = (
        supabase.table("battles")
        .select("*")
        .eq("id", setup["battle_id"])
        .execute()
    )
    battle = battle_response.data[0]

    assert battle["player1_ready"] is True
    assert battle["player2_ready"] is True

def test_guest_marks_ready_success(setup_guest_battle):
    """ Guest (player 2) can mark themselves ready. """
    setup = setup_guest_battle
    
    #Guest marks ready (no auth header)
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
        supabase.table("battles")
        .select("*")
        .eq("id", setup["battle_id"])
        .execute()
    )
    battle = battle_response.data[0]
    
    assert battle["player2_ready"] is True


def test_non_player_cannot_mark_ready(setup_battle):
    """User not in the battle can't mark ready. """
    setup = setup_battle
    supabase = get_supabase()
    
    # Create a third user (not in the battle)
    intruder_token = "intruder_token"
    intruder_id = "intruder_user_id"
    supabase.auth.add_user(intruder_token, intruder_id, "intruder@test.com")
    
    # Intruder tries to mark ready
    response = client.post(
        f"/api/battles/{setup['battle_id']}/ready",
        headers={"Authorization": f"Bearer {intruder_token}"}
    )
    
    #Request is rejected
    assert response.status_code == 403
    assert "not part of this battle" in response.json()["detail"].lower()

    battle_response = (
        supabase.table("battles")
        .select("*")
        .eq("id", setup["battle_id"])
        .execute()
    )
    battle = battle_response.data[0]

    assert battle["player1_ready"] is False
    assert battle["player2_ready"] is False


def test_mark_ready_invalid_battle_id(setup_battle):
    """Can't mark ready for non-existent battle. """
    setup = setup_battle
    
    # Try to mark ready for fake battle
    response = client.post(
        "/api/battles/fake_battle_id_999/ready",
        headers=setup["player1"]["headers"]
    )
    
 
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()



def test_cannot_mark_ready_when_in_progress(setup_battle):
    """Can't mark ready after game has started. """
    setup = setup_battle
    supabase = get_supabase()
    
    # Change battle status to IN_PROGRESS
    supabase.table("battles").update({
        "status": "IN_PROGRESS"
    }).eq("id", setup["battle_id"]).execute()
    
    # Try to mark ready
    response = client.post(
        f"/api/battles/{setup['battle_id']}/ready",
        headers=setup["player1"]["headers"]
    )
    
    assert response.status_code == 400
    assert "not in a joinable state" in response.json()["detail"].lower()


def test_cannot_mark_ready_when_completed(setup_battle):
    """ Can't mark ready after game is over. """
    setup = setup_battle
    supabase = get_supabase()
    
    # Change battle status to COMPLETED
    supabase.table("battles").update({
        "status": "COMPLETED"
    }).eq("id", setup["battle_id"]).execute()
    
    # Try to mark ready
    response = client.post(
        f"/api/battles/{setup['battle_id']}/ready",
        headers=setup["player1"]["headers"]
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
    """ What happens when no auth AND not a guest battle? """
    setup = setup_battle
    
    # No auth header, regular battle
    response = client.post(
        f"/api/battles/{setup['battle_id']}/ready"
    )
    
    # Rejected (this is a non-guest battle)
    assert response.status_code == 403