import logging
from datetime import date
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal, get_db_with_retry
from app.commands.handlers import CommandHandler as BotCommandHandler
from app.commands.parser import CommandParser, DateParser, CommandError
from app.services.user_service import UserService
from app.models import Workspace
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def format_telegram_text(text: str) -> str:
    """Convert markdown-like text to Telegram HTML/Markdown if needed"""
    # For now, we just use it as is since python-telegram-bot handles basic md
    return text


async def get_or_create_telegram_workspace(db: AsyncSession, chat_id: int) -> int:
    """Get or create Telegram workspace by chat ID"""
    external_id = str(chat_id)
    stmt = select(Workspace).where(
        (Workspace.workspace_type == 'telegram') &
        (Workspace.external_id == external_id)
    )
    result = await db.execute(stmt)
    workspace = result.scalars().first()

    if not workspace:
        workspace = Workspace(
            name=f"Telegram Chat {chat_id}",
            workspace_type='telegram',
            external_id=external_id
        )
        db.add(workspace)
        await db.commit()
        await db.refresh(workspace)
        logger.info(f"Created new Telegram workspace: {chat_id} (id={workspace.id})")
    else:
        logger.debug(f"Using existing Telegram workspace: {chat_id} (id={workspace.id})")

    return workspace.id


class TelegramHandler:
    def __init__(self):
        self.app = None


    async def start(self):
        """Start Telegram bot"""
        if not settings.telegram_token:
            logger.warning("Telegram token is not set, skipping Telegram bot start")
            return

        self.app = Application.builder().token(settings.telegram_token).build()

        # Add handlers
        self.app.add_handler(CommandHandler("duty", self.duty_command))
        self.app.add_handler(CommandHandler("team", self.team_command))
        self.app.add_handler(CommandHandler("schedule", self.schedule_command))
        self.app.add_handler(CommandHandler("shift", self.shift_command))
        self.app.add_handler(CommandHandler("escalation", self.escalation_command))
        self.app.add_handler(CommandHandler("escalate", self.escalate_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("start", self.help_command))

        await self.app.initialize()

        # Register commands menu
        commands = [
            BotCommand("duty", "Show on-duty people"),
            BotCommand("team", "Manage teams & members"),
            BotCommand("schedule", "Manage duty schedule"),
            BotCommand("shift", "Manage team shifts"),
            BotCommand("escalation", "Escalation settings"),
            BotCommand("escalate", "Escalate an issue"),
            BotCommand("help", "Show full command list"),
        ]
        await self.app.bot.set_my_commands(commands)
        logger.info("Bot commands registered")

        await self.app.start()
        await self.app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    async def stop(self):
        """Stop Telegram bot"""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

    async def duty_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /duty command"""
        try:
            async with get_db_with_retry() as db:
                workspace_id = await get_or_create_telegram_workspace(db, update.effective_chat.id)
                user_service = UserService(db)

                # Create or update user if they don't exist
                user_info = update.effective_user
                await user_service.get_or_create_by_telegram(
                    workspace_id,
                    user_info.username or f"user_{user_info.id}",
                    user_info.first_name or "Unknown"
                )

                handler = BotCommandHandler(db, workspace_id)

                args = context.args
                if not args:
                    # Show all duties today
                    result = await handler.duty_today()
                else:
                    # Mention specific team's duty
                    team_name = args[0]
                    result = await handler.mention_duty(team_name)

                await update.effective_message.reply_text(result)

        except CommandError as e:
            await update.effective_message.reply_text(f"❌ {str(e)}")
        except Exception as e:
            logger.exception(f"Error in duty_command: {e}")
            await update.effective_message.reply_text("❌ An error occurred")

    async def team_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /team command"""
        try:
            async with get_db_with_retry() as db:
                workspace_id = await get_or_create_telegram_workspace(db, update.effective_chat.id)
                handler = BotCommandHandler(db, workspace_id)
                user_service = UserService(db)

                # Create or update user if they don't exist
                user_info = update.effective_user
                await user_service.get_or_create_by_telegram(
                    workspace_id,
                    user_info.username or f"user_{user_info.id}",
                    user_info.first_name or "Unknown"
                )

                args = context.args
                if not args:
                    raise CommandError("Usage: /team <command> [args]")

                command = args[0]

                if command == "list":
                    result = await handler.team_list()

                elif command == "add" and len(args) >= 2:
                    name = args[1]
                    display_name = CommandParser.extract_quote_content(" ".join(args))
                    if not display_name:
                        raise CommandError('Usage: /team add <name> "<display_name>" [--shifts]')

                    has_shifts = CommandParser.extract_flag(" ".join(args), "shifts")
                    result = await handler.team_add(name, display_name, has_shifts)

                elif command == "edit" and len(args) >= 2:
                    team_name = args[1]
                    full_text = " ".join(args)

                    if "--name" in full_text:
                        idx = full_text.find("--name")
                        new_name = full_text[idx:].split()[1]
                        result = await handler.team_edit_name(team_name, new_name)

                    elif "--display" in full_text:
                        display_name = CommandParser.extract_quote_content(full_text)
                        if not display_name:
                            raise CommandError('Usage: /team edit <name> --display "<new_name>"')
                        result = await handler.team_edit_display(team_name, display_name)

                    elif "--shifts" in full_text:
                        result = await handler.team_edit_shifts(team_name, True)

                    elif "--no-shifts" in full_text:
                        result = await handler.team_edit_shifts(team_name, False)

                    else:
                        raise CommandError("Unknown team edit option")

                elif command == "lead" and len(args) >= 3:
                    team_name = args[1]
                    mentions = CommandParser.extract_mentions(" ".join(args[2:]))
                    if not mentions:
                        raise CommandError("Usage: /team lead <team> @user")

                    user = await user_service.get_user_by_telegram(workspace_id, mentions[0])
                    if not user:
                        raise CommandError(f"User not found: @{mentions[0]}")

                    result = await handler.team_set_lead(team_name, user)

                elif command == "add-member" and len(args) >= 2:
                    team_name = args[1]
                    mentions = CommandParser.extract_mentions(" ".join(args[2:]))
                    if not mentions:
                        raise CommandError("Usage: /team add-member <team> @user")

                    user = await user_service.get_user_by_telegram(workspace_id, mentions[0])
                    if not user:
                        raise CommandError(f"User not found: @{mentions[0]}")

                    result = await handler.team_add_member(team_name, user)

                elif command == "remove-member" and len(args) >= 2:
                    team_name = args[1]
                    mentions = CommandParser.extract_mentions(" ".join(args[2:]))
                    if not mentions:
                        raise CommandError("Usage: /team remove-member <team> @user")

                    user = await user_service.get_user_by_telegram(workspace_id, mentions[0])
                    if not user:
                        raise CommandError(f"User not found: @{mentions[0]}")

                    result = await handler.team_remove_member(team_name, user)

                elif command == "move" and len(args) >= 4:
                    mentions = CommandParser.extract_mentions(" ".join(args[1:]))
                    from_team = args[2]
                    to_team = args[3]

                    if not mentions:
                        raise CommandError("Usage: /team move @user <from_team> <to_team>")

                    user = await user_service.get_user_by_telegram(workspace_id, mentions[0])
                    if not user:
                        raise CommandError(f"User not found: @{mentions[0]}")

                    result = await handler.team_move_member(user, from_team, to_team)

                elif command == "delete" and len(args) >= 2:
                    team_name = args[1]
                    result = await handler.team_delete(team_name)

                else:
                    # Show team info
                    team_name = command
                    result = await handler.team_info(team_name)

                await update.effective_message.reply_text(result)

        except CommandError as e:
            await update.effective_message.reply_text(f"❌ {str(e)}")
        except Exception as e:
            logger.exception(f"Error in team_command: {e}")
            await update.effective_message.reply_text("❌ An error occurred")

    async def schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /schedule command"""
        try:
            async with get_db_with_retry() as db:
                workspace_id = await get_or_create_telegram_workspace(db, update.effective_chat.id)
                handler = BotCommandHandler(db, workspace_id)
                user_service = UserService(db)

                # Create or update user if they don't exist
                user_info = update.effective_user
                await user_service.get_or_create_by_telegram(
                    workspace_id,
                    user_info.username or f"user_{user_info.id}",
                    user_info.first_name or "Unknown"
                )

                args = context.args
                if not args:
                    raise CommandError("Usage: /schedule <team> [period] [set/clear] [date] [@user]")

                team_name = args[0]
                full_text = " ".join(args)

                if "set" in full_text and len(args) >= 3:
                    date_idx = full_text.find("set") + 3
                    date_part = full_text[date_idx:].split()[0]
                    mentions = CommandParser.extract_mentions(full_text)

                    if not mentions:
                        raise CommandError("Usage: /schedule <team> set <date> @user")

                    user = await user_service.get_user_by_telegram(workspace_id, mentions[0])
                    if not user:
                        raise CommandError(f"User not found: @{mentions[0]}")

                    result = await handler.schedule_set(team_name, date_part, user)

                elif "clear" in full_text and len(args) >= 3:
                    date_idx = full_text.find("clear") + 5
                    date_part = full_text[date_idx:].split()[0]
                    result = await handler.schedule_clear(team_name, date_part)

                else:
                    period = args[1] if len(args) > 1 else "week"
                    result = await handler.schedule_show(team_name, period)

                await update.effective_message.reply_text(result)

        except CommandError as e:
            await update.effective_message.reply_text(f"❌ {str(e)}")
        except Exception as e:
            logger.exception(f"Error in schedule_command: {e}")
            await update.effective_message.reply_text("❌ An error occurred")

    async def shift_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /shift command"""
        try:
            async with get_db_with_retry() as db:
                workspace_id = await get_or_create_telegram_workspace(db, update.effective_chat.id)
                handler = BotCommandHandler(db, workspace_id)
                user_service = UserService(db)

                # Create or update user if they don't exist
                user_info = update.effective_user
                await user_service.get_or_create_by_telegram(
                    workspace_id,
                    user_info.username or f"user_{user_info.id}",
                    user_info.first_name or "Unknown"
                )

                args = context.args
                if not args:
                    raise CommandError("Usage: /shift <team> [period] [set/add/remove/clear] [date] [@users]")

                team_name = args[0]
                full_text = " ".join(args)

                if "set" in full_text and len(args) >= 3:
                    date_idx = full_text.find("set") + 3
                    date_part = full_text[date_idx:].split()[0]
                    mentions = CommandParser.extract_mentions(full_text)

                    if not mentions:
                        raise CommandError("Usage: /shift <team> set <date> @user1 @user2 ...")

                    users = []
                    for mention in mentions:
                        user = await user_service.get_user_by_telegram(workspace_id, mention)
                        if not user:
                            raise CommandError(f"User not found: @{mention}")
                        users.append(user)

                    result = await handler.shift_set(team_name, date_part, users)

                elif "add" in full_text and len(args) >= 3:
                    date_idx = full_text.find("add") + 3
                    date_part = full_text[date_idx:].split()[0]
                    mentions = CommandParser.extract_mentions(full_text)

                    if not mentions:
                        raise CommandError("Usage: /shift <team> add <date> @user")

                    user = await user_service.get_user_by_telegram(workspace_id, mentions[0])
                    if not user:
                        raise CommandError(f"User not found: @{mentions[0]}")

                    result = await handler.shift_add_user(team_name, date_part, user)

                elif "remove" in full_text and len(args) >= 3:
                    date_idx = full_text.find("remove") + 6
                    date_part = full_text[date_idx:].split()[0]
                    mentions = CommandParser.extract_mentions(full_text)

                    if not mentions:
                        raise CommandError("Usage: /shift <team> remove <date> @user")

                    user = await user_service.get_user_by_telegram(workspace_id, mentions[0])
                    if not user:
                        raise CommandError(f"User not found: @{mentions[0]}")

                    result = await handler.shift_remove_user(team_name, date_part, user)

                elif "clear" in full_text and len(args) >= 3:
                    date_idx = full_text.find("clear") + 5
                    date_part = full_text[date_idx:].split()[0]
                    result = await handler.shift_clear(team_name, date_part)

                else:
                    period = args[1] if len(args) > 1 else "week"
                    result = await handler.shift_show(team_name, period)

                await update.effective_message.reply_text(result)

        except CommandError as e:
            await update.effective_message.reply_text(f"❌ {str(e)}")
        except Exception as e:
            logger.exception(f"Error in shift_command: {e}")
            await update.effective_message.reply_text("❌ An error occurred")

    async def escalation_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /escalation command"""
        try:
            async with get_db_with_retry() as db:
                workspace_id = await get_or_create_telegram_workspace(db, update.effective_chat.id)
                handler = BotCommandHandler(db, workspace_id)
                user_service = UserService(db)

                # Create or update user if they don't exist
                user_info = update.effective_user
                await user_service.get_or_create_by_telegram(
                    workspace_id,
                    user_info.username or f"user_{user_info.id}",
                    user_info.first_name or "Unknown"
                )

                args = context.args
                full_text = " ".join(args) if args else ""

                if "cto" in full_text:
                    mentions = CommandParser.extract_mentions(full_text)
                    if not mentions:
                        raise CommandError("Usage: /escalation cto @user")

                    user = await user_service.get_user_by_telegram(workspace_id, mentions[0])
                    if not user:
                        raise CommandError(f"User not found: @{mentions[0]}")

                    result = await handler.escalation_set_cto(user)
                else:
                    result = await handler.escalation_show()

                await update.effective_message.reply_text(result)

        except CommandError as e:
            await update.effective_message.reply_text(f"❌ {str(e)}")
        except Exception as e:
            logger.exception(f"Error in escalation_command: {e}")
            await update.effective_message.reply_text("❌ An error occurred")

    async def escalate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /escalate command"""
        try:
            async with get_db_with_retry() as db:
                workspace_id = await get_or_create_telegram_workspace(db, update.effective_chat.id)
                handler = BotCommandHandler(db, workspace_id)
                user_service = UserService(db)

                # Create or update user if they don't exist
                user_info = update.effective_user
                await user_service.get_or_create_by_telegram(
                    workspace_id,
                    user_info.username or f"user_{user_info.id}",
                    user_info.first_name or "Unknown"
                )

                args = context.args
                if not args:
                    raise CommandError("Usage: /escalate <team|level2|ack>")

                command = args[0]

                if command == "ack":
                    result = "✅ Escalation acknowledged"
                elif command == "level2":
                    result = await handler.escalate_cto()
                else:
                    result = await handler.escalate_team(command)

                await update.effective_message.reply_text(result)

        except CommandError as e:
            await update.effective_message.reply_text(f"❌ {str(e)}")
        except Exception as e:
            logger.exception(f"Error in escalate_command: {e}")
            await update.effective_message.reply_text("❌ An error occurred")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help and /start command"""
        try:
            async with get_db_with_retry() as db:
                workspace_id = await get_or_create_telegram_workspace(db, update.effective_chat.id)
                user_service = UserService(db)

                # Create or update user if they don't exist
                user_info = update.effective_user
                await user_service.get_or_create_by_telegram(
                    workspace_id,
                    user_info.username or f"user_{user_info.id}",
                    user_info.first_name or "Unknown"
                )

                handler = BotCommandHandler(db, workspace_id)
                result = await handler.help()
                await update.effective_message.reply_text(result, parse_mode='Markdown')
        except Exception as e:
            logger.exception(f"Error in help_command: {e}")
            await update.effective_message.reply_text("❌ An error occurred")
