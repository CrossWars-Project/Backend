from fastapi import FastAPI
from app.db import get_supabase
from fastapi.middleware.cors import CORSMiddleware
from app.routes import stats, invites
from dotenv import load_dotenv
from app.routes import crossword as crossword_router
import threading
import time
import requests
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    # return the message expected by tests
    return {"message": "Hello from FastAPI backend!"}


@app.get("/users")
def get_users():
    supabase = get_supabase()
    data = supabase.table("users").select("*").execute()
    return data.data


app.include_router(stats.router, prefix="/stats", tags=["Stats"])
app.include_router(invites.router, prefix="/invites", tags=["invites"])
app.include_router(crossword_router.router, prefix="/crossword", tags=["Crossword"])


# ============== DAILY CROSSWORD SCHEDULER ==============

GENERATOR_URL = "http://127.0.0.1:8000/crossword/generate"
APP_DIR = Path(__file__).parent
LATEST_JSON_PATH = APP_DIR / "latest_crossword.json"
SOLO_JSON_PATH = APP_DIR / "solo_play.json"
BATTLE_JSON_PATH = APP_DIR / "battle_play.json"

THEMES = [
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


def get_theme_for_today(offset=0):
    """Get theme based on day of year (consistent daily theme)."""
    day_of_year = datetime.now().timetuple().tm_yday + offset
    return THEMES[day_of_year % len(THEMES)]


def delete_all_crossword_files():
    """Delete all three crossword JSON files."""
    files_deleted = []
    for file_path in [LATEST_JSON_PATH, SOLO_JSON_PATH, BATTLE_JSON_PATH]:
        try:
            if file_path.exists():
                os.remove(file_path)
                files_deleted.append(file_path.name)
                print(f"[{datetime.now()}] Deleted {file_path.name}")
        except Exception as e:
            print(f"[{datetime.now()}] Error deleting {file_path.name}: {e}")

    if files_deleted:
        print(f"[{datetime.now()}] Deleted files: {', '.join(files_deleted)}")
    else:
        print(f"[{datetime.now()}] No files to delete")

    return len(files_deleted) > 0


def generate_crossword_with_theme(theme):
    """Make POST request to generate crossword with specific theme."""
    print(f"[{datetime.now()}] Generating crossword with theme: {theme}")

    try:
        response = requests.post(GENERATOR_URL, json={"theme": theme}, timeout=60)

        if response.status_code == 200:
            print(
                f"[{datetime.now()}] Successfully generated crossword with theme '{theme}'"
            )
            return True
        else:
            print(
                f"[{datetime.now()}] Failed to generate crossword: {response.status_code}"
            )
            return False
    except Exception as e:
        print(f"[{datetime.now()}] Error generating crossword: {e}")
        return False


def copy_latest_to_file(destination_path):
    """Copy latest_crossword.json to destination file."""
    try:
        if not LATEST_JSON_PATH.exists():
            print(f"[{datetime.now()}] ERROR: latest_crossword.json not found!")
            return False

        shutil.copy2(LATEST_JSON_PATH, destination_path)
        print(f"[{datetime.now()}] Copied to {destination_path.name}")
        return True
    except Exception as e:
        print(f"[{datetime.now()}] Error copying to {destination_path.name}: {e}")
        return False


def generate_daily_crosswords():
    """Generate both solo and battle crosswords."""
    print("=" * 60)
    print(f"[{datetime.now()}] Starting daily crossword generation")
    print("=" * 60)

    # Generate Solo Play crossword
    solo_theme = get_theme_for_today(offset=0)
    print(f"[{datetime.now()}] Generating SOLO crossword...")
    if generate_crossword_with_theme(solo_theme):
        time.sleep(2)  # Brief pause to ensure file is written
        if copy_latest_to_file(SOLO_JSON_PATH):
            print(f"[{datetime.now()}] ✓ Solo crossword ready")
        else:
            print(f"[{datetime.now()}] ✗ Failed to save solo crossword")
    else:
        print(f"[{datetime.now()}] ✗ Failed to generate solo crossword")

    # Small delay between generations
    time.sleep(3)

    # Generate Battle Play crossword (use different theme)
    battle_theme = get_theme_for_today(offset=1)
    print(f"[{datetime.now()}] Generating BATTLE crossword...")
    if generate_crossword_with_theme(battle_theme):
        time.sleep(2)  # Brief pause to ensure file is written
        if copy_latest_to_file(BATTLE_JSON_PATH):
            print(f"[{datetime.now()}] ✓ Battle crossword ready")
        else:
            print(f"[{datetime.now()}] ✗ Failed to save battle crossword")
    else:
        print(f"[{datetime.now()}] ✗ Failed to generate battle crossword")

    print("=" * 60)
    print(f"[{datetime.now()}] Daily crossword generation complete")
    print("=" * 60)


def get_seconds_until(target_hour, target_minute):
    """Calculate seconds until target time."""
    now = datetime.now()
    target = now.replace(
        hour=target_hour, minute=target_minute, second=0, microsecond=0
    )

    if target <= now:
        target += timedelta(days=1)

    return (target - now).total_seconds()


def scheduler_loop():
    """Main scheduler loop that runs in background thread."""
    print("=" * 60)
    print("Daily Crossword Scheduler Started")
    print(f"Solo Play file: {SOLO_JSON_PATH}")
    print(f"Battle Play file: {BATTLE_JSON_PATH}")
    print(f"Generator endpoint: {GENERATOR_URL}")
    print("=" * 60)

    # Generate immediately if files don't exist
    if not SOLO_JSON_PATH.exists() or not BATTLE_JSON_PATH.exists():
        print(
            f"[{datetime.now()}] One or more crossword files missing. Generating now..."
        )
        time.sleep(2)  # Wait for server to be fully ready
        generate_daily_crosswords()
    else:
        print(
            f"[{datetime.now()}] Both crossword files exist. Waiting for next scheduled time."
        )

    while True:
        try:
            # Calculate time until 11:59 PM
            seconds_until_delete = get_seconds_until(23, 59)
            hours_remaining = seconds_until_delete / 3600
            print(
                f"[{datetime.now()}] Next deletion in {hours_remaining:.1f} hours (at 11:59 PM)"
            )

            # Sleep until 11:59 PM
            time.sleep(seconds_until_delete)

            # Delete all files at 11:59 PM
            print(f"[{datetime.now()}] 11:59 PM - Deleting old crossword files...")
            delete_all_crossword_files()

            # Wait 1 minute until midnight
            print(f"[{datetime.now()}] Waiting 1 minute until midnight...")
            time.sleep(60)

            # Generate new crosswords at 12:00 AM
            generate_daily_crosswords()

        except Exception as e:
            print(f"[{datetime.now()}] Unexpected error in scheduler: {e}")
            import traceback

            traceback.print_exc()
            time.sleep(60)


@app.on_event("startup")
async def startup_event():
    """Start the scheduler when FastAPI starts."""
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()
    print("Daily crossword scheduler started in background thread")
