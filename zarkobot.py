# -*- coding: utf-8 -*-
import json
import requests
import asyncio
import hashlib
import random
import string
import os
import asyncpg
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ==== CONFIG ====
# Apne bot ka token yahan daalein ya environment variable se lein
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8116705267:AAGVx7azJJMndrXHwzoMnx7angKd0COJWjg")
# Render.com se mila DATABASE_URL environment variable se liya jayega
DATABASE_URL = os.environ.get("DATABASE_URL")

CHANNEL_USERNAME = "@chandhackz_78"   # Main channel
CHANNEL_USERNAME_2 = "@zarkoworld"  # Second channel
OWNER_USERNAME = "@pvt_s1n"    # Aapka username

LEAKOSINT_API_TOKEN = os.environ.get("LEAKOSINT_API_TOKEN", "8176139267:btRibc7y")
API_URL = "https://leakosintapi.com/"

AUDIT_LOG_FILE = "audit.log"

# ==== Security Functions ====
def generate_user_hash(user_id):
    """User identification ke liye 6-digit alphanumeric hash generate karein"""
    random.seed(user_id)
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(6))

def log_audit_event(user_id, event_type, details):
    """Monitoring ke liye security events log karein"""
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
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Audit log error: {e}")

# ==== Database Functions ====
async def init_db(app: Application):
    """Database connection pool banayein aur table ensure karein"""
    try:
        pool = await asyncpg.create_pool(DATABASE_URL)
        app.bot_data["pool"] = pool
        async with pool.acquire() as connection:
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    credits INTEGER DEFAULT 0,
                    name TEXT,
                    last_update TIMESTAMPTZ,
                    initial_credits_given BOOLEAN DEFAULT FALSE,
                    join_date DATE,
                    user_hash TEXT,
                    verification_history JSONB,
                    last_verified TIMESTAMPTZ
                )
            ''')
        print("Database connection pool initialized and table ensured.")
    except Exception as e:
        print(f"FATAL: Database connection failed: {e}")
        # Agar DB connect na ho to bot ko band kar dein
        os._exit(1)


async def get_user(pool, user_id):
    """Database se user data fetch karein"""
    async with pool.acquire() as connection:
        user_record = await connection.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        return dict(user_record) if user_record else None

async def upsert_user(pool, user_id, name, credits=None, last_verified=None, initial_credits_given=None):
    """User ko create ya update karein (UPSERT operation)"""
    user_hash = generate_user_hash(user_id)
    async with pool.acquire() as connection:
        # Pehle se user hai ya nahi, check karein
        existing_user = await get_user(pool, user_id)
        
        if existing_user:
            # User hai, to update karein
            update_fields = {"name": name, "last_update": datetime.now()}
            if credits is not None:
                update_fields["credits"] = credits
            if last_verified is not None:
                update_fields["last_verified"] = last_verified
            
            set_clauses = [f"{key} = ${i+2}" for i, key in enumerate(update_fields.keys())]
            query = f"UPDATE users SET {', '.join(set_clauses)} WHERE user_id = $1"
            await connection.execute(query, user_id, *update_fields.values())
        else:
            # Naya user, to insert karein
            await connection.execute(
                """
                INSERT INTO users (user_id, name, credits, join_date, user_hash, last_update, last_verified, initial_credits_given, verification_history)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                user_id,
                name,
                credits if credits is not None else 2, # Default 2 credits
                datetime.now().date(),
                user_hash,
                datetime.now(),
                last_verified,
                initial_credits_given if initial_credits_given is not None else True,
                json.dumps([]) # Initial empty history
            )
        
        log_audit_event(user_id, "USER_UPSERT", f"Name: {name}, Credits: {credits}")
        return await get_user(pool, user_id)

async def add_verification_record(pool, user_id, success, details):
    """User ki verification history mein naya record add karein"""
    async with pool.acquire() as connection:
        user = await get_user(pool, user_id)
        if not user:
            return False
            
        history = json.loads(user.get("verification_history", "[]")) if isinstance(user.get("verification_history"), str) else user.get("verification_history", [])
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "details": details
        }
        history.append(record)
        
        # Sirf aakhri 10 records rakhein
        history = history[-10:]
        
        await connection.execute(
            "UPDATE users SET verification_history = $1 WHERE user_id = $2",
            json.dumps(history), user_id
        )
        return True

async def get_admin_stats(pool):
    """Admin ke liye stats fetch karein"""
    async with pool.acquire() as connection:
        stats = await connection.fetchrow("SELECT COUNT(*) as total_users, SUM(credits) as total_credits FROM users")
        return dict(stats) if stats else {"total_users": 0, "total_credits": 0}

# ==== Check Channel Membership ====
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    try:
        member1 = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        member2 = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME_2, user_id=user_id)
        is_member = member1.status != "left" and member2.status != "left"
        log_audit_event(user_id, "MEMBERSHIP_CHECK", f"Channel1: {member1.status}, Channel2: {member2.status}, Result: {is_member}")
        return is_member
    except Exception as e:
        error_msg = f"Error checking membership: {e}"
        print(error_msg)
        log_audit_event(user_id, "MEMBERSHIP_ERROR", error_msg)
        return False

# ==== API Query ====
def query_leakosint(query: str):
    payload = {"token": LEAKOSINT_API_TOKEN, "request": query, "limit": 500, "lang": "en"}
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
            # ... (formatting logic same as before)
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
        pool = context.bot_data["pool"]
        user_data = await get_user(pool, user_id)
    
    if not user_data:
        user_data = {"credits": 0, "last_update": "N/A", "name": "Unknown", "join_date": "N/A"}

    name = user_data.get("name", "Unknown")
    credits = user_data.get("credits", 0)
    last_update = user_data.get("last_update").strftime("%Y-%m-%d %I:%M:%S %p") if user_data.get("last_update") else "N/A"
    join_date = user_data.get("join_date").strftime("%Y-%m-%d") if user_data.get("join_date") else "N/A"
    user_hash = user_data.get("user_hash", generate_user_hash(user_id))
    
    profile_msg = f"""
👤 Nᴀᴍᴇ ▶ {name} 
••••••••••••••••••••••••••
🆔 Usᴇʀ ɪᴅ ▶ {user_id}
••••••••••••••••••••••••••
🆔 Usᴇʀ Hᴀsʜ ▶ {user_hash}
••••••••••••••••••••••••••
💵 Cʀᴇᴅɪᴛ ▶ {credits} 💎
••••••••••••••••••••••••••
📅 Jᴏɪɴᴇᴅ ᴏɴ ▶ {join_date}
••••••••••••••••••••••••••
⌚️ Lᴀsᴛ Uᴘᴅᴀᴛᴇᴅ ▶ {last_update}
••••••••••••••••••••••••••
"""
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
... (buy message content same as before) ...
"""

    keyboard = [
        [InlineKeyboardButton("💬 Cᴏɴᴛᴀᴄᴛ Oᴡɴᴇʀ", url=f"https://t.me/{OWNER_USERNAME[1:]}")],
        [InlineKeyboardButton("🔙 Bᴀᴄᴋ", callback_data="profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(buy_message, reply_markup=reply_markup)

# ==== Fast Animated Spinner ====
async def show_spinner(update, context, message):
    spinner_frames = ["𓆗 •••••••••••••••••••••••••• Dᴏɴᴇ "]
    msg = await message.reply_text(spinner_frames[0])
    await asyncio.sleep(0.5)
    return msg

# ==== Handlers ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    pool = context.bot_data["pool"]
    
    log_audit_event(user_id, "START_COMMAND", f"User: {name}")
    
    user_data = await get_user(pool, user_id)
    is_member = await check_membership(update, context, user_id)
    
    if is_member:
        if not user_data:
            user_data = await upsert_user(pool, user_id, name, credits=2, last_verified=datetime.now(), initial_credits_given=True)
            await add_verification_record(pool, user_id, True, "New user - initial credits granted")
            
            await update.message.reply_text(
                "🍑 Vᴇʀɪꜰɪᴄᴀᴛɪᴏɴ Sᴜᴄᴄᴇꜱꜱꜰᴜʟ! 🎉🎊\n\n"
                "✨ Yᴏᴜ'ᴠᴇ Rᴇᴄᴇɪᴠᴇᴅ  💎 2 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ\n\n"
                "🚀 Use Bot Enter Number Like +91********** Format"
            )
        else:
            user_data = await upsert_user(pool, user_id, name=name)
            await add_verification_record(pool, user_id, True, "Existing user - membership verified")
        
        await show_profile(update, context, user_id, user_data)
    else:
        keyboard = [
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("🔐 ＶＥＲＩＦＹ", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if user_data:
            await add_verification_record(pool, user_id, False, "User not member of required channels")
        
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
    pool = context.bot_data["pool"]
    
    is_member = await check_membership(update, context, user_id)
    user_data = await get_user(pool, user_id)
    
    if is_member:
        if not user_data:
            user_data = await upsert_user(pool, user_id, name, credits=2, last_verified=datetime.now(), initial_credits_given=True)
            await add_verification_record(pool, user_id, True, "New user - initial credits granted via verify")
            
            await query.edit_message_text(
                "🍑 Vᴇʀɪꜰɪᴄᴀᴛɪᴏɴ Sᴜᴄᴄᴇꜱꜱꜱꜰᴜʟ! 🎉🎊\n\n"
                "✨ Yᴏᴜ'ᴠᴇ Rᴇᴄᴇɪᴠᴇᴅ  💎 2 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ\n\n"
                "🚀 Eɴᴊᴏʏ Yᴏᴜʀ Jᴏᴜʀɴᴇʏ Wɪᴛʜ ╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]      "
            )
            await show_profile(update, context, user_id, user_data)
        else:
            user_data = await upsert_user(pool, user_id, name=name, last_verified=datetime.now())
            await add_verification_record(pool, user_id, True, "Existing user - reverified")
            
            await query.edit_message_text(
                "✅ Yᴏᴜ Aʀᴇ Aʟʀᴇᴀᴅʏ ᴀ Mᴇᴍʙᴇʀ Aɴᴅ Hᴀᴠᴇ Aʟʀᴇᴀᴅʏ Rᴇᴄᴇɪᴠᴇᴅ Yᴏᴜʀ Iɴɪᴛɪᴀʟ Cʀᴇᴅɪᴛs.\n\n"
                "🚀 Eɴᴊᴏʏ Yᴏᴜʀ Jᴏᴜʀɴᴇʏ Wɪᴛʜ ╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]      "
            )
            await show_profile(update, context, user_id, user_data)
    else:
        if user_data:
            await add_verification_record(pool, user_id, False, "Verification failed - not member of channels")
        
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
    
    # ... (button handler logic same as before, just needs to call show_profile for 'profile' case)
    if query.data == "profile":
        user_id = update.effective_user.id
        await show_profile(update, context, user_id=user_id, edit_message=True)
    elif query.data == "help":
        # ... help text
        keyboard = [[InlineKeyboardButton("🔙 Bᴀᴄᴋ", callback_data="profile")]]
        await query.edit_message_text("Help text here...", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "search_prompt":
        # ... search prompt text
        keyboard = [[InlineKeyboardButton("🔙 Bᴀᴄᴋ", callback_data="profile")]]
        await query.edit_message_text("Search prompt text here...", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "buy":
        # ... buy message text
        keyboard = [
            [InlineKeyboardButton("💬 Cᴏɴᴛᴀᴄᴛ Oᴡɴᴇʀ", url=f"https://t.me/{OWNER_USERNAME[1:]}")],
            [InlineKeyboardButton("🔙 Bᴀᴄᴋ", callback_data="profile")]
        ]
        await query.edit_message_text("Buy credits text here...", reply_markup=InlineKeyboardMarkup(keyboard))


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pool = context.bot_data["pool"]

    is_member = await check_membership(update, context, user_id)
    if not is_member:
        # ... (membership check logic same as before)
        return

    user_data = await get_user(pool, user_id)
    if not user_data:
        name = update.effective_user.first_name
        user_data = await upsert_user(pool, user_id, name, credits=2, last_verified=datetime.now(), initial_credits_given=True)
        await add_verification_record(pool, user_id, True, "New user - initial credits granted via search")

    if user_data["credits"] <= 0:
        keyboard = [[InlineKeyboardButton("💳 Bᴜʏ Cʀᴇᴅɪᴛꜱ", callback_data="buy")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"❌ Nᴏ Cʀᴇᴅɪᴛ Lᴇꜰᴛ!\n\n💳Bᴜʏ Uɴʟɪᴍɪᴛᴇᴅ 🌀 Cʀᴇᴅɪᴛꜱ & Aᴘɪ⚡Cᴏɴᴛᴀᴄᴛ 👉 {OWNER_USERNAME}", reply_markup=reply_markup)
        return

    spinner_msg = await show_spinner(update, context, update.message)
    query_text = update.message.text
    result = query_leakosint(query_text)
    msg = format_results(result)

    if "Nᴏ Dᴀᴛᴀ" not in msg and "Sᴇʀᴠᴇʀ" not in msg:
        new_credits = user_data["credits"] - 1
        user_data = await upsert_user(pool, user_id, user_data['name'], credits=new_credits)
        log_audit_event(user_id, "SEARCH", f"Query: {query_text}, Success: True, Credits left: {new_credits}")
    else:
        log_audit_event(user_id, "SEARCH", f"Query: {query_text}, Success: False, Credits left: {user_data['credits']}")

    await spinner_msg.delete()
    
    credits_left = user_data["credits"]
    msg += f"\n💵 Cʀᴇᴅɪᴛ : {credits_left} 💎"
    
    keyboard = [[InlineKeyboardButton("💳 Bᴜʏ Cʀᴇᴅɪᴛꜱ", callback_data="buy")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(msg, reply_markup=reply_markup)

async def credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pool = context.bot_data["pool"]
    
    is_member = await check_membership(update, context, user_id)
    if not is_member:
        # ... (membership check logic same as before)
        return
        
    user_data = await get_user(pool, user_id)
    c = user_data.get("credits", 0) if user_data else 0
    await update.message.reply_text(f"💵 Yᴏᴜʀ Cʀᴇᴅɪᴛꜱ: {c} 💎")

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_member = await check_membership(update, context, user_id)
    if not is_member:
        # ... (membership check logic same as before)
        return
        
    await show_profile(update, context, user_id)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pool = context.bot_data["pool"]
    
    if user_id != 7975903577: # Aapki admin user ID
        await update.message.reply_text("❌ Aᴄᴄᴇꜱꜱ Dᴇɴɪᴇᴅ.")
        return
        
    stats = await get_admin_stats(pool)
    stats_msg = f"""
╏╠══[𝍖𝍖𝍖 ＡＤＭＩＮ  𝍖𝍖𝍖]    

👥 Tᴏᴛᴀʟ Usᴇʀs: {stats['total_users']}
💎 Tᴏᴛᴀʟ Cʀᴇᴅɪᴛs: {stats['total_credits'] or 0}
📊 Lᴀsᴛ Uᴘᴅᴀᴛᴇ: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}
"""
    await update.message.reply_text(stats_msg)

# ==== MAIN ====
def main():
    if not BOT_TOKEN:
        print("FATAL: BOT_TOKEN environment variable not set.")
        return
    if not DATABASE_URL:
        print("FATAL: DATABASE_URL environment variable not set.")
        return

    app = Application.builder().token(BOT_TOKEN).post_init(init_db).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("credits", credits))
    app.add_handler(CommandHandler("me", me))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("adminstats", admin_stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify$"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(help|search_prompt|buy|profile)$"))

    print("╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]    ......")
    app.run_polling()

if __name__ == "__main__":
    main()