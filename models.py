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
    balance = Column(Float, default=10000.0)  # Initial balance 10k USD
    holdings = Column(JSON, default={})  # Store holdings as JSON
    realized_pnl = Column(Float, default=0.0)
    history = Column(JSON, default=[])  # Store trade history as JSON
    context = Column(JSON, default={})  # Store current context as JSON
    referred_by = Column(BigInteger, nullable=True)
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
    
    # Add new columns if they don't exist
    with engine.connect() as conn:
        try:
            # Check if last_broadcast_message_id column exists
            check_column_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' 
                AND column_name='last_broadcast_message_id'
            """)
            result = conn.execute(check_column_query).fetchone()
            
            if not result:
                logger.info("Adding last_broadcast_message_id column to users table")
                add_column_query = text("""
                    ALTER TABLE users 
                    ADD COLUMN last_broadcast_message_id INTEGER
                """)
                conn.execute(add_column_query)
                conn.commit()
                logger.info("Successfully added last_broadcast_message_id column")
        except Exception as e:
            logger.error(f"Error during database migration: {e}")
            raise
    
    return engine 