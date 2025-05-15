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