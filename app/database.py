from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base

logger = logging.getLogger(__name__)

raw_db_url = os.getenv("DATABASE_URL", "").strip()

if not raw_db_url:
    SYNC_DATABASE_URL = "sqlite:///./surakshagrid.db"
    ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./surakshagrid.db"
else:
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

    if raw_db_url.startswith("postgresql://") and not raw_db_url.startswith("postgresql+asyncpg://"):
        ASYNC_DATABASE_URL = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        SYNC_DATABASE_URL = raw_db_url
    else:
        ASYNC_DATABASE_URL = raw_db_url
        SYNC_DATABASE_URL = raw_db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if SYNC_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(SYNC_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    connect_args={"check_same_thread": False} if ASYNC_DATABASE_URL.startswith("sqlite") else {},
)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)


def get_db() -> Generator[Session, None, None]:
    """Dependency injecting synchronous database session into FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injecting asynchronous database session into FastAPI routes."""
    async with AsyncSessionLocal() as session:
        yield session


def init_db() -> None:
    """Initialize DDL schema tables on startup."""
    try:
        import app.models.user
        import app.models.incident
        import app.models.flood_zone
        import app.models.route_log
        import app.models.gis_models
        import app.models.spatial
        Base.metadata.create_all(bind=engine)
        logger.info("Successfully initialized database schema DDL tables.")
    except Exception as err:
        logger.warning("Could not execute Base.metadata.create_all DDL: %s", err)


async def init_db_async() -> None:
    """Initialize DDL schema tables on async engine."""
    try:
        import app.models  # Ensures all model tables register on Base.metadata
        from app.models.base import Base
        logger.info("Tables registered on Base.metadata: %s", list(Base.metadata.tables.keys()))
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Successfully initialized async database schema DDL tables.")
    except Exception as err:
        logger.warning("Could not execute async Base.metadata.create_all DDL: %s", err)



def run_migrations() -> None:
    """Execute lightweight DDL migrations."""
    init_db()