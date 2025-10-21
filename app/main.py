from fastapi import FastAPI
from app.db import supabase
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configure CORS, allows requests from frontend dev servers
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


#@app.get("/users")
#def get_users():
#    data = supabase.table("users").select("*").execute()
#    return data.data
