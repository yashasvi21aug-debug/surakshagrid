from collections.abc import AsyncGenerator

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.base import Base

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

database_available = False
database_error: Exception | None = None


async def init_db() -> None:
    global database_available, database_error

    try:
        async with engine.begin() as conn:
            if engine.dialect.name == "postgresql":
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            await conn.run_sync(Base.metadata.create_all)
    except Exception as error:
        database_available = False
        database_error = error
        raise
    else:
        database_available = True
        database_error = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if not database_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable; SurakshaGrid is running in mock mode.",
        )

    async with AsyncSessionLocal() as session:
        yield session
