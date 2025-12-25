"""Repository for RotationConfig model."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import RotationConfig
from app.repositories.base_repository import BaseRepository


class RotationConfigRepository(BaseRepository[RotationConfig]):
    """Repository for RotationConfig operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, RotationConfig)

    async def get_by_team(self, team_id: int) -> Optional[RotationConfig]:
        """Get rotation config for team."""
        stmt = select(RotationConfig).where(RotationConfig.team_id == team_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_member_list(self, team_id: int, member_ids: list) -> Optional[RotationConfig]:
        """Update rotation member list."""
        config = await self.get_by_team(team_id)
        if config:
            config.member_ids = member_ids
            await self.db.commit()
            await self.db.refresh(config)
        return config

    async def update_last_assigned(self, team_id: int, user_id: int, assigned_date) -> Optional[RotationConfig]:
        """Update last assigned user and date."""
        config = await self.get_by_team(team_id)
        if config:
            config.last_assigned_user_id = user_id
            config.last_assigned_date = assigned_date
            await self.db.commit()
            await self.db.refresh(config)
        return config

    async def toggle_enabled(self, team_id: int, enabled: bool) -> Optional[RotationConfig]:
        """Enable or disable rotation."""
        config = await self.get_by_team(team_id)
        if config:
            config.enabled = enabled
            await self.db.commit()
            await self.db.refresh(config)
        return config

    async def enable_rotation(self, team_id: int, member_ids: list[int]) -> RotationConfig:
        """Enable rotation for team with member order."""
        config = await self.get_by_team(team_id)

        if config:
            # Update existing config
            config.enabled = True
            config.member_ids = member_ids
            if not config.last_assigned_user_id and member_ids:
                config.last_assigned_user_id = member_ids[0]
            await self.db.commit()
            await self.db.refresh(config)
        else:
            # Create new config
            config = await self.create({
                'team_id': team_id,
                'enabled': True,
                'member_ids': member_ids,
                'last_assigned_user_id': member_ids[0] if member_ids else None,
            })

        return config

    async def update_last_assigned_for_rotation(self, team_id: int, user_id: int, assigned_date) -> Optional[RotationConfig]:
        """Update last assigned user and date for rotation."""
        config = await self.get_by_team(team_id)
        if config:
            config.last_assigned_user_id = user_id
            config.last_assigned_date = assigned_date
            await self.db.commit()
            await self.db.refresh(config)
        return config
