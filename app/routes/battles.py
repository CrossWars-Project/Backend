# handles game room actions (ready, start, complete)
from typing import Dict, Union, Optional
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, date
from app.auth import get_current_user, get_current_user_optional
from app.db import get_supabase
import secrets

router = APIRouter()


# fetch battle id
@router.get("/{battle_id}")
async def get_battle(
    battle_id: str, current_user: dict | None = Depends(get_current_user_optional)
):
    """Fetch battle by battle id"""
    try:
        supabase = get_supabase()

        # Attempt to fetch battle by id
        battle_response = (
            supabase.table("battles").select("*").eq("id", battle_id).execute()
        )

        if not battle_response.data:
            raise HTTPException(status_code=404, detail="Battle not found.")

        battle = battle_response.data[0]

        """ potentially restrict access to battle data TBD
        if current_user:
            # Ensure user is part of the battle
            if user_id != battle["player1_id"] and user_id != battle["player2_id"]:
                raise HTTPException(status_code=403, detail="Access denied to this battle.")
        """
        return {"success": True, "battle": battle}

    except HTTPException:
        # Re-raise HTTPExceptions (like the "Invalid or expired token" above)
        raise
    except Exception as e:
        print("Error getting battle id:", e)
        raise HTTPException(status_code=500, detail="Failed to get battle")


# fetch battle ready status (ready to initiating game)
@router.post("/{battle_id}/ready")
async def mark_ready(
    battle_id: str, current_user: dict | None = Depends(get_current_user_optional)
):
    """Mark player as ready for battle"""
    try:
        supabase = get_supabase()

        # Fetch battle to check current status
        battle_response = (
            supabase.table("battles").select("*").eq("id", battle_id).execute()
        )

        if not battle_response.data:
            raise HTTPException(status_code=404, detail="Battle not found.")

        battle = battle_response.data[0]

        # Verify battle is in progress or completed
        if battle["status"] not in ["READY", "WAITING"]:
            raise HTTPException(
                status_code=400, detail="Battle not in a joinable state."
            )

        player = None

        if current_user:
            user_id = current_user["user_id"]
            if user_id == battle["player1_id"]:
                player = "player1"
            elif user_id == battle["player2_id"]:
                player = "player2"
            else:
                raise HTTPException(
                    status_code=403, detail="User not part of this battle."
                )

        else:  # player is player 2 and a guest

            if not battle["player2_is_guest"]:  # player 2 is not a guest
                raise HTTPException(
                    status_code=403,
                    detail="Player 2 is not a guest and guest cannot join this battle.",
                )

            player = "player2"

        # Update ready status for the player
        supabase.table("battles").update({f"{player}_ready": True}).eq(
            "id", battle_id
        ).execute()

        return {"success": True, "message": f"{player} marked as ready."}

    except HTTPException:
        # Re-raise HTTPExceptions (like the "Invalid or expired token" above)
        raise
    except Exception as e:
        print("Error marking player as ready:", e)
        raise HTTPException(status_code=500, detail="Failed to mark player as ready")


