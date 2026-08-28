import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Read DATABASE_URL or fallback to local SQLite
raw_db_url = os.getenv("DATABASE_URL", "").strip()

if not raw_db_url:
    DATABASE_URL = "sqlite:///./surakshagrid.db"
else:
    # Render PostgreSQL URLs start with postgres://, but SQLAlchemy requires postgresql://
    if raw_db_url.startswith("postgres://"):
        DATABASE_URL = raw_db_url.replace("postgres://", "postgresql://", 1)
    else:
        DATABASE_URL = raw_db_url

# SQLite requires check_same_thread=False
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency for injecting database sessions into FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initializes tables on startup."""
    Base.metadata.create_all(bind=engine)