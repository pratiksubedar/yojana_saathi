from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import settings
from app.db.session import check_db_health
from app.services.llm.gateway import LLMGateway

router = APIRouter()


class DatabaseStatus(BaseModel):
    status: str = Field(..., description="CONNECTED, NOT_INITIALIZED, or DISCONNECTED")
    type: str = Field(default="SQLite (aiosqlite)", description="Underlying database driver")
    initialized: bool = Field(default=False, description="True if schema tables exist")
    schemes_indexed: int = Field(default=0, description="Count of active schemes in database")
    message: Optional[str] = Field(default=None, description="Detailed diagnostic message")


class ServiceStatus(BaseModel):
    backend: str = Field(default="READY", description="Backend ASGI status")
    database: DatabaseStatus = Field(..., description="Live database connectivity and initialization status")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall system health status: HEALTHY, NEEDS_INITIALIZATION, or UNHEALTHY")
    version: str = Field(..., description="API software version")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of the health check")
    environment: str = Field(..., description="Application execution environment")
    services: ServiceStatus = Field(..., description="Individual service readiness states")
    supported_languages: List[str] = Field(
        default=["en", "hi", "kn", "te"],
        description="Four project-supported Indian language codes"
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System Health & Diagnostic Check",
    description="Returns live service availability, database initialization status, scheme count, and supported languages."
)
async def get_health() -> HealthResponse:
    db_info = await check_db_health()
    db_connected = db_info.get("status") == "CONNECTED"
    overall_status = "HEALTHY" if db_connected else ("NEEDS_INITIALIZATION" if db_info.get("status") == "NOT_INITIALIZED" else "UNHEALTHY")

    return HealthResponse(
        status=overall_status,
        version=settings.version,
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment=settings.environment,
        services=ServiceStatus(
            backend="READY",
            database=DatabaseStatus(
                status=db_info.get("status", "UNKNOWN"),
                type=db_info.get("database", "SQLite (aiosqlite)"),
                initialized=db_info.get("initialized", False),
                schemes_indexed=db_info.get("schemes_indexed", 0),
                message=db_info.get("message")
            )
        ),
        supported_languages=["en", "hi", "kn", "te"]
    )


@router.get(
    "/health/llm",
    summary="LLM Provider Gateway Health & Status",
    description="Returns live availability and diagnostic status of registered LLM providers without revealing API keys or secret credentials."
)
async def get_llm_health() -> Dict[str, Any]:
    gateway = LLMGateway()
    return await gateway.get_gateway_status()
