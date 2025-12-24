# Example: How to add Mini App button to your Telegram bot
# Add this to app/handlers/telegram_handler.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes, CommandHandler
from app.config import get_settings

settings = get_settings()

# Get mini app URL from environment or set default
MINIAPP_URL = getattr(settings, 'miniapp_url', 'https://yourdomain.com/miniapp')


async def app_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /app command - opens the mini app

    Usage: /app
    """
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            text="📅 Open Interactive Schedule",
            web_app=WebAppInfo(url=MINIAPP_URL)
        )
    ]])

    await update.message.reply_text(
        "Click the button below to open the interactive duty schedule:\n\n"
        "📅 View monthly calendar\n"
        "👥 Manage team duties\n"
        "⚙️ Assign shifts",
        reply_markup=keyboard
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command - show main menu with mini app button
    """
    first_name = update.effective_user.first_name

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            text="📅 Open Schedule App",
            web_app=WebAppInfo(url=MINIAPP_URL)
        )],
        [
            InlineKeyboardButton(text="📋 View Duty", callback_data="duty"),
            InlineKeyboardButton(text="👥 Teams", callback_data="teams"),
        ],
        [InlineKeyboardButton(text="❓ Help", callback_data="help")]
    ])

    await update.message.reply_text(
        f"Welcome to Duty Bot, {first_name}! 👋\n\n"
        "I help manage your team's duty schedule across Telegram and Slack.\n\n"
        "Use the button below to:\n"
        "📅 View and manage the complete schedule\n"
        "👥 Assign duties to team members\n"
        "⚙️ Configure your team\n\n"
        "Or use commands:\n"
        "/duty - Show today's duties\n"
        "/schedule - View schedule\n"
        "/team - Manage teams\n"
        "/app - Open the schedule app\n"
        "/help - Show all commands",
        reply_markup=keyboard
    )


async def duty_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /duty command - show today's duties with mini app button
    """
    # ... your existing duty command code ...

    # Add mini app button
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            text="📅 View Full Schedule",
            web_app=WebAppInfo(url=MINIAPP_URL)
        )
    ]])

    duty_text = "Your duty info here..."

    await update.message.reply_text(
        duty_text,
        reply_markup=keyboard
    )


# HOW TO INTEGRATE INTO YOUR TELEGRAM HANDLER
# =============================================
#
# 1. Add this import at top of app/handlers/telegram_handler.py:
#    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
#
# 2. Add to your TelegramHandler.setup_commands() method:
#    command_handlers = [
#        CommandHandler('start', self.handle_start),
#        CommandHandler('app', self.handle_app),
#        CommandHandler('duty', self.handle_duty),
#        # ... your other commands
#    ]
#
# 3. Add to .env:
#    MINIAPP_URL=https://yourdomain.com/miniapp
#
# 4. Update app/config.py to include:
#    miniapp_url: str = Field(default="http://localhost:5173")
#

# EXAMPLE FOR app/config.py
# ========================
"""
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # ... existing settings ...

    # Mini app configuration
    miniapp_url: str = Field(
        default="http://localhost:5173",
        description="URL for Telegram mini app"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra='ignore'
    )
"""

# STEP-BY-STEP DEPLOYMENT
# =======================
#
# 1. Register mini app in BotFather:
#    - Message @BotFather
#    - /newapp
#    - Select your bot
#    - Fill in app details
#    - Get your mini app link: https://t.me/YOUR_BOT/short_name
#
# 2. For local testing with ngrok:
#    ./ngrok http 5173
#    # Copy HTTPS URL
#    # Update in BotFather: /myapps -> select bot -> /editapp
#
# 3. For production:
#    - Deploy webapp (Docker or static hosting)
#    - Update mini app URL in BotFather to production domain
#    - Ensure SSL certificate is valid
#    - Test with: /app command
#
# 4. Verify everything works:
#    - Send /app to your bot
#    - Click button
#    - Mini app should open
#    - Check browser console for errors
#    - Check server logs: docker logs duty_bot_app
#

if __name__ == "__main__":
    print("""
    This is an example file showing how to integrate mini app into your bot.

    See comments above for integration steps.

    Full guide: See MINIAPP_SETUP.md
    """)
