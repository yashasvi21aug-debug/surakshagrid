import os
from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context

from app.models.base import Base
import app.models  # Import all canonical models for PostGIS table & index detection

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Retrieve and sanitize DATABASE_URL environment variable for Alembic migration compatibility."""
    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url") or ""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "")
    return url


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    db_url = get_database_url()
    config.set_main_option("sqlalchemy.url", db_url)

    engine = create_engine(db_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
