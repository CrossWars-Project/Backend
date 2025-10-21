from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from app.db import get_supabase_client_dep

router = APIRouter(prefix="/stats", tags=["stats"])

#get the users stats from the stats table
@router.get("/")
def get_user_stats(client: Client = Depends(get_supabase_client_dep)):
    """Fetch all stats from the stats table."""
    response = client.table("stats").select("*").execute()
    if response.error:
        raise HTTPException(status_code=500, detail="Error fetching stats")
    return response.data

#post the user stats to the stats table
@router.post("/")
def update_user_stats(stats: dict, client: Client = Depends(get_supabase_client_dep)):
    """Insert or update user stats in the stats table."""
    response = client.table("stats").upsert(stats).execute()
    if response.error:
        raise HTTPException(status_code=500, detail="Error updating stats")
    return response.data