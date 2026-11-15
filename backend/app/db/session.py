import json
from typing import AsyncGenerator, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# Create async engine for SQLite (using aiosqlite)
async_engine = create_async_engine(
    settings.database_url,
    echo=False,  # Set to False to keep logs clean; can be overridden via settings.debug
    future=True,
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
)

# Async session factory
async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an isolated asynchronous database session.
    Automatically commits or rolls back on exceptions and closes the session.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> Dict[str, Any]:
    """
    Actively checks SQLite database connectivity and table initialization.
    Does NOT falsely report ready if tables are not initialized.
    """
    try:
        async with async_engine.connect() as conn:
            # 1. Verify low-level connection
            await conn.execute(text("SELECT 1"))

            # 2. Check if the 'schemes' table exists
            table_check = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='schemes'")
            )
            has_table = table_check.scalar() is not None

            if not has_table:
                return {
                    "status": "NOT_INITIALIZED",
                    "database": "SQLite (aiosqlite)",
                    "initialized": False,
                    "schemes_indexed": 0,
                    "message": "Database connected but tables have not been created. Run init_db."
                }

            # 3. Count seeded schemes
            count_res = await conn.execute(text("SELECT COUNT(*) FROM schemes WHERE is_active = 1"))
            scheme_count = count_res.scalar() or 0

            return {
                "status": "CONNECTED",
                "database": "SQLite (aiosqlite)",
                "initialized": True,
                "schemes_indexed": scheme_count,
                "message": f"Database connected and active with {scheme_count} scheme(s)."
            }

    except Exception as exc:
        return {
            "status": "DISCONNECTED",
            "database": "SQLite (aiosqlite)",
            "initialized": False,
            "schemes_indexed": 0,
            "error": str(exc)
        }

