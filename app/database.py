from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from sqlalchemy.pool import NullPool, QueuePool
from app.config import get_settings
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
settings = get_settings()
# Configure engine with:
# - pool_pre_ping=True: validates connections before using them (detects closed connections)
# - pool_recycle=3600: recycle connections every hour to avoid stale connections
# - max_overflow=10: allow overflow connections beyond pool size
# - pool_size=10: number of connections to keep in pool
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,   # Recycle connections every hour
    pool_size=10,        # Connection pool size
    max_overflow=10,     # Allow overflow beyond pool size
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_db():
    """Dependency for getting database session"""
    async with AsyncSessionLocal() as session:
        yield session


async def apply_migrations():
    """Apply SQL migrations from migrations directory"""
    migrations_dir = Path(__file__).parent.parent / 'migrations'

    if not migrations_dir.exists():
        logger.info("No migrations directory found")
        return

    migration_files = sorted(migrations_dir.glob('*.sql'))
    if not migration_files:
        logger.info("No SQL migration files found")
        return

    async with engine.begin() as conn:
        for migration_file in migration_files:
            try:
                logger.info(f"Applying migration: {migration_file.name}")
                migration_sql = migration_file.read_text()

                # Split by semicolon and execute each statement
                statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
                for statement in statements:
                    await conn.execute(text(statement))

                logger.info(f"✓ Migration applied: {migration_file.name}")
            except Exception as e:
                logger.warning(f"Migration {migration_file.name} already applied or error: {e}")


async def init_db():
    """Initialize database tables"""
    # Apply SQL migrations first
    await apply_migrations()

    # Create ORM tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized successfully")


async def close_db():
    """Close database connection"""
    await engine.dispose()


class AsyncSessionWithRetry:
    """
    Async context manager that wraps AsyncSessionLocal with retry logic
    for handling transient connection errors.
    """

    def __init__(self, max_retries=3, initial_delay=0.1, backoff_factor=2.0):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.session = None

    async def __aenter__(self):
        from app.utils import retry_on_connection_error

        async def get_session():
            """Create and return a session"""
            # We enter the session context manager and return the session object
            ctx = AsyncSessionLocal()
            return await ctx.__aenter__(), ctx

        # Retry to get a session in case of connection issues
        self.session, self.ctx = await retry_on_connection_error(
            get_session,
            max_retries=self.max_retries,
            initial_delay=self.initial_delay,
            backoff_factor=self.backoff_factor,
        )
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.ctx:
            await self.ctx.__aexit__(exc_type, exc_val, exc_tb)


def get_db_with_retry(max_retries=3, initial_delay=0.1, backoff_factor=2.0):
    """
    Get a database session with automatic retry on connection errors.

    Args:
        max_retries: Number of retries for connection errors
        initial_delay: Initial delay in seconds before retry
        backoff_factor: Multiply delay by this factor for each retry

    Returns:
        Async context manager that provides a database session

    Usage:
        async with get_db_with_retry() as session:
            # Use session here
            pass
    """
    return AsyncSessionWithRetry(
        max_retries=max_retries,
        initial_delay=initial_delay,
        backoff_factor=backoff_factor,
    )
