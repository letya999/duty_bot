# External Services Setup Guide

This guide provides detailed instructions for configuring Telegram, Slack, and Google Calendar integrations.

## 1. Telegram Bot Setup
1. **Create Bot**: Message [@BotFather](https://t.me/botfather) and use `/newbot`.
2. **Get Token**: BotFather will provide an API token. Save it as `TELEGRAM_TOKEN`.
3. **Get Chat ID**: Add your bot to the target group and use a service like `@getidsbot` to find the Group ID (usually starts with `-100`).
4. **Mini App**: 
   - Use `/mybots` in BotFather -> Select your bot -> "Bot Settings" -> "Menu Button".
   - Set the URL to your hosted webapp (e.g., `https://yourdomain.com/webapp`).

## 2. Slack Bot Setup

### 2.1 Create Slack App
1. Visit [Slack API](https://api.slack.com/apps) and click **Create New App** -> **From scratch**.
2. Enter an app name (e.g., "duty_bot") and select your workspace.
3. You'll get your **App ID**, **Client ID**, and other credentials in the **App Credentials** section.

### 2.2 Configure OAuth & Permissions
1. Go to **OAuth & Permissions** in the left sidebar.
2. Under **Redirect URLs**, add your OAuth callback URL:
   - `https://yourdomain.com/api/admin/auth/slack/callback` (e.g., `https://your-ngrok-url.ngrok-free.dev/api/admin/auth/slack/callback`)
   - Click **Save URLs**
3. Under **Bot Token Scopes**, add the following scopes:
   - `chat:write` - Send messages as the bot
   - `commands` - Add shortcuts and slash commands
   - `groups:read` - View basic information about private channels
   - `users.profile:read` - View profile details about people
   - `users:read` - View people in the workspace
   - `users:read.email` - View email addresses of people

### 2.3 Install to Workspace
1. Go to **Install App** in the sidebar.
2. Click **Install to Workspace** (or **Reinstall to Workspace** if you've made changes).
3. Copy the **Bot User OAuth Token** (starts with `xoxb-`) and save it as `SLACK_BOT_TOKEN` in your `.env` file.

### 2.4 Configure Slash Commands
1. Go to **Slash Commands** in the left sidebar.
2. Click **Create New Command** for each command you need (e.g., `/duty`).
3. For each command, set:
   - **Command**: `/duty` (or your command name)
   - **Request URL**: `https://yourdomain.com/slack/events` (same ngrok URL + `/slack/events`)
   - **Short Description**: Brief description (e.g., "Show all on-duty today")
   - **Usage Hint**: Optional hint for parameters (e.g., "[which rocket to launch]")
4. Click **Save**.

### 2.5 Configure Event Subscriptions
1. Go to **Event Subscriptions** in the left sidebar.
2. Toggle **Enable Events** to ON.
3. Under **Request URL**, enter: `https://yourdomain.com/slack/events`
4. Slack will verify the URL by sending a challenge request.
5. Under **Subscribe to bot events**, add the events you need (e.g., `app_mention`, `message.channels`).

### 2.6 Get Signing Secret
1. Go to **Basic Information** in the sidebar.
2. Under **App Credentials**, copy the **Signing Secret** and save it as `SLACK_SIGNING_SECRET` in your `.env` file.
3. Also copy:
   - **Client ID** → `SLACK_CLIENT_ID`
   - **Client Secret** → `SLACK_CLIENT_SECRET`

### 2.7 Channel Setup
1. Right-click a channel in Slack -> **View channel details** -> Copy the channel ID from the bottom.
2. Save this as `SLACK_CHANNEL_ID` in your `.env` file.

### 2.8 Final Steps
- After making any changes to URLs, Scopes, or Permissions, return to **Install App** and click **Reinstall to Workspace**.
- Verify that all environment variables are set correctly in your `.env` file.

## 3. Google Calendar Integration

### 3.1 Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Click the **Project** dropdown at the top.
3. Click **NEW PROJECT**.
4. Enter a project name (e.g., "duty_bot") and click **CREATE**.
5. Wait for the project to be created and selected.

### 3.2 Enable Google Calendar API
1. In the Google Cloud Console, go to **APIs & Services** → **Library**.
2. Search for "Google Calendar API".
3. Click on it and then click **ENABLE**.
4. You should see "API enabled" confirmation.

### 3.3 Create Service Account
1. Go to **APIs & Services** → **Credentials**.
2. Click **+ CREATE CREDENTIALS** at the top.
3. Select **Service Account**.
4. Fill in the details:
   - **Service account name**: e.g., "duty-bot"
   - **Service account ID**: Auto-generated
   - **Description**: Optional (e.g., "Service account for duty_bot calendar integration")
5. Click **CREATE AND CONTINUE**.
6. On the next page, you can skip "Grant this service account access to project" for now.
7. Click **CONTINUE** and then **DONE**.

### 3.4 Generate Service Account Key (JSON)
1. Go to **APIs & Services** → **Service Accounts**.
2. Click on the service account you just created.
3. Go to the **Keys** tab.
4. Click **ADD KEY** → **Create new key**.
5. Select **JSON** and click **CREATE**.
6. A JSON file will be downloaded automatically. Save it securely.

### 3.5 Grant Calendar Access (If Using Shared Calendar)
If you want the service account to access a specific calendar:
1. Open the calendar in Google Calendar.
2. Go to **Settings & sharing** → **Calendar settings**.
3. Scroll to **Share with specific people and groups**.
4. Click **Add people and groups**.
5. Add the service account email (found in the JSON file under `client_email`, looks like `name@project-id.iam.gserviceaccount.com`).
6. Grant **Editor** or **Viewer** permissions depending on what the bot needs.

### 3.6 Configure Your Application
Choose one of the following methods to provide the service account credentials:

**Option A: Upload JSON via Admin Panel (Recommended)**
1. Start your application.
2. Go to the **Admin Panel** → **Settings** → **Google Calendar**.
3. Upload the downloaded JSON file.
4. The system will automatically extract and use the credentials.

**Option B: Use Environment Variable**
1. Open the JSON key file in a text editor.
2. Copy the entire JSON content.
3. In your `.env` file, add:
   ```
   GOOGLE_SERVICE_ACCOUNT_KEY='{"type":"service_account","project_id":"...","private_key":"...","client_email":"..."}'
   ```
   (Keep it on one line, escaped properly for your shell environment, or use a heredoc).

**Option C: Paste JSON Path**
1. Save the JSON file in a secure location.
2. In your `.env` file, add:
   ```
   GOOGLE_SERVICE_ACCOUNT_KEY_PATH=/path/to/service-account-key.json
   ```
   (Ensure the file is not accessible to unauthorized users).

### 3.7 Test the Integration
1. Restart your application.
2. Try creating or updating an event through your app.
3. Check if the calendar updates in Google Calendar.
4. If there are issues, check application logs for auth errors.

## 4. Troubleshooting Common Issues
- **Ports**: If port 8000 is taken, change `PORT` in `.env`.
- **Database**: Ensure PostgreSQL is running and the connection string is valid.
- **SSL**: For Slack events and Telegram Mini App, you MUST use HTTPS (or `ngrok` for local development).
