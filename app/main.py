from fastapi import FastAPI
from app.db import get_supabase
from fastapi.middleware.cors import CORSMiddleware
from app.routes import stats, invites
from dotenv import load_dotenv
from app.routes import crossword as crossword_router

load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://crosswars-988ycwmvo-jacquis-projects-6689649a.vercel.app",
        "*",
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
