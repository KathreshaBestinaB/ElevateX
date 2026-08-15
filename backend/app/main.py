"""
Application entrypoint.

Run with:
    uvicorn app.main:app --reload

Keep this file thin — it should only wire things together (config, logging,
middleware, routers). Business logic belongs in services/, data access in
repositories/, request/response shapes in models/.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health, patients, trials, outcomes, matching, analytics, research, documents, compliance, pipeline
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.firebase.client import FirebaseNotConfiguredError

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s (env=%s)", settings.app_name, settings.environment)
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description=(
        "Research decision-support prototype for matching synthetic patient "
        "records against clinical trial eligibility criteria. Not a substitute "
        "for physician, clinical researcher, or regulatory review."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(health.router)
app.include_router(patients.router)
app.include_router(trials.router)
app.include_router(outcomes.router)
app.include_router(matching.router)
app.include_router(analytics.router)
app.include_router(research.router)
app.include_router(documents.router)
app.include_router(compliance.router)
app.include_router(pipeline.router)


@app.exception_handler(FirebaseNotConfiguredError)
async def firebase_not_configured_handler(request: Request, exc: FirebaseNotConfiguredError) -> JSONResponse:
    logger.error("Firebase call failed at %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)},
    )
