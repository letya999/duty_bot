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
1. **Create App**: Visit [Slack API](https://api.slack.com/apps) and create "From scratch".
2. **Scopes**: Add `chat:write`, `users:read`, `commands`, and `app_mentions:read` to Bot Token Scopes.
3. **Install**: Install to your workspace and copy the "Bot User OAuth Token" (`SLACK_BOT_TOKEN`).
4. **Slash Commands (Important)**:
   - Go to **Slash Commands** in the sidebar.
   - For **EACH** registered command (e.g., `/duty`, `/team`), you must set the **Request URL**.
   - Set the URL to: `https://yourdomain.com/slack/events` (e.g., your ngrok URL + `/slack/events`).
   - *Note*: This is the same URL used for Event Subscriptions, but it must be explicitly set for each command.
5. **Events**: Enable "Event Subscriptions" and set Request URL to `https://yourdomain.com/slack/events`.
6. **Reinstall**: After changing any URLs or Scopes, go to **Install App** and click **Reinstall to Workspace**.
7. **Channel ID**: Right-click a channel in Slack -> "View channel details" -> Copy ID from the bottom.

## 3. Google Calendar Integration
1. **Google Cloud**: Create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. **Enable API**: Enable the "Google Calendar API".
3. **Service Account**: Create a Service Account, generate a **JSON key**, and download it.
4. **Integration**:
   - Option A: Upload the JSON key via the **Admin Panel** (Settings -> Google Calendar).
   - Option B: Paste the JSON content directly into `GOOGLE_SERVICE_ACCOUNT_KEY` in `.env`.

## 4. Troubleshooting Common Issues
- **Ports**: If port 8000 is taken, change `PORT` in `.env`.
- **Database**: Ensure PostgreSQL is running and the connection string is valid.
- **SSL**: For Slack events and Telegram Mini App, you MUST use HTTPS (or `ngrok` for local development).
