from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import psycopg2

app = FastAPI()

# Connect to Postgres using DATABASE_URL from Railway environment variables
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

# Request body model
class TrialRequest(BaseModel):
    email: str
    name: str
    message: str

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/free-trial")
def free_trial(data: TrialRequest):
    # Check if user exists
    cursor.execute("SELECT trial_credits, is_paid FROM users WHERE email=%s", (data.email,))
    user = cursor.fetchone()

    if user:
        trial_credits, is_paid = user

        if is_paid:
            # Paid users get unlimited access
            return {
                "status": "success",
                "email": data.email,
                "trial_credits_remaining": trial_credits,
                "reply": "You are a paid user. Enjoy unlimited access!"
            }

        if trial_credits <= 0:
            # Trial ended → prompt to pay
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
        cursor.execute("SELECT trial_credits FROM users WHERE email=%s", (data.email,))
        remaining = cursor.fetchone()[0]

        return {
            "status": "success",
            "email": data.email,
            "trial_credits_remaining": remaining,
            "reply": "Backend is working."
        }

    else:
        # New user → create with 3 trials, deduct 1 immediately
        cursor.execute(
            "INSERT INTO users (email, trial_credits) VALUES (%s, %s)",
            (data.email, 2)
        )
        conn.commit()
        return {
            "status": "success",
            "email": data.email,
            "trial_credits_remaining": 2,
            "reply": "Backend is working. You have 2 trial credits remaining."
        }
