from fastapi import FastAPI
from app.db import supabase

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello from FastAPI + Supabase!"}

@app.get("/users")
def get_users():
    data = supabase.table("users").select("*").execute()
    return data.data
