from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String)
    balance = Column(Float, default=10000.0)  # Initial balance 10k USD
    referred_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
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
    # Drop all tables first to ensure clean state
    Base.metadata.drop_all(engine)
    # Create all tables
    Base.metadata.create_all(engine)
    return engine 