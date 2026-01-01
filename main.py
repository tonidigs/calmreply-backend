from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import psycopg2

app = FastAPI()

# Railway provides DATABASE_URL automatically
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

class TrialRequest(BaseModel):
    name: str
    email: str
    message: str

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/free-trial")
def free_trial(data: TrialRequest):
    cursor.execute(
        "SELECT trial_credits, is_paid FROM users WHERE email=%s",
        (data.email,)
    )
    user = cursor.fetchone()

    if user:
        trial_credits, is_paid = user

        if not is_paid and trial_credits <= 0:
            raise HTTPException(status_code=403, detail="No trial credits left")

        if not is_paid:
            cursor.execute(
                "UPDATE users SET trial_credits = trial_credits - 1 WHERE email=%s",
                (data.email,)
            )
    else:
        # New user gets 3 trials, consume 1 immediately
        cursor.execute(
            "INSERT INTO users (email, trial_credits) VALUES (%s, %s)",
            (data.email, 2)
        )

    conn.commit()

    cursor.execute(
        "SELECT trial_credits FROM users WHERE email=%s",
        (data.email,)
    )
    remaining = cursor.fetchone()[0]

    return {
        "status": "success",
        "email": data.email,
        "trial_credits_remaining": remaining,
        "reply": "Backend is working."
    }
