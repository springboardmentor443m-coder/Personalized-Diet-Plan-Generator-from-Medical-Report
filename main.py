"""FastAPI application entry-point."""

import asyncio
import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import UPLOAD_DIR, SESSION_TTL_HOURS
from api.routers import health, reports, diet, tasks
from services.database import init_db, cleanup_old_sessions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Upload directory ready: %s", UPLOAD_DIR)

    init_db()

    # Schedule periodic session cleanup
    async def _cleanup_loop():
        while True:
            await asyncio.sleep(3600)  # every hour
            try:
                deleted = cleanup_old_sessions(SESSION_TTL_HOURS)
                if deleted:
                    logger.info("Periodic cleanup: removed %d old session(s)", deleted)
            except Exception:
                logger.exception("Cleanup task error")

    cleanup_task = asyncio.create_task(_cleanup_loop())

    yield

    # Shutdown
    cleanup_task.cancel()


app = FastAPI(
    title="Diet Plan Generator – Medical Report Processing",
    description=(
        "Processes medical reports (PDF/Image) and extracts structured "
        "patient data, test results, and BMI.  Supports single- and "
        "multi-document uploads with deterministic health-state aggregation "
        "and AI-powered personalised diet plan generation."
    ),
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check logs for details."},
    )


app.include_router(health.router)
app.include_router(reports.router)
app.include_router(diet.router)
app.include_router(tasks.router)
