import logging
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
from app.database import AsyncSessionLocal
from app.commands.handlers import CommandHandler as BotCommandHandler
from app.commands.parser import CommandParser, DateParser, CommandError
from app.services.user_service import UserService
from app.models import Workspace
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_or_create_slack_workspace(db, team_id: str) -> int:
    """Get or create Slack workspace by team ID"""
    stmt = select(Workspace).where(
        (Workspace.workspace_type == 'slack') &
        (Workspace.external_id == team_id)
    )
    result = await db.execute(stmt)
    workspace = result.scalars().first()

    if not workspace:
        workspace = Workspace(
            name=f"Slack Workspace {team_id}",
            workspace_type='slack',
            external_id=team_id
        )
        db.add(workspace)
        await db.commit()
        await db.refresh(workspace)
        logger.info(f"Created new Slack workspace: {team_id} (id={workspace.id})")
    else:
        logger.debug(f"Using existing Slack workspace: {team_id} (id={workspace.id})")

    return workspace.id


class SlackHandler:
    def __init__(self):
        if not settings.slack_bot_token or not settings.slack_signing_secret:
            self.app = None
            self.client = None
            return

        self.app = AsyncApp(
            token=settings.slack_bot_token,
            signing_secret=settings.slack_signing_secret,
        )
        self.client = AsyncWebClient(token=settings.slack_bot_token)
        self.setup_handlers()

    async def _get_or_create_user(self, db: AsyncSession, command: dict):
        """Ensure current user is in database"""
        user_id = command.get("user_id")
        user_name = command.get("user_name")
        if not user_id:
            return None
            
        user_service = UserService(db)
        return await user_service.get_or_create_by_slack(
            slack_user_id=user_id,
            display_name=user_name or user_id
        )

    def setup_handlers(self):
        """Setup all Slack event handlers"""
        self.app.command("/duty")(self.duty_command)
        self.app.command("/team")(self.team_command)
        self.app.command("/schedule")(self.schedule_command)
        self.app.command("/shift")(self.shift_command)
        self.app.command("/escalation")(self.escalation_command)
        self.app.command("/escalate")(self.escalate_command)
        self.app.command("/help")(self.help_command)

    async def duty_command(self, ack, command, body):
        """Handle /duty command"""
        await ack()

        try:
            async with AsyncSessionLocal() as db:
                handler = BotCommandHandler(db)

                text = command.get("text", "").strip()
                if not text:
                    # Show all duties today
                    result = await handler.duty_today()
                else:
                    # Mention specific team's duty
                    team_name = text.split()[0]
                    result = await handler.mention_duty(team_name)

                await self.client.chat_postMessage(
                    channel=command["channel_id"],
                    text=result
                )

        except CommandError as e:
            await self.client.chat_postMessage(
                channel=command["channel_id"],
                text=f"❌ {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Error in duty_command: {e}")
            await self.client.chat_postMessage(
                channel=command["channel_id"],
                text="❌ An error occurred"
            )

    async def team_command(self, ack, command, body):
        """Handle /team command"""
        await ack()

        try:
            async with AsyncSessionLocal() as db:
                handler = BotCommandHandler(db)
                user_service = UserService(db)

                text = command.get("text", "").strip()
                if not text:
                    raise CommandError("Usage: /team <command> [args]")

                parts = text.split()
                cmd = parts[0]

                if cmd == "list":
                    result = await handler.team_list()

                elif cmd == "add" and len(parts) >= 2:
                    name = parts[1]
                    display_name = CommandParser.extract_quote_content(text)
                    if not display_name:
                        raise CommandError('Usage: /team add <name> "<display_name>" [--shifts]')

                    has_shifts = CommandParser.extract_flag(text, "shifts")
                    result = await handler.team_add(name, display_name, has_shifts)

                elif cmd == "edit" and len(parts) >= 2:
                    team_name = parts[1]

                    if "--name" in text:
                        idx = text.find("--name")
                        new_name = text[idx:].split()[1]
                        result = await handler.team_edit_name(team_name, new_name)

                    elif "--display" in text:
                        display_name = CommandParser.extract_quote_content(text)
                        if not display_name:
                            raise CommandError('Usage: /team edit <name> --display "<new_name>"')
                        result = await handler.team_edit_display(team_name, display_name)

                    elif "--shifts" in text:
                        result = await handler.team_edit_shifts(team_name, True)

                    elif "--no-shifts" in text:
                        result = await handler.team_edit_shifts(team_name, False)

                    else:
                        raise CommandError("Unknown team edit option")

                elif cmd == "lead" and len(parts) >= 3:
                    team_name = parts[1]
                    mentions = CommandParser.extract_mentions(text)
                    if not mentions:
                        raise CommandError("Usage: /team lead <team> @user")

                    user = await user_service.get_user_by_slack(workspace_id, mentions[0])
                    if not user:
                        raise CommandError(f"User not found: <@{mentions[0]}>")

                    result = await handler.team_set_lead(team_name, user)

                elif cmd == "add-member" and len(parts) >= 2:
                    team_name = parts[1]
                    mentions = CommandParser.extract_mentions(text)
                    if not mentions:
                        raise CommandError("Usage: /team add-member <team> @user")

                    user = await user_service.get_user_by_slack(workspace_id, mentions[0])
                    if not user:
                        raise CommandError(f"User not found: <@{mentions[0]}>")

                    result = await handler.team_add_member(team_name, user)

                elif cmd == "remove-member" and len(parts) >= 2:
                    team_name = parts[1]
                    mentions = CommandParser.extract_mentions(text)
                    if not mentions:
                        raise CommandError("Usage: /team remove-member <team> @user")

                    user = await user_service.get_user_by_slack(workspace_id, mentions[0])
                    if not user:
                        raise CommandError(f"User not found: <@{mentions[0]}>")

                    result = await handler.team_remove_member(team_name, user)

                elif cmd == "move" and len(parts) >= 4:
                    mentions = CommandParser.extract_mentions(text)
                    from_team = parts[2]
                    to_team = parts[3]

                    if not mentions:
                        raise CommandError("Usage: /team move @user <from_team> <to_team>")

                    user = await user_service.get_user_by_slack(workspace_id, mentions[0])
                    if not user:
                        raise CommandError(f"User not found: <@{mentions[0]}>")

                    result = await handler.team_move_member(user, from_team, to_team)

                elif cmd == "delete" and len(parts) >= 2:
                    team_name = parts[1]
                    result = await handler.team_delete(team_name)

                else:
                    # Show team info
                    team_name = cmd
                    result = await handler.team_info(team_name)

                await self.client.chat_postMessage(
                    channel=command["channel_id"],
                    text=result
                )

        except CommandError as e:
            await self.client.chat_postMessage(
                channel=command["channel_id"],
                text=f"❌ {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Error in team_command: {e}")
            await self.client.chat_postMessage(
                channel=command["channel_id"],
                text="❌ An error occurred"
            )

    async def schedule_command(self, ack, command, body):
        """Handle /schedule command"""
        await ack()

        try:
            async with AsyncSessionLocal() as db:
                handler = BotCommandHandler(db)
                user_service = UserService(db)

                text = command.get("text", "").strip()
                if not text:
                    raise CommandError("Usage: /schedule <team> [period] [set/clear] [date] [@user]")

                parts = text.split()
                team_name = parts[0]

                if "set" in text and len(parts) >= 3:
                    date_idx = text.find("set") + 3
                    date_part = text[date_idx:].split()[0]
                    mentions = CommandParser.extract_mentions(text)

                    if not mentions:
                        raise CommandError("Usage: /schedule <team> set <date> @user")

                    user = await user_service.get_user_by_slack(workspace_id, mentions[0])
                    if not user:
                        raise CommandError(f"User not found: <@{mentions[0]}>")

                    result = await handler.schedule_set(team_name, date_part, user)

                elif "clear" in text and len(parts) >= 3:
                    date_idx = text.find("clear") + 5
                    date_part = text[date_idx:].split()[0]
                    result = await handler.schedule_clear(team_name, date_part)

                else:
                    period = parts[1] if len(parts) > 1 else "week"
                    result = await handler.schedule_show(team_name, period)

                await self.client.chat_postMessage(
                    channel=command["channel_id"],
                    text=result
                )

        except CommandError as e:
            await self.client.chat_postMessage(
                channel=command["channel_id"],
                text=f"❌ {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Error in schedule_command: {e}")
            await self.client.chat_postMessage(
                channel=command["channel_id"],
                text="❌ An error occurred"
            )

    async def shift_command(self, ack, command, body):
        """Handle /shift command"""
        await ack()

        try:
            async with AsyncSessionLocal() as db:
                handler = BotCommandHandler(db)
                user_service = UserService(db)

                text = command.get("text", "").strip()
                if not text:
                    raise CommandError("Usage: /shift <team> [period] [set/add/remove/clear] [date] [@users]")

                parts = text.split()
                team_name = parts[0]

                if "set" in text and len(parts) >= 3:
                    date_idx = text.find("set") + 3
                    date_part = text[date_idx:].split()[0]
                    mentions = CommandParser.extract_mentions(text)

                    if not mentions:
                        raise CommandError("Usage: /shift <team> set <date> @user1 @user2 ...")

                    users = []
                    for mention in mentions:
                        user = await user_service.get_user_by_slack(workspace_id, mention)
                        if not user:
                            raise CommandError(f"User not found: <@{mention}>")
                        users.append(user)

                    result = await handler.shift_set(team_name, date_part, users)

                elif "add" in text and len(parts) >= 3:
                    date_idx = text.find("add") + 3
                    date_part = text[date_idx:].split()[0]
                    mentions = CommandParser.extract_mentions(text)

                    if not mentions:
                        raise CommandError("Usage: /shift <team> add <date> @user")

                    user = await user_service.get_user_by_slack(workspace_id, mentions[0])
                    if not user:
                        raise CommandError(f"User not found: <@{mentions[0]}>")

                    result = await handler.shift_add_user(team_name, date_part, user)

                elif "remove" in text and len(parts) >= 3:
                    date_idx = text.find("remove") + 6
                    date_part = text[date_idx:].split()[0]
                    mentions = CommandParser.extract_mentions(text)

                    if not mentions:
                        raise CommandError("Usage: /shift <team> remove <date> @user")

                    user = await user_service.get_user_by_slack(workspace_id, mentions[0])
                    if not user:
                        raise CommandError(f"User not found: <@{mentions[0]}>")

                    result = await handler.shift_remove_user(team_name, date_part, user)

                elif "clear" in text and len(parts) >= 3:
                    date_idx = text.find("clear") + 5
                    date_part = text[date_idx:].split()[0]
                    result = await handler.shift_clear(team_name, date_part)

                else:
                    period = parts[1] if len(parts) > 1 else "week"
                    result = await handler.shift_show(team_name, period)

                await self.client.chat_postMessage(
                    channel=command["channel_id"],
                    text=result
                )

        except CommandError as e:
            await self.client.chat_postMessage(
                channel=command["channel_id"],
                text=f"❌ {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Error in shift_command: {e}")
            await self.client.chat_postMessage(
                channel=command["channel_id"],
                text="❌ An error occurred"
            )

    async def escalation_command(self, ack, command, body):
        """Handle /escalation command"""
        await ack()

        try:
            async with AsyncSessionLocal() as db:
                handler = BotCommandHandler(db)
                user_service = UserService(db)

                text = command.get("text", "").strip()

                if "cto" in text:
                    mentions = CommandParser.extract_mentions(text)
                    if not mentions:
                        raise CommandError("Usage: /escalation cto @user")

                    user = await user_service.get_user_by_slack(workspace_id, mentions[0])
                    if not user:
                        raise CommandError(f"User not found: <@{mentions[0]}>")

                    result = await handler.escalation_set_cto(user)
                else:
                    result = await handler.escalation_show()

                await self.client.chat_postMessage(
                    channel=command["channel_id"],
                    text=result
                )

        except CommandError as e:
            await self.client.chat_postMessage(
                channel=command["channel_id"],
                text=f"❌ {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Error in escalation_command: {e}")
            await self.client.chat_postMessage(
                channel=command["channel_id"],
                text="❌ An error occurred"
            )

    async def escalate_command(self, ack, command, body):
        """Handle /escalate command"""
        await ack()

        try:
            async with AsyncSessionLocal() as db:
                handler = BotCommandHandler(db)

                text = command.get("text", "").strip()
                if not text:
                    raise CommandError("Usage: /escalate <team|level2|ack>")

                cmd = text.split()[0]

                if cmd == "ack":
                    result = "✅ Escalation acknowledged"
                elif cmd == "level2":
                    result = await handler.escalate_cto()
                else:
                    result = await handler.escalate_team(cmd)

                await self.client.chat_postMessage(
                    channel=command["channel_id"],
                    text=result
                )

        except CommandError as e:
            await self.client.chat_postMessage(
                channel=command["channel_id"],
                text=f"❌ {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Error in escalate_command: {e}")
            await self.client.chat_postMessage(
                channel=command["channel_id"],
                text="❌ An error occurred"
            )

    async def help_command(self, ack, command, body):
        """Handle /help command"""
        await ack()
        try:
            async with AsyncSessionLocal() as db:
                await self._get_or_create_user(db, command)
                handler = BotCommandHandler(db)
                result = await handler.help()
                await self.client.chat_postMessage(
                    channel=command["channel_id"],
                    text=result
                )
        except Exception as e:
            logger.exception(f"Error in help_command: {e}")
            await self.client.chat_postMessage(
                channel=command["channel_id"],
                text="❌ An error occurred"
            )
