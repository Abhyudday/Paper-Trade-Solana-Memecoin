import os
import logging
import re
import signal
import sys
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from sqlalchemy.orm import sessionmaker
import requests
import asyncio

from models import User, init_db

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
BIRDEYE_API_KEY = os.getenv('BIRDEYE_API_KEY')

# Global application instance
application = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal. Cleaning up...")
    if application:
        application.stop()
    sys.exit(0)

def is_solana_address(text):
    return bool(re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", text.strip()))

async def get_token_price(token_address):
    url = f"https://public-api.birdeye.so/defi/price?address={token_address}"
    headers = {
        "accept": "application/json",
        "x-chain": "solana",
        "X-API-KEY": BIRDEYE_API_KEY
    }
    try:
        response = await asyncio.to_thread(requests.get, url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return float(data["data"]["value"])
    except Exception as e:
        logger.error(f"Error fetching token price: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    try:
        session = Session()
        user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
        
        if not user:
            user = User(
                telegram_id=update.effective_user.id,
                username=update.effective_user.username,
                balance=INITIAL_BALANCE,
                holdings={},
                realized_pnl=0.0,
                history=[],
                context={}
            )
            session.add(user)
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
        await update.message.reply_text(
            "👋 Welcome to the Memecoin Paper Trading Bot!\nChoose an action:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def handle_buy_start(query, context):
    """Handle buy menu selection"""
    try:
        session = Session()
        user = session.query(User).filter_by(telegram_id=query.from_user.id).first()
        user.context = {'mode': 'buy'}
        session.commit()
        await query.message.reply_text("🔍 Enter the Solana token contract address to buy:")
    except Exception as e:
        logger.error(f"Error in buy start: {e}")
        await query.message.reply_text("❌ An error occurred. Please try again.")

async def handle_sell_start(query, context):
    """Handle sell menu selection"""
    try:
        session = Session()
        user = session.query(User).filter_by(telegram_id=query.from_user.id).first()
        tokens = list((user.holdings or {}).keys())
        if not tokens:
            await query.message.reply_text("📭 No tokens to sell.")
            return
        keyboard = [[InlineKeyboardButton(token, callback_data=f"sell_token:{token}")] for token in tokens]
        await query.message.reply_text("📉 Choose token to sell:", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in sell start: {e}")
        await query.message.reply_text("❌ An error occurred. Please try again.")

async def handle_token_selected_for_sell(query, context):
    """Handle token selection for selling"""
    try:
        session = Session()
        user = session.query(User).filter_by(telegram_id=query.from_user.id).first()
        token = query.data.split(":")[1]
        user.context = {'mode': 'sell', 'token': token}
        session.commit()
        await query.message.reply_text("💸 Enter the % of token to sell:")
    except Exception as e:
        logger.error(f"Error in token selection: {e}")
        await query.message.reply_text("❌ An error occurred. Please try again.")

async def handle_buy_token(update, context, ca, usd_amount):
    """Handle token purchase"""
    try:
        session = Session()
        user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
        
        # Get token price
        price = await get_token_price(ca)
        if not price:
            await update.message.reply_text("❌ Token price fetch failed.")
            return

        # Calculate quantity
        qty = usd_amount / price
        if usd_amount > user.balance:
            await update.message.reply_text(f"❌ Insufficient balance. You have ${user.balance:.2f}")
            return

        # Update user balance
        user.balance -= usd_amount

        # Update holdings
        holdings = user.holdings or {}
        holding = holdings.get(ca)
        if holding:
            total_cost = holding['qty'] * holding['avg_price'] + usd_amount
            new_qty = holding['qty'] + qty
            holding['avg_price'] = total_cost / new_qty
            holding['qty'] = new_qty
        else:
            holdings[ca] = {'qty': qty, 'avg_price': price}
        
        user.holdings = holdings
        user.history = user.history or []
        user.history.append(f"🟢 Bought {qty:.4f} of {ca} at ${price:.4f}")
        session.commit()

        # Send confirmation message
        await update.message.reply_text(
            f"✅ Trade executed successfully!\n\n"
            f"• Amount: ${usd_amount:.2f}\n"
            f"• Quantity: {qty:.4f}\n"
            f"• Price: ${price:.4f}\n"
            f"• Remaining Balance: ${user.balance:.2f}"
        )
    except Exception as e:
        logger.error(f"Error in buy token: {e}")
        await update.message.reply_text("❌ An error occurred during the trade. Please try again.")
        session.rollback()

async def handle_sell_token(update, context, token, percent):
    """Handle token sale"""
    try:
        session = Session()
        user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
        
        holdings = user.holdings or {}
        holding = holdings.get(token)
        if not holding:
            await update.message.reply_text("❌ You don't own this token.")
            return

        price = await get_token_price(token)
        if not price:
            await update.message.reply_text("❌ Token price fetch failed.")
            return

        qty_to_sell = holding['qty'] * (percent / 100)
        if qty_to_sell <= 0 or qty_to_sell > holding['qty']:
            await update.message.reply_text("❗ Invalid sell percentage.")
            return

        usd_value = qty_to_sell * price
        pnl = (price - holding['avg_price']) * qty_to_sell
        user.balance += usd_value
        user.realized_pnl += pnl
        holding['qty'] -= qty_to_sell

        if holding['qty'] <= 0.00001:
            del holdings[token]
        
        user.holdings = holdings
        user.history = user.history or []
        user.history.append(f"🔴 Sold {qty_to_sell:.4f} of {token} at ${price:.4f} | PnL: ${pnl:.2f}")
        session.commit()

        await update.message.reply_text(f"✅ Sold {qty_to_sell:.4f} of {token} at ${price:.4f}\n💵 PnL: ${pnl:.2f}")
    except Exception as e:
        logger.error(f"Error in sell token: {e}")
        await update.message.reply_text("❌ An error occurred during the trade. Please try again.")

async def show_balance(query, context):
    """Show user's balance"""
    try:
        session = Session()
        user = session.query(User).filter_by(telegram_id=query.from_user.id).first()
        
        # Calculate total holdings value
        total_holdings = 0
        holdings = user.holdings or {}
        for token, holding in holdings.items():
            price = await get_token_price(token)
            if price:
                total_holdings += holding['qty'] * price

        msg = (
            f"💵 Cash: ${user.balance:.2f}\n"
            f"📦 Holdings Value: ${total_holdings:.2f}\n"
            f"💰 Total Value: ${(user.balance + total_holdings):.2f}\n"
            f"📈 Realized PnL: ${user.realized_pnl:.2f}"
        )
        keyboard = [[InlineKeyboardButton("📈 View Token PnL", callback_data="menu_pnl")]]
        await query.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in show balance: {e}")
        await query.message.reply_text("❌ An error occurred. Please try again.")

async def show_pnl_tokens(query, context):
    """Show list of tokens for PnL check"""
    try:
        session = Session()
        user = session.query(User).filter_by(telegram_id=query.from_user.id).first()
        tokens = list((user.holdings or {}).keys())
        if not tokens:
            await query.message.reply_text("📭 No active positions.")
            return
        keyboard = [[InlineKeyboardButton(token, callback_data=f"pnl:{token}")] for token in tokens]
        await query.message.reply_text("📈 Click on a token to view PnL:", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in show PnL tokens: {e}")
        await query.message.reply_text("❌ An error occurred. Please try again.")

async def show_token_pnl(query, context):
    """Show PnL for specific token"""
    try:
        session = Session()
        user = session.query(User).filter_by(telegram_id=query.from_user.id).first()
        token = query.data.split(":")[1]
        holding = (user.holdings or {}).get(token)
        if not holding:
            await query.message.reply_text("❌ No holdings found for this token.")
            return

        price = await get_token_price(token)
        if not price:
            await query.message.reply_text("❌ Couldn't fetch price.")
            return

        qty = holding['qty']
        avg = holding['avg_price']
        pnl = (price - avg) * qty
        msg = (
            f"📊 Token: {token}\n"
            f"• Qty: {qty:.4f}\n"
            f"• Avg Price: ${avg:.4f}\n"
            f"• Current Price: ${price:.4f}\n"
            f"• PnL: ${pnl:.2f}"
        )
        await query.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Error in show token PnL: {e}")
        await query.message.reply_text("❌ An error occurred. Please try again.")

async def handle_coming_soon(query, context, feature):
    """Handle features under construction"""
    await query.message.reply_text(f"🚧 {feature} feature is under construction.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users (admin only)"""
    try:
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
    except Exception as e:
        logger.error(f"Error in broadcast: {e}")
        await update.message.reply_text("❌ An error occurred during broadcast.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    try:
        session = Session()
        user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
        if not user:
            await start(update, context)
            return

        text = update.message.text.strip()
        ctx = user.context or {}
        
        if 'mode' in ctx:
            if ctx['mode'] == 'buy':
                if is_solana_address(text):
                    ctx['ca'] = text
                    user.context = ctx
                    session.commit()
                    await update.message.reply_text("💵 How much USD to invest?")
                elif 'ca' in ctx:
                    try:
                        usd = float(text)
                        if usd <= 0:
                            await update.message.reply_text("❌ Please enter a positive amount.")
                            return
                        await handle_buy_token(update, context, ctx['ca'], usd)
                        user.context = {}
                        session.commit()
                    except ValueError:
                        await update.message.reply_text("❌ Please enter a valid number.")
                    except Exception as e:
                        logger.error(f"Error processing buy amount: {e}")
                        await update.message.reply_text("❌ An error occurred. Please try again.")
                return
            elif ctx['mode'] == 'sell' and 'token' in ctx:
                try:
                    percent = float(text)
                    if percent <= 0 or percent > 100:
                        await update.message.reply_text("❌ Please enter a percentage between 0 and 100.")
                        return
                    await handle_sell_token(update, context, ctx['token'], percent)
                    user.context = {}
                    session.commit()
                except ValueError:
                    await update.message.reply_text("❌ Please enter a valid percentage.")
                except Exception as e:
                    logger.error(f"Error processing sell percentage: {e}")
                    await update.message.reply_text("❌ An error occurred. Please try again.")
                return

        if is_solana_address(text):
            keyboard = [
                [InlineKeyboardButton("🟢 Buy", callback_data=f"ca_buy:{text}"),
                 InlineKeyboardButton("🔴 Sell", callback_data=f"ca_sell:{text}")]
            ]
            await update.message.reply_text("Detected token address. Choose action:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await start(update, context)
    except Exception as e:
        logger.error(f"Error in handle message: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    try:
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
            session = Session()
            user = session.query(User).filter_by(telegram_id=query.from_user.id).first()
            ca = data.split(":")[1]
            user.context = {'mode': 'buy', 'ca': ca}
            session.commit()
            await query.message.reply_text("💵 How much USD to invest?")
        elif data.startswith("ca_sell:"):
            session = Session()
            user = session.query(User).filter_by(telegram_id=query.from_user.id).first()
            token = data.split(":")[1]
            user.context = {'mode': 'sell', 'token': token}
            session.commit()
            await query.message.reply_text("💸 Enter the % of token to sell:")
        elif data == "menu_copy_trade":
            await handle_coming_soon(query, context, "Copy Trade")
        elif data == "menu_check_wallet_pnl":
            await handle_coming_soon(query, context, "Check Wallet PnL")
        elif data == "menu_track_wallet":
            await handle_coming_soon(query, context, "Track Wallet")
    except Exception as e:
        logger.error(f"Error in button handler: {e}")
        await update.callback_query.message.reply_text("❌ An error occurred. Please try again.")

def main():
    """Start the bot"""
    global application
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create application
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the bot
    logger.info("Bot starting...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main() 