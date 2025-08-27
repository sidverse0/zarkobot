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
        return f"⚠️ Sᴇʀᴠᴇʀ Iꜱ Oɴ Mᴀɪɴᴛᴀɪɴᴇɴᴄᴇ"

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
👤 Nᴀᴍᴇ ➤ {name}
🧓 Fᴀᴛʜᴇʀ'ꜱ Nᴀᴍᴇ ➤ {father}
📱 Mᴏʙɪʟᴇ ➤ {mobile}
📞 Aʟᴛ Nᴜᴍʙᴇʀ1 ➤ {alt1}
📞 Aʟᴛ Nᴜᴍʙᴇʀ2 ➤ {alt2}
📞 Aʟᴛ Nᴜᴍʙᴇʀ3 ➤ {alt3}
📞 Aʟᴛ Nᴜᴍʙᴇʀ4 ➤ {alt4}
📞 Aʟᴛ Nᴜᴍʙᴇʀ5 ➤ {alt5}
🆔 Aᴀᴅʜᴀʀ 𝙸𝙳 ➤ {doc}
📶 Cɪʀᴄʟᴇ ➤ {region}
🏠 Aᴅᴅʀᴇꜱꜱ ➤ {address}
────────────────────
"""
    return msg or "❌ Nᴏ Dᴀᴛᴀ Aᴠᴀɪʟᴀʙʟᴇ Iɴ Dᴀᴛᴀʙᴀꜱᴇ"

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
👤 Nᴀᴍᴇ ▶ {name} 
••••••••••••••••••••••••••
🆔 Usᴇʀ ɪᴅ ▶ {user_id}
••••••••••••••••••••••••••
🆔 Usᴇʀ ʜᴀsʜ ▶ {user_hash}
••••••••••••••••••••••••••
💵 Cʀᴇᴅɪᴛ ▶ {credits} 💎
••••••••••••••••••••••••••
📅 Jᴏɪɴᴇᴅ ᴏɴ ▶ {join_date}
••••••••••••••••••••••••••
⌚️ Lᴀsᴛ Uᴘᴅᴀᴛᴇᴅ ▶ {last_update}
••••••••••••••••••••••••••
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
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("🔐 ＶＥＲＩＦＹ", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("⚠️ Yᴏᴜ ᴍᴜꜱᴛ ᴊᴏɪɴ ᴀʟʟ ᴄʜᴀɴɴᴇʟꜱ ᴀɴᴅ ᴠᴇʀɪғʏ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ.", reply_markup=reply_markup)
        return
        
    buy_message = """
╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]      

💎 Cʀᴇᴅɪᴛ Pʟᴀɴꜱ
━━━━━━━━━━━━━━━━━━━━━

1️⃣ Sᴛᴀʀᴛᴇʀ Pᴀᴄᴋ 🎯 
✨10 Cʀᴇᴅɪᴛꜱ → ₹25 
🎁Bᴏɴᴜꜱ: +2 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ 
💡Bᴇꜱᴛ ꜰᴏʀ ᴛᴇꜱᴛɪɴɢ ᴛʜᴇ ᴀᴘᴘ
━━━━━━━━━━━━━━━━━━━━━

2️⃣ Vᴀʟᴜᴇ Pᴀᴄᴋ 📦 
✨25 Cʀᴇᴅɪᴛꜱ → ₹50 
🎁Bᴏɴᴜꜱ: +5 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ 
💡Pᴏᴘᴜʟᴀʀ ᴄʜᴏɪᴄᴇ ꜰᴏʀ ɴᴇᴡ ᴜꜱᴇʀꜱ
━━━━━━━━━━━━━━━━━━━━━

3️⃣ Sᴍᴀʀᴛ Sᴀᴠᴇʀ Pᴀᴄᴋ 🪙 
✨50 Cʀᴇᴅɪᴛꜱ → ₹90 
🎁Bᴏɴᴜꜱ: +15 Fʀᴇᴅɪᴛꜱ 
💡Mᴏʀᴇ ᴘʜᴀᴛɪᴍᴇ, ᴍᴏʀᴇ ʀᴇᴡᴀʀᴅꜱ
━━━━━━━━━━━━━━━━━━━━━

4️⃣ Pʀᴏ Pᴀᴄᴋ 🚀 
✨75 Cʀᴇᴅɪᴛꜱ → ₹120 
🎁Bᴏɴᴜꜱ: +25 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ 
💡Bᴇꜱᴛ ꜰᴏʀ ʀᴇɢᴜʟᴀʀ ᴜꜱᴇʀꜱ
━━━━━━━━━━━━━━━━━━━━━

