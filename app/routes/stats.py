# Handle get and posts to the user stats table
from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from app.db import get_supabase
from app.auth import get_current_user

router = APIRouter()


from fastapi import Depends


@router.post("/create_user_stats")
def create_user_stats(user: dict, current_user: dict = Depends(get_current_user)):
    """
    Creates a new entry in the stats table with default values for a new user.
    First verifies whether the users user id already exists in the table. If it does, returns gracefully.
    If not, proceeds with adding a new entry with default stats.
    """
    supabase = get_supabase()
    user_id = current_user["user_id"]

    try:
        # Check if stats already exist
        existing = supabase.table("Stats").select("*").eq("user_id", user_id).execute()

        if existing.data:
            # Return existing stats instead of failing if users stats already exist
            return {
                "success": True,
                "data": existing.data[0],
                "message": "Stats already exist",
            }

        # otherwise create new entry with default stats
        display_name = user.get("display_name") or current_user.get("username") or ""

        response = (
            supabase.table("Stats")
            .insert(
                {
                    "user_id": user_id,
                    "display_name": display_name,
                    "num_solo_games": 0,
                    "num_battle_games": 0,
                    "fastest_solo_time": 0,
                    "fastest_battle_time": 0,
                    "num_complete_solo": 0,
                    "num_wins_battle": 0,
                    "dt_last_seen_solo": None,
                    "dt_last_seen_battle": None,
                    "streak_count_solo": 0,
                    "streak_count_battle": 0,
                }
            )
            .execute()
        )

        return {"success": True, "data": response.data}

    except Exception as e:
        print("Error inserting user stats:", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_user_stats/{user_id}")
def get_user_stats(user_id: str):
    supabase = get_supabase()
    try:
        response = supabase.table("Stats").select("*").eq("user_id", user_id).execute()

        # ✅ No .error; just check for data
        data = response.data or []
        return {"exists": len(data) > 0, "data": data}

    except Exception as e:
        print("Error fetching user stats:", e)
        raise HTTPException(status_code=500, detail=str(e))


from datetime import datetime, timedelta


@router.put("/update_user_stats")
def update_user_stats(user: dict, current_user: dict = Depends(get_current_user)):
    """
    Updates stats for an (authenticated) user.
    The request body may contain fields to increment or new times:
      - fields like 'num_wins', 'num_solo_games', 'num_competition_games' are treated as increments
      - 'fastest_solo_time' and 'fastest_competition_time' treat lower as better
      - 'dt_last_seen' (ISO string) is used for streak logic
    The user_id used is the authenticated user's id (current_user['user_id']).
    """
    supabase = get_supabase()
    user_id = current_user.get("user_id")

    if not user_id:
        # should not happen for an authenticated request, but guard anyway.
        raise HTTPException(status_code=400, detail="Missing authenticated user_id")

    try:
        # Get existing stats
        response = supabase.table("Stats").select("*").eq("user_id", user_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="User not found")

        current = response.data[0]
        updated_fields = {}

        # ---------------- Handle dt_last_seen and streak logic (solo) ----------------
        new_dt_solo = user.get("dt_last_seen_solo")
        if new_dt_solo:
            new_dt = datetime.fromisoformat(new_dt_solo)
            old_dt_str = current.get("dt_last_seen_solo")
            if old_dt_str:
                old_dt = datetime.fromisoformat(old_dt_str)
                # Compare calendar dates only
                if (new_dt.date() - old_dt.date()) == timedelta(days=1):
                    updated_fields["streak_count_solo"] = (
                        current.get("streak_count_solo", 0) + 1
                    )
                elif (new_dt.date() - old_dt.date()) > timedelta(days=1):
                    updated_fields["streak_count_solo"] = 1
                # same-day play → do not increment streak
            else:
                updated_fields["streak_count_solo"] = 1
            updated_fields["dt_last_seen_solo"] = new_dt_solo

        # ---------------- Handle dt_last_seen and streak logic (battle) ----------------
        new_dt_battle = user.get("dt_last_seen_battle")
        if new_dt_battle:
            new_dt = datetime.fromisoformat(new_dt_battle)
            old_dt_str = current.get("dt_last_seen_battle")
            if old_dt_str:
                old_dt = datetime.fromisoformat(old_dt_str)
                # Compare calendar dates only
                if (new_dt.date() - old_dt.date()) == timedelta(days=1):
                    updated_fields["streak_count_battle"] = (
                        current.get("streak_count_battle", 0) + 1
                    )
                elif (new_dt.date() - old_dt.date()) > timedelta(days=1):
                    updated_fields["streak_count_battle"] = 1
                # same-day play → do not increment streak
            else:
                updated_fields["streak_count_battle"] = 1
            updated_fields["dt_last_seen_battle"] = new_dt_battle

        # ---------------- Handle other fields ----------------
        # Keys to skip because they are handled above
        skip_keys = {"user_id", "dt_last_seen_solo", "dt_last_seen_battle"}

        for key, new_value in user.items():
            if key in skip_keys:
                continue

            # Skip None inputs
            if new_value is None:
                continue

            old_value = current.get(key)

            # lower = better (times)
            if key in ("fastest_solo_time", "fastest_battle_time"):
                # treat 0 or missing as "no recorded time" -> accept any positive new_value
                if (old_value == 0 or old_value is None) and (new_value > 0):
                    updated_fields[key] = new_value
                # otherwise only update if new_value is better (lower)
                elif new_value > 0 and old_value and new_value < old_value:
                    updated_fields[key] = new_value

            # higher = better (counts)
            elif key in (
                "num_complete_solo",
                "num_solo_games",
                "num_wins_battle",
                "num_battle_games",
            ):
                increment = new_value  # frontend now sends how much to increment by
                updated_fields[key] = (old_value or 0) + increment

        if not updated_fields:
            return {"success": False, "message": "No better stats to update"}

        update_res = (
            supabase.table("Stats")
            .update(updated_fields)
            .eq("user_id", user_id)
            .execute()
        )

        return {"success": True, "updated_data": update_res.data}

    except HTTPException:
        raise
    except Exception as e:
        print("Error updating user stats:", e)
        raise HTTPException(status_code=500, detail=str(e))
