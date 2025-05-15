from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String)
    balance = Column(Float, default=10000.0)  # Initial balance 10k USD
    referred_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    trades = relationship("Trade", back_populates="user")

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    token_address = Column(String)
    token_symbol = Column(String)
    amount = Column(Float)
    price = Column(Float)
    trade_type = Column(String)  # 'buy' or 'sell'
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="trades")

def init_db(database_url):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine 