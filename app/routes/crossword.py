# app/routes/crossword.py
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import traceback
import shutil
import time
from datetime import datetime
import os
import random


router = APIRouter()


@router.post("/generate")
def generate_crossword(payload: dict):
    """
    POST /crossword/generate
    Body: { "theme": "<theme-string>" }
    Calls app.generator.build_and_save(theme) and returns the JSON result.
    """
    theme = (payload.get("theme") or "").strip() if isinstance(payload, dict) else ""
    if not theme:
        raise HTTPException(
            status_code=400, detail='Request JSON must include {"theme":"..."}'
        )

    try:
        from app import generator
    except Exception as e:
        print("Error importing app.generator:", e)
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Generator module not available.",
        )

    if not hasattr(generator, "build_and_save"):
        raise HTTPException(
            status_code=500,
            detail="Generator module missing build_and_save(theme) function.",
        )

    try:
        result = generator.build_and_save(theme)
        return {"success": True, "data": result}
    except Exception as e:
        print("Error running build_and_save:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-daily")
def generate_daily_crosswords():
    """
    POST /crossword/generate-daily
    Generates both solo and battle crosswords for the day.
    Called by GitHub Actions daily at midnight.
    """
    try:
        from app import generator

        # Determine themes for today
        day_of_year = datetime.now().timetuple().tm_yday
        themes = [
            "technology",
            "nature",
            "science",
            "sports",
            "music",
            "food",
            "travel",
            "history",
            "art",
            "space",
            "ocean",
            "animals",
            "weather",
            "books",
            "movies",
        ]

        solo_theme = themes[day_of_year % len(themes)]
        battle_theme = themes[(day_of_year + 1) % len(themes)]

        results = {}
        app_dir = Path(__file__).parent.parent
        latest_path = app_dir / "latest_crossword.json"
        solo_path = app_dir / "solo_play.json"
        battle_path = app_dir / "battle_play.json"

        # Generate solo crossword
        print(f"Generating solo crossword with theme: {solo_theme}")
        generator.build_and_save(solo_theme)
        shutil.copy2(latest_path, solo_path)
        results["solo"] = {"theme": solo_theme, "status": "generated"}

        time.sleep(3)

        # Generate battle crossword
        print(f"Generating battle crossword with theme: {battle_theme}")
        generator.build_and_save(battle_theme)
        shutil.copy2(latest_path, battle_path)
        results["battle"] = {"theme": battle_theme, "status": "generated"}

        return {
            "success": True,
            "message": "Daily crosswords generated successfully",
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"Error in generate_daily_crosswords: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/solo")
def get_solo_crossword():
    """
    GET /crossword/solo
    Returns the daily solo play crossword from solo_play.json.
    """
    file_path = Path(__file__).parent.parent / "solo_play.json"

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No solo crossword available. Wait for daily generation.",
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"success": True, "data": data}
    except Exception as e:
        print("Error reading solo_play.json:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/battle")
def get_battle_crossword():
    """
    GET /crossword/battle
    Returns the daily battle play crossword from battle_play.json.
    """
    file_path = Path(__file__).parent.parent / "battle_play.json"

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No battle crossword available. Wait for daily generation.",
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"success": True, "data": data}
    except Exception as e:
        print("Error reading battle_play.json:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
def get_latest_crossword():
    """
    GET /crossword/latest
    Returns the last saved latest_crossword.json.
    """
    file_path = Path(__file__).parent.parent / "latest_crossword.json"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="No latest crossword found")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"success": True, "data": data}
    except Exception as e:
        print("Error reading latest_crossword.json:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/generate-new")
def test_generate_new_crossword(payload: dict = None):
    """
    POST /crossword/test/generate-new
    Body (optional): { "mode": "solo" or "battle", "theme": "custom-theme" }

    TESTING ONLY: Manually generates a new crossword and overwrites the current one.
    This allows developers to test with fresh crosswords without waiting for midnight.

    Examples:
    - POST /crossword/test/generate-new  (generates both with random themes)
    - POST /crossword/test/generate-new {"mode": "solo"}  (only solo)
    - POST /crossword/test/generate-new {"mode": "solo", "theme": "ocean"}
    """
    import random

    payload = payload or {}
    mode = payload.get("mode", "both")  # "solo", "battle", or "both"
    custom_theme = payload.get("theme")

    themes = [
        "technology",
        "nature",
        "science",
        "sports",
        "music",
        "food",
        "travel",
        "history",
        "art",
        "space",
        "ocean",
        "animals",
        "weather",
        "books",
        "movies",
    ]

    try:
        from app import generator

        app_dir = Path(__file__).parent.parent
        latest_path = app_dir / "latest_crossword.json"
        results = {}

        # Generate Solo
        if mode in ["solo", "both"]:
            solo_theme = custom_theme or random.choice(themes)
            print(f"TEST: Generating solo crossword with theme: {solo_theme}")
            generator.build_and_save(solo_theme)

            solo_path = app_dir / "solo_play.json"
            shutil.copy2(latest_path, solo_path)
            results["solo"] = {
                "theme": solo_theme,
                "status": "generated",
                "file": "solo_play.json",
            }
            time.sleep(2)

        # Generate Battle
        if mode in ["battle", "both"]:
            battle_theme = custom_theme or random.choice(themes)
            print(f"TEST: Generating battle crossword with theme: {battle_theme}")
            generator.build_and_save(battle_theme)

            battle_path = app_dir / "battle_play.json"
            shutil.copy2(latest_path, battle_path)
            results["battle"] = {
                "theme": battle_theme,
                "status": "generated",
                "file": "battle_play.json",
            }

        return {
            "success": True,
            "message": "Test crossword(s) generated successfully",
            "results": results,
            "note": "This endpoint is for testing only. Production uses scheduled generation.",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"Error in test generation: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/test/clear-all")
def test_clear_crosswords():
    """
    DELETE /crossword/test/clear-all

    TESTING ONLY: Deletes all crossword JSON files.
    Useful for testing the "no crossword available" error state.
    """
    try:
        app_dir = Path(__file__).parent.parent
        files_to_delete = [
            "latest_crossword.json",
            "solo_play.json",
            "battle_play.json",
        ]

        deleted = []
        for filename in files_to_delete:
            file_path = app_dir / filename
            if file_path.exists():
                os.remove(file_path)
                deleted.append(filename)

        return {
            "success": True,
            "message": f"Deleted {len(deleted)} file(s)",
            "deleted_files": deleted,
        }
    except Exception as e:
        print(f"Error clearing files: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
