#!/usr/bin/env python3
"""
Test script to verify bot startup without asyncio issues
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def test_bot_startup():
    """Test basic bot startup without running the full application"""
    try:
        from telegram.ext import Application
        
        # Create application
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            logger.error("BOT_TOKEN not found in environment variables")
            return False
            
        application = Application.builder().token(bot_token).build()
        
        # Test initialization
        await application.initialize()
        logger.info("✅ Bot initialization successful")
        
        # Test starting
        await application.start()
        logger.info("✅ Bot start successful")
        
        # Test stopping
        await application.stop()
        await application.shutdown()
        logger.info("✅ Bot shutdown successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Bot startup test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def test_uptime_server():
    """Test uptime server startup"""
    try:
        from aiohttp import web
        
        app = web.Application()
        app.router.add_get('/', lambda r: web.Response(text="OK"))
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', 8081)
        await site.start()
        
        logger.info("✅ Uptime server startup successful")
        
        await runner.cleanup()
        logger.info("✅ Uptime server cleanup successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Uptime server test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def main():
    """Run all tests"""
    logger.info("🧪 Starting bot tests...")
    
    # Test uptime server
    uptime_success = await test_uptime_server()
    
    # Test bot startup
    bot_success = await test_bot_startup()
    
    if uptime_success and bot_success:
        logger.info("🎉 All tests passed!")
        return True
    else:
        logger.error("❌ Some tests failed")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Test runner failed: {e}")
        exit(1) 