5️⃣ Mᴇɢᴀ Pᴀᴄᴋ 👑 
✨100 Cʀᴇᴅɪᴛꜱ → ₹150 
🎁Bᴏɴᴜꜱ: +40 Fʀᴇᴅɪᴛꜱ 
💡Mᴀxɪᴍᴜᴍ ᴠᴀʟᴜᴇ & ꜱᴀᴠɪɴɢꜱ
━━━━━━━━━━━━━━━━━━━━━

🔌 Aᴘɪ Pᴜʀᴄʜᴀꜱᴇ
━━━━━━━━━━━━━━━━━━━━━

🕒 Bᴜʏ Aᴘɪ — 1 Mᴏɴᴛʜ — ₹399/-
🔒Bᴜʏ Aᴘɪ — Lɪꜰᴇᴛɪᴍᴇ — ₹1999/-
ℹ️Cᴏɴᴛᴀᴄᴛ Oᴡɴᴇʀ ꜰᴏʀ ᴍᴏʀᴇ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ: @pvt_s1n
"""

    keyboard = [
        [InlineKeyboardButton("💬 Cᴏɴᴛᴀᴄᴛ Oᴡɴᴇʀ", url=f"https://t.me/{OWNER_USERNAME[1:]}")],
        [InlineKeyboardButton("🔙 Bᴀᴄᴋ", callback_data="profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(buy_message, reply_markup=reply_markup)

# ==== Fast Animated Spinner ====
async def show_spinner(update, context, message):
    spinner_frames = [
        "𓆗 •••••••••••••••••••••••••• Dᴏɴᴇ "
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
        await update.message.reply_text("❌ Aᴄᴄᴇꜱꜱ Dᴇɴɪᴇᴅ.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("❌ Uꜱᴀɢᴇ: /addcredits <user_id> <amount>")
        return

    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Iɴᴠᴀʟɪᴅ ᴜꜱᴇʀ ID ᴏʀ ᴀᴍᴏᴜɴᴛ")
        return

    user_data = users_collection.find_one({"_id": str(target_user_id)})
    
    if not user_data:
        await update.message.reply_text("❌ Uꜱᴇʀ ɴᴏᴛ ꜰᴏᴜɴᴅ")
        return

    new_credits = user_data.get("credits", 0) + amount
    users_collection.update_one(
        {"_id": str(target_user_id)},
        {"$set": {"credits": new_credits}}
    )
    
    log_audit_event(user_id, "ADMIN_ADD_CREDITS", 
                   f"Target: {target_user_id}, Amount: {amount}, New Balance: {new_credits}")
    
    await update.message.reply_text(f"✅ Aᴅᴅᴇᴅ {amount} ᴄʀᴇᴅɪᴛꜱ ᴛᴏ ᴜꜱᴇʀ {target_user_id}\nNᴇᴡ ʙᴀʟᴀɴᴄᴇ: {new_credits} 💎")

async def setcredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user's credits to specific amount"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Aᴄᴄᴇꜱꜱ Dᴇɴɪᴇᴅ.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("❌ Uꜱᴀɢᴇ: /setcredits <user_id> <amount>")
        return

    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Iɴᴠᴀʟɪᴅ ᴜꜱᴇʀ ID ᴏʀ ᴀᴍᴏᴜɴᴛ")
        return

    user_data = users_collection.find_one({"_id": str(target_user_id)})
    
    if not user_data:
        await update.message.reply_text("❌ Uꜱᴇʀ ɴᴏᴛ ꜰᴏᴜɴᴅ")
        return

    users_collection.update_one(
        {"_id": str(target_user_id)},
        {"$set": {"credits": amount}}
    )
    
    log_audit_event(user_id, "ADMIN_SET_CREDITS", 
                   f"Target: {target_user_id}, New Amount: {amount}")
    
    await update.message.reply_text(f"✅ Sᴇᴛ ᴄʀᴇᴅɪᴛꜱ ᴏꜰ ᴜꜱᴇʀ {target_user_id} ᴛᴏ {amount} 💎")

async def userinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user information"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Aᴄᴄᴇꜱꜱ Dᴇɴɪᴇᴅ.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("❌ Uꜱᴀɢᴇ: /userinfo <user_id>")
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Iɴᴠᴀʟɪᴅ ᴜꜱᴇʀ ID")
        return

    user_data = users_collection.find_one({"_id": str(target_user_id)})
    
    if not user_data:
        await update.message.reply_text("❌ Uꜱᴇʀ ɴᴏᴛ ꜰᴏᴜɴᴅ")
        return

    info_msg = f"""
