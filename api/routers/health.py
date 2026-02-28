"""
Health Router — liveness / readiness probe.
"""

from fastapi import APIRouter
from schemas.models import HealthCheckResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthCheckResponse)
async def health():
    return HealthCheckResponse()
