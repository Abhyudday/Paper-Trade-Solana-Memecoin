import os
import logging
import re
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from sqlalchemy.orm import sessionmaker
import requests
import json
import asyncio

from models import User, Trade, init_db
from token_utils import TokenUtils

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

def is_solana_address(text):
    return bool(re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", text.strip()))

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
        [InlineKeyboardButton("🟢 Buy", callback_data="menu_buy"),
         InlineKeyboardButton("🔴 Sell", callback_data="menu_sell")],
        [InlineKeyboardButton("💰 Balance", callback_data="menu_balance"),
         InlineKeyboardButton("📈 PnL", callback_data="menu_pnl")],
        [InlineKeyboardButton("🔁 Copy Trade", callback_data="menu_copy_trade"),
         InlineKeyboardButton("🔎 Check Wallet PnL", callback_data="menu_check_wallet_pnl")],
        [InlineKeyboardButton("👤 Track Wallet", callback_data="menu_track_wallet")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Welcome to the Memecoin Paper Trading Bot!\nChoose an action:",
        reply_markup=reply_markup
    )

async def handle_buy_start(query, context):
    """Handle buy menu selection"""
    await query.message.reply_text("🔍 Enter the Solana token contract address to buy:")

async def handle_sell_start(query, context):
    """Handle sell menu selection"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=query.from_user.id).first()
    trades = session.query(Trade).filter_by(user_id=user.id, trade_type='buy').all()
    
    if not trades:
        await query.message.reply_text("📭 No tokens to sell.")
        return
    
    # Get unique tokens
    tokens = list(set(trade.token_address for trade in trades))
    keyboard = [[InlineKeyboardButton(token, callback_data=f"sell_token:{token}")] for token in tokens]
    await query.message.reply_text("📉 Choose token to sell:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_token_selected_for_sell(query, context):
    """Handle token selection for selling"""
    token = query.data.split(":")[1]
    await query.message.reply_text("💸 Enter the % of token to sell:")

async def handle_buy_token(update, context, token_address, usd_amount):
    """Handle token purchase"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    price = await TokenUtils.get_token_price(token_address)
    if not price:
        await update.message.reply_text("❌ Token price fetch failed.")
        return

    qty = usd_amount / price
    if usd_amount > user.balance:
        await update.message.reply_text("❌ Insufficient balance.")
        return

    user.balance -= usd_amount
    
    # Create trade record
    trade = Trade(
        user_id=user.id,
        token_address=token_address,
        token_symbol=token_address[:8],  # Using first 8 chars as symbol
        amount=qty,
        price=price,
        trade_type='buy'
    )
    session.add(trade)
    session.commit()

    await update.message.reply_text(f"✅ Bought {qty:.4f} of {token_address} at ${price:.4f}")

async def handle_sell_token(update, context, token_address, percent):
    """Handle token sale"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    # Get all buy trades for this token
    buy_trades = session.query(Trade).filter_by(
        user_id=user.id,
        token_address=token_address,
        trade_type='buy'
    ).all()
    
    if not buy_trades:
        await update.message.reply_text("❌ You don't own this token.")
        return

    price = await TokenUtils.get_token_price(token_address)
    if not price:
        await update.message.reply_text("❌ Token price fetch failed.")
        return

    total_qty = sum(trade.amount for trade in buy_trades)
    qty_to_sell = total_qty * (percent / 100)
    
    if qty_to_sell <= 0 or qty_to_sell > total_qty:
        await update.message.reply_text("❗ Invalid sell percentage.")
        return

    usd_value = qty_to_sell * price
    avg_price = sum(trade.price * trade.amount for trade in buy_trades) / total_qty
    pnl = (price - avg_price) * qty_to_sell
    
    user.balance += usd_value
    
    # Create sell trade record
    trade = Trade(
        user_id=user.id,
        token_address=token_address,
        token_symbol=token_address[:8],
        amount=qty_to_sell,
        price=price,
        trade_type='sell'
    )
    session.add(trade)
    session.commit()

    await update.message.reply_text(
        f"✅ Sold {qty_to_sell:.4f} of {token_address} at ${price:.4f}\n"
        f"💵 PnL: ${pnl:.2f}"
    )

async def show_balance(query, context):
    """Show user's balance"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=query.from_user.id).first()
    
    msg = (
        f"💵 Cash: ${user.balance:.2f}\n"
        f"📦 Holdings Value: Click to Check token PnL"
    )
    keyboard = [[InlineKeyboardButton("📈 View Token PnL", callback_data="menu_pnl")]]
    await query.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_pnl_tokens(query, context):
    """Show list of tokens for PnL check"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=query.from_user.id).first()
    trades = session.query(Trade).filter_by(user_id=user.id, trade_type='buy').all()
    
    if not trades:
        await query.message.reply_text("📭 No active positions.")
        return
    
    tokens = list(set(trade.token_address for trade in trades))
    keyboard = [[InlineKeyboardButton(token, callback_data=f"pnl:{token}")] for token in tokens]
    await query.message.reply_text("📈 Click on a token to view PnL:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_token_pnl(query, context):
    """Show PnL for specific token"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=query.from_user.id).first()
    token = query.data.split(":")[1]
    
    trades = session.query(Trade).filter_by(
        user_id=user.id,
        token_address=token
    ).all()
    
    if not trades:
        await query.message.reply_text("❌ No trades found for this token.")
        return

    buy_trades = [t for t in trades if t.trade_type == 'buy']
    sell_trades = [t for t in trades if t.trade_type == 'sell']
    
    total_bought = sum(t.amount for t in buy_trades)
    total_sold = sum(t.amount for t in sell_trades)
    current_holding = total_bought - total_sold
    
    if current_holding <= 0:
        await query.message.reply_text("❌ No active position for this token.")
        return

    avg_price = sum(t.price * t.amount for t in buy_trades) / total_bought
    current_price = await TokenUtils.get_token_price(token)
    
    if not current_price:
        await query.message.reply_text("❌ Couldn't fetch current price.")
        return

    pnl = (current_price - avg_price) * current_holding
    
    msg = (
        f"📊 Token: {token}\n"
        f"• Qty: {current_holding:.4f}\n"
        f"• Avg Price: ${avg_price:.4f}\n"
        f"• Current Price: ${current_price:.4f}\n"
        f"• PnL: ${pnl:.2f}"
    )
    await query.message.reply_text(msg)

async def handle_coming_soon(query, context, feature):
    """Handle features under construction"""
    await query.message.reply_text(f"🚧 {feature} feature is under construction.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users (admin only)"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("📝 Usage: /broadcast Your message here")
        return
    
    message = ' '.join(context.args)
    session = Session()
    users = session.query(User).all()
    
    sent = 0
    for user in users:
        try:
            await context.bot.send_message(chat_id=user.telegram_id, text=message)
            sent += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to user {user.telegram_id}: {e}")
    
    await update.message.reply_text(f"✅ Message sent to {sent} users.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    text = update.message.text.strip()
    
    if is_solana_address(text):
        keyboard = [
            [InlineKeyboardButton("🟢 Buy", callback_data=f"ca_buy:{text}"),
             InlineKeyboardButton("🔴 Sell", callback_data=f"ca_sell:{text}")]
        ]
        await update.message.reply_text(
            "Detected token address. Choose action:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await start(update, context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_buy":
        await handle_buy_start(query, context)
    elif data == "menu_sell":
        await handle_sell_start(query, context)
    elif data.startswith("sell_token:"):
        await handle_token_selected_for_sell(query, context)
    elif data == "menu_balance":
        await show_balance(query, context)
    elif data == "menu_pnl":
        await show_pnl_tokens(query, context)
    elif data.startswith("pnl:"):
        await show_token_pnl(query, context)
    elif data.startswith("ca_buy:"):
        token = data.split(":")[1]
        await query.message.reply_text("💵 How much USD to invest?")
    elif data.startswith("ca_sell:"):
        token = data.split(":")[1]
        await query.message.reply_text("💸 Enter the % of token to sell:")
    elif data == "menu_copy_trade":
        await handle_coming_soon(query, context, "Copy Trade")
    elif data == "menu_check_wallet_pnl":
        await handle_coming_soon(query, context, "Check Wallet PnL")
    elif data == "menu_track_wallet":
        await handle_coming_soon(query, context, "Track Wallet")

def main():
    """Start the bot"""
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the bot
    print("Bot running...")
    application.run_polling()

if __name__ == '__main__':
    main() 