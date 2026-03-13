"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import init_db
from app.models.schemas import HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup and shutdown logic for the application."""
    logger.info("Initializing database tables")
    init_db()
    logger.info("Application ready (LLM provider: %s)", settings.llm_provider)
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title="LLM-Project",
    description="RAG-powered AI assistant — chat freely or upload documents and ask questions about them",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register API routers
from app.api import chat, conversations, documents  # noqa: E402

app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")


@app.get("/", include_in_schema=False)
def serve_frontend() -> FileResponse:
    """Serve the frontend HTML page."""
    return FileResponse("static/index.html")


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health_check() -> dict:
    """Check application health status."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "llm_provider": settings.llm_provider,
    }