╏╠══[𝍖𝍖𝍖 ＵＳＥＲ ＩＮＦＯ 𝍖𝍖𝍖]    

👤 Nᴀᴍᴇ: {user_data.get('name', 'N/A')}
🆔 Usᴇʀ ID: {target_user_id}
🆔 Usᴇʀ Hᴀsʜ: {user_data.get('user_hash', 'N/A')}
💎 Cʀᴇᴅɪᴇᴛꜱ: {user_data.get('credits', 0)}
📅 Jᴏɪɴ Dᴀᴛᴇ: {user_data.get('join_date', 'N/A')}
⌚️ Lᴀsᴛ Uᴘᴅᴀᴛᴇ: {user_data.get('last_update', 'N/A')}
✅ Lᴀsᴛ Vᴇʀɪꜰɪᴇᴅ: {user_data.get('last_verified', 'N/A')}

📊 Vᴇʀɪꜰɪᴄᴀᴛɪᴏɴ Hɪꜱᴛᴏʀʏ:
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
        await update.message.reply_text("❌ Aᴄᴄᴇꜱꜱ Dᴇɴɪᴇᴅ.")
        return

    if not context.args:
        await update.message.reply_text("❌ Uꜱᴀɢᴇ: /broadcast <message>")
        return

    message = " ".join(context.args)
    users = list(users_collection.find({}))
    success_count = 0
    fail_count = 0

    broadcast_msg = f"""
╏╠══[𝍖𝍖𝍖 ＢＲＯＡＤＣＡＳＴ 𝍖𝍖𝍖]    

{message}

━━━━━━━━━━━━━━━━━━━━━
✨ Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ
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
    
    await update.message.reply_text(f"✅ Bʀᴏᴀᴅᴄᴀꜱᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ!\nSᴜᴄᴄᴇꜱꜱ: {success_count}\nFᴀɪʟᴇᴅ: {fail_count}")

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
                "🍑 Vᴇʀɪꜰɪᴄᴀᴛɪᴏɴ Sᴜᴄᴄᴇꜱꜱꜰᴜʟ! 🎉🎊\n\n"
                "✨ Yᴏᴜ'ᴠᴇ Rᴇᴄᴇɪᴠᴇᴅ  💎 2 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ\n\n"
                "🚀 Eɴᴊᴏʏ Yᴏᴜʀ Jᴏᴜʀɴᴇʏ Wɪᴛʜ ╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]      "
            )
        else:
            # Existing user - just update name if needed
            user_data = update_user(user_id, name=name)
            add_verification_record(user_id, True, "Existing user - membership verified")
        
        await show_profile(update, context, user_id, user_data)
    else:
        # User hasn't joined both channels, show join buttons
        keyboard = [
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("🔐 ＶＥＲＩＦＹ", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        add_verification_record(user_id, False, "User not member of required channels")
        
        await update.message.reply_text(
            "╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]      \n\n"
            "✮ 🤖 Tᴏ Uꜱᴇ Tʜɪꜱ Bᴏᴛ Yᴏᴜ Mᴜꜱᴛ:\n\n"
            "✮ 🔗 Jᴏɪɴ Bᴏᴛʜ Oꜰꜰɪᴄɪᴀʟ Cʜᴀɴɴᴇʟ Aʙᴏᴠᴇ\n"
            "✮ 🔐 Cʟɪᴄᴋ Tʜᴇ Vᴇʀɪꜰʏ Bᴜᴛᴛᴏɴ\n\n"
            "✮🎁 Rᴇᴡᴀʀᴅ: Aꜰᴛᴇʀ Vᴇʀɪꜰɪᴄᴀᴛɪᴏɴ  Yᴏᴜ Wɪʟʟ  Iɴꜱᴛᴀɴᴛʟʏ Rᴇᴄᴇɪᴠᴇ\n"
            "✮💎 2 Fʀᴇᴅɪᴛꜱ\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🌀 Bᴜʏ Uɴʟɪᴍɪᴛᴇᴅ Cʀᴇᴅɪᴛꜱ & Aᴘɪ⚡Cᴏɴᴛᴀᴄᴛ 👉 @pvt_s1n",
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
                "🍑 Vᴇʀɪꜰɪᴄᴀᴛɪᴏɴ Sᴜᴄᴄᴇꜱꜱꜱꜰᴜʟ! 🎉🎊\n\n"
                "✨ Yᴏᴜ'ᴠᴇ Rᴇᴄᴇɪᴠᴇᴅ  💎 2 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ\n\n"
                "🚀 Eɴᴊᴏʏ Yᴏᴜʀ Jᴏᴜʀɴᴇʏ Wɪᴛʜ ╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]      "
            )
            await show_profile(update, context, user_id, user_data)
        else:
            # Existing user - update verification status but don't give credits again
            user_data = update_user(user_id, name=name, 
                                  last_verified=datetime.now().isoformat())
            add_verification_record(user_id, True, "Existing user - reverified")
            
            await query.edit_message_text(
                "✅ Yᴏᴜ Aʀᴇ Aʟʀᴇᴀᴅʏ ᴀ Mᴇᴍʙᴇʀ Aɴᴅ Hᴀᴠᴇ Aʟʀᴇᴀᴅʏ Rᴇᴄᴇɪᴠᴇᴅ Yᴏᴜʀ Iɴɪᴛɪᴀʟ Cʀᴇᴅɪᴛs.\n\n"
                "🚀 Eɴᴊᴏʏ Yᴏᴜʀ Jᴏᴜʀɴᴇʏ Wɪᴛʜ ╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]      "
            )
            await show_profile(update, context, user_id, user_data)
    else:
        # User hasn't joined both channels
        add_verification_record(user_id, False, "Verification failed - not member of channels")
        
        keyboard = [
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("🔄 ＣＨＥＣＫ", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "━━━⚠️ WᴀʀɴɪɴG ⚠️━━━\n\n"
            "🚫 Yᴏᴜ Hᴀᴠᴇɴ'ᴛ Jᴏɪɴᴇᴅ Bᴏᴛʜ Cʜᴀɴɴᴇʟꜱ Yᴇᴛ!\n\n"
            "📢 Pʟᴇᴀꜱᴇ Jᴏɪɴ Bᴏᴛʜ Cʜᴀɴɴʟᴇ Aʙᴏᴠᴇ 📡\n"
            "🔁 Tʜᴇɴ Cʟɪᴄᴋ Cʜᴇᴋ🔘\n\n"
            "━━━━━━━━━━━━━━━━━━━━━",
            reply_markup=reply_markup
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "help":
        help_text = """╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]    

