from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import psycopg2

app = FastAPI()

# Connect to Postgres using Railway DATABASE_URL
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Create users table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    trial_credits INTEGER DEFAULT 3,
    is_paid BOOLEAN DEFAULT FALSE
)
""")
conn.commit()

# Request model
class TrialRequest(BaseModel):
    email: str
    name: str
    message: str

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/free-trial")
def free_trial(data: TrialRequest):
    # Fetch user from DB
    cursor.execute("SELECT trial_credits, is_paid FROM users WHERE email=%s", (data.email,))
    user = cursor.fetchone()

    if user:
        trial_credits, is_paid = user
        if is_paid:
            # Paid users: no trial deduction
            remaining = trial_credits
        else:
            if trial_credits <= 0:
                return {
                    "status": "trial_ended",
                    "email": data.email,
                    "trial_credits_remaining": 0,
                    "message": "Your free trial is over. Please upgrade to a paid plan to continue using CalmReply."
                }
            # Deduct 1 trial credit
            cursor.execute(
                "UPDATE users SET trial_credits = trial_credits - 1 WHERE email=%s",
                (data.email,)
            )
            conn.commit()
            remaining = cursor.execute(
                "SELECT trial_credits FROM users WHERE email=%s",
                (data.email,)
            ).fetchone()[0]
    else:
        # New user: add to DB with 3 trial credits, deduct 1
        cursor.execute(
            "INSERT INTO users (email, trial_credits) VALUES (%s, %s)",
            (data.email, 2)
        )
        conn.commit()
        remaining = 2

    return {
        "status": "success",
        "email": data.email,
        "trial_credits_remaining": remaining,
        "reply": "Backend is working."
    }
