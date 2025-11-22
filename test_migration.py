#!/usr/bin/env python3
"""
Test script to verify the database migration from referred_by to referral_id
"""

import os
import logging
from dotenv import load_dotenv
from models import init_db
from sqlalchemy import text

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def test_migration():
    """Test the database migration"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL not found in environment variables")
            return False
        
        logger.info("Initializing database (this will run the migration)...")
        engine = init_db(database_url)
        
        # Check the current columns in the users table
        with engine.connect() as conn:
            check_columns = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users'
                ORDER BY ordinal_position
            """)
            columns = conn.execute(check_columns).fetchall()
            
            logger.info("Current columns in users table:")
            for col in columns:
                logger.info(f"  - {col[0]}")
            
            # Check if referred_by still exists (should not)
            referred_by_exists = any(col[0] == 'referred_by' for col in columns)
            # Check if referral_id exists (should exist)
            referral_id_exists = any(col[0] == 'referral_id' for col in columns)
            
            if referred_by_exists:
                logger.error("❌ Migration failed: 'referred_by' column still exists")
                return False
            
            if not referral_id_exists:
                logger.error("❌ Migration failed: 'referral_id' column does not exist")
                return False
            
            logger.info("✅ Migration successful: 'referral_id' column exists")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error during migration test: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_migration()
    exit(0 if success else 1)
