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
