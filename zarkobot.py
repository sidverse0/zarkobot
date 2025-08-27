# -*- coding: utf-8 -*-
import json
import requests
import asyncio
import hashlib
import random
import string
import os
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from pymongo import MongoClient
from bson import ObjectId

# ==== CONFIG ====
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8116705267:AAGVx7azJJMndrXHwzoMnx7angKd0COJWjg")
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', "@zarkoworld")   # Main channel
CHANNEL_USERNAME_2 = os.environ.get('CHANNEL_USERNAME_2', "@chandhackz_78")  # Second channel
OWNER_USERNAME = os.environ.get('OWNER_USERNAME', "@pvt_s1n")    # Your username
ADMIN_ID = int(os.environ.get('ADMIN_ID', 7975903577))  # Your user ID

LEAKOSINT_API_TOKEN = os.environ.get('LEAKOSINT_API_TOKEN', "8176139267:btRibc7y")
API_URL = os.environ.get('API_URL', "https://leakosintapi.com/")

# MongoDB Connection
MONGO_URI = os.environ.get('MONGO_URI', "mongodb+srv://Sidverse0:sidverse18@cluster0.50emoak.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

# Connect to MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client['zarkobot']
    users_collection = db['users']
    audit_collection = db['audit_logs']
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    exit(1)

# ==== Security Functions ====
def generate_user_hash(user_id):
    """Generate a 6-digit alphanumeric hash for user identification"""
    # Create a consistent but unique 6-digit code for each user
    random.seed(user_id)  # Seed with user_id for consistency
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(6))

def log_audit_event(user_id, event_type, details):
    """Log security events for monitoring"""
    timestamp = datetime.now().isoformat()
    user_hash = generate_user_hash(user_id)
    
    log_entry = {
        "timestamp": timestamp,
        "user_id": user_id,
        "user_hash": user_hash,
        "event_type": event_type,
        "details": details
    }
    
    try:
        audit_collection.insert_one(log_entry)
    except Exception as e:
        print(f"Audit log error: {e}")

# ==== User Data Functions ====
def load_users():
    """Get all users from MongoDB"""
    try:
        users = {}
        for user in users_collection.find():
            users[str(user["_id"])] = user
        return users
    except Exception as e:
        print(f"Error loading users: {e}")
        return {}

def save_users(users):
    """Save users to MongoDB"""
    try:
        for user_id, user_data in users.items():
            users_collection.update_one(
                {"_id": user_id},
                {"$set": user_data},
                upsert=True
            )
    except Exception as e:
        print(f"Error saving users: {e}")

def update_user(user_id, credits=None, name=None, last_verified=None):
    uid = str(user_id)
    
    # Get existing user or create new
    user_data = users_collection.find_one({"_id": uid})
    
    if not user_data:
        user_data = {
            "_id": uid,
            "credits": 0,
            "name": name or "Unknown", 
            "last_update": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
            "initial_credits_given": False,
            "join_date": datetime.now().strftime("%Y-%m-%d"),
            "user_hash": generate_user_hash(user_id),
            "verification_history": [],
            "last_verified": None
        }
        users_collection.insert_one(user_data)
    else:
        # Update fields if provided
        update_data = {}
        if credits is not None:
            update_data["credits"] = credits
        if name is not None:
            update_data["name"] = name
        if last_verified is not None:
            update_data["last_verified"] = last_verified
            
        update_data["last_update"] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        
        if update_data:
            users_collection.update_one(
                {"_id": uid},
                {"$set": update_data}
            )
            user_data.update(update_data)
    
    # Log the update
    log_audit_event(user_id, "USER_UPDATE", f"Credits: {user_data.get('credits', 0)}, Name: {user_data.get('name', 'Unknown')}")
    
    return user_data

def add_verification_record(user_id, success, details):
    """Add a verification attempt to user's history"""
    uid = str(user_id)
    
    user_data = users_collection.find_one({"_id": uid})
    if not user_data:
        return False
    
    record = {
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "details": details
    }
    
    # Update verification history
    users_collection.update_one(
        {"_id": uid},
        {
            "$push": {
                "verification_history": {
                    "$each": [record],
                    "$slice": -10  # Keep only last 10 records
                }
            }
        }
    )
    
    return True

