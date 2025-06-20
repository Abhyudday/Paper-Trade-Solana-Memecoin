#!/usr/bin/env python3
"""
Uptime Monitor Script for Railway Bot
This script can be used with external uptime monitoring services like UptimeRobot
to keep the bot alive by making periodic requests to the bot's health endpoint.
"""

import requests
import time
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def ping_bot():
    """Ping the bot's health endpoint"""
    try:
        # Get the bot URL from environment variable or use default
        bot_url = os.getenv('BOT_URL', 'https://your-bot-name.railway.app')
        
        # Add health endpoint
        health_url = f"{bot_url}/health"
        
        response = requests.get(health_url, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ Bot is alive! Response: {response.text}")
            return True
        else:
            logger.warning(f"⚠️ Bot responded with status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to ping bot: {e}")
        return False

def main():
    """Main function to run the uptime monitor"""
    logger.info("🚀 Starting uptime monitor...")
    
    # Get ping interval from environment (default: 5 minutes)
    ping_interval = int(os.getenv('PING_INTERVAL', 300))
    
    logger.info(f"📡 Will ping bot every {ping_interval} seconds")
    
    while True:
        try:
            ping_bot()
        except KeyboardInterrupt:
            logger.info("🛑 Uptime monitor stopped by user")
            break
        except Exception as e:
            logger.error(f"💥 Unexpected error: {e}")
        
        time.sleep(ping_interval)

if __name__ == "__main__":
    main() 