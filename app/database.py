from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.config import get_settings
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False, future=True)
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
