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
