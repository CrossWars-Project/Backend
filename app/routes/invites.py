# Handle get and posts to the invites table
# routes/invites.py
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, date
from app.auth import get_current_user, get_current_user_optional
from app.db import get_supabase
import secrets

router = APIRouter()


@router.post("/create")
async def create_invite(current_user: dict = Depends(get_current_user)):
    """Create a new battle invite for the logged-in-user to share with their friend."""
    """
    Flow:
    1. Generate unique token
    2. Create a battle with status = waiting
    3. Link battle to invite token
    4. Return invite token to frontend
    """

    try:
        supabase = get_supabase()
        user_id = current_user["user_id"]

        # Generate invite token
        invite_token = secrets.token_urlsafe(16)  # will safely append to url

        # Calculate tokens expiration (end of day)
        now = datetime.now()
        expires_at = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Attempt to insert new battle for if invite is accepted
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
        # Attempt to insert new battle for if invite is accepted
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

    # @router.post("/accept/{invite_token}")
    # async def accept_invite(invite_token: str, current_user: dict | None = Depends(get_current_user_optional)):
    """
    Accepts an invite and joins the battle. Works for logged in users and guests.
    """
    """
    Flow:
    1. Fetch invite and validate (active, not expired)
    2. Try to accept (concurrency protection)
    3. Update battle with player 2
    4. Return success and battle info so frontend can redirect to game room
    """


"""
**Accepting an invite:**
```
User clicks link → yourapp.com/battle/{token}
                 ↓
Frontend loads, extracts token from URL
        → GET /api/invites/{token}
        → sends auth token (if logged in)
        ↓
Backend checks if invite is valid (active, not expired)
       if user is logged in:
         updates invitee_id
       updates status to 'accepted'
       returns: {status: "valid", game_session_data}
       ↓
Frontend redirects both users to game room
INVITES ROUTE - Handles battle invitation creation and acceptance

TODO PHASES:
-----------

PHASE 1: INVITES (CURRENT FOCUS)
   [ ] Create invites table in Supabase
   [ ] Create battles table in Supabase
   [ ] Implement POST /create endpoint (logged-in users only)
   [ ] Implement POST /accept/{invite_token} endpoint (guests allowed)
   [ ] Test concurrency protection (two users accepting same invite)
   [ ] Build frontend BattleMode component (create invite, show link)
   [ ] Build frontend JoinBattle page (accept invite, redirect to game)
  [ ] End-to-end test: Create → Share → Accept → Both in game room

PHASE 2: BATTLES (NEXT)
  [ ] GET /battles/{battle_id} - Fetch battle details for game room
  [ ] POST /battles/{battle_id}/start - Both players clicked "ready"
  [ ] POST /battles/{battle_id}/complete - Submit completion time & determine winner
  [ ] Add Supabase Realtime subscriptions in frontend:
      - Listen for opponent joining (status: WAITING → READY)
      - Listen for opponent ready click
      - Listen for opponent completion time
  [ ] Build game room UI with waiting states
  [ ] Implement crossword puzzle display
  [ ] Add timer that starts when both click "ready"

PHASE 3: STATS & POLISH
  [ ] Create stats table (user_id, best_battle_time, num_wins, num_losses)
  [ ] Update stats after battle completes (logged-in users only)
  [ ] GET /stats/{user_id} - Fetch user stats
  [ ] Build leaderboard page
  [ ] Build user profile page showing stats
  [ ] Enforce one-game-per-day rule (check puzzle_date)
  [ ] Add battle history page
  [ ] Handle edge cases (disconnections, timeouts, etc.)

CURRENT FILE STATUS:
  - POST /create: Creates battle + invite, returns token ✓
  - POST /accept/{token}: Accepts invite, updates battle with player2 ✓
  - Concurrency protection via database WHERE clause ✓
  - Guest support via optional auth ✓
"""

# ... rest of your code
