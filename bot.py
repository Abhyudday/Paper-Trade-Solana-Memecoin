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
import aiohttp
from aiohttp import web
import threading
import time

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
import time
max_retries = 5
retry_delay = 10  # seconds

for attempt in range(max_retries):
    try:
        logger.info(f"Attempting to connect to database (attempt {attempt + 1}/{max_retries})...")
        engine = init_db(os.getenv('DATABASE_URL'))
        Session = sessionmaker(bind=engine)
        logger.info("Database initialized successfully")
        break
    except Exception as e:
        logger.error(f"Failed to initialize database (attempt {attempt + 1}/{max_retries}): {e}")
        if attempt < max_retries - 1:
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            logger.error("Max retries reached. Please check your DATABASE_URL and ensure the database is running.")
            raise

# Constants
INITIAL_BALANCE = 1000.0
REFERRAL_BONUS = 500.0
ADMIN_ID = int(os.getenv('ADMIN_ID'))
BIRDEYE_API_KEY = os.getenv('BIRDEYE_API_KEY')

# Uptime monitoring settings
UPTIME_MONITORING_ENABLED = os.getenv('UPTIME_MONITORING_ENABLED', 'true').lower() == 'true'
UPTIME_PING_INTERVAL = int(os.getenv('UPTIME_PING_INTERVAL', '300'))  # 5 minutes default
UPTIME_URLS = os.getenv('UPTIME_URLS', '').split(',') if os.getenv('UPTIME_URLS') else []

# Promotional links
TROJAN_BOT_LINK = "https://t.me/solana_trojanbot?start=r-abhyudday"
GMGN_BOT_LINK = "https://t.me/GMGN_sol_bot?start=i_NEu2DbZx"

# In-memory user data
USERS = {}

# Global variables for uptime monitoring
uptime_server = None
uptime_task = None

async def uptime_ping_handler(request):
    """Handle uptime ping requests"""
    return web.Response(text="Bot is alive! 🚀", status=200)