🔍 *Hᴏᴡ Tᴏ Uꜱᴇ Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ:*

✯ 📱 *Pʜᴏɴᴇ Nᴜᴍʙᴇ Sᴇᴀʀᴄʜ* – Sᴇɴᴅ Nᴏ. Lɪᴋᴇ  `91XXXXXXXXXX`
✯ 📧 *Eᴍᴀɪʟ Sᴇᴀʀᴄʜ* – Sᴇɴᴅ Eᴍᴀɪʙ Lɪᴋᴇ  `example@gmail.com`
✯ 👤 *Nᴀᴍᴇ Sᴇᴀʀᴄʜ* – Jᴜꜱᴛ Sᴇɴᴅ Tʜᴇ Nᴀᴍᴇ
↣↣↣↣↣↣↣↣↣↣
📂 I Wɪʟʟ Sᴄᴀɴ Aᴄʀᴏꜱꜱ Mᴜʟᴛɪᴘʟᴇ Dᴀᴛᴀʙᴀꜱᴇꜱ 🗂️
━━━━━━━━━━━━━━━━━━━━━
☛ *Nᴏᴛᴇ:* Eᴀᴄʜ Sᴇᴀʀᴄʜ Cᴏꜱᴛꜱ 💎 1 Cʀᴇᴅɪᴛ
"""
        keyboard = [[InlineKeyboardButton("🔙 Bᴀᴄᴋ", callback_data="profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(help_text, parse_mode="Markdown", reply_markup=reply_markup)
        
    elif query.data == "search_prompt":
        search_prompt_text = """╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]    

🔍 *Wʜᴀᴛ Cᴀɴ ɪ Dᴏ?*

