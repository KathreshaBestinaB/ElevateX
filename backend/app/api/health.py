"""Health check endpoint — used for uptime checks and to verify the API (and Firebase) are reachable."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.firebase.client import is_firebase_configured

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    firebase_configured: bool


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", firebase_configured=is_firebase_configured())