# battle start (initiating game to in progress and set started_at)
@router.post("/{battle_id}/start")
async def start(
    battle_id: str, current_user: dict | None = Depends(get_current_user_optional)
):
    """Start the battle game by setting its status to 'IN_PROGRESS' and recording the start time.
    WHEN: both players click ready, frontend coutdown has completed"""

    try:
        supabase = get_supabase()
        # Fetch battle to check current status

        battle_result = (
            supabase.table("battles").select("*").eq("id", battle_id).execute()
        )

        if not battle_result.data:
            raise HTTPException(status_code=404, detail="Battle not found.")

        battle = battle_result.data[0]

        # verify player is in battle
        if current_user:
            # logged-in user
            user_id = current_user["user_id"]
            is_player1 = battle["player1_id"] == user_id
            is_player2 = battle["player2_id"] == user_id

            if not (is_player1 or is_player2):
                raise HTTPException(
                    status_code=403, detail="You are not part of this battle."
                )
        else:
            # guest user
            if not battle["player2_is_guest"]:
                raise HTTPException(
                    status_code=403, detail="Guest access denied for this battle."
                )

        # validate game state

        player1_ready = battle.get("player1_ready", False)
        player2_ready = battle.get("player2_ready", False)

        if not (player1_ready and player2_ready):
            raise HTTPException(
                status_code=400,
                detail="Both players must be ready before starting."
                f"player1_ready: {player1_ready}, player2_ready: {player2_ready}",
            )

        # check game not already started
        if battle["status"] == "IN_PROGRESS":
            # someone already started the game, ok (idempotent
            return {
                "success": True,
                "message": "Battle already in progress.",
                "started_at": battle["started_at"],
                "already_started": True,
            }

        # ensure game is ready to be started
        if battle["status"] != "READY":
            raise HTTPException(
                status_code=400,
                detail=f"Battle not in a startable state. Current status: {battle['status']}",
            )

        # update game to be in progress

        started_at = datetime.now().isoformat()

        supabase.table("battles").update(
            {"status": "IN_PROGRESS", "started_at": started_at}
        ).eq("id", battle_id).execute()

        return {
            "success": True,
            "message": "Battle started",
            "started_at": started_at,
            "already_started": False,
        }
    except HTTPException:
        raise
    except Exception as e:
        print("Error starting battle:", e)
        raise HTTPException(status_code=500, detail=f"Failed to start battle: {str(e)}")


# battle complete game (status from in progress to completed and set completed_at, who won, what their time was)
@router.post("/{battle_id}/complete")
async def end(
    battle_id: str, current_user: dict | None = Depends(get_current_user_optional)
):
    """Mark battle as complete and return winner and completed_at time.
    WHEN: frontend notifies backend that game is complete (someone won)"""

    try:
        supabase = get_supabase()
        # Fetch battle to check current status

        battle_result = (
            supabase.table("battles").select("*").eq("id", battle_id).execute()
        )

        if not battle_result.data:
            raise HTTPException(status_code=404, detail="Battle not found.")

        battle = battle_result.data[0]

        # verify player is in battle
        if current_user:
            # logged-in user
            user_id = current_user["user_id"]
            is_player1 = battle["player1_id"] == user_id
            is_player2 = battle["player2_id"] == user_id

            if not (is_player1 or is_player2):
                raise HTTPException(
                    status_code=403, detail="You are not part of this battle."
                )
        else:
            # guest user
            if not battle["player2_is_guest"]:
                raise HTTPException(
                    status_code=403, detail="Guest access denied for this battle."
                )
            
        #validate game state
        if battle["status"] == "COMPLETED":
            # Already completed - return existing result (idempotent)
            return {
                "success": True,
                "message": "Battle already complete.",
                "completed_at": battle.get("completed_at"),
                "winner_id": battle.get("winner_id"),
                "is_tie": battle.get("winner_id") is None,
                "already_completed": True
            }
        
        if battle["status"] != "IN_PROGRESS":
            raise HTTPException(
                status_code=400,
                detail=f"Battle not in progress. Current status: {battle['status']}",
            )
        
        # Determine who just finished
        current_player_id = current_user["user_id"] if current_user else None
        completed_at = datetime.now().isoformat()
        
        # Check if this is the first or second person to finish
        # Whoever finishes first is the winner
        # If both finish at "same time" (within same request), it's whoever called first
        
        # First player to complete wins
        winner_id = current_player_id
        winner = "player1" if winner_id == battle["player1_id"] else "player2"
        is_tie = False


        supabase.table("battles").update(
            {
                "status": "COMPLETED",
                f"{winner}_completed_at": completed_at,
                "completed_at": completed_at,
                "winner_id": winner_id,
            }
        ).eq("id", battle_id).execute()

        return{
            "success": True,
            "message": "Battle marked as complete.",
            "completed_at": completed_at,
            "time": completed_at - battle["started_at"],
            "winner_id": winner_id,
            "winner": winner,
            "is_tie": is_tie,
            "already_completed": False
        }

    except HTTPException:
        raise
    except Exception as e:
        print("Error marking battle as complete:", e)
        raise HTTPException(status_code=500, detail=f"Failed to mark battle as complete: {str(e)}")
