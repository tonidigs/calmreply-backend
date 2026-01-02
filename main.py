from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import os
import psycopg2
import stripe

app = FastAPI()

# Database connection
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

# Stripe secret key and webhook signing secret
stripe.api_key = os.environ.get("STRIPE_API_KEY")  # Set this in Railway environment
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")  # Set this in Railway environment

# Existing trial endpoint
class TrialRequest(BaseModel):
    email: str
    name: str
    message: str

@app.post("/free-trial")
def free_trial(data: TrialRequest):
    cursor.execute("SELECT trial_credits, is_paid FROM users WHERE email=%s", (data.email,))
    user = cursor.fetchone()

    if user:
        trial_credits, is_paid = user
        if is_paid:
            return {
                "status": "success",
                "email": data.email,
                "trial_credits_remaining": trial_credits,
                "reply": "You are a paid user. Unlimited access granted."
            }
        if trial_credits <= 0:
            return {
                "status": "trial_ended",
                "email": data.email,
                "trial_credits_remaining": 0,
                "message": "Your free trial is over. Please upgrade to a paid plan to continue using CalmReply."
            }
        cursor.execute(
            "UPDATE users SET trial_credits = trial_credits - 1 WHERE email=%s",
            (data.email,)
        )
        conn.commit()
        remaining = cursor.execute("SELECT trial_credits FROM users WHERE email=%s", (data.email,)).fetchone()[0]
        return {"status": "success", "email": data.email, "trial_credits_remaining": remaining, "reply": "Backend is working."}
    else:
        # New user, insert with 2 remaining trials
        cursor.execute("INSERT INTO users (email, trial_credits) VALUES (%s, %s)", (data.email, 2))
        conn.commit()
        return {"status": "success", "email": data.email, "trial_credits_remaining": 2, "reply": "Backend is working."}

# Stripe webhook endpoint to mark paid users
@app.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=sig_header, secret=STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the checkout.session.completed event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = session.get("customer_email")
        if customer_email:
            cursor.execute("UPDATE users SET is_paid = TRUE WHERE email=%s", (customer_email,))
            conn.commit()
            print(f"User {customer_email} upgraded to paid.")

    return {"status": "success"}
