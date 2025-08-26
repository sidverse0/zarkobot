# -*- coding: utf-8 -*-
import json
import requests
import asyncio
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
BOT_TOKEN = "8116705267:AAGVx7azJJMndrXHwzoMnx7angKd0COJWjg"
CHANNEL_USERNAME = "@chandhackz_78"   # Main channel
CHANNEL_USERNAME_2 = "@cyb3rnothing"  # Second channel
OWNER_USERNAME = "@pvt_s1n"    # Your username

LEAKOSINT_API_TOKEN = "8248142663:8EzDAWZ6"
API_URL = "https://leakosintapi.com/"

USERS_FILE = "users.json"

# ==== User Data Functions ====
def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def update_user(user_id, credits=None, joined=None, name=None):
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"credits": 5, "joined": False, "name": name or "Unknown", "last_update": None}
    if credits is not None:
        users[uid]["credits"] = credits
    if joined is not None:
        users[uid]["joined"] = joined
    if name is not None:
        users[uid]["name"] = name
    users[uid]["last_update"] = datetime.now().strftime("%I:%M:%S %p")
    save_users(users)
    return users[uid]

# ==== Check Channel Membership ====
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    try:
        # Check first channel
        member1 = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        # Check second channel
        member2 = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME_2, user_id=user_id)
        
        return member1.status != "left" and member2.status != "left"
    except Exception as e:
        print(f"Error checking membership: {e}")
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
        return f"⚠️ Sᴇʀᴠᴇʀ Iꜱ Oɴ Mᴀɪɴᴛᴀɪɴᴇɴᴄᴇ: {err}"

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
async def show_profile(update, context, user_id=None, user_data=None):
    if not user_id:
        user_id = update.effective_user.id
        
    if not user_data:
        users = load_users()
        user_data = users.get(str(user_id), {"credits": 0, "last_update": "N/A", "name": "Unknown"})
    
    name = user_data.get("name", "Unknown")
    credits = user_data.get("credits", 0)
    last_update = user_data.get("last_update", "N/A")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Create profile message
    profile_msg = f"""
👤 Nᴀᴍᴇ ▶ {name} 
••••••••••••••••••••••••••
🆔 Usᴇʀ ɪᴅ ▶ {user_id}
••••••••••••••••••••••••••
💵 Cʀᴇᴅɪᴛ ▶ {credits} 💎
••••••••••••••••••••••••••
⌚️ Lᴀsᴛ Uᴘᴅᴀᴛᴇᴅ ▶ {last_update}
••••••••••••••••••••••••••
📆 Dᴀᴛᴇ ▶ {current_date}
"""
    # Create buttons
    keyboard = [
        [InlineKeyboardButton("❓ Help", callback_data="help"),
         InlineKeyboardButton("🔍 Search", callback_data="search_prompt")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'message'):
        await update.message.reply_text(profile_msg, reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text(profile_msg, reply_markup=reply_markup)

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

# ==== Handlers ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    
    # Check if user is already verified
    users = load_users()
    user_data = users.get(str(user_id), {})
    
    # Always check current membership status
    is_member = await check_membership(update, context, user_id)
    
    if is_member and user_data.get("joined", False):
        # User is verified and still in channels, show profile
        await show_profile(update, context, user_id, user_data)
        return
    
    if is_member:
        # User has joined both channels, update status
        user_data = update_user(user_id, credits=5, joined=True, name=name)
        await show_profile(update, context, user_id, user_data)
    else:
        # User hasn't joined both channels, show join buttons
        keyboard = [
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 ＪＯＩＮ", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("🔐 ＶＥＲＩＦＹ", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]      \n\n"
            "✮ 🤖 Tᴏ Uꜱᴇ Tʜɪꜱ Bᴏᴛ Yᴏᴜ Mᴜꜱᴛ:\n\n"
            "✮ 🔗 Jᴏɪɴ Bᴏᴛʜ Oꜰꜰɪᴄɪᴀʟ Cʜᴀɴɴᴇʟ Aʙᴏᴠᴇ\n"
            "✮ 🔐 Cʟɪᴄᴋ Tʜᴇ Vᴇʀɪꜰʏ Bᴜᴛᴛᴏɴ\n\n"
            "✮🎁 Rᴇᴡᴀʀᴅ: Aꜰᴛᴇʀ Vᴇʀɪꜰɪᴄᴀᴛɪᴏɴ  Yᴏᴜ Wɪʟʟ  Iɴꜱᴛᴀɴᴛʟʏ Rᴇᴄᴇɪᴠᴇ\n"
            "✮💎 5 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ\n\n"
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
    
    if is_member:
        # Update user as verified and give credits
        user_data = update_user(user_id, credits=5, joined=True, name=name)
        
        # Show success message and immediately show profile
        await query.edit_message_text(
            "🍑 Vᴇʀɪꜰɪᴄᴀᴛɪᴏɴ Sᴜᴄᴄᴇꜱꜱꜰᴜʟ! 🎉🎊\n\n"
            "✨ Yᴏᴜ'ᴠᴇ Rᴇᴄᴇɪᴠᴇᴅ  💎 5 Fʀᴇᴇ Cʀᴇᴅɪᴛꜱ\n\n"
            "🚀 Eɴᴊᴏʏ Yᴏᴜʀ Jᴏᴜʀɴᴇʏ Wɪᴛʜ ╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]      "
        )
        await show_profile(update, context, user_id, user_data)
    else:
        # User hasn't joined both channels
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
            "🔁 Tʜᴇɴ Cʟɪᴄᴋ Cʜᴇᴄᴋ🔘\n\n"
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
✯ 📧 *Eᴍᴀɪʟ Sᴇᴀʀᴄʜ* – Sᴇɴᴅ Eᴍᴀɪʟ Lɪᴋᴇ  `example@gmail.com`
✯ 👤 *Nᴀᴍᴇ Sᴇᴀʀᴄʜ* – Jᴜꜱᴛ Sᴇɴᴅ Tʜᴇ Nᴀᴍᴇ
↣↣↣↣↣↣↣↣↣↣
📂 I Wɪʟʟ Sᴄᴀɴ Aᴄʀᴏꜱꜱ Mᴜʟᴛɪᴘʟᴇ Dᴀᴛᴀʙᴀꜱᴇꜱ 🗂️
━━━━━━━━━━━━━━━━━━━━━
☛ *Nᴏᴛᴇ:* Eᴀᴄʜ Sᴇᴀʀᴄʜ Cᴏꜱᴛꜱ 💎 1 Cʀᴇᴅɪᴛ
"""
        await query.edit_message_text(help_text, parse_mode="Markdown")
        
    elif query.data == "search_prompt":
        search_prompt_text = """╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]    

🔍 *Wʜᴀᴛ Cᴀɴ ɪ Dᴏ?*

☛ 📱 *Pʜᴏɴᴇ Nᴜᴍʙᴇ Sᴇᴀʀᴄʜ* – Sᴇɴᴅ Nᴏ. Lɪᴋᴇ  `91XXXXXXXXXX`
↣↣↣↣↣↣↣↣↣↣
☛ 📧 *Eᴍᴀɪʟ Sᴇᴀʀᴄʜ* – Sᴇɴᴅ Eᴍᴀɪʟ Lɪᴋᴇ  `example@gmail.com`
↣↣↣↣↣↣↣↣↣↣
☛ 👤 *Nᴀᴍᴇ Sᴇᴀʀᴄʜ* – Jᴜꜱᴛ Sᴇɴᴅ Tʜᴇ Nᴀᴍᴇ
↣↣↣↣↣↣↣↣↣↣
📂 I Wɪʟʟ Sᴄᴀɴ Aᴄʀᴏꜱꜱ Mᴜʟᴛɪᴘʟᴇ Dᴀᴛᴀʙᴀꜱᴇꜱ 🗂️
━━━━━━━━━━━━━━━━━━━━━
⚠️ *Nᴏᴛᴇ:* Eᴀᴄʜ Sᴇᴀʀᴄʜ Cᴏꜱᴛꜱ 💎 1 Cʀᴇᴅɪᴛ
"""
        await query.edit_message_text(search_prompt_text, parse_mode="Markdown")
        
    elif query.data == "buy":
        await query.edit_message_text(f"💳Bᴜʏ Uɴʟɪᴍɪᴛᴇᴅ Cʀᴇᴅɪᴛꜱ & Aᴘɪ⚡Cᴏɴᴛᴀᴄᴛ 👉 {OWNER_USERNAME}")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users = load_users()

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

    if str(user_id) not in users or not users[str(user_id)]["joined"]:
        # Update user as verified since they are in channels
        name = update.effective_user.first_name
        update_user(user_id, credits=5, joined=True, name=name)
        users = load_users()  # Reload users after update

    if users[str(user_id)]["credits"] <= 0:
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
        users[str(user_id)]["credits"] -= 1
        users[str(user_id)]["last_update"] = datetime.now().strftime("%I:%M:%S %p")
        save_users(users)

    # Delete spinner message
    await spinner_msg.delete()

    # Add credits info and deposit button
    credits_left = users[str(user_id)]["credits"]
    msg += f"\n💵 Cʀᴇᴅɪᴛ : {credits_left} 💎"
    
    keyboard = [[InlineKeyboardButton("💳 Bᴜʏ Cʀᴇᴅɪᴛꜱ", callback_data="buy")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(msg, reply_markup=reply_markup)

async def credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users = load_users()
    
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
        
    c = users.get(str(user_id), {}).get("credits", 0)
    await update.message.reply_text(f"💵 Yᴏᴜʀ Cʀᴇᴅɪᴛꜱ: {c} 💎")

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
    users = load_users()
    user_data = users.get(str(user_id), {"credits": 0, "last_update": "N/A", "name": "Unknown"})
    await show_profile(update, context, user_id, user_data)

# ==== MAIN ====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("credits", credits))
    app.add_handler(CommandHandler("me", me))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify$"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(help|search_prompt|buy)$"))

    print("╏╠══[𝍖𝍖𝍖Ｚᴀʀᴋᴏ 𓆗 Ｏꜱɪɴᴛ 𝍖𝍖𝍖]    ......")
    app.run_polling()

if __name__ == "__main__":
    main()