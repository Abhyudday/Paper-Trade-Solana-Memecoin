import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from sqlalchemy.orm import sessionmaker
import requests
import json

from models import User, Trade, init_db

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database
engine = init_db(os.getenv('DATABASE_URL'))
Session = sessionmaker(bind=engine)

# Constants
INITIAL_BALANCE = 10000.0
REFERRAL_BONUS = 500.0
ADMIN_ID = int(os.getenv('ADMIN_ID'))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        # Check if user was referred
        referral_id = context.args[0] if context.args else None
        user = User(
            telegram_id=update.effective_user.id,
            username=update.effective_user.username,
            referred_by=int(referral_id) if referral_id else None
        )
        session.add(user)
        
        # Add referral bonus if applicable
        if referral_id:
            referrer = session.query(User).filter_by(telegram_id=int(referral_id)).first()
            if referrer:
                referrer.balance += REFERRAL_BONUS
                await context.bot.send_message(
                    chat_id=referral_id,
                    text=f"🎉 You received {REFERRAL_BONUS} USD for referring a new user!"
                )
    
    session.commit()
    
    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data='balance'),
         InlineKeyboardButton("📈 Trade", callback_data='trade')],
        [InlineKeyboardButton("📊 Portfolio", callback_data='portfolio'),
         InlineKeyboardButton("📱 Refer", callback_data='refer')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Welcome to Solana Memecoin Paper Trading Bot! 🚀\n\n"
        f"Your initial balance: ${INITIAL_BALANCE}\n"
        f"Use the buttons below to start trading:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'balance':
        await show_balance(update, context)
    elif query.data == 'trade':
        await show_trade_options(update, context)
    elif query.data == 'portfolio':
        await show_portfolio(update, context)
    elif query.data == 'refer':
        await show_referral_link(update, context)

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's current balance"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    await update.callback_query.message.reply_text(
        f"💰 Your current balance: ${user.balance:.2f}"
    )

async def show_trade_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show trading options"""
    keyboard = [
        [InlineKeyboardButton("🔍 Search Token", callback_data='search_token')],
        [InlineKeyboardButton("📊 Top Gainers", callback_data='top_gainers')],
        [InlineKeyboardButton("📉 Top Losers", callback_data='top_losers')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.reply_text(
        "Choose a trading option:",
        reply_markup=reply_markup
    )

async def show_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's portfolio"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    trades = session.query(Trade).filter_by(user_id=user.id).all()
    
    if not trades:
        await update.callback_query.message.reply_text("Your portfolio is empty.")
        return
    
    portfolio_text = "📊 Your Portfolio:\n\n"
    for trade in trades:
        portfolio_text += f"Token: {trade.token_symbol}\n"
        portfolio_text += f"Amount: {trade.amount}\n"
        portfolio_text += f"Price: ${trade.price:.6f}\n"
        portfolio_text += f"Type: {trade.trade_type}\n"
        portfolio_text += f"Date: {trade.timestamp.strftime('%Y-%m-%d %H:%M')}\n\n"
    
    await update.callback_query.message.reply_text(portfolio_text)

async def show_referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's referral link"""
    bot = await context.bot.get_me()
    referral_link = f"https://t.me/{bot.username}?start={update.effective_user.id}"
    
    await update.callback_query.message.reply_text(
        f"🎯 Your Referral Link:\n{referral_link}\n\n"
        f"Share this link with your friends! For each new user who joins using your link, "
        f"you'll receive ${REFERRAL_BONUS} in your paper trading balance!"
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users (admin only)"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ This command is only available to administrators.")
        return
    
    if not context.args:
        await update.message.reply_text("Please provide a message to broadcast.")
        return
    
    message = ' '.join(context.args)
    session = Session()
    users = session.query(User).all()
    
    success_count = 0
    for user in users:
        try:
            await context.bot.send_message(chat_id=user.telegram_id, text=message)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to user {user.telegram_id}: {e}")
    
    await update.message.reply_text(f"Broadcast sent to {success_count} users.")

def main():
    """Start the bot"""
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main() 