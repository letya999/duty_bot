"""Base repository with standard CRUD operations."""

from typing import Generic, TypeVar, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import DeclarativeBase

ModelT = TypeVar('ModelT', bound=DeclarativeBase)


class BaseRepository(Generic[ModelT]):
    """Generic repository providing standard CRUD operations."""

    def __init__(self, db: AsyncSession, model_class: type[ModelT]):
        self.db = db
        self.model_class = model_class

    async def get_by_id(self, entity_id: int) -> Optional[ModelT]:
        """Get entity by primary key ID."""
        return await self.db.get(self.model_class, entity_id)

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[ModelT]:
        """List all entities with pagination."""
        stmt = select(self.model_class).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, obj_in: dict) -> ModelT:
        """Create new entity."""
        db_obj = self.model_class(**obj_in)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(self, entity_id: int, obj_in: dict) -> Optional[ModelT]:
        """Update entity by ID."""
        db_obj = await self.get_by_id(entity_id)
        if not db_obj:
            return None

        for key, value in obj_in.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, value)

        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, entity_id: int) -> bool:
        """Delete entity by ID."""
        db_obj = await self.get_by_id(entity_id)
        if not db_obj:
            return False

        await self.db.delete(db_obj)
        await self.db.commit()
        return True

    async def execute(self, stmt: Any) -> Any:
        """Execute raw SQLAlchemy statement."""
        return await self.db.execute(stmt)
