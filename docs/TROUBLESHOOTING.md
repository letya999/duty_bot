# Troubleshooting Guide

## Database Errors
- **Connection Refused**: Check if PostgreSQL is running. In Docker, use `docker-compose ps` to verify the `db` service.
- **Migration Errors**: If the schema is out of sync, try running migrations manually or check logs for `alembic` errors.

## Bot Response Issues
- **Telegram**: Ensure `TELEGRAM_TOKEN` is valid. Check logs with `docker-compose logs -f app | grep telegram`.
- **Slack**: Verification fails? Check `SLACK_SIGNING_SECRET`. Events not reaching? Check if your server is reachable via the public URL.
- **Commands ignored**: Ensure the bot has permission to read messages in the group/channel.

## Google Calendar Sync
- **Events not appearing**: Ensure the Service Account has permission to create calendars. Check the "Google Calendar" settings in the Admin Panel for sync status.
- **Encryption error**: If you changed `ENCRYPTION_KEY` after syncing, you may need to re-upload the Google key.

## Common Docker Commands
```bash
# View logs
docker-compose logs -f app

# Restart application
docker-compose restart app

# Rebuild images
docker-compose up -d --build
```
