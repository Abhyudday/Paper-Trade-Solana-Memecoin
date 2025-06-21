# Troubleshooting Guide

## Common Issues and Solutions

### 1. Asyncio Coroutine Errors

**Symptoms:**
- `RuntimeWarning: coroutine 'Application.stop' was never awaited`
- `RuntimeError: Event loop is closed`
- `Task was destroyed but it is pending`

**Solutions:**
- The bot has been updated to handle asyncio lifecycle properly
- Use the new `start_bot.py` script instead of running `bot.py` directly
- Ensure all coroutines are properly awaited

### 2. Port Conflicts

**Symptoms:**
- `Address already in use` errors
- Uptime server fails to start

**Solutions:**
- Uptime server now uses port 8081 by default (configurable via `UPTIME_PORT`)
- Main application uses port 8080 (configurable via `PORT`)
- Check for other services using the same ports

### 3. Database Connection Issues

**Symptoms:**
- `Failed to initialize database` errors
- Connection timeouts

**Solutions:**
- Ensure `DATABASE_URL` environment variable is set correctly
- Check database server is running and accessible
- Verify network connectivity

### 4. Environment Variables

**Required Variables:**
- `BOT_TOKEN`: Your Telegram bot token
- `DATABASE_URL`: PostgreSQL connection string
- `ADMIN_ID`: Your Telegram user ID for admin commands
- `BIRDEYE_API_KEY`: API key for token price data

**Optional Variables:**
- `UPTIME_MONITORING_ENABLED`: Set to 'true' to enable uptime monitoring
- `UPTIME_PING_INTERVAL`: Seconds between uptime pings (default: 300)
- `UPTIME_URLS`: Comma-separated list of uptime service URLs
- `UPTIME_PORT`: Port for uptime server (default: 8081)

### 5. Testing

Run the test script to verify everything is working:

```bash
python test_bot.py
```

This will test:
- Bot initialization
- Uptime server startup
- Database connectivity

### 6. Deployment

For Railway deployment:
- Use the updated `Procfile` that points to `start_bot.py`
- Ensure all environment variables are set in Railway dashboard
- Check logs for any startup errors

### 7. Logs

The bot provides detailed logging. Check for:
- Database initialization messages
- Uptime server startup messages
- Bot application startup messages
- Any error messages with full tracebacks

### 8. Manual Startup

If you need to start the bot manually:

```bash
# Test first
python test_bot.py

# Start the bot
python start_bot.py
```

### 9. Common Error Messages

**"Missing required environment variables"**
- Set all required environment variables

**"Failed to initialize database"**
- Check `DATABASE_URL` format and connectivity

**"Bot startup failed"**
- Check `BOT_TOKEN` is valid
- Verify bot is not already running

**"Uptime server startup failed"**
- Check if port 8081 is available
- Try changing `UPTIME_PORT` environment variable 