☛ 📱 *Pʜᴏɴᴇ Nᴜᴍʙᴇ Sᴇᴀʀᴄʜ* – Sᴇɴᴇ Nᴏ. Lɪᴋᴇ  `91XXXXXXXXXX`
↣↣↣↣↣↣↣↣↣↣
☛ 📧 *Eᴍᴀɪʟ Sᴇᴀʀᴄʜ* – Sᴇɴᴅ Eᴍᴀɪʟ Lɪᴋᴇ  `example@gmail.com`
↣↣↣↣↣↣↣↣↣↣
☛ 👤 *Nᴀᴍᴇ Sᴇᴀʀᴄʜ* – Jᴜꜱᴛ Sᴇɴᴅ Tʜᴇ Nᴀᴍᴇ
↣↣↣↣↣↣↣↣↣↣
📂 I Wɪʟʟ Sᴄᴀɴ Aᴄʀᴏꜱꜱ Mᴜʟᴛɪᴘʟᴇ Dᴀᴛᴀʙᴀꜱᴇꜱ 🗂️
━━━━━━━━━━━━━━━━━━━━━
⚠️ *Nᴏᴛᴇ:* Eᴀᴄʜ Sᴇᴀʀᴄʜ Cᴏꜱᴛꜱ 💎 1 Cʀᴇᴅɪᴛ
"""
        keyboard = [[InlineKeyboardButton("🔙 Bᴀᴄᴋ", callback_data="profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(search_prompt_text, parse_mode="Markdown", reply_markup=reply_markup)
        
    elif query.data == "buy":
        buy_message = """
╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]      

💎 Cʀᴇᴅɪᴛ Pʟᴀɴꜱ
━━━━━━━━━━━━━━━━━━━━━

1️⃣ Sᴛᴀʀᴛᴇʀ Pᴀᴄᴋ 🎯 
✨10 Cʀᴇᴅɪᴛꜱ → ₹25 
🎁Bᴏɴᴜꜱ: +2 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ 
💡Bᴇꜱᴛ ꜰᴏʀ ᴛᴇꜱᴛɪɴɢ ᴛʜᴇ ᴀᴘᴐ
━━━━━━━━━━━━━━━━━━━━━

2️⃣ Vᴀʟᴜᴇ Pᴀᴄᴋ 📦 
✨25 Cʀᴇᴅɪᴛꜱ → ₹50 
🎁Bᴏɴᴜꜱ: +5 Fʀᴇᴅɪᴛꜱ 
💡Pᴏᴘᴜʟᴀʜ ᴄʜᴏɪᴄᴇ ꜰᴏʀ ɴᴇᴡ ᴜꜱᴇʀꜱ
━━━━━━━━━━━━━━━━━━━━━

3️⃣ Sᴍᴀʀᴛ Sᴀᴠᴇʀ Pᴀᴄᴋ 🪙 
✨50 Cʀᴇᴅɪᴛꜱ → ₹90 
🎁Bᴏɴᴜꜱ: +15 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ 
💡Mᴏʜᴇ ᴘʜᴀᴛɪᴍᴇ, ᴍᴏʀᴇ ʀᴇᴡᴀʀᴅꜱ
━━━━━━━━━━━━━━━━━━━━━

4️⃣ Pʀᴏ Pᴀᴄᴋ 🚀 
✨75 Cʀᴇᴅɪᴛꜱ → ₹120 
🎁Bᴏɴᴜꜱ: +25 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ 
💡Bᴇꜱᴛ ꜰᴏʀ ʀᴇɢᴜʟᴀʀ ᴜꜱᴇʀꜱ
━━━━━━━━━━━━━━━━━━━━━

5️⃣ Mᴇɢᴀ Pᴀᴄᴋ 👑 
✨100 Cʀᴇᴅɪᴛꜱ → ₹150 
🎁Bᴏɴᴜꜱ: +40 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ 
💡Mᴀxɪᴍᴜᴍ ᴠᴀʟᴜᴇ & ꜱᴀᴠɪɴɢꜱ
━━━━━━━━━━━━━━━━━━━━━

🔌 Aᴘɪ Pᴜʀᴄʜᴀꜱᴇ
━━━━━━━━━━━━━━━━━━━━━

