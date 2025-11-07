# Handle get and posts to the user stats table
from fastapi import APIRouter, HTTPException
from app.db import get_supabase

router = APIRouter()


@router.post("/create_user_stats")
def create_user_stats(user: dict):
    """
    Expects a dict with keys:
      - 'id': user ID from auth
      - 'display_name': string
    Inserts default stats row for new user.
    """
    supabase = get_supabase()
    try:
        # Attempt to insert new stats record
        response = (
            supabase.table("Stats")
            .insert(
                {
                    "user_id": user["id"],
                    "display_name": user["display_name"],
                    "num_solo_games": 0,
                    "num_competition_games": 0,
                    "fastest_solo_time": 0,
                    "fastest_competition_time": 0,
                    "num_wins": 0,
                    "dt_last_seen": None,
                    "streak_count": 0,
                }
            )
            .execute()
        )

        # ✅ Modern client: use response.data, no .error attribute
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to insert user stats")

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
def update_user_stats(user: dict):
    """
    Expects JSON body with:
      - 'user_id': str (required)
      - fields to update (e.g., 'num_wins', 'streak_count', etc.)
    Only updates fields if new values are 'better' than existing ones.
    """
    supabase = get_supabase()
    user_id = user.get("user_id")

    if not user_id:
        raise HTTPException(status_code=400, detail="Missing required field: user_id")

    try:
        # Get existing stats
        response = supabase.table("Stats").select("*").eq("user_id", user_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="User stats not found")

        current = response.data[0]
        updated_fields = {}

        # ---------------- Handle dt_last_seen and streak logic ----------------
        new_dt_str = user.get("dt_last_seen")
        if new_dt_str:
            new_dt = datetime.fromisoformat(new_dt_str)
            old_dt_str = current.get("dt_last_seen")
            if old_dt_str:
                old_dt = datetime.fromisoformat(old_dt_str)
                # Compare calendar dates only
                if (new_dt.date() - old_dt.date()) == timedelta(days=1):
                    updated_fields["streak_count"] = current.get("streak_count", 0) + 1
                elif (new_dt.date() - old_dt.date()) > timedelta(days=1):
                    updated_fields["streak_count"] = 1
                # same-day play → do not increment streak
            else:
                updated_fields["streak_count"] = 1
            updated_fields["dt_last_seen"] = new_dt_str

        # ---------------- Handle other fields ----------------
        for key, new_value in user.items():
            if key in ("user_id", "dt_last_seen"):
                continue
            old_value = current.get(key)

            # lower = better (times)
            if key in ("fastest_solo_time", "fastest_competition_time"):
                if old_value == 0 or (new_value > 0 and new_value < old_value):
                    updated_fields[key] = new_value
            # higher = better (counts)
            elif key in ("num_wins", "num_solo_games", "num_competition_games"):
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

    except Exception as e:
        print("Error updating user stats:", e)
        raise HTTPException(status_code=500, detail=str(e))