# ==== Check Channel Membership ====
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    try:
        # Check first channel
        member1 = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        # Check second channel
        member2 = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME_2, user_id=user_id)
        
        is_member = member1.status != "left" and member2.status != "left"
        
        # Log membership check
        log_audit_event(user_id, "MEMBERSHIP_CHECK", 
                       f"Channel1: {member1.status}, Channel2: {member2.status}, Result: {is_member}")
        
        return is_member
    except Exception as e:
        error_msg = f"Error checking membership: {e}"
        print(error_msg)
        log_audit_event(user_id, "MEMBERSHIP_ERROR", error_msg)
        return False

# ==== API Query ====
def query_leakosint(query: str):
    payload = {
        "token": LEAKOSINT_API_TOKEN,
        "request": query,
        "limit": 500,
        "lang": "en"
    }
    try:
        resp = requests.post(API_URL, json=payload, timeout=30)
        return resp.json()
    except Exception as e:
        return {"Error": str(e)}

# ==== Format Result ====
def format_results(resp):
    if "Error" in resp or "Error code" in resp:
        err = resp.get("Error") or resp.get("Error code")
        return f"⚠️ Server Is Offline Or Maintenance"
    
    if not resp.get("List"):
        return "❌ No Data Found In Database"

    msg = ""
    for db, data in resp.get("List", {}).items():
        for row in data.get("Data", []):
            name = row.get("FatherName", "N/A")
            father = row.get("FullName", "N/A")
            mobile = row.get("Phone", "N/A")
            alt1 = row.get("Phone2", "N/A")
            alt2 = row.get("Phone3", "N/A")
            alt3 = row.get("Phone4", "N/A")
            alt4 = row.get("Phone5", "N/A")
            alt5 = row.get("Phone6", "N/A")
            doc = row.get("DocNumber", "N/A")
            region = row.get("Region", "N/A")
            address = row.get("Address", "N/A")

            msg += f"""
👤 Name ➤ {name}
📛 Father's Name ➤ {father}
📱 Mobile ➤ {mobile}
📞 Alt Number1 ➤ {alt1}
📞 Alt Number2 ➤ {alt2}
📞 Alt Number3 ➤ {alt3}
📞 Alt Number4 ➤ {alt4}
📞 Alt Number5 ➤ {alt5}
🎫 Aadhaar 🎫 ➤ {doc}
📍 City ➤ {region}
🏠 Address ➤ {address}
────────────────────
"""
    return msg or "❌ No Data Found In Database"

