# Handle get and posts to the invites table
# routes/invites.py
from typing import Dict, Union, Optional
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, date
from app.auth import get_current_user, get_current_user_optional
from app.db import get_supabase
import secrets

router = APIRouter()


@router.post("/create")
async def create_invite(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Union[bool, str]]:
    """Create battle invite for logged-in user. Generates token, creates WAITING battle, links invite.

    Returns: {"success": bool, "invite_token": str, "battle_id": str}
    Raises: 500 if creation fails
    """

    try:
        supabase = get_supabase()
        user_id = current_user["user_id"]

        # Generate invite token
        invite_token = secrets.token_urlsafe(16)  # will safely append to url

        # Calculate tokens expiration (end of day)
        now = datetime.now()
        expires_at = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Attempt to insert new battle
        battles_response = (
            supabase.table("battles")
            .insert(
                {
                    "player1_id": user_id,
                    "status": "WAITING",
                    "puzzle_date": date.today().isoformat(),
                    "created_at": now.isoformat(),
                }
            )
            .execute()
        )

        if not battles_response.data:
            raise HTTPException(status_code=500, detail="Failed to create battle.")

        battle_id = battles_response.data[0]["id"]

        # Attempt to insert new invite record
        invites_response = (
            supabase.table("invites")
            .insert(
                {
                    "invite_token": invite_token,
                    "inviter_id": user_id,
                    "battle_id": battle_id,
                    "status": "ACTIVE",
                    "expires_at": expires_at.isoformat(),
                    "created_at": now.isoformat(),
                }
            )
            .execute()
        )

        if not invites_response.data:
            supabase.table("battles").delete().eq(
                "id", battle_id
            ).execute()  # Rollback battle creation if invite fails
            raise HTTPException(status_code=500, detail="Failed to create invite.")

        return {"success": True, "invite_token": invite_token, "battle_id": battle_id}
    except HTTPException:
        # Re-raise HTTPExceptions (like the "Invalid or expired token" above)
        raise
    except Exception as e:
        print("Error creating invite:", e)
        raise HTTPException(status_code=500, detail="Failed to create Invite")


@router.post("/accept/{invite_token}")
async def accept_invite(
    invite_token: str, current_user: dict | None = Depends(get_current_user_optional)
) -> Dict[str, Union[bool, str]]:
    """Accept invite and join battle. Works for logged-in users and guests. Changes WAITING → READY.

    Returns: {"success": bool, "battle_id": str, "is_guest": bool}
    Raises: 400 if expired/self-invite, 404 if not found, 409 if already accepted
    """
    try:
        # validate invite
        supabase = get_supabase()
        invites_response = (
            supabase.table("invites")
            .select("*")  # we will need the battle_id, status
            .eq("invite_token", invite_token)
            .execute()
        )

        if not invites_response.data:
            raise HTTPException(status_code=404, detail="Could not find invite.")

        battle_id = invites_response.data[0]["battle_id"]
        invite_status = invites_response.data[0]["status"]
        expires_at = invites_response.data[0]["expires_at"]
        now = datetime.now().isoformat()

        if invite_status == "EXPIRED" or now > expires_at:
            supabase.table("invites").update({"status": "EXPIRED"}).eq(
                "invite_token", invite_token
            ).execute()
            raise HTTPException(status_code=400, detail="Invite has expired.")

        # dont allow battle against self
        if (
            current_user
            and current_user["user_id"] == invites_response.data[0]["inviter_id"]
        ):
            raise HTTPException(
                status_code=400, detail="Cannot accept your own invite."
            )

        # concurency protection: only one can accept
        invite_update_response = {"status": "ACCEPTED", "accepted_at": now}

        if current_user:
            invite_update_response["invitee_id"] = current_user["user_id"]

        # update invite if status is still ACTIVE
        updated_invite = (
            supabase.table("invites")
            .update(invite_update_response)
            .eq("invite_token", invite_token)
            .eq("status", "ACTIVE")  # concurrency protection
            .execute()
        )

        # check if update succeeded
        if not updated_invite.data or len(updated_invite.data) == 0:
            raise HTTPException(
                status_code=409,
                detail="Invite has already been accepted by another user.",
            )

        # update battle with player 2 info (guest or auth user)

        battle_update: Dict[str, Union[str, bool, None]] = {
            "status": "READY",
        }

        if current_user:
            battle_update["player2_id"] = current_user["user_id"]  # auth user
            battle_update["player2_is_guest"] = False
        else:
            battle_update["player2_id"] = None  # Guest user
            battle_update["player2_is_guest"] = True

        update_battles = (
            supabase.table("battles")
            .update(battle_update)
            .eq("id", battle_id)
            .execute()
        )

        if not update_battles.data:
            raise HTTPException(
                status_code=500, detail="Failed to update battle with player 2."
            )

        return {
            "success": True,
            "battle_id": battle_id,
            "is_guest": current_user is None,
        }

    except HTTPException:
        # Re-raise HTTPExceptions (like the "Invalid or expired token" above)
        raise
    except Exception as e:
        print("Error accepting invite:", e)
        raise HTTPException(status_code=500, detail="Failed to accept Invite")
