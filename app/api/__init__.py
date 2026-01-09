"""FastAPI application for CleanSlate."""
from fastapi import FastAPI

app = FastAPI(title="CleanSlate", version="0.0.1")


@app.get("/health")
async def health_check():
    """Healthcheck endpoint."""
    return {"status": "ok"}
