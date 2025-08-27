# -*- coding: utf-8 -*-
import json
import requests
import asyncio
import hashlib
import random
import string
import os
import httpx # Use httpx for asynchronous requests
from datetime import datetime
from functools import wraps
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from pymongo import MongoClient

# ==== CONFIG ====
# It's recommended to set these in your Render environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN', "YOUR_FALLBACK_BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', "@zarkoworld")   # Main channel
CHANNEL_USERNAME_2 = os.environ.get('CHANNEL_USERNAME_2', "@chandhackz_78")  # Second channel
OWNER_USERNAME = os.environ.get('OWNER_USERNAME', "@pvt_s1n")    # Your username
ADMIN_ID = int(os.environ.get('ADMIN_ID', 7975903577))  # Your user ID

LEAKOSINT_API_TOKEN = os.environ.get('LEAKOSINT_API_TOKEN', "YOUR_FALLBACK_LEAKOSINT_TOKEN")
API_URL = os.environ.get('API_URL', "https://leakosintapi.com/")

# MongoDB Connection
MONGO_URI = os.environ.get('MONGO_URI', "YOUR_FALLBACK_MONGO_URI")

# Connect to MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client['zarkobot']
    users_collection = db['users']
    audit_collection = db['audit_logs']
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ Error connecting to MongoDB: {e}")
    exit(1)

# ==== DECORATORS ====
def membership_required(func):
    """Decorator to check if a user is a member of the required channels."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not await check_membership(update, context, user_id):
            keyboard = [
                [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
                [InlineKeyboardButton("🔐 ＶＥＲＩＦＹ", callback_data="verify")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message_target = update.message or update.callback_query.message
            await message_target.reply_text(
                "⚠️ Yᴏᴜ ᴍᴜꜱᴛ ᴊᴏɪɴ ᴀʟʟ ᴄʜᴀɴɴᴇʟꜱ ᴀɴᴅ ᴠᴇʀɪғʏ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ.",
                reply_markup=reply_markup
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# ==== Security Functions ====
def generate_user_hash(user_id: int) -> str:
    """Generate a consistent 6-digit alphanumeric hash for user identification."""
    sha = hashlib.sha256(str(user_id).encode()).hexdigest()
    return sha[:6].upper()

def log_audit_event(user_id: int, event_type: str, details: str):
    """Log security and key events for monitoring."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "user_hash": generate_user_hash(user_id),
        "event_type": event_type,
        "details": details
    }
    try:
        audit_collection.insert_one(log_entry)
    except Exception as e:
        print(f"Audit log error: {e}")

# ==== User Data Functions ====
def get_or_create_user(user_id: int, name: str = "Unknown"):
    """Find a user by ID or create a new one if they don't exist."""
    uid = str(user_id)
    user_data = users_collection.find_one({"_id": uid})

    if not user_data:
        user_data = {
            "_id": uid,
            "credits": 0,
            "name": name,
            "last_update": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
            "initial_credits_given": False,
            "join_date": datetime.now().strftime("%Y-%m-%d"),
            "user_hash": generate_user_hash(user_id),
            "verification_history": [],
            "last_verified": None
        }
        users_collection.insert_one(user_data)
        log_audit_event(user_id, "USER_CREATE", f"New user created: {name}")
    return user_data

def update_user(user_id: int, updates: dict):
    """Update user data in MongoDB."""
    uid = str(user_id)
    updates["last_update"] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    users_collection.update_one({"_id": uid}, {"$set": updates}, upsert=True)
    log_audit_event(user_id, "USER_UPDATE", f"Updated fields: {list(updates.keys())}")

def add_verification_record(user_id: int, success: bool, details: str):
    """Add a verification attempt to user's history."""
    record = {"timestamp": datetime.now().isoformat(), "success": success, "details": details}
    users_collection.update_one(
        {"_id": str(user_id)},
        {"$push": {"verification_history": {"$each": [record], "$slice": -10}}}
    )

# ==== Bot Logic ====
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """Check if the user is a member of both required channels."""
    try:
        member1 = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        member2 = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME_2, user_id=user_id)
        is_member = member1.status not in ["left", "kicked"] and member2.status not in ["left", "kicked"]
        log_audit_event(user_id, "MEMBERSHIP_CHECK", f"Channel1: {member1.status}, Channel2: {member2.status}, Result: {is_member}")
        return is_member
    except Exception as e:
        print(f"Error checking membership for user {user_id}: {e}")
        log_audit_event(user_id, "MEMBERSHIP_ERROR", str(e))
        if update.message:
            await update.message.reply_text("Couldn't verify channel membership due to a Telegram error. Please try again later.")
        return False

