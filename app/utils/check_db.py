import asyncio
import logging
from app.database import init_db, engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_schema():
    logger.info("Initializing database (applying migrations)...")
    await init_db()

    async with engine.connect() as conn:
        logger.info("Checking 'user' table columns:")
        result = await conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'user'
        """))
        for row in result:
            logger.info(f"  - {row[0]}: {row[1]}")

        logger.info("Checking 'team' table columns:")
        result = await conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'team'
        """))
        for row in result:
            logger.info(f"  - {row[0]}: {row[1]}")

        logger.info("Checking 'workspace' table content:")
        result = await conn.execute(text("SELECT id, name, external_id FROM workspace"))
        for row in result:
            logger.info(f"  - ID: {row[0]}, Name: {row[1]}, External ID: {row[2]}")

if __name__ == "__main__":
    asyncio.run(check_schema())
