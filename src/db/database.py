"""
Database connection manager.
Supports both async (FastAPI) and sync (scheduler) access patterns.
"""
import logging
from contextlib import asynccontextmanager, contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session

from src.config import config
from src.db.models import Base

logger = logging.getLogger(__name__)

# ── Derive sync URL from async URL ───────────────────
_async_url = config.env.database_url
# Convert async URL to sync (e.g., sqlite+aiosqlite:// → sqlite:// , postgresql+asyncpg:// → postgresql://)
_sync_url = _async_url.replace("+aiosqlite", "").replace("+asyncpg", "")

# ── Async engine (for FastAPI + async pipeline) ─────
async_engine = create_async_engine(
    _async_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Sync engine (for scheduler + migrations) ────────
sync_engine = create_engine(
    _sync_url,
    echo=False,
    pool_size=5,
)

SyncSessionLocal = sessionmaker(bind=sync_engine)


# ── Session helpers ─────────────────────────────────

@asynccontextmanager
async def get_async_session():
    """Async context manager for DB sessions."""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@contextmanager
def get_sync_session():
    """Sync context manager for DB sessions."""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def get_session():
    """Dependency for FastAPI routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables (run once on startup)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")


async def close_db():
    """Cleanup on shutdown."""
    await async_engine.dispose()
