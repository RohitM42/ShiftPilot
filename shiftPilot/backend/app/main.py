from fastapi import FastAPI
from app.api.routes import auth, users

app = FastAPI(title="ShiftPilot API", version="0.1.0")

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}