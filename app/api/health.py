"""Health endpoints (SDD 23.1): liveness and readiness probes."""

from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error shape for all endpoints (SDD 23)."""

    error: ErrorBody


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    """Liveness: the process is up. No dependencies, no I/O."""
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=None, responses={503: {"model": ErrorResponse}})
async def readyz() -> JSONResponse:
    """Readiness probe. PLACEHOLDER: always reports not ready.

    TODO(Spike 1): replace with the real check per SDD 23.1: DB schema health
    (FR-SES-09), config loaded, KB version readable. On success return
    200 {"status": "ready", "kb_version": ...}.
    """
    body = ErrorResponse(error=ErrorBody(code="NOT_CONFIGURED", message="not configured"))
    return JSONResponse(status_code=503, content=body.model_dump())
