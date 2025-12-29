from app.models import User
from app.repositories import UserRepository, AdminLogRepository, UserAccountRepository
from typing import Optional


class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        admin_log_repo: AdminLogRepository = None,
        user_account_repo: UserAccountRepository = None
    ):
        self.user_repo = user_repo
        self.admin_log_repo = admin_log_repo
        self.user_account_repo = user_account_repo

    async def create_user(self, workspace_id: int, username: str, telegram_username: str = None, first_name: str = None, last_name: str = None, slack_user_id: str = None, telegram_id: int = None, display_name: str = None) -> User:
        """Create a new user and associated accounts"""
        if not display_name:
             if first_name and last_name:
                 display_name = f"{first_name} {last_name}"
             else:
                 display_name = first_name or username

        # Get organization_id from workspace
        from app.models import Workspace
        stmt_ws = select(Workspace.organization_id).where(Workspace.id == workspace_id)
        res_ws = await self.user_repo.db.execute(stmt_ws)
        organization_id = res_ws.scalar_one_or_none()

        # Create base user
        user = await self.user_repo.create({
            'workspace_id': workspace_id,
            'organization_id': organization_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'display_name': display_name
        })
        
        # Create UserAccounts
        if self.user_account_repo:
            if telegram_id:
                try:
                    await self.user_account_repo.create({
                        'user_id': user.id,
                        'workspace_id': workspace_id,
                        'provider': 'telegram',
                        'provider_id': str(telegram_id),
                        'username': telegram_username,
                        'account_email': None
                    })
                except Exception:
                    pass

            if slack_user_id:
                try:
                    await self.user_account_repo.create({
                        'user_id': user.id,
                        'workspace_id': workspace_id,
                        'provider': 'slack',
                        'provider_id': slack_user_id,
                        'username': None, # Slack username often not unique/stable or not passed here
                        'account_email': None
                    })
                except Exception:
                    pass
                    
        return user

    async def get_or_create_by_telegram(self, workspace_id: int, telegram_username: str, display_name: str, first_name: str = None, last_name: str = None, telegram_id: int = None) -> User:
        """Get or create user by Telegram username or ID in workspace"""
        user = None
        
        # 1. Try to find by telegram_id (via UserAccount)
        if telegram_id:
            user = await self.user_repo.get_by_telegram_id(workspace_id, telegram_id)
        
        # 2. If not found, try by username
        if not user and telegram_username:
            user = await self.user_repo.get_by_telegram_username(workspace_id, telegram_username)

        if not user:
            # Use get_settings to check for master admins
            from app.config import get_settings
            settings = get_settings()
            is_master = False
            if telegram_id and str(telegram_id) in settings.get_admin_ids('telegram'):
                is_master = True

            # Generate display_name if missing
            if not display_name:
                if first_name and last_name:
                    display_name = f"{first_name} {last_name}"
                else:
                     display_name = first_name or telegram_username or (str(telegram_id) if telegram_id else "Unknown")

            # Get organization_id from workspace
            from app.models import Workspace
            stmt_ws = select(Workspace.organization_id).where(Workspace.id == workspace_id)
            res_ws = await self.user_repo.db.execute(stmt_ws)
            organization_id = res_ws.scalar_one_or_none()

            # Create new user
            user = await self.user_repo.create({
                'workspace_id': workspace_id,
                'organization_id': organization_id,
                'username': telegram_username or (str(telegram_id) if telegram_id else None),
                'first_name': first_name,
                'last_name': last_name,
                'display_name': display_name,
                'is_admin': is_master
            })

            # Create UserAccount
            if self.user_account_repo and telegram_id:
                try:
                    await self.user_account_repo.create({
                        'user_id': user.id,
                        'workspace_id': workspace_id,
                        'provider': 'telegram',
                        'provider_id': str(telegram_id),
                        'username': telegram_username,
                        'account_email': None
                    })
                except Exception:
                    pass
        else:
            # Update info if it was missing
            update_data = {}
            if not user.username and telegram_username:
                update_data['username'] = telegram_username
            if first_name and not user.first_name:
                update_data['first_name'] = first_name
            if last_name and not user.last_name:
                update_data['last_name'] = last_name
            
            # If display_name is missing/empty, try to fill it
            if not user.display_name:
                 if first_name and last_name:
                     update_data['display_name'] = f"{first_name} {last_name}"
                 elif first_name:
                     update_data['display_name'] = first_name
                 elif telegram_username:
                     update_data['display_name'] = telegram_username

            # Sync master admin status
            from app.config import get_settings
            settings = get_settings()
            if telegram_id and str(telegram_id) in settings.get_admin_ids('telegram') and not user.is_admin:
                update_data['is_admin'] = True

            if update_data:
                user = await self.user_repo.update(user.id, update_data)

            # Ensure UserAccount exists or update it
            if self.user_account_repo and telegram_id:
                try:
                    # We might have found user by username but they missed the ID link
                    account = await self.user_account_repo.get_by_telegram_id(str(telegram_id), workspace_id)
                    if not account:
                        await self.user_account_repo.create({
                            'user_id': user.id,
                            'workspace_id': workspace_id,
                            'provider': 'telegram',
                            'provider_id': str(telegram_id),
                            'username': telegram_username,
                            'account_email': None
                        })
                    elif telegram_username and account.username != telegram_username:
                        # Update username in account if changed
                         await self.user_account_repo.update(account.id, {'username': telegram_username})
                except Exception:
                    pass

        return user

    async def get_or_create_by_slack(self, workspace_id: int, slack_user_id: str, display_name: str, first_name: str = None, last_name: str = None) -> User:
        """Get or create user by Slack user ID in workspace"""
        
        # 1. Try to find by slack_user_id (via UserAccount)
        user = await self.user_repo.get_by_slack_user_id(workspace_id, slack_user_id)

        if not user:
            # Generate default display_name if needed
            if not display_name:
                if first_name and last_name:
                    display_name = f"{first_name} {last_name}"
                else:
                    display_name = first_name or slack_user_id

            # Get organization_id from workspace
            from app.models import Workspace
            stmt_ws = select(Workspace.organization_id).where(Workspace.id == workspace_id)
            res_ws = await self.user_repo.db.execute(stmt_ws)
            organization_id = res_ws.scalar_one_or_none()

            user = await self.user_repo.create({
                'workspace_id': workspace_id,
                'organization_id': organization_id,
                'username': slack_user_id, # Fallback username
                'first_name': first_name,
                'last_name': last_name,
                'display_name': display_name
            })

            # Create UserAccount record
            if self.user_account_repo:
                try:
                    await self.user_account_repo.create({
                        'user_id': user.id,
                        'workspace_id': workspace_id,
                        'provider': 'slack',
                        'provider_id': slack_user_id,
                        'username': None,
                        'account_email': None
                    })
                except Exception:
                    pass
        else:
             # Update basic info if missing
            update_data = {}
            if first_name and not user.first_name:
                update_data['first_name'] = first_name
            if last_name and not user.last_name:
                update_data['last_name'] = last_name
            
            if update_data:
                 user = await self.user_repo.update(user.id, update_data)

        return user

    async def get_user(self, user_id: int, workspace_id: int = None) -> User | None:
        """Get user by ID, optionally filtered by workspace"""
        user = await self.user_repo.get_by_id(user_id)
        if user and workspace_id is not None and user.workspace_id != workspace_id:
            return None
        return user

    async def get_user_by_telegram(self, workspace_id: int, telegram_username: str) -> User | None:
        """Get user by Telegram username in workspace, fetch from TG and create/update if needed"""
        # 1. Try to find in current workspace
        user = await self.user_repo.get_by_telegram_username(workspace_id, telegram_username)
        
        # 2. Try to find anywhere else to get user info if not found in current workspace
        anywhere_user = None
        if not user:
            anywhere_user = await self.user_repo.find_anywhere_by_telegram_username(telegram_username)
            
        # 3. Prepare initial info
        info = {
            "telegram_id": (user.telegram_id if user else None) or (anywhere_user.telegram_id if anywhere_user else None),
            "first_name": (user.first_name if user else None) or (anywhere_user.first_name if anywhere_user else telegram_username),
            "last_name": (user.last_name if user else None) or (anywhere_user.last_name if anywhere_user else None),
            "display_name": (user.display_name if user else None) or (anywhere_user.display_name if anywhere_user else telegram_username)
        }

        # 4. If Telegram ID is missing, try to fetch it from Telegram Bot API
        from app.config import get_settings
        settings = get_settings()
        if not info["telegram_id"] and settings.telegram_token:
            try:
                from telegram import Bot
                import logging
                logger = logging.getLogger(__name__)
                
                bot = Bot(token=settings.telegram_token)
                # get_chat works for users with public usernames if the bot has seen them or they are in the same chat
                chat = await bot.get_chat(f"@{telegram_username}")
                info["telegram_id"] = chat.id
                info["first_name"] = chat.first_name or info["first_name"]
                info["last_name"] = chat.last_name or info["last_name"]
                if chat.first_name:
                    info["display_name"] = f"{chat.first_name} {chat.last_name or ''}".strip()
                else:
                    info["display_name"] = chat.username or info["display_name"]
                
                logger.info(f"Fetched Telegram info for @{telegram_username}: {info['telegram_id']}")
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to fetch Telegram info for {telegram_username}: {e}")

        # 5. Create or update record in this workspace
        return await self.get_or_create_by_telegram(
            workspace_id,
            telegram_username,
            info["display_name"],
            first_name=info["first_name"],
            last_name=info["last_name"],
            telegram_id=info["telegram_id"]
        )

    async def get_user_by_slack(self, workspace_id: int, slack_user_id: str) -> User | None:
        """Get user by Slack user ID in workspace, fetch from Slack if needed"""
        # 1. Try to find in current workspace
        user = await self.user_repo.get_by_slack_user_id(workspace_id, slack_user_id)
        if user:
            return user
        
        # 2. Try to fetch from Slack API
        from app.config import get_settings
        settings = get_settings()
        
        info = {
            "display_name": slack_user_id,
            "first_name": None,
            "last_name": None,
        }

        if settings.slack_bot_token:
            try:
                from slack_sdk.web.async_client import AsyncWebClient
                import logging
                logger = logging.getLogger(__name__)

                client = AsyncWebClient(token=settings.slack_bot_token)
                response = await client.users_info(user=slack_user_id)
                
                if response["ok"]:
                    slack_user = response["user"]
                    profile = slack_user.get("profile", {})
                    
                    real_name = profile.get("real_name") or slack_user.get("real_name")
                    first_name = profile.get("first_name")
                    last_name = profile.get("last_name")
                    
                    if not first_name and real_name:
                        parts = real_name.split(' ', 1)
                        first_name = parts[0]
                        if len(parts) > 1:
                            last_name = parts[1]
                            
                    info["first_name"] = first_name or real_name or "Slack User"
                    info["last_name"] = last_name
                    info["display_name"] = profile.get("display_name") or real_name or slack_user.get("name")
                    
                    logger.info(f"Fetched Slack info for {slack_user_id}: {info['display_name']}")
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to fetch Slack info for {slack_user_id}: {e}")

        # 3. Create record in this workspace
        return await self.get_or_create_by_slack(
            workspace_id,
            slack_user_id,
            info["display_name"],
            first_name=info["first_name"],
            last_name=info["last_name"]
        )

    async def get_all_users(self, workspace_id: int) -> list[User]:
        """Get all users in workspace"""
        return await self.user_repo.list_by_workspace(workspace_id)

    async def promote_user(self, user_id: int, workspace_id: int, admin_user_id: int = None) -> User:
        """Promote user to admin with audit logging"""
        user = await self.user_repo.update_admin_status(user_id, True)
        if user and self.admin_log_repo and admin_user_id:
            await self.admin_log_repo.log_action(
                workspace_id=workspace_id,
                admin_user_id=admin_user_id,
                action='promoted_admin',
                target_user_id=user_id,
                details=f'Promoted {user.display_name} to admin'
            )
        return user

    async def demote_user(self, user_id: int, workspace_id: int, admin_user_id: int = None) -> User:
        """Demote user from admin with audit logging"""
        user = await self.user_repo.update_admin_status(user_id, False)
        if user and self.admin_log_repo and admin_user_id:
            await self.admin_log_repo.log_action(
                workspace_id=workspace_id,
                admin_user_id=admin_user_id,
                action='demoted_admin',
                target_user_id=user_id,
                details=f'Demoted {user.display_name} from admin'
            )
        return user

    async def set_admin(self, user_id: int, is_admin: bool) -> User:
        """Set or unset admin status for a user"""
        return await self.user_repo.update_admin_status(user_id, is_admin)

    async def get_all_admins(self, workspace_id: int) -> list[User]:
        """Get all admin users in workspace"""
        return await self.user_repo.list_admins_in_workspace(workspace_id)

    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        user = await self.user_repo.get_by_id(user_id)
        return user.is_admin if user else False

    async def update_user(self, user_id: int, workspace_id: int, update_data: dict) -> User | None:
        """Update user information"""
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.workspace_id != workspace_id:
            return None
        return await self.user_repo.update(user_id, update_data)

    async def merge_users(self, target_user_id: int, source_user_id: int) -> User:
        """Merge source_user into target_user and delete source_user (SuperAdmin only)"""
        if target_user_id == source_user_id:
            return await self.user_repo.get_by_id(target_user_id)

        from sqlalchemy import update, delete, select
        from app.models import UserAccount, Team, Schedule, Escalation, team_members, RotationConfig, DutyStats, AdminLog, Organization
        
        target_user = await self.user_repo.get_by_id(target_user_id)
        source_user = await self.user_repo.get_by_id(source_user_id)
        if not target_user or not source_user:
            raise Exception("User not found")

        # 1. Inherit status and names
        if source_user.is_superadmin:
            target_user.is_superadmin = True
        if source_user.is_admin:
            target_user.is_admin = True
        if not target_user.display_name and source_user.display_name:
            target_user.display_name = source_user.display_name
        if not target_user.first_name and source_user.first_name:
            target_user.first_name = source_user.first_name
        if not target_user.last_name and source_user.last_name:
            target_user.last_name = source_user.last_name
        
        # 1. Transfer UserAccounts
        stmt = update(UserAccount).where(UserAccount.user_id == source_user_id).values(user_id=target_user_id)
        await self.user_repo.db.execute(stmt)
        
        # 2. Transfer Team Leadership
        stmt = update(Team).where(Team.team_lead_id == source_user_id).values(team_lead_id=target_user_id)
        await self.user_repo.db.execute(stmt)
        
        # 3. Transfer Schedules (handle duplicates)
        source_schedules_stmt = select(Schedule).where(Schedule.user_id == source_user_id)
        source_schedules = (await self.user_repo.db.execute(source_schedules_stmt)).scalars().all()
        for s in source_schedules:
            exists_stmt = select(Schedule).where(
                Schedule.user_id == target_user_id,
                Schedule.team_id == s.team_id,
                Schedule.date == s.date
            )
            exists = (await self.user_repo.db.execute(exists_stmt)).scalar_one_or_none()
            if exists:
                await self.user_repo.db.delete(s)
            else:
                s.user_id = target_user_id
        
        # 4. Transfer Escalations
        stmt = update(Escalation).where(Escalation.cto_id == source_user_id).values(cto_id=target_user_id)
        await self.user_repo.db.execute(stmt)
        
        # 5. Team Membership (handle duplicates)
        source_teams_stmt = select(team_members.c.team_id).where(team_members.c.user_id == source_user_id)
        target_teams_stmt = select(team_members.c.team_id).where(team_members.c.user_id == target_user_id)
        
        source_teams = (await self.user_repo.db.execute(source_teams_stmt)).scalars().all()
        target_teams = (await self.user_repo.db.execute(target_teams_stmt)).scalars().all()
        
        teams_to_transfer = set(source_teams) - set(target_teams)
        for team_id in teams_to_transfer:
            stmt = team_members.insert().values(user_id=target_user_id, team_id=team_id)
            await self.user_repo.db.execute(stmt)
            
        # Remove source from all teams
        stmt = team_members.delete().where(team_members.c.user_id == source_user_id)
        await self.user_repo.db.execute(stmt)
        
        # 6. Transfer Admin Logs
        stmt = update(AdminLog).where(AdminLog.admin_user_id == source_user_id).values(admin_user_id=target_user_id)
        await self.user_repo.db.execute(stmt)
        
        stmt = update(AdminLog).where(AdminLog.target_user_id == source_user_id).values(target_user_id=target_user_id)
        await self.user_repo.db.execute(stmt)

        # 7. Transfer Organization Ownership
        stmt = update(Organization).where(Organization.created_by_user_id == source_user_id).values(created_by_user_id=target_user_id)
        await self.user_repo.db.execute(stmt)

        # 8. Transfer RotationConfig
        rotation_configs_stmt = select(RotationConfig)
        rotation_configs_res = await self.user_repo.db.execute(rotation_configs_stmt)
        rotation_configs = rotation_configs_res.scalars().all()
        for rc in rotation_configs:
            changed = False
            if rc.last_assigned_user_id == source_user_id:
                rc.last_assigned_user_id = target_user_id
                changed = True
            
            if rc.member_ids and source_user_id in rc.member_ids:
                new_ids = []
                for uid in rc.member_ids:
                    if uid == source_user_id:
                        if target_user_id not in new_ids:
                            new_ids.append(target_user_id)
                    else:
                        new_ids.append(uid)
                rc.member_ids = new_ids
                changed = True
            
            if changed:
                self.user_repo.db.add(rc)

        # 9. Transfer DutyStats
        source_stats_stmt = select(DutyStats).where(DutyStats.user_id == source_user_id)
        source_stats_res = await self.user_repo.db.execute(source_stats_stmt)
        source_stats = source_stats_res.scalars().all()
        for st in source_stats:
            target_st_stmt = select(DutyStats).where(
                DutyStats.user_id == target_user_id,
                DutyStats.workspace_id == st.workspace_id,
                DutyStats.team_id == st.team_id,
                DutyStats.year == st.year,
                DutyStats.month == st.month
            )
            target_st_res = await self.user_repo.db.execute(target_st_stmt)
            target_st = target_st_res.scalar_one_or_none()
            if target_st:
                target_st.duty_days += st.duty_days
                target_st.shift_days += st.shift_days
                if st.hours_worked:
                    target_st.hours_worked = (target_st.hours_worked or 0) + st.hours_worked
                await self.user_repo.db.delete(st)
            else:
                st.user_id = target_user_id

        # 10. Delete source user
        await self.user_repo.delete(source_user_id)
        
        await self.user_repo.db.commit()
        return await self.user_repo.get_by_id(target_user_id)
