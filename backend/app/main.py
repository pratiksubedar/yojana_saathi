from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from sqlalchemy import func, select
from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError
from app.db.init_db import init_db
from app.db.models import Scheme
from app.db.seed import seed_schemes
from app.db.session import async_session_factory
from app.services.document_service import DocumentChecklistService

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: ensures tables exist, seeds schemes if empty, and purges expired ephemeral sessions on startup."""
    await init_db()
    async with async_session_factory() as session:
        count_res = await session.execute(select(func.count()).select_from(Scheme))
        scheme_count = count_res.scalar() or 0
        if scheme_count == 0:
            await seed_schemes()
        await DocumentChecklistService.cleanup_expired_sessions(session)
    yield


def create_application() -> FastAPI:
    """
    Application factory for Yojana Saathi (योजना साथी) Backend API.
    Configures CORS, routes, lifecycle, and OpenAPI documentation.
    """
    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        description=(
            "Multilingual Voice AI Assistant for Government Scheme Access (योजना साथी). "
            "Supports English, Hindi, Kannada, and Telugu with zero-cost local architecture."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Configure CORS for local React + Vite frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global structured error handler for domain exceptions
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error_code": exc.error_code,
                "timestamp": exc.timestamp,
            },
        )

    # Register master API router under /api/v1 prefix
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", summary="Root Welcome")
    async def root():
        index_file = FRONTEND_DIST / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)
        return JSONResponse({
            "message": "Welcome to Yojana Saathi API (योजना साथी)",
            "version": settings.version,
            "status": "ONLINE",
            "docs_url": "/docs",
            "health_url": f"{settings.api_v1_prefix}/health",
            "supported_languages": ["en", "hi", "kn", "te"]
        })

    # Serve the built React app from the same public service as the API.
    # This keeps browser requests on one origin and supports client-side routes.
    if FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app


app = create_application()

