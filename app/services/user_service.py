from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_by_telegram(self, telegram_username: str, display_name: str) -> User:
        """Get or create user by Telegram username"""
        stmt = select(User).where(User.telegram_username == telegram_username)
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if not user:
            user = User(
                telegram_username=telegram_username,
                display_name=display_name,
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)

        return user

    async def get_or_create_by_slack(self, slack_user_id: str, display_name: str) -> User:
        """Get or create user by Slack user ID"""
        stmt = select(User).where(User.slack_user_id == slack_user_id)
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if not user:
            user = User(
                slack_user_id=slack_user_id,
                display_name=display_name,
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)

        return user

    async def get_user(self, user_id: int) -> User | None:
        """Get user by ID"""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_user_by_telegram(self, telegram_username: str) -> User | None:
        """Get user by Telegram username"""
        stmt = select(User).where(User.telegram_username == telegram_username)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_user_by_slack(self, slack_user_id: str) -> User | None:
        """Get user by Slack user ID"""
        stmt = select(User).where(User.slack_user_id == slack_user_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_all_users(self) -> list[User]:
        """Get all users"""
        stmt = select(User)
        result = await self.db.execute(stmt)
        return result.scalars().all()
