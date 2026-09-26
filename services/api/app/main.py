import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, policies, search
from app.api.errors import RequestIdMiddleware, install_error_handlers
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    app = FastAPI(
        title="Clause compliance API",
        version="0.1.0",
        description=(
            "Policy compliance service for Clause. Demo data is a fictional organization's "
            "policies, not real policy, law or regulatory guidance."
        ),
    )
    app.add_middleware(RequestIdMiddleware)
    # The web app is served same-origin through the Vite proxy or reverse proxy; CORS only
    # admits the configured development origins.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Idempotency-Key", "Last-Event-ID", "X-Request-ID"],
    )
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(policies.router)
    app.include_router(search.router)
    return app


app = create_app()
