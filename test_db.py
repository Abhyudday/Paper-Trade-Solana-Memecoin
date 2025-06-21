#!/usr/bin/env python3
"""
Database connection test script
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test database connection"""
    try:
        from models import init_db
        from sqlalchemy.orm import sessionmaker
        
        # Get database URL
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("❌ DATABASE_URL environment variable not set")
            return False
        
        logger.info(f"🔗 Testing connection to database...")
        logger.info(f"📝 Database URL: {database_url[:20]}..." if len(database_url) > 20 else f"📝 Database URL: {database_url}")
        
        # Test connection
        engine = init_db(database_url)
        Session = sessionmaker(bind=engine)
        
        # Try to create a session
        session = Session()
        session.execute("SELECT 1")
        session.close()
        
        logger.info("✅ Database connection successful!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def check_environment_variables():
    """Check if all required environment variables are set"""
    required_vars = ['DATABASE_URL', 'BOT_TOKEN', 'ADMIN_ID', 'BIRDEYE_API_KEY']
    missing_vars = []
    
    logger.info("🔍 Checking environment variables...")
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'TOKEN' in var or 'KEY' in var or 'URL' in var:
                masked_value = value[:10] + "..." if len(value) > 10 else "***"
                logger.info(f"✅ {var}: {masked_value}")
            else:
                logger.info(f"✅ {var}: {value}")
        else:
            logger.error(f"❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def main():
    """Main test function"""
    logger.info("🧪 Starting database connection test...")
    
    # Check environment variables
    env_ok = check_environment_variables()
    
    # Test database connection
    db_ok = test_database_connection()
    
    if env_ok and db_ok:
        logger.info("🎉 All tests passed!")
        return True
    else:
        logger.error("❌ Some tests failed")
        return False

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Test runner failed: {e}")
        exit(1) 