🕒 Bᴜʏ Aᴘɪ — 1 Mᴏɴᴛʜ — ₹399/-
🔒Bᴜʏ Aᴘɪ — Lɪꜰᴇᴛɪᴍᴇ — ₹1999/-
ℹ️Cᴏɴᴛᴀᴄᴛ Oᴡɴᴇʀ ꜰᴏʀ ᴍᴏʀᴇ ɪɴꜰᴏʀᴍᴀᴛɪᴜɴ: @pvt_s1n
"""

        keyboard = [
            [InlineKeyboardButton("💬 Cᴏɴᴛᴀᴄᴛ Oᴡɴᴇʀ", url=f"https://t.me/{OWNER_USERNAME[1:]}")],
            [InlineKeyboardButton("🔙 Bᴀᴄᴋ", callback_data="profile")]
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
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("🔐 ＶＥＲＩＦＹ", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("⚠️ Yᴏᴜ ᴍᴜꜱᴛ ᴊᴏɪɴ ᴀʟʟ ᴄʜᴀɴɴᴇʟꜱ ᴀɴᴅ ᴠᴇʀɪғʏ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ.", reply_markup=reply_markup)
        return

    user_data = users_collection.find_one({"_id": str(user_id)})
    
    if not user_data:
        # New user - add to database with initial credits
        name = update.effective_user.first_name
        user_data = update_user(user_id, credits=2, name=name, last_verified=datetime.now().isoformat())
        add_verification_record(user_id, True, "New user - initial credits granted via search")

    if user_data.get("credits", 0) <= 0:
        keyboard = [[InlineKeyboardButton("💳 Bᴜʏ Cʀᴇᴅɪᴛꜱ", callback_data="buy")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"❌ Nᴏ Cʀᴇᴅɪᴛ Lᴇꜰᴛ!\n\n💳Bᴜʏ Uɴʟɪᴍɪᴛᴇᴅ 🌀 Cʀᴇᴅɪᴛꜱ & Aᴘɪ⚡Cᴏɴᴛᴀᴄᴛ 👉 {OWNER_USERNAME}", reply_markup=reply_markup)
        return

    # Show animated spinner
    spinner_msg = await show_spinner(update, context, update.message)

    query = update.message.text
    result = query_leakosint(query)
    msg = format_results(result)

    # Deduct 1 credit only if search was successful
    if "Nᴏ Dᴀᴛᴀ" not in msg and "Sᴇʀᴠᴇʀ" not in msg:
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
    msg += f"\n💵 Cʀᴇᴅɪᴛ : {credits_left} 💎"
    
    keyboard = [[InlineKeyboardButton("💳 Bᴜʏ Cʀᴇᴅɪᴛꜱ", callback_data="buy")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(msg, reply_markup=reply_markup)

async def credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check membership first
    is_member = await check_membership(update, context, user_id)
    if not is_member:
        keyboard = [
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("🔐 ＶＥＲＩＦＹ", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("⚠️ Yᴏᴜ ᴍᴜꜱᴛ ᴊᴏɪɴ ᴀʟʟ ᴄʜᴀɴɴᴇʟꜱ ᴀɴᴅ ᴠᴇʀɪғʏ ᴛᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ.", reply_markup=reply_markup)
        return
        
    user_data = users_collection.find_one({"_id": str(user_id)})
    c = user_data.get("credits", 0) if user_data else 0
    await update.message.reply_text(f"💵 Yᴏᴜʀ Cʀᴇᴅɪᴛꜱ: {c} 💎")

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check membership first
    is_member = await check_membership(update, context, user_id)
    if not is_member:
        keyboard = [
            [InlineKeyboardButton("📢 ＪＯ𝐼𝐍", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 ＪＯ𝐼𝐍", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("🔐 ＶＥ１𝐼ＦＹ", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("⚠️ Yᴏᴜ ᴍᴜꜱᴛ ᴊᴏɪɴ ᴀʟʟ ᴄʜᴀɴɴᴇʟꜱ ᴀɴᴅ ᴠᴇʀɪғʏ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ.", reply_markup=reply_markup)
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
        await update.message.reply_text("❌ Aᴄᴄᴇꜱꜱ Dᴇɴɪᴇᴅ.")
        return
        
    users_count = users_collection.count_documents({})
    total_credits = 0
    for user in users_collection.find({}):
        total_credits += user.get("credits", 0)
    
    stats_msg = f"""
╏╠══[𝍖𝍖𝍖 ＡＤＭＩＮ  𝍖𝍖𝍖]    

👥 Tᴏᴛᴀʟ Usᴇʀs: {users_count}
💎 Tᴏᴛᴀʟ Cʀᴇᴅɪᴛs: {total_credits}
📊 Lᴀsᴛ Uᴘᴅᴀᴛᴇ: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}
"""
    await update.message.reply_text(stats_msg)

# ==== MAIN ====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("credits", credits))
    app.add_handler(CommandHandler("me", me))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("adminstats", admin_stats))
    app.add_handler(CommandHandler("addcredits", addcredits_command))
    app.add_handler(CommandHandler("setcredits", setcredits_command))
    app.add_handler(CommandHandler("userinfo", userinfo_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify$"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(help|search_prompt|buy|profile)$"))

    print("╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]    ......")
    app.run_polling()

if __name__ == "__main__":
    main()