# Troubleshooting Guide

## Common Issues and Solutions

### 1. Railway Database Connection Issues

**Symptoms:**
- `connection to server at "postgres.railway.internal" failed: Connection refused`
- `Is the server running on that host and accepting TCP/IP connections?`
- Database initialization fails

**Solutions:**
1. **Check if PostgreSQL service is provisioned:**
   - Go to your Railway dashboard
   - Check if you have a PostgreSQL service added to your project
   - If not, add a PostgreSQL service from the Railway marketplace

2. **Verify DATABASE_URL:**
   - In Railway dashboard, go to your bot service
   - Check the "Variables" tab
   - Ensure `DATABASE_URL` is set correctly
   - The format should be: `postgresql://username:password@host:port/database`

3. **Check service status:**
   - Ensure the PostgreSQL service is running (green status)
   - Restart the PostgreSQL service if needed

4. **Test database connection:**
   ```bash
   python3 test_db.py
   ```

5. **Common Railway DATABASE_URL format:**
   ```
   postgresql://postgres:password@containers-us-west-XX.railway.app:XXXX/railway
   ```

### 2. Asyncio Coroutine Errors

**Symptoms:**
- `RuntimeWarning: coroutine 'Application.stop' was never awaited`
- `RuntimeError: Event loop is closed`
- `Task was destroyed but it is pending`

**Solutions:**
- The bot has been updated to handle asyncio lifecycle properly
- Use the new `start_bot.py` script instead of running `bot.py` directly
- Ensure all coroutines are properly awaited

### 3. Port Conflicts

**Symptoms:**
- `Address already in use` errors
- Uptime server fails to start

**Solutions:**
- Uptime server now uses port 8081 by default (configurable via `UPTIME_PORT`)
- Main application uses port 8080 (configurable via `PORT`)
- Check for other services using the same ports

### 4. Database Connection Issues

**Symptoms:**
- `Failed to initialize database` errors
- Connection timeouts

**Solutions:**
- Ensure `DATABASE_URL` environment variable is set correctly
- Check database server is running and accessible
- Verify network connectivity
- The bot now includes retry logic (5 attempts with 10-second delays)

### 5. Environment Variables

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

### 6. Testing

Run the test scripts to verify everything is working:

```bash
# Test database connection
python3 test_db.py

# Test bot components
python3 test_bot.py
```

### 7. Deployment

For Railway deployment:
- Use the updated `Procfile` that points to `start_bot.py`
- Ensure all environment variables are set in Railway dashboard
- Check logs for any startup errors
- Make sure PostgreSQL service is provisioned and running

### 8. Logs

The bot provides detailed logging. Check for:
- Database initialization messages
- Uptime server startup messages
- Bot application startup messages
- Any error messages with full tracebacks

### 9. Manual Startup

If you need to start the bot manually:

```bash
# Test database first
python3 test_db.py

# Test bot components
python3 test_bot.py

# Start the bot
python3 start_bot.py
```

### 10. Common Error Messages

**"Missing required environment variables"**
- Set all required environment variables in Railway dashboard

**"Failed to initialize database"**
- Check `DATABASE_URL` format and connectivity
- Ensure PostgreSQL service is running on Railway
- Use `test_db.py` to diagnose connection issues

**"Bot startup failed"**
- Check `BOT_TOKEN` is valid
- Verify bot is not already running

**"Uptime server startup failed"**
- Check if port 8081 is available
- Try changing `UPTIME_PORT` environment variable

### 11. Railway-Specific Issues

**Service not found:**
- Add PostgreSQL service from Railway marketplace
- Link the service to your bot project

**Connection refused:**
- Check if PostgreSQL service is running
- Verify the service is linked to your bot project
- Check the `DATABASE_URL` in your bot service variables

**Permission denied:**
- Ensure the database user has proper permissions
- Check if the database exists and is accessible 