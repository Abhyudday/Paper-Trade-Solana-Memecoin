from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, BigInteger, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    username = Column(String)
    balance = Column(Float, default=1000.0)  # Initial balance 1k USD
    holdings = Column(JSON, default={})  # Store holdings as JSON
    realized_pnl = Column(Float, default=0.0)
    history = Column(JSON, default=[])  # Store trade history as JSON
    context = Column(JSON, default={})  # Store current context as JSON
    referral_id = Column(BigInteger, nullable=True)  # Renamed from referred_by
    created_at = Column(DateTime, default=datetime.utcnow)
    last_broadcast_message_id = Column(Integer, nullable=True)  # Store last broadcast message ID
    
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_address = Column(String, nullable=False)
    token_symbol = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    trade_type = Column(String, nullable=False)  # 'buy' or 'sell'
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="trades")

def init_db(database_url):
    engine = create_engine(database_url)
    
    # Create tables if they don't exist
    Base.metadata.create_all(engine)
    
    # Ensure all expected columns exist (helps if someone dropped columns manually)
    expected_columns = {
        # column_name: SQL definition to add if missing
        'telegram_id': 'BIGINT UNIQUE',
        'username': 'VARCHAR',
        'balance': 'FLOAT DEFAULT 1000.0',
        'holdings': 'JSONB DEFAULT \'{}\'',
        'realized_pnl': 'FLOAT DEFAULT 0.0',
        'history': 'JSONB DEFAULT \'[]\'',
        'context': 'JSONB DEFAULT \'{}\'',
        'referral_id': 'BIGINT',
        'created_at': 'TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()',
        'last_broadcast_message_id': 'INTEGER'
    }
    
    with engine.connect() as conn:
        try:
            # First, handle the migration from referred_by to referral_id
            check_old_column = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' 
                AND column_name='referred_by'
            """)
            old_column_exists = conn.execute(check_old_column).fetchone()
            
            if old_column_exists:
                logger.info("Renaming 'referred_by' column to 'referral_id'")
                rename_query = text("ALTER TABLE users RENAME COLUMN referred_by TO referral_id")
                conn.execute(rename_query)
                conn.commit()
                logger.info("Successfully renamed column")
            
            # Then ensure all expected columns exist
            for column_name, column_def in expected_columns.items():
                # Check if column exists
                check_column_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='users' 
                    AND column_name=:col
                """)
                result = conn.execute(check_column_query, {'col': column_name}).fetchone()
                if not result:
                    logger.info(f"Adding missing column '{column_name}' to users table")
                    add_column_query = text(f"ALTER TABLE users ADD COLUMN {column_name} {column_def}")
                    conn.execute(add_column_query)
                    conn.commit()
                    logger.info(f"Successfully added '{column_name}' column")
        except Exception as e:
            logger.error(f"Error ensuring columns exist: {e}")
            raise
    
    return engine 