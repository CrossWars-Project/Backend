# app/routes/crossword.py
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import traceback

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
        # Import lazily so the route file can be imported even if generator.py is not present yet
        from app import generator
    except Exception as e:
        print("Error importing app.generator:", e)
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Generator module not available. Ensure app/generator.py exists and exports build_and_save().",
        )

    if not hasattr(generator, "build_and_save"):
        raise HTTPException(
            status_code=500,
            detail="Generator module missing build_and_save(theme) function.",
        )

    try:
        result = generator.build_and_save(theme)
        # Return consistent structure used across the project
        return {"success": True, "data": result}
    except Exception as e:
        # Log the error server-side for debugging and return 500 to client
        print("Error running build_and_save:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
def get_latest_crossword():
    """
    GET /crossword/latest
    Returns the last saved latest_crossword.json produced by the generator.
    """
    try:
        import app.generator as genmod
        base = Path(genmod.__file__).parent
        file_path = base / "latest_crossword.json"
    except Exception:
        # Fallback: try to find latest_crossword.json relative to repository root
        file_path = Path(__file__).parent.parent / "latest_crossword.json"

    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail="No latest_crossword.json file found"
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"success": True, "data": data}
    except Exception as e:
        print("Error reading latest_crossword.json:", e)
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to read latest_crossword.json: {e}"
        )


@router.get("/solo")
def get_solo_crossword():
    """
    GET /crossword/solo
    Returns the daily solo play crossword from solo_play.json.
    """
    file_path = Path(__file__).parent.parent / "solo_play.json"

    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail="No solo_play.json file found. Wait for daily generation."
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"success": True, "data": data}
    except Exception as e:
        print("Error reading solo_play.json:", e)
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to read solo_play.json: {e}"
        )


@router.get("/battle")
def get_battle_crossword():
    """
    GET /crossword/battle
    Returns the daily battle play crossword from battle_play.json.
    """
    file_path = Path(__file__).parent.parent / "battle_play.json"

    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail="No battle_play.json file found. Wait for daily generation."
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"success": True, "data": data}
    except Exception as e:
        print("Error reading battle_play.json:", e)
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to read battle_play.json: {e}"
        )