# ==== Show Profile Function ====
async def show_profile(update, context, user_id=None, user_data=None, edit_message=False):
    if not user_id:
        user_id = update.effective_user.id
        
    if not user_data:
        user_data = users_collection.find_one({"_id": str(user_id)})
        if not user_data:
            user_data = {"credits": 0, "last_update": "N/A", "name": "Unknown"}
    
    name = user_data.get("name", "Unknown")
    credits = user_data.get("credits", 0)
    last_update = user_data.get("last_update", "N/A")
    join_date = user_data.get("join_date", "N/A")
    user_hash = user_data.get("user_hash", generate_user_hash(user_id))
    
    # Create profile message
    profile_msg = f"""
👤 Name ➤ {name} 
•••••••••••••••••••••••••
🗃 User ID ➤ {user_id}
•••••••••••••••••••••••••
🗃 User Hash ➤ {user_hash}
•••••••••••••••••••••••••
💰 Credits ➤ {credits} 💸
•••••••••••••••••••••••••
📅 Join Date ➤ {join_date}
•••••••••••••••••••••••••
🔄 Last Updated ➤ {last_update}
•••••••••••••••••••••••••
"""
    # Create buttons
    keyboard = [
        [InlineKeyboardButton("❓ Help", callback_data="help"),
         InlineKeyboardButton("🔍 Search", callback_data="search_prompt")],
        [InlineKeyboardButton("💳 Buy Credits", callback_data="buy")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if edit_message and hasattr(update, 'callback_query'):
        await update.callback_query.edit_message_text(profile_msg, reply_markup=reply_markup)
    elif hasattr(update, 'message'):
        await update.message.reply_text(profile_msg, reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text(profile_msg, reply_markup=reply_markup)

# ==== Buy Command Function ====
async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check membership first
    is_member = await check_membership(update, context, user_id)
    if not is_member:
        keyboard = [
            [InlineKeyboardButton("📢 Channel 1", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 Channel 2", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("✅ Verify", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("⚠️ You must join both channels and verify to use this bot.", reply_markup=reply_markup)
        return
        
    buy_message = """
════[💎 ZarkoWorld Credits 💎]══════

💸 Credits Plans
────────────────────

1️⃣ Starter Pack 🎒 
➡️ 10 Credits → ₹25 
🎁Bonus: +2 Free Credits 
💳Buy now and get started
────────────────────

2️⃣ Value Pack 🎰 
➡️ 25 Credits → ₹50 
🎁Bonus: +5 Free Credits 
💎Perfect for regular users
────────────────────

3️⃣ Super Saver Pack 🏆 
➡️ 50 Credits → ₹90 
🎁Bonus: +15 Free Credits 
💪More searches, more results
────────────────────

4️⃣ Pro Pack 🚀 
➡️ 75 Credits → ₹120 
🎁Bonus: +25 Free Credits 
🔥Best for power users
────────────────────

5️⃣ Mega Pack 🎯 
➡️ 100 Credits → ₹150 
🎁Bonus: +40 Free Credits 
⚡Maximum value & savings
────────────────────

📢 Any Plans
────────────────────

🎯 Buy Any — 1 Month — ₹399/-
📈Buy Any — Lifetime — ₹1999/-
ℹ️Contact Owner for any queries: @pvt_s1n
"""

    keyboard = [
        [InlineKeyboardButton("💬 Contact Owner", url=f"https://t.me/{OWNER_USERNAME[1:]}")],
        [InlineKeyboardButton("🔙 Back", callback_data="profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(buy_message, reply_markup=reply_markup)

# ==== Fast Animated Spinner ====
async def show_spinner(update, context, message):
    spinner_frames = [
        "💎 ••••••••••••••••••••••••• Doing ",
        "💎 ••••••••••••••••••••••••• Doing ",
        "💎 ••••••••••••••••••••••••• Doing "
    ]
    
    msg = await message.reply_text(spinner_frames[0])
    
    for frame in spinner_frames:
        await asyncio.sleep(0.5)
        try:
            await msg.edit_text(frame)
        except:
            break
    
    return msg

# ==== ADMIN FUNCTIONS ====
async def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id == ADMIN_ID

async def addcredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add credits to a user"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Access Denied.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /addcredits <user_id> <amount>")
        return

    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID or amount")
        return

    user_data = users_collection.find_one({"_id": str(target_user_id)})
    
    if not user_data:
        await update.message.reply_text("❌ User not found")
        return

    new_credits = user_data.get("credits", 0) + amount
    users_collection.update_one(
        {"_id": str(target_user_id)},
        {"$set": {"credits": new_credits}}
    )
    
    log_audit_event(user_id, "ADMIN_ADD_CREDITS", 
                   f"Target: {target_user_id}, Amount: {amount}, New Balance: {new_credits}")
    
    await update.message.reply_text(f"✅ Added {amount} credits to user {target_user_id}\nNew Balance: {new_credits} 💸")

async def setcredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user's credits to specific amount"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Access Denied.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /setcredits <user_id> <amount>")
        return

    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID or amount")
        return

    user_data = users_collection.find_one({"_id": str(target_user_id)})
    
    if not user_data:
        await update.message.reply_text("❌ User not found")
        return

    users_collection.update_one(
        {"_id": str(target_user_id)},
        {"$set": {"credits": amount}}
    )
    
    log_audit_event(user_id, "ADMIN_SET_CREDITS", 
                   f"Target: {target_user_id}, New Amount: {amount}")
    
    await update.message.reply_text(f"✅ Set credits for user {target_user_id} to {amount} 💸")

async def userinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user information"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Access Denied.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: /userinfo <user_id>")
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID")
        return

    user_data = users_collection.find_one({"_id": str(target_user_id)})
    
    if not user_data:
        await update.message.reply_text("❌ User not found")
        return

    info_msg = f"""
════[📊 User Info ]════

👤 Name: {user_data.get('name', 'N/A')}
🗃 User ID: {target_user_id}
🗃 User Hash: {user_data.get('user_hash', 'N/A')}
💸 Credits: {user_data.get('credits', 0)}
📅 Join Date: {user_data.get('join_date', 'N/A')}
🔄 Last Updated: {user_data.get('last_update', 'N/A')}
✅ Last Verified: {user_data.get('last_verified', 'N/A')}

📊 Verification History:
"""
    
    for i, record in enumerate(user_data.get('verification_history', [])[-5:]):
        status = "✅" if record.get('success') else "❌"
        info_msg += f"{i+1}. {status} {record.get('timestamp')} - {record.get('details')}\n"

    log_audit_event(user_id, "ADMIN_USERINFO", 
                   f"Viewed info for user: {target_user_id}")
    
    await update.message.reply_text(info_msg)

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Access Denied.")
        return

    if not context.args:
        await update.message.reply_text("❌ Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    users = list(users_collection.find({}))
    success_count = 0
    fail_count = 0

    broadcast_msg = f"""
════[📢 Broadcast ]════

{message}

────────────────────
➡️ 💎 ZarkoWorld Credits
"""
    
    for user in users:
        try:
            await context.bot.send_message(chat_id=int(user["_id"]), text=broadcast_msg)
            success_count += 1
        except Exception as e:
            print(f"Failed to send to {user['_id']}: {e}")
            fail_count += 1
        await asyncio.sleep(0.1)  # Prevent flooding

    log_audit_event(user_id, "ADMIN_BROADCAST", 
                   f"Message: {message}, Success: {success_count}, Failed: {fail_count}")
    
    await update.message.reply_text(f"✅ Broadcast completed!\nSuccess: {success_count}\nFailed: {fail_count}")

# ==== Handlers ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    
    # Log the start command
    log_audit_event(user_id, "START_COMMAND", f"User: {name}")
    
    # Check if user is already in database
    user_data = users_collection.find_one({"_id": str(user_id)})
    
    # Always check current membership status
    is_member = await check_membership(update, context, user_id)
    
    if is_member:
        # User is a member of channels
        if not user_data:
            # New user - add to database with initial credits
            user_data = update_user(user_id, credits=2, name=name, 
                                  last_verified=datetime.now().isoformat())
            add_verification_record(user_id, True, "New user - initial credits granted")
            
            await update.message.reply_text(
                "✅ Verification Successful! 🎉🎊\n\n"
                "➡️ You've Received  💸 2 Free Credits\n\n"
                "🚀 Enjoy Your Journey With ════[💎 ZarkoWorld Credits 💎]══════"
            )
        else:
            # Existing user - just update name if needed
            user_data = update_user(user_id, name=name)
            add_verification_record(user_id, True, "Existing user - membership verified")
        
        await show_profile(update, context, user_id, user_data)
    else:
        # User hasn't joined both channels, show join buttons
        keyboard = [
            [InlineKeyboardButton("📢 Channel 1", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 Channel 2", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("✅ Verify", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        add_verification_record(user_id, False, "User not member of required channels")
        
        await update.message.reply_text(
            "════[💎 ZarkoWorld Credits 💎]══════\n\n"
            "🔔 To Use This Bot You Must:\n\n"
            "🔹 Join Both Official Channels\n"
            "🔹 Click The Verify Button\n\n"
            "🎁Reward: After Verification  You Will  Instantly Receive\n"
            "💸 2 Free Credits\n\n"
            "────────────────────\n"
            "💳 Buy Unlimited Credits & Any📱Contact 👨 @pvt_s1n",
            reply_markup=reply_markup
        )

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    
    # Check if user has joined both channels
    is_member = await check_membership(update, context, user_id)
    
    user_data = users_collection.find_one({"_id": str(user_id)})
    
    if is_member:
        if not user_data:
            # New user - add to database with initial credits
            user_data = update_user(user_id, credits=2, name=name, 
                                  last_verified=datetime.now().isoformat())
            add_verification_record(user_id, True, "New user - initial credits granted via verify")
            
            # Show success message and immediately show profile
            await query.edit_message_text(
                "✅ Verification Successful! 🎉🎊\n\n"
                "➡️ You've Received  💸 2 Free Credits\n\n"
                "🚀 Enjoy Your Journey With ════[💎 ZarkoWorld Credits 💎]══════"
            )
            await show_profile(update, context, user_id, user_data)
        else:
            # Existing user - update verification status but don't give credits again
            user_data = update_user(user_id, name=name, 
                                  last_verified=datetime.now().isoformat())
            add_verification_record(user_id, True, "Existing user - reverified")
            
            await query.edit_message_text(
                "✅ You Are Already A Member And Have Already Received Your Initial Credits.\n\n"
                "🚀 Enjoy Your Journey With ════[💎 ZarkoWorld Credits 💎]══════"
            )
            await show_profile(update, context, user_id, user_data)
    else:
        # User hasn't joined both channels
        add_verification_record(user_id, False, "Verification failed - not member of channels")
        
        keyboard = [
            [InlineKeyboardButton("📢 Channel 1", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 Channel 2", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("🔄 Retry", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "────⚠️ Warning ⚠️────\n\n"
            "❌ You Haven't Joined Both Channels Yet!\n\n"
            "📢 Please Join Both Channels First 📢\n"
            "🔒 Then Click Verify Button 🔒\n\n"
            "────────────────────",
            reply_markup=reply_markup
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "help":
        help_text = """════[💎 ZarkoWorld Credits 💎]════

🔍 *How To Use ZarkoWorld Credits:*

🔹 📱 *Phone Number Search* – Send No. Like  `91XXXXXXXXXX`
🔹 📧 *Email Search* – Send Email Like  `example@gmail.com`
🔹 👤 *Name Search* – Just Send The Name
⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️
📋 I Will Scan All Available Multiple Databases 🔍🔎
────────────────────
⚠️ *Note:* Each Search Costs 💸 1 Credit
"""
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(help_text, parse_mode="Markdown", reply_markup=reply_markup)
        
    elif query.data == "search_prompt":
        search_prompt_text = """════[💎 ZarkoWorld Credits 💎]════

🔍 *What Can I Do?*

🔹 📱 *Phone Number Search* – Send No. Like  `91XXXXXXXXXX`
⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️
🔹 📧 *Email Search* – Send Email Like  `example@gmail.com`
⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️
🔹 👤 *Name Search* – Just Send The Name
⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️
📋 I Will Scan All Available Multiple Databases 🔍🔎
────────────────────
⚠️ *Note:* Each Search Costs 💸 1 Credit
"""
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(search_prompt_text, parse_mode="Markdown", reply_markup=reply_markup)
        
    elif query.data == "buy":
        buy_message = """
════[💎 ZarkoWorld Credits 💎]══════

💸 Credits Plans
────────────────────

1️⃣ Starter Pack 🎒 
➡️ 10 Credits → ₹25 
🎁Bonus: +2 Free Credits 
💳Buy now and get started
────────────────────

2️⃣ Value Pack 🎰 
➡️ 25 Credits → ₹50 
🎁Bonus: +5 Free Credits 
💎Perfect for regular users
────────────────────

3️⃣ Super Saver Pack 🏆 
➡️ 50 Credits → ₹90 
🎁Bonus: +15 Free Credits 
💪More searches, more results
────────────────────

4️⃣ Pro Pack 🚀 
➡️ 75 Credits → ₹120 
🎁Bonus: +25 Free Credits 
🔥Best for power users
────────────────────

5️⃣ Mega Pack 🎯 
➡️ 100 Credits → ₹150 
🎁Bonus: +40 Free Credits 
⚡Maximum value & savings
────────────────────

📢 Any Plans
────────────────────

🎯 Buy Any — 1 Month — ₹399/-
📈Buy Any — Lifetime — ₹1999/-
ℹ️Contact Owner for any queries: @pvt_s1n
"""

        keyboard = [
            [InlineKeyboardButton("?? Contact Owner", url=f"https://t.me/{OWNER_USERNAME[1:]}")],
            [InlineKeyboardButton("🔙 Back", callback_data="profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(buy_message, reply_markup=reply_markup)
        
    elif query.data == "profile":
        user_id = update.effective_user.id
        user_data = users_collection.find_one({"_id": str(user_id)})
        if not user_data:
            user_data = {"credits": 0, "last_update": "N/A", "name": "Unknown"}
        await show_profile(update, context, user_id, user_data, edit_message=True)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Check membership first
    is_member = await check_membership(update, context, user_id)
    if not is_member:
        keyboard = [
            [InlineKeyboardButton("📢 Channel 1", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 Channel 2", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("✅ Verify", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("⚠️ You must join both channels and verify to use this bot.", reply_markup=reply_markup)
        return

    user_data = users_collection.find_one({"_id": str(user_id)})
    
    if not user_data:
        # New user - add to database with initial credits
        name = update.effective_user.first_name
        user_data = update_user(user_id, credits=2, name=name, last_verified=datetime.now().isoformat())
        add_verification_record(user_id, True, "New user - initial credits granted via search")

    if user_data.get("credits", 0) <= 0:
        keyboard = [[InlineKeyboardButton("💳 Buy Credits", callback_data="buy")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"❌ No Credits Left!\n\n💳Buy Unlimited 💸Credits & Any📱Contact 👨 {OWNER_USERNAME}", reply_markup=reply_markup)
        return

    # Show animated spinner
    spinner_msg = await show_spinner(update, context, update.message)

    query = update.message.text
    result = query_leakosint(query)
    msg = format_results(result)

    # Deduct 1 credit only if search was successful
    if "No Data Found" not in msg and "Server Is Offline" not in msg:
        new_credits = user_data.get("credits", 0) - 1
        users_collection.update_one(
            {"_id": str(user_id)},
            {"$set": {"credits": new_credits, "last_update": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")}}
        )
        
        # Log the search
        log_audit_event(user_id, "SEARCH", f"Query: {query}, Success: True, Credits left: {new_credits}")
    else:
        # Log failed search
        log_audit_event(user_id, "SEARCH", f"Query: {query}, Success: False, Credits left: {user_data.get('credits', 0)}")

    # Delete spinner message
    await spinner_msg.delete()

    # Add credits info and deposit button
    user_data = users_collection.find_one({"_id": str(user_id)})
    credits_left = user_data.get("credits", 0) if user_data else 0
    msg += f"\n💰 Credits : {credits_left} 💸"
    
    keyboard = [[InlineKeyboardButton("💳 Buy Credits", callback_data="buy")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(msg, reply_markup=reply_markup)

async def credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check membership first
    is_member = await check_membership(update, context, user_id)
    if not is_member:
        keyboard = [
            [InlineKeyboardButton("📢 Channel 1", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 Channel 2", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("✅ Verify", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("⚠️ You must join both channels and verify to use this bot.", reply_markup=reply_markup)
        return
        
    user_data = users_collection.find_one({"_id": str(user_id)})
    c = user_data.get("credits", 0) if user_data else 0
    await update.message.reply_text(f"💰 Your Credits: {c} 💸")

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check membership first
    is_member = await check_membership(update, context, user_id)
    if not is_member:
        keyboard = [
            [InlineKeyboardButton("📢 Channel 1", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 Channel 2", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("✅ Verify", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("⚠️ You must join both channels and verify to use this bot.", reply_markup=reply_markup)
        return
        
    user_data = users_collection.find_one({"_id": str(user_id)})
    if not user_data:
        user_data = {"credits": 0, "last_update": "N/A", "name": "Unknown"}
    await show_profile(update, context, user_id, user_data)

# ==== ADMIN COMMANDS ====
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Simple admin check - you might want to implement a more robust system
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Access Denied.")
        return
    
    # Get statistics
    total_users = users_collection.count_documents({})
    total_credits = sum(user.get("credits", 0) for user in users_collection.find({}))
    
    # Get recent activity
    recent_logs = list(audit_collection.find().sort("timestamp", -1).limit(5))
    
    stats_msg = f"""
════[📊 Admin Stats ]════

👥 Total Users: {total_users}
💰 Total Credits: {total_credits}

📊 Recent Activity:
"""
    
    for log in recent_logs:
        timestamp = log.get("timestamp", "N/A")
        event_type = log.get("event_type", "N/A")
        user_hash = log.get("user_hash", "N/A")
        stats_msg += f"• {timestamp} - {user_hash} - {event_type}\n"
    
    await update.message.reply_text(stats_msg)

# ==== MAIN FUNCTION ====
def main():
    # Create the Application
    app = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("credits", credits))
    app.add_handler(CommandHandler("me", me))
    app.add_handler(CommandHandler("buy", buy_command))
    
    # Admin commands
    app.add_handler(CommandHandler("adminstats", admin_stats))
    app.add_handler(CommandHandler("addcredits", addcredits_command))
    app.add_handler(CommandHandler("setcredits", setcredits_command))
    app.add_handler(CommandHandler("userinfo", userinfo_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify$"))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()