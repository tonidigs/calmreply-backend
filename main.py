from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class TrialRequest(BaseModel):
    name: str
    email: str
    message: str

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/free-trial")
def free_trial(data: TrialRequest):
    return {
        "status": "success",
        "email": data.email,
        "reply": "This is a test reply. Backend is working."
    }
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class TrialRequest(BaseModel):
    email: str

@app.post("/free-trial")
def free_trial(data: TrialRequest):
    # For now, just confirm receipt
    # Later this is where we’ll store “3 trial credits”
    return {
        "email": data.email,
        "trial_credits_granted": 3
    }

@app.get("/")
def root():
    return {"status": "ok"}
    # main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3

app = FastAPI()

# Connect to SQLite database (file will be created automatically)
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    trial_credits INTEGER DEFAULT 3,
    is_paid BOOLEAN DEFAULT 0
)
""")
conn.commit()

# Pydantic model for incoming requests
class User(BaseModel):
    email: str

@app.post("/grant_trial")
def grant_trial(user: User):
    cursor.execute("SELECT trial_credits FROM users WHERE email = ?", (user.email,))
    row = cursor.fetchone()

    if row:
        if row[0] <= 0:
            raise HTTPException(status_code=400, detail="No trial credits left")
        # Deduct 1 trial credit
        cursor.execute("UPDATE users SET trial_credits = trial_credits - 1 WHERE email = ?", (user.email,))
    else:
        # Add new user with 3 trial credits, deduct 1
        cursor.execute("INSERT INTO users (email, trial_credits) VALUES (?, ?)", (user.email, 2))

    conn.commit()
    return {"status": "ok", "trial_credits_remaining": cursor.execute("SELECT trial_credits FROM users WHERE email = ?", (user.email,)).fetchone()[0]}


