# Telegram Mini App Integration Guide

## Step-by-Step Setup

### 1. Register Mini App in BotFather

1. Open Telegram and message **@BotFather**
2. Send command `/newapp`
3. Select your bot
4. Fill in the information:
   - **App name**: `Duty Bot` (display name)
   - **Short name**: `duty_bot` (lowercase, no spaces, used in URLs)
   - **Description**: `Interactive duty schedule calendar`
   - **App photo**: Upload 512×512px PNG (optional)
   - **App URL**: See section 2 below

5. After creation, BotFather will show:
   ```
   Here is your web app link:
   https://t.me/YOUR_BOT_USERNAME/duty_bot
   ```

### 2. Set the App URL

After creating the app, you'll need to set the actual URL where your mini app is hosted.

#### For Production:
```
https://yourdomain.com/miniapp
```

#### For Development:
You have two options:

**Option A: Using ngrok (Recommended)**
```bash
# Install ngrok from https://ngrok.com
ngrok http 5173

# You'll get a URL like: https://abc123.ngrok.io
# Use this URL in BotFather
```

**Option B: Using localhost**
```
http://localhost:5173
```
⚠️ Only works locally when testing with Telegram Desktop or web version.

### 3. Update Bot Commands (Optional)

Send to @BotFather:
```
/setcommands

Select your bot, then provide:
duty - Show today's duties
schedule - View schedule
team - Manage teams
app - Open interactive schedule
help - Show help
```

### 4. Add Mini App Button to Your Bot

Update `app/handlers/telegram_handler.py`:

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send main menu with mini app button"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            text="📅 View Schedule",
            web_app=WebAppInfo(url="https://yourdomain.com/miniapp")
        )],
        [
            InlineKeyboardButton(text="👥 Teams", callback_data="teams"),
            InlineKeyboardButton(text="⚙️ Help", callback_data="help")
        ]
    ])

    await update.message.reply_text(
        "Welcome to Duty Bot! 👋\n\n"
        "Manage your team's duty schedule with our interactive calendar.",
        reply_markup=keyboard
    )
```

### 5. Create a /app Command

Add this to handle the `/app` command:

```python
# In your command handlers
async def app_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open the mini app"""
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            text="📅 Open Schedule App",
            web_app=WebAppInfo(url="https://yourdomain.com/miniapp")
        )
    ]])

    await update.message.reply_text(
        "Click the button below to open the interactive duty schedule:",
        reply_markup=keyboard
    )
```

### 6. Configure in Environment

Add to `.env`:
```env
MINIAPP_URL=https://yourdomain.com/miniapp
```

## Testing Locally

### Setup ngrok:

```bash
# Download from https://ngrok.com/download
# Extract and run:
./ngrok http 5173

# Copy the HTTPS URL (not HTTP)
# Example: https://abc123.ngrok.io
```

### Update BotFather:

1. Message @BotFather
2. `/myapps`
3. Select your bot
4. `/editapp`
5. Edit App URL to: `https://abc123.ngrok.io`
6. Confirm changes

### Test in Telegram:

1. Send `/app` to your bot
2. Click the button
3. Mini app should open

## Production Deployment

### 1. Build the Mini App

```bash
cd webapp
npm run build
# Creates dist/ folder with optimized build
```

### 2. Deploy to Server

Options:
- **Docker**: Use the provided Dockerfile
  ```bash
  docker build -t duty-bot-webapp:latest .
  docker run -p 80:5173 duty-bot-webapp:latest
  ```

- **Nginx**: Serve the `dist/` folder
  ```nginx
  server {
      listen 80;
      server_name yourdomain.com;

      root /path/to/duty_bot/webapp/dist;
      index index.html;

      location / {
          try_files $uri /index.html;
      }
  }
  ```

- **Vercel/Netlify**: Deploy directly from git
  ```bash
  # Build command: npm run build
  # Output directory: dist
  ```

### 3. Get SSL Certificate

```bash
# Using Let's Encrypt with Certbot
certbot certonly --standalone -d yourdomain.com
```

### 4. Update BotFather

Set App URL to your production domain:
```
https://yourdomain.com/miniapp
```

## How Users Access the Mini App

### Method 1: Via /app Command
```
User sends: /app
Bot replies with button: "📅 Open Schedule App"
User clicks → Mini app opens
```

### Method 2: Via Keyboard
Any message with the mini app button:
```
Click the button below to open the schedule
[📅 Open Schedule App]
```

### Method 3: Direct Link
Users can also open directly via:
```
https://t.me/YOUR_BOT_USERNAME/duty_bot
```

## Troubleshooting

### Mini app shows blank page
- Check browser console for API errors
- Verify `VITE_API_URL` in `webapp/.env`
- Make sure backend API is running and accessible

### "Cannot read user data" error
- Verify Telegram is sending init data header
- Check auth validation in `app/routes/miniapp.py:get_user_from_telegram`
- Ensure user is sending request from within Telegram mini app context

### CORS errors
- Mini app requests include `X-Telegram-Init-Data` header
- Backend should accept requests from mini app origin
- Check FastAPI CORS middleware if needed

### ngrok tunnel keeps changing
- Use ngrok's paid tier for static URL
- Or use alternative like Cloudflare Tunnel (free)

## Useful Links

- [Telegram Bot API Docs](https://core.telegram.org/bots)
- [Telegram Mini Apps Docs](https://core.telegram.org/bots/webapps)
- [Web App Reference](https://core.telegram.org/bots/webapps#initializing-mini-apps)
- [ngrok Documentation](https://ngrok.com/docs)

## Example: Complete Command Handler

```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes

class TelegramHandler:
    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        command = update.message.text.split()[0].lstrip('/')

        if command == 'app':
            # Open mini app
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    text="📅 Open Interactive Schedule",
                    web_app=WebAppInfo(url="https://yourdomain.com/miniapp")
                )
            ]])
            await update.message.reply_text(
                "Click below to manage your team's schedule:",
                reply_markup=keyboard
            )

        elif command == 'help':
            help_text = """
Available commands:
/duty - Show today's duties
/schedule - View full schedule
/team - Manage teams
/app - Open interactive schedule app 📅
/help - Show this help
            """
            await update.message.reply_text(help_text)
```

That's it! Your mini app is now integrated with your Telegram bot! 🎉
