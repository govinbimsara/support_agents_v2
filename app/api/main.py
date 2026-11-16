"""Chat API application entry point.

Run locally: `uv run uvicorn app.api.main:app --reload`
"""

from fastapi import FastAPI

from app.api.health import router as health_router


def create_app() -> FastAPI:
    """Build the FastAPI app. No I/O happens here."""
    app = FastAPI(title="Genie Business Support Agent API")
    app.include_router(health_router)
    return app


app = create_app()
