"""
Async database session management.
Works with both SQLite (development) and PostgreSQL (production).
"""
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool
from loguru import logger
from src.config import config
from src.db.models import Base


_db_url = config.env.database_url

# SQLite needs special handling: no pool, check_same_thread=False
if "sqlite" in _db_url:
    engine = create_async_engine(
        _db_url,
        echo=config.env.app_env == "development",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_async_engine(
        _db_url,
        echo=config.env.app_env == "development",
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

async_session = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db():
    """Create all tables. Use Alembic for migrations in production."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")


async def get_db() -> AsyncSession:
    """Dependency for FastAPI routes."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