async def start_uptime_server():
    """Start the uptime monitoring HTTP server"""
    global uptime_server
    app = web.Application()
    app.router.add_get('/', uptime_ping_handler)
    app.router.add_get('/ping', uptime_ping_handler)
    app.router.add_get('/health', uptime_ping_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Use a different port for uptime server to avoid conflicts
    uptime_port = int(os.getenv('UPTIME_PORT', 8081))  # Default to 8081 instead of 8080
    site = web.TCPSite(runner, '0.0.0.0', uptime_port)
    await site.start()
    
    logger.info(f"Uptime server started on port {uptime_port}")
    return runner

async def ping_uptime_services():
    """Ping external uptime monitoring services"""
    if not UPTIME_MONITORING_ENABLED or not UPTIME_URLS:
        return
    
    async with aiohttp.ClientSession() as session:
        for url in UPTIME_URLS:
            url = url.strip()
            if url:
                try:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            logger.info(f"Successfully pinged uptime service: {url}")
                        else:
                            logger.warning(f"Uptime service returned status {response.status}: {url}")
                except Exception as e:
                    logger.error(f"Failed to ping uptime service {url}: {e}")

async def uptime_ping_loop():
    """Background task to periodically ping uptime services"""
    while True:
        try:
            await ping_uptime_services()
        except Exception as e:
            logger.error(f"Error in uptime ping loop: {e}")
        
        await asyncio.sleep(UPTIME_PING_INTERVAL)

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
        uid = update.effective_user.id
        session = Session()
        user = session.query(User).filter_by(telegram_id=uid).first()
        
        # Check for referral
        referral_id = None
        if context.args and context.args[0].startswith('ref_'):
            try:
                referral_id = int(context.args[0].split('_')[1])
                if referral_id == uid:  # Prevent self-referral
                    referral_id = None
            except:
                referral_id = None
        
        if not user:
            user = User(
                telegram_id=uid,
                username=update.effective_user.username,
                balance=INITIAL_BALANCE,
                holdings={},
                realized_pnl=0.0,
                history=[],
                context={},
                referral_id=referral_id
            )
            session.add(user)
            session.commit()
            
            # If referred, add bonus to both users
            if referral_id:
                referrer = session.query(User).filter_by(telegram_id=referral_id).first()
                if referrer:
                    # Add bonus to referrer
                    referrer.balance += REFERRAL_BONUS
                    referrer.history = referrer.history or []
                    referrer.history.append(f"🎁 Referral bonus: +${REFERRAL_BONUS}")
                    
                    # Add bonus to new user
                    user.balance += REFERRAL_BONUS
                    user.history = user.history or []
                    user.history.append(f"🎁 Referral bonus: +${REFERRAL_BONUS}")
                    
                    session.commit()
        
        # Initialize in-memory user data
        USERS[uid] = {
            'balance': user.balance,
            'holdings': user.holdings or {},
            'realized_pnl': user.realized_pnl,
            'history': user.history or [],
            'context': user.context or {},
            'referral_id': user.referral_id
        }

        # Generate referral link
        bot_username = (await context.bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start=ref_{uid}"

        keyboard = [
            [InlineKeyboardButton("🟢 Buy", callback_data="menu_buy"),
             InlineKeyboardButton("🔴 Sell", callback_data="menu_sell")],
            [InlineKeyboardButton("💰 Balance", callback_data="menu_balance"),
             InlineKeyboardButton("📈 PnL", callback_data="menu_pnl")],
            [InlineKeyboardButton("🔁 Copy Trade", callback_data="menu_copy_trade"),
             InlineKeyboardButton("🔎 Check Wallet PnL", callback_data="menu_check_wallet_pnl")],
            [InlineKeyboardButton("🚀 Real Trading Bots", callback_data="menu_promotions")],
            [InlineKeyboardButton("👥 Invite Friends", callback_data="menu_referral")]
        ]
        
        welcome_text = (
            "👋 Welcome to the Memecoin Paper Trading Bot!\n\n"
            f"💰 Initial Balance: ${INITIAL_BALANCE}\n"
            f"🎁 Referral Bonus: ${REFERRAL_BONUS}\n\n"
            "Choose an action:"
        )
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def handle_buy_start(query, context):
    """Handle buy menu selection"""
    try:
        uid = query.from_user.id
        USERS[uid]['context'] = {'mode': 'buy'}
        await query.message.reply_text("🔍 Enter the Solana token contract address to buy:")
    except Exception as e:
        logger.error(f"Error in buy start: {e}")
        await query.message.reply_text("❌ An error occurred. Please try again.")

async def handle_sell_start(query, context):
    """Handle sell menu selection"""
    try:
        uid = query.from_user.id
        user = USERS.get(uid)
        tokens = list(user['holdings'].keys())
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
        uid = query.from_user.id
        token = query.data.split(":")[1]
        USERS[uid]['context'] = {'mode': 'sell', 'token': token}
        await query.message.reply_text("💸 Enter the % of token to sell:")
    except Exception as e:
        logger.error(f"Error in token selection: {e}")
        await query.message.reply_text("❌ An error occurred. Please try again.")

async def handle_buy_token(update, context, ca, usd_amount):
    """Handle token purchase"""
    try:
        uid = update.effective_user.id
        user = USERS[uid]
        
        price = await get_token_price(ca)
        if not price:
            await update.message.reply_text("❌ Token price fetch failed.")
            return

        qty = usd_amount / price
        if usd_amount > user['balance']:
            await update.message.reply_text(f"❌ Insufficient balance. You have ${user['balance']:.2f}")
            return

        user['balance'] -= usd_amount

        holding = user['holdings'].get(ca)
        if holding:
            total_cost = holding['qty'] * holding['avg_price'] + usd_amount
            new_qty = holding['qty'] + qty
            holding['avg_price'] = total_cost / new_qty
            holding['qty'] = new_qty
        else:
            user['holdings'][ca] = {'qty': qty, 'avg_price': price}

        user['history'].append(f"🟢 Bought {qty:.4f} of {ca} at ${price:.4f}")
        
        # Update database
        session = Session()
        db_user = session.query(User).filter_by(telegram_id=uid).first()
        db_user.balance = user['balance']
        db_user.holdings = user['holdings']
        db_user.history = user['history']
        session.commit()

        await update.message.reply_text(
            f"✅ Bought {qty:.4f} of {ca} at ${price:.4f}\n"
            f"💵 Remaining Balance: ${user['balance']:.2f}"
        )
    except Exception as e:
        logger.error(f"Error in buy token: {e}")
        await update.message.reply_text("❌ An error occurred during the trade. Please try again.")
        session.rollback()

async def handle_sell_token(update, context, token, percent):
    """Handle token sale"""
    try:
        uid = update.effective_user.id
        user = USERS[uid]
        
        holding = user['holdings'].get(token)
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
        user['balance'] += usd_value
        user['realized_pnl'] += pnl
        holding['qty'] -= qty_to_sell

        if holding['qty'] <= 0.00001:
            del user['holdings'][token]
        
        user['history'].append(f"🔴 Sold {qty_to_sell:.4f} of {token} at ${price:.4f} | PnL: ${pnl:.2f}")
        
        # Update database
        session = Session()
        db_user = session.query(User).filter_by(telegram_id=uid).first()
        db_user.balance = user['balance']
        db_user.holdings = user['holdings']
        db_user.realized_pnl = user['realized_pnl']
        db_user.history = user['history']
        session.commit()

        await update.message.reply_text(
            f"✅ Sold {qty_to_sell:.4f} of {token} at ${price:.4f}\n"
            f"💵 PnL: ${pnl:.2f}\n"
            f"💰 New Balance: ${user['balance']:.2f}"
        )
    except Exception as e:
        logger.error(f"Error in sell token: {e}")
        await update.message.reply_text("❌ An error occurred during the trade. Please try again.")
        session.rollback()

async def show_balance(query, context):
    """Show user's balance"""
    try:
        uid = query.from_user.id
        user = USERS[uid]
        
        msg = (
            f"💵 Cash: ${user['balance']:.2f}\n"
            f"📦 Holdings Value: Click to Check token PnL"
        )
        keyboard = [[InlineKeyboardButton("📈 View Token PnL", callback_data="menu_pnl")]]
        await query.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in show balance: {e}")
        await query.message.reply_text("❌ An error occurred. Please try again.")

async def show_pnl_tokens(query, context):
    """Show list of tokens for PnL check"""
    try:
        uid = query.from_user.id
        user = USERS[uid]
        tokens = list(user['holdings'].keys())
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
        uid = query.from_user.id
        token = query.data.split(":")[1]
        user = USERS[uid]
        holding = user['holdings'].get(token)
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
    await query.message.reply_text(
        f"🚧 {feature} feature is under construction.\n\n"
        "💡 In the meantime, check out our real trading bots:\n\n"
        f"🤖 Trojan on Solana: {TROJAN_BOT_LINK}\n"
        f"🤖 GMGN Sniper Bot: {GMGN_BOT_LINK}"
    )

async def show_promotions(message):
    """Show promotional messages for other bots"""
    promo_text = (
        "🚀 Want to trade real tokens? Check out these amazing bots:\n\n"
        "🤖 Trojan on Solana\n"
        "• Advanced trading features\n"
        "• Real-time price alerts\n"
        "• Fee rebates available\n"
        f"• Start here: {TROJAN_BOT_LINK}\n\n"
        "🤖 GMGN Sniper Bot\n"
        "• Fast token sniping\n"
        "• Multiple backup bots\n"
        "• Fee rebates available\n"
        f"• Start here: {GMGN_BOT_LINK}\n\n"
        "💡 Use these bots to trade real tokens and get fee rebates!"
    )
    await message.reply_text(promo_text)

async def show_referral_info(query, context):
    """Show referral information and link"""
    try:
        uid = query.from_user.id
        
        # Get user from database if not in memory
        session = Session()
        db_user = session.query(User).filter_by(telegram_id=uid).first()
        
        if not db_user:
            await query.message.reply_text("❌ User not found. Please use /start to register.")
            return
        
        # Generate referral link
        bot_username = (await context.bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start=ref_{uid}"
        
        # Count referrals
        referral_count = session.query(User).filter_by(referral_id=uid).count()
        
        msg = (
            "🎁 Referral Program\n\n"
            f"• Get ${REFERRAL_BONUS} for each friend you invite\n"
            f"• Your friends also get ${REFERRAL_BONUS} bonus\n"
            f"• Total referrals: {referral_count}\n\n"
            "Share your referral link:\n"
            f"`{referral_link}`\n\n"
            "💡 Copy and share this link with your friends!"
        )
        
        await query.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in show referral info: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        await query.message.reply_text("❌ An error occurred. Please try again.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users (admin only)"""
    try:
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("🚫 You are not authorized to use this command.")
            return
        
        if not context.args:
            await update.message.reply_text("📝 Usage: /broadcast Your message here\n\n💡 Use 'bros' to include user's name in the message")
            return
        
        # Get the full message text to preserve formatting
        message = update.message.text
        # Remove the "/broadcast " part to get just the message content
        message = message.replace('/broadcast ', '', 1)
        
        session = Session()
        users = session.query(User).all()
        
        if not users:
            await update.message.reply_text("❌ No users found in the database.")
            return

        sent = 0
        failed = 0
        
        # Check if message contains 'bros' placeholder
        has_name_placeholder = 'bros' in message
        
        for user in users:
            try:
                # Get user's Telegram info for name replacement
                user_message = message
                if has_name_placeholder:
                    try:
                        # Get user's Telegram info
                        chat_member = await context.bot.get_chat_member(user.telegram_id, user.telegram_id)
                        user_name = None
                        
                        # Try to get the best available name
                        if chat_member.user.first_name:
                            user_name = chat_member.user.first_name
                            if chat_member.user.last_name:
                                user_name += f" {chat_member.user.last_name}"
                        elif chat_member.user.username:
                            user_name = f"@{chat_member.user.username}"
                        
                        # Replace 'bros' with user's name or empty string if no name
                        user_message = message.replace('bros', user_name or '')
                        
                    except Exception as e:
                        logger.warning(f"Could not get user info for {user.telegram_id}: {e}")
                        # If we can't get user info, just remove the 'bros' placeholder
                        user_message = message.replace('bros', '')
                
                if user.last_broadcast_message_id:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=user.telegram_id,
                            message_id=user.last_broadcast_message_id,
                            text=user_message
                        )
                        sent += 1
                    except Exception as e:
                        new_message = await context.bot.send_message(
                            chat_id=user.telegram_id,
                            text=user_message
                        )
                        user.last_broadcast_message_id = new_message.message_id
                        sent += 1
                else:
                    new_message = await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=user_message
                    )
                    user.last_broadcast_message_id = new_message.message_id
                    sent += 1
            except Exception as e:
                failed += 1
                logger.error(f"Failed to send broadcast to user {user.telegram_id}: {e}")
        
        session.commit()
        status_message = f"✅ Message sent to {sent} users."
        if failed > 0:
            status_message += f"\n❌ Failed to send to {failed} users."
        await update.message.reply_text(status_message)
    except Exception as e:
        logger.error(f"Error in broadcast: {e}")
        await update.message.reply_text("❌ An error occurred during broadcast.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    try:
        uid = update.effective_user.id
        text = update.message.text.strip()
        user = USERS.get(uid)
        
        if not user:
            await start(update, context)
            return

        ctx = user['context']
        if 'mode' in ctx:
            if ctx['mode'] == 'buy':
                if is_solana_address(text):
                    ctx['ca'] = text
                    await update.message.reply_text("💵 How much USD to invest?")
                elif 'ca' in ctx:
                    try:
                        usd = float(text)
                        if usd <= 0:
                            await update.message.reply_text("❌ Please enter a positive amount.")
                            return
                        await handle_buy_token(update, context, ctx['ca'], usd)
                        user['context'] = {}
                    except ValueError:
                        await update.message.reply_text("❌ Please enter a valid number.")
                    except Exception as e:
                        logger.error(f"Error processing buy amount: {e}")
                        await update.message.reply_text("❌ An error occurred. Please try again.")
                return
            elif ctx['mode'] == 'sell' and 'token' in ctx:
                try:
                    percent = float(text)
                    await handle_sell_token(update, context, ctx['token'], percent)
                    user['context'] = {}
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
            ca = data.split(":")[1]
            USERS[query.from_user.id]['context'] = {'mode': 'buy', 'ca': ca}
            await query.message.reply_text("💵 How much USD to invest?")
        elif data.startswith("ca_sell:"):
            token = data.split(":")[1]
            USERS[query.from_user.id]['context'] = {'mode': 'sell', 'token': token}
            await query.message.reply_text("💸 Enter the % of token to sell:")
        elif data == "menu_copy_trade":
            await handle_coming_soon(query, context, "Copy Trade")
        elif data == "menu_check_wallet_pnl":
            await handle_coming_soon(query, context, "Check Wallet PnL")
        elif data == "menu_promotions":
            await show_promotions(query.message)
        elif data == "menu_referral":
            await show_referral_info(query, context)
    except Exception as e:
        logger.error(f"Error in button handler: {e}")
        await update.callback_query.message.reply_text("❌ An error occurred. Please try again.")

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Global variables for cleanup
    global uptime_server, uptime_task
    
    def run_uptime_server():
        """Run uptime server in a separate thread"""
        import asyncio
        import threading
        
        def start_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def server():
                global uptime_server, uptime_task
                
                # Start uptime HTTP server
                logger.info("Starting uptime HTTP server...")
                uptime_server = await start_uptime_server()
                
                # Start background ping task
                if UPTIME_MONITORING_ENABLED:
                    logger.info("Starting uptime monitoring...")
                    uptime_task = asyncio.create_task(uptime_ping_loop())
                    logger.info("Uptime monitoring started")
                
                # Keep the server running
                while True:
                    await asyncio.sleep(1)
            
            try:
                loop.run_until_complete(server())
            except Exception as e:
                logger.error(f"Uptime server error: {e}")
            finally:
                loop.close()
        
        # Start server in thread
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        return server_thread
    
    # Run the services
    logger.info("Starting bot with uptime monitoring...")
    
    try:
        # Start uptime server in background thread
        if UPTIME_MONITORING_ENABLED:
            uptime_thread = run_uptime_server()
            logger.info("Uptime services started in background")
        
        # Start the bot with standard polling
        logger.info("Starting bot polling...")
        application.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        logger.info("Bot shutdown complete")

if __name__ == '__main__':
    main() 