async def query_leakosint(query: str) -> dict:
    """Perform an asynchronous API query to Leakosint."""
    payload = {"token": LEAKOSINT_API_TOKEN, "request": query, "limit": 500, "lang": "en"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(API_URL, json=payload, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except httpx.RequestError as e:
        print(f"API request error: {e}")
        return {"Error": f"Could not connect to the API server: {e}"}
    except Exception as e:
        print(f"An unexpected error occurred during API query: {e}")
        return {"Error": str(e)}

def format_results(resp: dict) -> str:
    """Format the API JSON response into a user-friendly string."""
    if "Error" in resp or "Error code" in resp:
        return "⚠️ Sᴇʀᴠᴇʀ Iꜱ Oɴ Mᴀɪɴᴛᴀɪɴᴇɴᴄᴇ ᴏʀ ʏᴏᴜʀ ᴛᴏᴋᴇɴ ɪꜱ ɪɴᴠᴀʟɪᴅ."

    results = []
    for db, data in resp.get("List", {}).items():
        for row in data.get("Data", []):
            result_entry = f"""
👤 Nᴀᴍᴇ ➤ {row.get("FatherName", "N/A")}
🧓 Fᴀᴛʜᴇʀ'ꜱ Nᴀᴍᴇ ➤ {row.get("FullName", "N/A")}
📱 Mᴏʙɪʟᴇ ➤ {row.get("Phone", "N/A")}
📞 Aʟᴛ Nᴜᴍʙᴇʀ1 ➤ {row.get("Phone2", "N/A")}
📞 Aʟᴛ Nᴜᴍʙᴇʀ2 ➤ {row.get("Phone3", "N/A")}
📞 Aʟᴛ Nᴜᴍʙᴇʀ3 ➤ {row.get("Phone4", "N/A")}
📞 Aʟᴛ Nᴜᴍʙᴇʀ4 ➤ {row.get("Phone5", "N/A")}
📞 Aʟᴛ Nᴜᴍʙᴇʀ5 ➤ {row.get("Phone6", "N/A")}
🆔 Aᴀᴅʜᴀʀ 𝙸𝙳 ➤ {row.get("DocNumber", "N/A")}
📶 Cɪʀᴄʟᴇ ➤ {row.get("Region", "N/A")}
🏠 Aᴅᴅʀᴇꜱꜱ ➤ {row.get("Address", "N/A")}"""
            results.append(result_entry)

    if not results:
        return "❌ Nᴏ Dᴀᴛᴀ Aᴠᴀɪʟᴀʙʟᴇ Iɴ Dᴀᴛᴀʙᴀꜱᴇ"

    return "\n────────────────────\n".join(results)

# ==== Message Templates ====
BUY_CREDITS_MESSAGE = f"""
╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]      

💎 **Cʀᴇᴅɪᴛ Pʟᴀɴꜱ**
━━━━━━━━━━━━━━━━━━━━━

1️⃣ **Sᴛᴀʀᴛᴇʀ Pᴀᴄᴋ** 🎯 
✨ 10 Cʀᴇᴅɪᴛꜱ → ₹25 
🎁 Bᴏɴᴜꜱ: +2 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ 
💡 Bᴇꜱᴛ ꜰᴏʀ ᴛᴇꜱᴛɪɴɢ

2️⃣ **Vᴀʟᴜᴇ Pᴀᴄᴋ** 📦 
✨ 25 Cʀᴇᴅɪᴛꜱ → ₹50 
🎁 Bᴏɴᴜꜱ: +5 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ 
💡 Pᴏᴘᴜʟᴀʀ ᴄʜᴏɪᴄᴇ

3️⃣ **Sᴍᴀʀᴛ Sᴀᴠᴇʀ Pᴀᴄᴋ** 🪙 
✨ 50 Cʀᴇᴅɪᴛꜱ → ₹90 
🎁 Bᴏɴᴜꜱ: +15 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ 
💡 Mᴏʀᴇ ᴠᴀʟᴜᴇ

4️⃣ **Pʀᴏ Pᴀᴄᴋ** 🚀 
✨ 75 Cʀᴇᴅɪᴛꜱ → ₹120 
🎁 Bᴏɴᴜꜱ: +25 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ 
💡 Fᴏʀ ʀᴇɢᴜʟᴀʀ ᴜꜱᴇʀꜱ

5️⃣ **Mᴇɢᴀ Pᴀᴄᴋ** 👑 
✨ 100 Cʀᴇᴅɪᴛꜱ → ₹150 
🎁 Bᴏɴᴜꜱ: +40 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ 
💡 Mᴀxɪᴍᴜᴍ ꜱᴀᴠɪɴɢꜱ

🔌 **Aᴘɪ Pᴜʀᴄʜᴀꜱᴇ**
━━━━━━━━━━━━━━━━━━━━━
🕒 1 Mᴏɴᴛʜ Aᴘɪ — ₹399/-
🔒 Lɪꜰᴇᴛɪᴍᴇ Aᴘɪ — ₹1999/-
ℹ️ Cᴏɴᴛᴀᴄᴛ Oᴡɴᴇʀ ꜰᴏʀ ᴍᴏʀᴇ ɪɴꜰᴏ: {OWNER_USERNAME}
"""

def get_buy_keyboard() -> InlineKeyboardMarkup:
    """Returns the keyboard for the buy message."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Cᴏɴᴛᴀᴄᴛ Oᴡɴᴇʀ", url=f"https://t.me/{OWNER_USERNAME[1:]}")],
        [InlineKeyboardButton("🔙 Bᴀᴄᴋ", callback_data="profile")]
    ])

# ==== Command Handlers ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log_audit_event(user.id, "START_COMMAND", f"User: {user.first_name}")

    user_data = get_or_create_user(user.id, user.first_name)
    is_member = await check_membership(update, context, user.id)

    if is_member:
        if not user_data.get("initial_credits_given"):
            update_user(user.id, {"credits": 2, "initial_credits_given": True, "last_verified": datetime.now().isoformat()})
            add_verification_record(user.id, True, "New user - initial 2 credits granted")
            await update.message.reply_text(
                "🍑 Vᴇʀɪꜰɪᴄᴀᴛɪᴏɴ Sᴜᴄᴄᴇꜱꜱꜰᴜʟ! 🎉\n\n"
                "✨ Yᴏᴜ'ᴠᴇ Rᴇᴄᴇɪᴠᴇᴅ 💎 2 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ.\n\n"
                "Eɴᴊᴏʏ ʏᴏᴜʀ ᴊᴏᴜʀɴᴇʏ!"
            )
        else:
             add_verification_record(user.id, True, "Existing user - membership re-verified")
        
        await show_profile(update, context) # No edit_message needed
    else:
        keyboard = [
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("🔐 ＶＥＲＩＦＹ", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        add_verification_record(user.id, False, "User not member of required channels")
        await update.message.reply_text(
            "╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]      \n\n"
            "✮ 🤖 Tᴏ Uꜱᴇ Tʜɪꜱ Bᴏᴛ, ʏᴏᴜ ᴍᴜꜱᴛ:\n\n"
            "1️⃣ Jᴏɪɴ Bᴏᴛʜ ᴏꜰꜰɪᴄɪᴀʟ ᴄʜᴀɴɴᴇʟꜱ.\n"
            "2️⃣ Cʟɪᴄᴋ ᴛʜᴇ 'ＶＥＲＩＦＹ' ʙᴜᴛᴛᴏɴ.\n\n"
            "🎁 Aꜰᴛᴇʀ Vᴇʀɪꜰɪᴄᴀᴛɪᴏɴ, ʏᴏᴜ ᴡɪʟʟ ʀᴇᴄᴇɪᴠᴇ 💎 2 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ.",
            reply_markup=reply_markup
        )

@membership_required
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_or_create_user(user_id, update.effective_user.first_name)

    if user_data.get("credits", 0) <= 0:
        await update.message.reply_text(
            f"❌ Yᴏᴜ ʜᴀᴠᴇ ɴᴏ ᴄʀᴇᴅɪᴛꜱ ʟᴇꜰᴛ!\n\n💳 Bᴜʏ ᴍᴏʀᴇ ᴄʀᴇᴅɪᴛꜱ ᴏʀ ᴄᴏɴᴛᴀᴄᴛ {OWNER_USERNAME} ꜰᴏʀ ʜᴇʟᴘ.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Bᴜʏ Cʀᴇᴅɪᴛꜱ", callback_data="buy")]])
        )
        return

    query = update.message.text
    spinner_msg = await update.message.reply_text("🔍 Sᴇᴀʀᴄʜɪɴɢ...")

    api_task = asyncio.create_task(query_leakosint(query))
    spinner_frames = ["▖", "▘", "▝", "▗"]
    i = 0
    while not api_task.done():
        try:
            await spinner_msg.edit_text(f"🔍 Sᴇᴀʀᴄʜɪɴɢ... {spinner_frames[i % len(spinner_frames)]}")
            i += 1
            await asyncio.sleep(0.2)
        except Exception:
            break

    result_json = await api_task
    msg_text = format_results(result_json)

    if "Nᴏ Dᴀᴛᴀ" not in msg_text and "Sᴇʀᴠᴇʀ" not in msg_text:
        new_credits = user_data.get("credits", 1) - 1
        update_user(user_id, {"credits": new_credits})
        log_audit_event(user_id, "SEARCH_SUCCESS", f"Query: '{query}', Credits left: {new_credits}")
    else:
        log_audit_event(user_id, "SEARCH_FAIL", f"Query: '{query}', No data found or error.")

    await spinner_msg.delete()

    updated_user_data = get_or_create_user(user_id)
    credits_left = updated_user_data.get("credits", 0)
    final_message = f"{msg_text}\n\n💵 Cʀᴇᴅɪᴛꜱ Lᴇꜰᴛ: {credits_left} 💎"
    
    await update.message.reply_text(final_message, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Bᴜʏ Cʀᴇᴅɪᴛꜱ", callback_data="buy")]]))

# ===================================================================
# ==== THIS IS THE CORRECTED FUNCTION ====
# ===================================================================
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, edit_message: bool = False):
    """Displays the user profile. Can either edit an existing message or send a new one."""
    user_id = update.effective_user.id
    user_data = get_or_create_user(user_id, update.effective_user.first_name)
    
    profile_msg = f"""
👤 **Nᴀᴍᴇ:** {user_data.get("name", "Unknown")}
🆔 **Usᴇʀ ID:** `{user_id}`
✨ **Usᴇʀ Hᴀsʜ:** `{user_data.get("user_hash")}`
💎 **Cʀᴇᴅɪᴛꜱ:** {user_data.get("credits", 0)}
📅 **Jᴏɪɴᴇᴅ Oɴ:** {user_data.get("join_date", "N/A")}
⌚️ **Lᴀsᴛ Uᴘᴅᴀᴛᴇᴅ:** {user_data.get("last_update", "N/A")}
"""
    keyboard = [
        [InlineKeyboardButton("❓ Help", callback_data="help"), InlineKeyboardButton("🔍 New Search", callback_data="search_prompt")],
        [InlineKeyboardButton("💳 Buy Credits", callback_data="buy")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # This logic now correctly handles all cases
    if edit_message and update.callback_query:
        # If called from a button and we need to edit the message
        await update.callback_query.message.edit_text(
            profile_msg, reply_markup=reply_markup, parse_mode="Markdown"
        )
    else:
        # If called from a command OR after verification, send a new message
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=profile_msg,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

@membership_required
async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_profile(update, context, edit_message=False)

@membership_required
async def credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_or_create_user(update.effective_user.id)
    await update.message.reply_text(f"💵 Yᴏᴜʀ Cᴜʀʀᴇɴᴛ Cʀᴇᴅɪᴛꜱ: {user_data.get('credits', 0)} 💎")

@membership_required
async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(BUY_CREDITS_MESSAGE, reply_markup=get_buy_keyboard(), parse_mode="Markdown")

# ==== Callback Query Handlers ====
async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Checking membership status...")
    
    user = update.effective_user
    user_data = get_or_create_user(user.id, user.first_name)
    is_member = await check_membership(update, context, user.id)
    
    if is_member:
        if not user_data.get("initial_credits_given"):
            update_user(user.id, {"credits": 2, "initial_credits_given": True, "last_verified": datetime.now().isoformat()})
            add_verification_record(user.id, True, "Verification success - 2 credits granted")
            await query.edit_message_text(
                "🍑 Vᴇʀɪꜰɪᴄᴀᴛɪᴏɴ Sᴜᴄᴄᴇꜱꜱꜰᴜʟ! 🎉\n\n"
                "✨ Yᴏᴜ'ᴠᴇ Rᴇᴄᴇɪᴠᴇᴅ 💎 2 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ."
            )
        else:
            add_verification_record(user.id, True, "Existing user - reverified successfully")
            await query.edit_message_text("✅ Vᴇʀɪꜰɪᴄᴀᴛɪᴏɴ Sᴜᴄᴄᴇꜱꜱꜰᴜʟ! Yᴏᴜ ᴀʀᴇ ᴀʟʀᴇᴀᴅʏ ᴀ ᴠᴇʀɪꜰɪᴇᴅ ᴍᴇᴍʙᴇʀ.")
        
        # This will now correctly send a new message with the profile info
        await show_profile(update, context, edit_message=False)
    else:
        add_verification_record(user.id, False, "Verification failed - not in channels")
        keyboard = [
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("🔄 ＲＥ-ＣＨＥＣＫ", callback_data="verify")]
        ]
        await query.edit_message_text(
            "⚠️ **Vᴇʀɪꜰɪᴄᴀᴛɪᴏɴ Fᴀɪʟᴇᴅ** ⚠️\n\n"
            "🚫 Yᴏᴜ ʜᴀᴠᴇɴ'ᴛ ᴊᴏɪɴᴇᴅ ʙᴏᴛʜ ᴄʜᴀɴɴᴇʟꜱ ʏᴇᴛ.\n\n"
            "Pʟᴇᴀꜱᴇ ᴊᴏɪɴ ᴛʜᴇᴍ ᴀɴᴅ ᴄʟɪᴄᴋ 'ＲＥ-ＣＨＥＣＫ'.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "profile":
        await show_profile(update, context, edit_message=True)
        return

    if data == "buy":
        await query.edit_message_text(BUY_CREDITS_MESSAGE, reply_markup=get_buy_keyboard(), parse_mode="Markdown")
        return

    text_map = {
        "help": """
╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]    

*How To Use The Bot:*
Just send me any of the following to start a search:

📱 **Phone Number:** `91XXXXXXXXXX`
📧 **Email Address:** `example@gmail.com`
👤 **Full Name:** `John Doe`

📂 I will scan across multiple databases to find a match.
*Note: Each search costs 💎 1 Credit.*
""",
        "search_prompt": """
*Ready to start a new search?*

Just send a message with the information you want to find. For example:

- A phone number: `919876543210`
- An email: `user@domain.com`
- A name: `Alex Smith`
"""
    }
    
    keyboard = [[InlineKeyboardButton("🔙 Bᴀᴄᴋ", callback_data="profile")]]
    await query.edit_message_text(
        text_map.get(data, "Invalid selection."), 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

# ==== ADMIN FUNCTIONS ====
async def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

async def admin_command_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, command_func, required_args: int):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Aᴄᴄᴇꜱꜱ Dᴇɴɪᴇᴅ. This command is for admins only.")
        return
    
    if len(context.args) < required_args:
        await update.message.reply_text(f"❌ Iɴᴠᴀʟɪᴅ ᴜꜱᴀɢᴇ. Requires {required_args} argument(s).")
        return
    
    await command_func(update, context)

async def addcredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def cmd(update, context):
        try:
            target_user_id = int(context.args[0])
            amount = int(context.args[1])
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Uꜱᴀɢᴇ: /addcredits `<user_id>` `<amount>`")
            return

        user_data = get_or_create_user(target_user_id)
        new_credits = user_data.get("credits", 0) + amount
        update_user(target_user_id, {"credits": new_credits})
        
        log_audit_event(ADMIN_ID, "ADMIN_ADD_CREDITS", f"Target: {target_user_id}, Amount: {amount}, New Balance: {new_credits}")
        await update.message.reply_text(f"✅ Aᴅᴅᴇᴅ {amount} ᴄʀᴇᴅɪᴛꜱ ᴛᴏ ᴜꜱᴇʀ {target_user_id}.\nNᴇᴡ ʙᴀʟᴀɴᴄᴇ: {new_credits} 💎")

    await admin_command_wrapper(update, context, cmd, 2)

async def setcredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def cmd(update, context):
        try:
            target_user_id = int(context.args[0])
            amount = int(context.args[1])
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Uꜱᴀɢᴇ: /setcredits `<user_id>` `<amount>`")
            return

        update_user(target_user_id, {"credits": amount})
        log_audit_event(ADMIN_ID, "ADMIN_SET_CREDITS", f"Target: {target_user_id}, New Amount: {amount}")
        await update.message.reply_text(f"✅ Sᴇᴛ ᴄʀᴇᴅɪᴛꜱ ᴏꜰ ᴜꜱᴇʀ {target_user_id} ᴛᴏ {amount} 💎")

    await admin_command_wrapper(update, context, cmd, 2)

async def userinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def cmd(update, context):
        try:
            target_user_id = int(context.args[0])
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Uꜱᴀɢᴇ: /userinfo `<user_id>`")
            return
            
        user_data = users_collection.find_one({"_id": str(target_user_id)})
        if not user_data:
            await update.message.reply_text("❌ Uꜱᴇʀ ɴᴏᴛ ꜰᴏᴜɴᴅ")
            return

        history_log = "\n".join([f"{'✅' if r.get('success') else '❌'} {r.get('timestamp')} - {r.get('details')}" for r in user_data.get('verification_history', [])])
        info_msg = f"""
*USER INFO*
👤 **Name:** {user_data.get('name', 'N/A')}
🆔 **User ID:** `{target_user_id}`
✨ **User Hash:** `{user_data.get('user_hash', 'N/A')}`
💎 **Credits:** {user_data.get('credits', 0)}
📅 **Join Date:** {user_data.get('join_date', 'N/A')}
⌚️ **Last Update:** {user_data.get('last_update', 'N/A')}
✅ **Last Verified:** {user_data.get('last_verified', 'N/A')}

*Verification History (Last 10):*
{history_log or "No history found."}
"""
        log_audit_event(ADMIN_ID, "ADMIN_USERINFO", f"Viewed info for user: {target_user_id}")
        await update.message.reply_text(info_msg, parse_mode="Markdown")

    await admin_command_wrapper(update, context, cmd, 1)

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def cmd(update, context):
        message = " ".join(context.args)
        all_users = list(users_collection.find({}))
        success_count, fail_count = 0, 0
        
        broadcast_msg = f"📢 **Broadcast Message from Admin** 📢\n\n{message}"
        
        status_msg = await update.message.reply_text(f"📢 Starting broadcast to {len(all_users)} users...")

        for i, user in enumerate(all_users):
            try:
                await context.bot.send_message(chat_id=int(user["_id"]), text=broadcast_msg, parse_mode="Markdown")
                success_count += 1
            except Exception as e:
                print(f"Failed to send broadcast to {user['_id']}: {e}")
                fail_count += 1
            await asyncio.sleep(0.1)
            if (i + 1) % 20 == 0:
                await status_msg.edit_text(f"📢 Broadcasting... Sent: {i+1}/{len(all_users)}")

        log_audit_event(ADMIN_ID, "ADMIN_BROADCAST", f"Success: {success_count}, Failed: {fail_count}")
        await status_msg.edit_text(f"✅ Bʀᴏᴀᴅᴄᴀꜱᴛ ᴄᴏᴍᴘʟᴇᴛᴇ!\nSᴜᴄᴄᴇꜱꜱ: {success_count}\nFᴀɪʟᴇᴅ: {fail_count}")

    await admin_command_wrapper(update, context, cmd, 1)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id): return
    users_count = users_collection.count_documents({})
    total_credits_pipeline = [{"$group": {"_id": None, "total": {"$sum": "$credits"}}}]
    total_credits = next(users_collection.aggregate(total_credits_pipeline), {}).get("total", 0)
    
    stats_msg = f"""
*BOT STATISTICS*
👥 **Total Users:** {users_count}
💎 **Total Credits in Circulation:** {total_credits}
📊 **Last Updated:** {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}
"""
    await update.message.reply_text(stats_msg, parse_mode="Markdown")

# ==== MAIN ====
def main():
    """Start the bot."""
    app = Application.builder().token(BOT_TOKEN).build()

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("credits", credits_command))
    app.add_handler(CommandHandler("me", me))
    app.add_handler(CommandHandler("buy", buy_command))
    
    # Admin commands
    app.add_handler(CommandHandler("adminstats", admin_stats))
    app.add_handler(CommandHandler("addcredits", addcredits_command))
    app.add_handler(CommandHandler("setcredits", setcredits_command))
    app.add_handler(CommandHandler("userinfo", userinfo_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    
    # Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify$"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(help|search_prompt|buy|profile)$"))

    print("🚀 Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()