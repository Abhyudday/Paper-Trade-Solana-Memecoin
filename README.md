# Solana Memecoin Paper Trading Bot

A Telegram bot that allows users to paper trade Solana memecoins with a virtual balance. Users start with $10,000 in paper trading balance and can earn $500 for each referral.

## Features

- 💰 Initial $10,000 paper trading balance
- 🎯 Referral system ($500 bonus per referral)
- 📊 Portfolio tracking
- 📈 Real-time memecoin price tracking
- 🔍 Token search functionality
- 📱 User-friendly button interface
- 📢 Admin broadcast messages

## Uptime Monitoring

The bot includes built-in uptime monitoring to keep it alive on Railway and prevent it from going to sleep.

### Built-in HTTP Server

The bot now runs a simple HTTP server that responds to health check requests:

- **Root endpoint**: `https://your-bot.railway.app/`
- **Health endpoint**: `https://your-bot.railway.app/health`
- **Ping endpoint**: `https://your-bot.railway.app/ping`

All endpoints return "Bot is alive! 🚀" with a 200 status code.

### Environment Variables for Uptime Monitoring

Add these to your Railway environment variables:

```bash
# Enable/disable uptime monitoring (default: true)
UPTIME_MONITORING_ENABLED=true

# Ping interval in seconds (default: 300 = 5 minutes)
UPTIME_PING_INTERVAL=300

# Comma-separated list of uptime monitoring service URLs
# Example: https://uptimerobot.com/ping/your-monitor-id
UPTIME_URLS=https://your-uptime-service.com/ping/your-id
```

### External Uptime Monitoring Services

You can use external services to ping your bot:

1. **UptimeRobot** (Free):
   - Create a new monitor
   - Set URL to: `https://your-bot.railway.app/health`
   - Set check interval to 5 minutes

2. **Cron-job.org** (Free):
   - Create a new cron job
   - Set URL to: `https://your-bot.railway.app/ping`
   - Set schedule to every 5 minutes

3. **Custom Script**:
   - Use the provided `uptime_monitor.py` script
   - Set `BOT_URL` environment variable to your bot's URL
   - Run it on a separate server or VPS

### Using the Uptime Monitor Script

```bash
# Install dependencies
pip install requests

# Set your bot URL
export BOT_URL=https://your-bot.railway.app

# Run the monitor
python uptime_monitor.py
```

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with the following variables:
   ```
   BOT_TOKEN=your_telegram_bot_token
   BIRDEYE_API_KEY=your_birdeye_api_key
   ADMIN_ID=your_telegram_id
   HELIUS_API_KEY=your_helius_api_key
   DATABASE_URL=your_postgresql_database_url
   UPTIME_MONITORING_ENABLED=true
   UPTIME_PING_INTERVAL=300
   UPTIME_URLS=https://your-uptime-service.com/ping/your-id
   ```

## Deployment on Railway

1. Create a new project on Railway
2. Connect your GitHub repository
3. Add the following environment variables in Railway:
   - BOT_TOKEN
   - BIRDEYE_API_KEY
   - ADMIN_ID
   - HELIUS_API_KEY
   - DATABASE_URL (Railway will provide this for PostgreSQL)
4. Deploy the project

## Usage

1. Start the bot with `/start`
2. Use the buttons to:
   - Check your balance
   - Trade memecoins
   - View your portfolio
   - Get your referral link

## Admin Commands

- `/broadcast <message>` - Send a message to all users

## Security

- All sensitive data is stored in environment variables
- Database credentials are never exposed
- Admin commands are restricted to authorized users

## Contributing

Feel free to submit issues and enhancement requests! 