from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.base import Base



def _async_database_url(database_url: str) -> str:
    """Normalize Render's postgres URLs for SQLAlchemy's asyncpg dialect."""
    if database_url.startswith("postgres://"):
        database_url = "postgresql+asyncpg://" + database_url.removeprefix("postgres://")
    elif database_url.startswith("postgresql://"):
        database_url = "postgresql+asyncpg://" + database_url.removeprefix("postgresql://")

    # asyncpg expects `ssl=require`, while hosted PostgreSQL URLs commonly use
    # libpq's `sslmode=require` query parameter.
    parts = urlsplit(database_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if query.get("sslmode") and "ssl" not in query:
        query["ssl"] = query.pop("sslmode")
        database_url = urlunsplit(parts._replace(query=urlencode(query)))
    return database_url


database_url = _async_database_url(settings.DATABASE_URL)
engine_options: dict[str, object] = {
    "pool_pre_ping": True,
    "echo": settings.DEBUG,
    "future": True,
}
if database_url.startswith("postgresql"):
    engine_options.update(
        {
            "pool_recycle": 1800,
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 30,
        }
    )

engine = create_async_engine(database_url, **engine_options)

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
        # Import all mapped classes before create_all, including when run_local.py
        # initializes the database without importing the FastAPI application.
        from app import models as _models

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
