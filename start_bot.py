#!/usr/bin/env python3
"""
Startup script for the Telegram bot with better error handling
"""

import os
import sys
import asyncio
import logging
import signal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

def main():
    """Main startup function"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check required environment variables
    required_vars = ['BOT_TOKEN', 'DATABASE_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    logger.info("🚀 Starting Telegram bot...")
    
    try:
        # Import and run the main bot
        from bot import main as bot_main
        bot_main()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"❌ Bot startup failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main() 