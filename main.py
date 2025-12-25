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
    name TEXT,
    message TEXT,
    trial_credits INTEGER DEFAULT 3,
    is_paid BOOLEAN DEFAULT 0
)
""")
conn.commit()

# Pydantic model for incoming requests (Free Trial)
class TrialRequest(BaseModel):
    name: str
    email: str
    message: str

# Health check route
@app.get("/")
def health():
    return {"status": "ok"}

# Free trial route
@app.post("/free-trial")
def free_trial(data: TrialRequest):
    cursor.execute("SELECT trial_credits FROM users WHERE email = ?", (data.email,))
    row = cursor.fetchone()

    if row:
        # User exists, return remaining trial credits
        remaining = row[0]
    else:
        # New user: insert with 3 trial credits
        cursor.execute(
            "INSERT INTO users (email, name, message, trial_credits) VALUES (?, ?, ?, ?)",
            (data.email, data.name, data.message, 3)
        )
        conn.commit()
        remaining = 3

    return {
        "status": "success",
        "email": data.email,
        "trial_credits_remaining": remaining,
        "reply": "Backend is working."
    }

# Deduct one trial credit
@app.post("/grant_trial")
def grant_trial(user: TrialRequest):
    cursor.execute("SELECT trial_credits FROM users WHERE email = ?", (user.email,))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    if row[0] <= 0:
        raise HTTPException(status_code=400, detail="No trial credits left")

    cursor.execute(
        "UPDATE users SET trial_credits = trial_credits - 1 WHERE email = ?",
        (user.email,)
    )
    conn.commit()

    remaining = cursor.execute(
        "SELECT trial_credits FROM users WHERE email = ?", (user.email,)
    ).fetchone()[0]

    return {"status": "ok", "trial_credits_remaining": remaining}
