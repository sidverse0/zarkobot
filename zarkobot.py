# -*- coding: utf-8 -*-
import json
import requests
import asyncio
import hashlib
import random
import string
import re
import os
import qrcode
import io
import time
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask
from threading import Thread
import logging

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==== Flask Server for Render ====
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=5000)

# Start Flask server in a thread
Thread(target=run_flask, daemon=True).start()

# ==== Firebase Initialization ====
try:
    firebase_cred = credentials.Certificate(json.loads(os.environ['FIREBASE_CREDENTIALS']))
    firebase_admin.initialize_app(firebase_cred)
    db = firestore.client()
    print("Firebase initialized successfully")
except Exception as e:
    print(f"Firebase initialization error: {e}")
    db = None

# ==== CONFIG ====
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8116705267:AAFE_JuESoq6i8mRvj7b8VX-3vSxjPtO0Xw")
CHANNEL_USERNAME = "@zarkoworld"
CHANNEL_USERNAME_2 = "@chandhackz_78"
OWNER_USERNAME = "@pvt_s1n"
ADMIN_ID = 7975903577
UPI_ID = "reyazmbi2003@okaxis"

LEAKOSINT_API_TOKEN = os.environ.get('LEAKOSINT_API_TOKEN', "8250754854:64fCZifF")
API_URL = "https://leakosintapi.com/"

# Bot status
BOT_STOPPED = False

# Image URLs
START_IMAGE_URL = "https://files.catbox.moe/ppjby2.jpg"
HELP_IMAGE_URL = "https://files.catbox.moe/pajxmc.png"
SEARCH_IMAGE_URL = "https://files.catbox.moe/6bwo6k.png"
CREDITS_IMAGE_URL = "https://files.catbox.moe/b9ww9u.png"
PROFILE_IMAGE_URL = "https://files.catbox.moe/wf5q79.png"
BUY_IMAGE_URL = "https://files.catbox.moe/5d0xs0.png"
VERIFY_IMAGE_URL = "https://files.catbox.moe/pvqg1l.png"
ADMIN_IMAGE_URL = "https://files.catbox.moe/kh5d20.png"
REFER_IMAGE_URL = "https://files.catbox.moe/oatkv3.png"
GIFT_IMAGE_URL = "https://files.catbox.moe/ytbj2s.png"
BANNED_IMAGE_URL = "https://files.catbox.moe/2c88t0.png"
LOCKED_IMAGE_URL = "https://files.catbox.moe/ll5vrz.png"
PAYMENT_IMAGE_URL = "https://files.catbox.moe/b6hyv7.png"
STOPPED_IMAGE_URL = "https://files.catbox.moe/86ccxo.png"
WAITING_IMAGE_URL = "https://files.catbox.moe/86ccxo.png"  # Add a waiting image URL

# Constants for messages
HELP_TEXT = """[𝍖𝍖𝍖🚨 𝐇ᴇʟᴘ 🚨𝍖𝍖𝍖]

☞📱 𝐏ʜᴏɴᴇ 𝐍ᴜᴍʙᴇʀ - 𝐒ᴇᴀʀᴄʜ 𝐍ᴏ. 𝐋ɪᴋᴇ 91XXXXXXXXXX & 79XXXXXX68

☞📧 𝐄ᴍᴀɪʟ - 𝐒ᴇᴀʀᴄʜ 𝐄ᴍᴀɪʟ 𝐋ɪᴋᴇ example@gmail.com

☞👤 𝐍ᴀᴍᴇ - 𝐒ᴇᴀʀᴄʜ 𝐀ɴʏ 𝐍ᴀᴍᴇ

🌏 𝐈 𝐒ᴇᴀʀᴄʜ 𝐀ᴄʀᴏss 𝐌ᴜʟᴛɪᴘʟᴇ 𝐃ᴀᴛᴀʙᴀsᴇs 📂
────────────────────
➛ 𝐄ᴀᴄʜ 𝐒ᴇᴀʀᴄʜ 𝐂ᴏsᴛ 1 𝐂ʀᴇᴅɪᴛ 💎
➛ 𝐈ғ 𝐀ɴʏ 𝐐ᴜᴇʀʏ 𝐂ᴏɴᴛᴀᴄᴛ 𝐎ᴡɴᴇʀ ☎️ @Pvt_s1n
"""

SEARCH_PROMPT_TEXT = """[𝍖𝍖𝍖🎯 𝐒ᴇᴀʀᴄʜ 🎯 𝍖𝍖𝍖]
 ━━━━━━━━━━━━━━━━━━━━      

✮📱 𝐏ʜᴏɴᴇ 𝐍ᴜᴍʙᴇʀ - 𝐒ᴇᴀʀᴄʜ 𝐍ᴏ. 𝐋ɪᴋᴇ 91XXXXXXXXXX & 79XXXXXX68

✮📧 𝐄ᴍᴀɪʙ - 𝐒ᴇᴀʀᴄʜ 𝐄ᴍᴀɪʟ 𝐋ɪᴋᴇ example@gmail.com

✮👤 𝐍ᴀᴍᴇ - 𝐒ᴇᴀʀᴄʜ �𝐴ɴʏ 𝐍ᴀᴍᴇ

🌏 𝐈 𝐒ᴇᴀʀᴄʜ �𝐴ᴄʀᴏss 𝐌ᴜʟᴛɪᴘʟᴇ 𝐃ᴀᴛᴀʙᴀsᴇs 📂
────────────────────
➛ 𝐄ᴀᴄʜ 𝐒ᴇᴀʀᴄʜ 𝐂ᴏsᴛ 1 𝐂ʀᴇᴅɪᴛ 💎 
➛ 𝐈ғ 𝐀ɴʏ 𝐐ᴜᴇʀʏ 𝐂ᴏɴᴛᴀᴄᴛ 𝐎ᴡɴᴇʀ ☎️ @Pvt_s1n
"""

# Payment packages
PAYMENT_PACKAGES = {
    "10": {"credits": 100, "amount": 10},
    "20": {"credits": 200, "amount": 20},
    "30": {"credits": 300, "amount": 30},
    "40": {"credits": 400, "amount": 40},
    "50": {"credits": 500, "amount": 50},
    "100": {"credits": 1000, "amount": 100},
    "200": {"credits": 2000, "amount": 200},
    "500": {"credits": 5000, "amount": 500}
}

# ==== Firebase Data Functions ====
def load_users():
    if db is None:
        return {}
    try:
        users_ref = db.collection('users')
        docs = users_ref.stream()
        users = {}
        for doc in docs:
            users[doc.id] = doc.to_dict()
        return users
    except Exception as e:
        print(f"Error loading users from Firebase: {e}")
        return {}

def save_users(users):
    if db is None:
        return
    try:
        for user_id, user_data in users.items():
            db.collection('users').document(str(user_id)).set(user_data)
    except Exception as e:
        print(f"Error saving users to Firebase: {e}")

def load_banned_users():
    if db is None:
        return {}
    try:
        banned_ref = db.collection('banned_users')
        docs = banned_ref.stream()
        banned_users = {}
        for doc in docs:
            banned_users[doc.id] = doc.to_dict()
        return banned_users
    except Exception as e:
        print(f"Error loading banned users from Firebase: {e}")
        return {}

def save_banned_users(banned_users):
    if db is None:
        return
    try:
        for user_id, ban_data in banned_users.items():
            db.collection('banned_users').document(str(user_id)).set(ban_data)
    except Exception as e:
        print(f"Error saving banned users to Firebase: {e}")

def load_locked_features():
    if db is None:
        return {"phone": False, "email": False, "name": False}
    try:
        locked_ref = db.collection('settings').document('locked_features')
        doc = locked_ref.get()
        if doc.exists:
            return doc.to_dict()
        return {"phone": False, "email": False, "name": False}
    except Exception as e:
        print(f"Error loading locked features from Firebase: {e}")
        return {"phone": False, "email": False, "name": False}

def save_locked_features(locked_features):
    if db is None:
        return
    try:
        db.collection('settings').document('locked_features').set(locked_features)
    except Exception as e:
        print(f"Error saving locked features to Firebase: {e}")

def load_payment_requests():
    if db is None:
        return {}
    try:
        requests_ref = db.collection('payment_requests')
        docs = requests_ref.stream()
        payment_requests = {}
        for doc in docs:
            payment_requests[doc.id] = doc.to_dict()
        return payment_requests
    except Exception as e:
        print(f"Error loading payment requests from Firebase: {e}")
        return {}

def save_payment_requests(payment_requests):
    if db is None:
        return
    try:
        for req_id, req_data in payment_requests.items():
            db.collection('payment_requests').document(req_id).set(req_data)
    except Exception as e:
        print(f"Error saving payment requests to Firebase: {e}")

def load_bot_status():
    if db is None:
        return {"stopped": False}
    try:
        status_ref = db.collection('settings').document('bot_status')
        doc = status_ref.get()
        if doc.exists:
            return doc.to_dict()
        return {"stopped": False}
    except Exception as e:
        print(f"Error loading bot status from Firebase: {e}")
        return {"stopped": False}

def save_bot_status(status):
    if db is None:
        return
    try:
        db.collection('settings').document('bot_status').set(status)
    except Exception as e:
        print(f"Error saving bot status to Firebase: {e}")

def update_user(user_id, credits=None, name=None, last_verified=None, initial_credits_given=None, referred_by=None):
    users = load_users()
    uid = str(user_id)
    
    if uid not in users:
        users[uid] = {
            "credits": 0,
            "name": name or "Unknown", 
            "last_update": datetime.now().strftime("%d/%m - %I:%M %p"),
            "initial_credits_given": False,
            "join_date": datetime.now().strftime("%Y-%m-%d"),
            "user_hash": generate_user_hash(user_id),
            "referral_code": generate_referral_code(user_id),
            "referrals": 0,
            "referral_credits": 0,
            "referred_by": referred_by,
            "verification_history": [],
            "last_verified": None,
            "last_verification_check": None,
            "claimed_gift_codes": [],
            "banned": False,
            "ban_reason": None
        }
    
    if credits is not None:
        users[uid]["credits"] = credits
    if name is not None:
        users[uid]["name"] = name
    if last_verified is not None:
        users[uid]["last_verified"] = last_verified
    if initial_credits_given is not None:
        users[uid]["initial_credits_given"] = initial_credits_given
    if referred_by is not None and "referred_by" not in users[uid]:
        users[uid]["referred_by"] = referred_by
    
    users[uid]["last_update"] = datetime.now().strftime("%d/%m - %I:%M %p")
    save_users(users)
    
    log_audit_event(user_id, "USER_UPDATE", f"Credits: {users[uid]['credits']}, Name: {users[uid]['name']}")
    
    return users[uid]

def load_gift_codes():
    if db is None:
        return {}
    try:
        gift_ref = db.collection('gift_codes').document('active_codes')
        doc = gift_ref.get()
        if doc.exists:
            return doc.to_dict()
        return {}
    except Exception as e:
        print(f"Error loading gift codes from Firebase: {e}")
        return {}

def save_gift_codes(gift_codes):
    if db is None:
        return
    try:
        db.collection('gift_codes').document('active_codes').set(gift_codes)
    except Exception as e:
        print(f"Error saving gift codes to Firebase: {e}")

def log_audit_event(user_id, event_type, details):
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
        if db is not None:
            db.collection('audit_logs').add(log_entry)
        else:
            with open("audit.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Audit log error: {e}")

# ==== Reply Keyboard Setup ====
def get_main_keyboard():
    keyboard = [
        ["🔍 𝐒ᴇᴀʀᴄʜ", "💎 𝐂ʀᴇᴅɪᴛs", "🎁 𝐆ɪғᴛ 𝐂ᴏᴅᴇ"],
        ["🎖️ 𝐏ʀᴏғɪʟᴇ", "🛍️ 𝐒ʜᴏᴘ", "💠 𝐑ᴇғᴇʀ"],
        ["☎️ 𝐇ᴇʟᴘ", "🧧 𝐀ᴅᴍɪɴ"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, input_field_placeholder="Choose Options")

def get_admin_keyboard():
    keyboard = [
        ["🃏 𝐀ᴅᴅ 𝐂ʀᴇᴅɪᴛs", "💶 𝐒ᴇᴛ 𝐂ʀᴇᴅɪᴛs", "🏅 𝐔sᴇʀ 𝐈ɴғᴏ"],
        ["📮 𝐁ʀᴏᴀᴅᴄᴀsᴛ", "🎁 𝐆ᴇɴᴇʀᴀᴛᴇ 𝐆ɪғᴛ", "💰 𝐏ᴀʏᴍᴇɴᴛ 𝐑ᴇǫᴜᴇsᴛs"],
        ["🔒 𝐋ᴏᴄᴋ 𝐅ᴇᴀᴛᴜʀᴇs", "🔓 𝐔ɴʟᴏᴄᴋ 𝐅ᴇᴀᴛᴜʀᴇs", "🚫 𝐁ᴀɴ 𝐔sᴇʀ"],
        ["🟢 𝐒ᴛᴀʀᴛ 𝐁ᴏᴛ", "🔴 𝐒ᴛᴏᴩ 𝐁ᴏᴛ", "🎲 𝐌ᴀɪɴ 𝐌ᴇɴᴜ"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, input_field_placeholder="Admin Panel")

def get_banned_keyboard():
    keyboard = [[InlineKeyboardButton("☎️ 𝐂ᴏɴᴛᴀᴄᴛ 𝐎ᴡɴᴇʀ", url=f"https://t.me/{OWNER_USERNAME[1:]}")]]
    return InlineKeyboardMarkup(keyboard)

# ==== Gift Code Functions ====
def generate_gift_code(length=12):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def create_gift_code(amount, name, created_by):
    gift_codes = load_gift_codes()
    
    while True:
        code = generate_gift_code()
        if code not in gift_codes:
            break
    
    gift_codes[code] = {
        "amount": amount,
        "name": name,
        "created_by": created_by,
        "created_at": datetime.now().isoformat(),
        "claimed_by": None,
        "claimed_at": None
    }
    
    save_gift_codes(gift_codes)
    return code

def claim_gift_code(code, user_id, user_name):
    gift_codes = load_gift_codes()
    
    if code not in gift_codes:
        return False, "Invalid gift code"
    
    gift = gift_codes[code]
    
    if gift["claimed_by"] is not None:
        return False, "Gift code already claimed"
    
    gift["claimed_by"] = user_id
    gift["claimed_by_name"] = user_name
    gift["claimed_at"] = datetime.now().isoformat()
    
    save_gift_codes(gift_codes)
    return True, gift["amount"]

# ==== Phone Number Normalization Function ====
def normalize_phone_number(query):
    cleaned = re.sub(r'[^\d+]', '', query)
    
    if re.fullmatch(r'[\d+]+', cleaned):
        digits_only = re.sub(r'[^\d]', '', cleaned)
        
        if len(digits_only) == 10:
            return "91" + digits_only
        elif len(digits_only) == 11 and digits_only.startswith('0'):
            return "91" + digits_only[1:]
        elif len(digits_only) == 12 and digits_only.startswith('91'):
            return digits_only
        elif len(digits_only) > 12:
            return digits_only[:12]
        else:
            return digits_only
    else:
        return query

# ==== Query Optimization Functions ====
def optimize_name_query(name):
    name = re.sub(r'[^\w\s]', '', name.strip())
    
    words = name.split()
    if len(words) > 3:
        return " ".join(words[:3])
    return name

def optimize_email_query(email):
    email = email.strip().lower()
    return email

# ==== Security Functions ====
def generate_user_hash(user_id):
    random.seed(user_id)
    characters = string.ascii_uppercase + string.digits
    return ''.join([random.choice(characters) for _ in range(6)])

def generate_referral_code(user_id):
    random.seed(user_id)
    characters = string.ascii_uppercase + string.digits
    return ''.join([random.choice(characters) for _ in range(8)])

def add_referral_credits(referrer_id):
    users = load_users()
    ruid = str(referrer_id)
    
    if ruid in users:
        users[ruid]["referrals"] = users[ruid].get("referrals", 0) + 1
        users[ruid]["referral_credits"] = users[ruid].get("referral_credits", 0) + 2
        users[ruid]["credits"] = users[ruid].get("credits", 0) + 2
        save_users(users)
        
        log_audit_event(referrer_id, "REFERRAL_CREDITS", f"Added 2 credits for referral. Total referrals: {users[ruid]['referrals']}")
        return True
    return False

def add_verification_record(user_id, success, details):
    users = load_users()
    uid = str(user_id)
    
    if uid not in users:
        return False
    
    record = {
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "details": details
    }
    
    if "verification_history" not in users[uid]:
        users[uid]["verification_history"] = []
    
    users[uid]["verification_history"].append(record)
    
    if len(users[uid]["verification_history"]) > 10:
        users[uid]["verification_history"] = users[uid]["verification_history"][-10:]
    
    save_users(users)
    return True

# ==== Check if user is banned ====
def is_user_banned(user_id):
    banned_users = load_banned_users()
    return str(user_id) in banned_users

# ==== Check if bot is stopped ====
def is_bot_stopped():
    global BOT_STOPPED
    status = load_bot_status()
    BOT_STOPPED = status.get("stopped", False)
    return BOT_STOPPED

# ==== Check Channel Membership ====
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    try:
        if is_user_banned(user_id):
            return False
            
        member1 = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        member2 = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME_2, user_id=user_id)
        
        is_member = member1.status != "left" and member2.status != "left"
        
        log_audit_event(user_id, "MEMBERSHIP_CHECK", 
                       f"Channel1: {member1.status}, Channel2: {member2.status}, Result: {is_member}")
        
        return is_member
    except Exception as e:
        error_msg = f"Error checking membership: {e}"
        print(error_msg)
        log_audit_event(user_id, "MEMBERSHIP_ERROR", error_msg)
        return False

# ==== Force Membership Check ====
async def force_membership_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if bot is stopped
    if is_bot_stopped() and user_id != ADMIN_ID:
        await update.message.reply_photo(
            photo=STOPPED_IMAGE_URL,
            caption="🚫 Bot is currently stopped for maintenance.\n\nServer request is high. Please try again later.\n\nContact owner for more information.",
            reply_markup=get_banned_keyboard()
        )
        return False
    
    # Check if user is banned
    if is_user_banned(user_id):
        banned_users = load_banned_users()
        ban_data = banned_users.get(str(user_id), {})
        ban_reason = ban_data.get("reason", "No reason provided")
        
        await update.message.reply_photo(
            photo=BANNED_IMAGE_URL,
            caption=f"🚫 You have been banned from using this bot.\n\nReason: {ban_reason}\n\nContact owner for more information: {OWNER_USERNAME}",
            reply_markup=get_banned_keyboard()
        )
        return False
    
    is_member = await check_membership(update, context, user_id)
    
    if not is_member:
        keyboard = [
            [InlineKeyboardButton("🎲 𝐉ᴏɪɴ", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("🎲 𝐉ᴏɪɴ", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("🟢 𝐕ᴇʀɪғʏ", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if hasattr(update, 'callback_query') and update.callback_query:
            try:
                await update.callback_query.message.reply_photo(
                    photo=VERIFY_IMAGE_URL,
                    caption="🔒 You Must Join Both Channels And Verify To Use This Bot",
                    reply_markup=reply_markup
                )
            except Exception as e:
                print(f"Error sending verification message: {e}")
                await update.callback_query.message.reply_text(
                    "🔒 You Must Join Both Channels And Verify To Use This Bot",
                    reply_markup=reply_markup
                )
        else:
            try:
                await update.message.reply_photo(
                    photo=VERIFY_IMAGE_URL,
                    caption="🔒 You Must Join Both Channels And Verify To Use This Bot",
                    reply_markup=reply_markup
                )
            except Exception as e:
                print(f"Error sending verification message: {e}")
                await update.message.reply_text(
                    "🔒 You Must Join Both Channels And Verify To Use This Bot",
                    reply_markup=reply_markup
                )
        return False
    return True

# ==== API Query ====
def query_leakosint(query: str):
    normalized_query = normalize_phone_number(query)
    
    if not re.match(r'^[\d+]+$', query):
        if '@' in query:
            optimized_query = optimize_email_query(query)
        else:
            optimized_query = optimize_name_query(query)
        
        results = {}
        
        payload = {
            "token": LEAKOSINT_API_TOKEN,
            "request": optimized_query,
            "limit": 500,
            "lang": "en"
        }
        
        try:
            resp = requests.post(API_URL, json=payload, timeout=30)
            results["optimized"] = resp.json()
        except Exception as e:
            results["optimized"] = {"Error": str(e)}
        
        if optimized_query != query:
            payload = {
                "token": LEAKOSINT_API_TOKEN,
                "request": query,
                "limit": 500,
                "lang": "en"
            }
            
            try:
                resp = requests.post(API_URL, json=payload, timeout=30)
                results["original"] = resp.json()
            except Exception as e:
                results["original"] = {"Error": str(e)}
            
            if "List" in results.get("optimized", {}) and "List" in results.get("original", {}):
                combined_result = {"List": {}}
                
                for source in ["optimized", "original"]:
                    for db, data in results[source].get("List", {}).items():
                        if db not in combined_result["List"]:
                            combined_result["List"][db] = data
                        else:
                            combined_result["List"][db]["Data"].extend(data["Data"])
                
                return combined_result
            
            if "List" in results.get("optimized", {}):
                return results["optimized"]
            elif "List" in results.get("original", {}):
                return results["original"]
            else:
                return {"Error": "No data found"}
        
        return results.get("optimized", {})
    
    else:
        payload = {
            "token": LEAKOSINT_API_TOKEN,
            "request": normalized_query,
            "limit": 500,
            "lang": "en"
        }
        try:
            resp = requests.post(API_URL, json=payload, timeout=30)
            return resp.json()
        except Exception as e:
            return {"Error": str(e)}

# ==== Format Result ====
def format_results(resp, max_length=4000):
    if "Error" in resp or "Error code" in resp:
        err = resp.get("Error") or resp.get("Error code")
        return ["⚠️ Server Is Under Construction"]

    results = []
    current_result = ""
    results_count = 0
    seen_entries = set()
    
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
            email = row.get("Email", "N/A")
            
            entry_id = f"{name}|{father}|{mobile}|{doc}|{email}"
            
            if entry_id in seen_entries:
                continue
            seen_entries.add(entry_id)
            
            all_fields_empty = True
            for field in [name, father, mobile, alt1, alt2, alt3, alt4, alt5, doc, email]:
                if field != "N/A" and field.strip() != "":
                    all_fields_empty = False
                    break
            
            if all_fields_empty:
                continue

            result_entry = f"""
👤 Name ➜ {name}
👨 Father's Name ➜ {father}
📞 Mobile ➜ {mobile}
📱 Alt Number1 ➜ {alt1}
📱 Alt Number2 ➜ {alt2}
📱 Alt Number3 ➜ {alt3}
📱 Alt Number4 ➜ {alt4}
📱 Alt Number5 ➜ {alt5}
📧 Email ➜ {email}
🆔 Aadhar ID ➜ {doc}
📍 City ➜ {region}
🏠 Address ➜ {address}
────────────────────
"""
            
            if len(current_result) + len(result_entry) > max_length:
                if current_result:
                    results.append(current_result)
                current_result = result_entry
            else:
                current_result += result_entry
                
            results_count += 1

    if results_count == 0:
        return ["❌ No Data Available In Database 👉"]
    
    if current_result:
        results.append(current_result)
    
    return results

# ==== Show Profile Function ====
async def show_profile(update, context, user_id=None, user_data=None, edit_message=False):
    if not user_id:
        user_id = update.effective_user.id
        
    if not user_data:
        users = load_users()
        user_data = users.get(str(user_id), {"credits": 0, "last_update": "N/A", "name": "Unknown"})
    
    name = user_data.get("name", "Unknown")
    credits = user_data.get("credits", 0)
    last_update = user_data.get("last_update", "N/A")
    join_date = user_data.get("join_date", "N/A")
    user_hash = user_data.get("user_hash", generate_user_hash(user_id))
    
    if join_date != "N/A":
        try:
            dt = datetime.strptime(join_date, "%Y-%m-%d")
            join_date_display = dt.strftime("%d/%m/%Y")
        except:
            join_date_display = join_date
    else:
        join_date_display = "N/A"

    profile_msg = f"""
👤 Name ➜ {name} 
────────────────────
🆔 User ID ➜ {user_id}
────────────────────
🔐 User Code ➜ {user_hash}
────────────────────
🪙 Credit ➜ {credits} 🪙
────────────────────
📅 Joined ➜ {join_date_display}
────────────────────
🔄 Updated ➜ {last_update}
────────────────────
"""

    if edit_message and hasattr(update, 'callback_query'):
        await update.callback_query.edit_message_text(profile_msg)
    elif hasattr(update, 'message'):
        await update.message.reply_photo(
            photo=PROFILE_IMAGE_URL, 
            caption=profile_msg
        )
    else:
        await update.callback_query.message.reply_photo(
            photo=PROFILE_IMAGE_URL, 
            caption=profile_msg
        )

# ==== Referral Function ====
async def show_referral_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await force_membership_check(update, context):
        return
        
    users = load_users()
    uid = str(user_id)
    
    if uid not in users:
        await update.message.reply_text("❌ User not found. Please use /start first.")
        return
        
    user_data = users[uid]
    referral_code = user_data.get("referral_code", generate_referral_code(user_id))
    referrals = user_data.get("referrals", 0)
    referral_credits = user_data.get("referral_credits", 0)
    
    bot_username = context.bot.username
    referral_link = f"https://t.me/{bot_username}?start={referral_code}"
    
    referral_msg = f"""
🤝 [ REFER & EARN ] 🤝
────────────────────

🔗 Your Referral Link:
{referral_link}

📊 Your Referral Stats:
👥 Total Referrals ➜ {referrals}
🎁 Total Credits Earned ➜ {referral_credits} 🪙

💰 Referral Rewards:
- For each successful referral, you get 2 🪙 credits
- Your friend gets 2 🪙 bonus credits too!

⚡ How It Works:
1. Share your referral link with friends
2. When they join using your link
3. Both of you get 2 🪙 credits each
4. Credits are added after they verify

────────────────────
Note: Fake referrals or self-referrals are strictly prohibited and will result in account ban.
"""

    await update.message.reply_photo(
        photo=REFER_IMAGE_URL, 
        caption=referral_msg
    )

# ==== Generate QR Code Function ====
def generate_qr_code(amount, upi_id=UPI_ID):
    upi_url = f"upi://pay?pa={upi_id}&pn=Bot Owner&am={amount}&cu=INR"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return img_byte_arr

# ==== Payment Request Functions ====
def create_payment_request(user_id, amount, credits):
    payment_requests = load_payment_requests()
    
    # Generate 6-digit request ID
    request_id = str(random.randint(100000, 999999))
    
    users = load_users()
    user_name = users.get(str(user_id), {}).get("name", "Unknown")
    
    payment_requests[request_id] = {
        "user_id": user_id,
        "user_name": user_name,
        "amount": amount,
        "credits": credits,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    save_payment_requests(payment_requests)
    return request_id

def update_payment_request(request_id, status, admin_notes=None):
    payment_requests = load_payment_requests()
    
    if request_id in payment_requests:
        payment_requests[request_id]["status"] = status
        payment_requests[request_id]["updated_at"] = datetime.now().isoformat()
        
        if admin_notes:
            payment_requests[request_id]["admin_notes"] = admin_notes
        
        save_payment_requests(payment_requests)
        return True
    return False

# ==== Buy Command Function ====
async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await force_membership_check(update, context):
        return
        
    keyboard = []
    row = []
    
    for i, (amount, details) in enumerate(PAYMENT_PACKAGES.items()):
        row.append(InlineKeyboardButton(f"₹{amount} - {details['credits']}🪙", callback_data=f"buy_{amount}"))
        
        if (i + 1) % 2 == 0:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    buy_message = """
💳 [ BUY CREDITS ] 💳
────────────────────

Choose a payment package:

💰 Payment Options:
- 10 Rs = 100 Credits
- 20 Rs = 200 Credits
- 30 Rs = 300 Credits
- 40 Rs = 400 Credits
- 50 Rs = 500 Credits
- 100 Rs = 1000 Credits
- 200 Rs = 2000 Credits
- 500 Rs = 5000 Credits

📝 How to purchase:
1. Select a package
2. Pay via UPI using the QR code
3. Click "I've Paid" after payment
4. Wait for admin approval

────────────────────
Note: Payments are manually verified by admin. Please be patient.
"""

    await update.message.reply_photo(
        photo=BUY_IMAGE_URL, 
        caption=buy_message,
        reply_markup=reply_markup
    )

# ==== Handle Buy Package Selection ====
async def handle_buy_package(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if not await force_membership_check(update, context):
        return
    
    amount = query.data.split("_")[1]
    
    if amount not in PAYMENT_PACKAGES:
        await query.edit_message_text("❌ Invalid package selected.")
        return
    
    package = PAYMENT_PACKAGES[amount]
    
    # Generate QR code
    qr_img = generate_qr_code(package["amount"])
    
    # Create payment request
    request_id = create_payment_request(user_id, package["amount"], package["credits"])
    
    keyboard = [
        [InlineKeyboardButton("✅ I've Paid", callback_data=f"paid_{request_id}")],
        [InlineKeyboardButton("📞 Contact Owner", url=f"https://t.me/{OWNER_USERNAME[1:]}")],
        [InlineKeyboardButton("🔙 Back to Packages", callback_data="back_to_packages")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    caption = f"""
💳 Payment Details:
────────────────────
Amount: ₹{package['amount']}
Credits: {package['credits']} 🪙
UPI ID: {UPI_ID}
Request ID: {request_id}

📸 Scan the QR code to pay or send money directly to the UPI ID.

After payment, click "I've Paid" to notify admin.
"""

    # Send the QR code as a photo with caption
    await query.message.reply_photo(
        photo=qr_img,
        caption=caption,
        reply_markup=reply_markup
    )

# ==== Handle Payment Confirmation ====
async def handle_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    request_id = query.data.split("_")[1]
    
    payment_requests = load_payment_requests()
    
    if request_id not in payment_requests:
        await query.edit_message_text("❌ Payment request not found.")
        return
    
    payment_request = payment_requests[request_id]
    
    if payment_request["user_id"] != user_id:
        await query.edit_message_text("❌ This is not your payment request.")
        return
    
    # Update payment request status to under review
    update_payment_request(request_id, "under_review")
    
    # Show waiting message to user
    await query.message.reply_photo(
        photo=WAITING_IMAGE_URL,
        caption="⏳ Your payment is under review. Admin will approve it shortly."
    )
    
    # Notify admin
    admin_message = f"""
💰 New Payment Request:
────────────────────
User: {payment_request['user_name']} (ID: {user_id})
Amount: ₹{payment_request['amount']}
Credits: {payment_request['credits']} 🪙
Request ID: {request_id}
Status: Under Review

Click below to approve or reject:
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{request_id}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"reject_{request_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Error notifying admin: {e}")

# ==== Handle Admin Payment Approval ====
async def handle_admin_payment_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await query.edit_message_text("❌ Admin only.")
        return
    
    data_parts = query.data.split("_")
    action = data_parts[0]
    request_id = data_parts[1]
    
    payment_requests = load_payment_requests()
    
    if request_id not in payment_requests:
        await query.edit_message_text("❌ Payment request not found.")
        return
    
    payment_request = payment_requests[request_id]
    target_user_id = payment_request["user_id"]
    
    if action == "approve":
        # Add credits to user
        users = load_users()
        uid = str(target_user_id)
        
        if uid not in users:
            await query.edit_message_text("❌ User not found.")
            return
        
        users[uid]["credits"] += payment_request["credits"]
        save_users(users)
        
        # Update payment request status
        update_payment_request(request_id, "approved")
        
        # Notify user
        user_message = f"""
✅ Payment Approved!
────────────────────
Your payment of ₹{payment_request['amount']} has been approved.

💰 {payment_request['credits']} 🪙 credits have been added to your account.

New balance: {users[uid]['credits']} 🪙

Thank you for your purchase!
"""
        
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=user_message
            )
        except Exception as e:
            print(f"Error notifying user: {e}")
        
        await query.edit_message_text(f"✅ Payment approved. {payment_request['credits']} 🪙 credits added to user {target_user_id}.")
        
    elif action == "reject":
        # Ask admin for rejection reason
        context.user_data['admin_action'] = f"reject_{request_id}"
        await query.edit_message_text("Please provide a reason for rejection:")

# ==== Handle Admin Payment Rejection ====
async def handle_admin_rejection_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only.")
        return
    
    if 'admin_action' not in context.user_data or not context.user_data['admin_action'].startswith("reject_"):
        await update.message.reply_text("❌ No rejection action in progress.")
        return
    
    request_id = context.user_data['admin_action'].split("_")[1]
    reason = update.message.text
    
    payment_requests = load_payment_requests()
    
    if request_id not in payment_requests:
        await update.message.reply_text("❌ Payment request not found.")
        return
    
    payment_request = payment_requests[request_id]
    target_user_id = payment_request["user_id"]
    
    # Update payment request status
    update_payment_request(request_id, "rejected", reason)
    
    # Notify user
    user_message = f"""
❌ Payment Rejected
────────────────────
Your payment of ₹{payment_request['amount']} has been rejected.

Reason: {reason}

If you believe this is a mistake, please contact {OWNER_USERNAME}.
"""
    
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=user_message
        )
    except Exception as e:
        print(f"Error notifying user: {e}")
    
    await update.message.reply_text("✅ Payment rejected. User has been notified.")
    
    # Clear admin action
    context.user_data['admin_action'] = None

# ==== Gift Code Function ====
async def gift_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await force_membership_check(update, context):
        return
    
    context.user_data.pop('in_search_mode', None)
    context.user_data.pop('admin_action', None)
    
    context.user_data['waiting_for_gift_code'] = True
    
    await update.message.reply_photo(
        photo=GIFT_IMAGE_URL,
        caption="🎁 [ GIFT CODE ] 🎁\n\nPlease enter your gift code:"
    )

async def process_gift_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    gift_code = update.message.text.strip().upper()
    
    if not context.user_data.get('waiting_for_gift_code', False):
        return
    
    context.user_data['waiting_for_gift_code'] = False
    
    users = load_users()
    uid = str(user_id)
    
    if uid not in users:
        await update.message.reply_text("❌ User not found. Please use /start first.")
        return
    
    if gift_code in users[uid].get("claimed_gift_codes", []):
        await update.message.reply_text("❌ You have already claimed this gift code.")
        return
    
    success, result = claim_gift_code(gift_code, user_id, users[uid]["name"])
    
    if success:
        users[uid]["credits"] += result
        users[uid]["last_update"] = datetime.now().strftime("%d/%m - %I:%M %p")
        
        if "claimed_gift_codes" not in users[uid]:
            users[uid]["claimed_gift_codes"] = []
        users[uid]["claimed_gift_codes"].append(gift_code)
        
        save_users(users)
        
        gift_codes = load_gift_codes()
        gift_name = gift_codes[gift_code].get("name", "Unknown Gift")
        
        broadcast_msg = f"""
🎉 [ GIFT CODE CLAIMED ] 🎉

🎁 Gift: {gift_name}
💰 Amount: {result} 🪙
👤 Claimed by: {users[uid]['name']} (ID: {user_id})
⏰ Claimed at: {datetime.now().strftime('%d/%m - %I:%M %p')}
"""
        
        await broadcast_to_all_users(context, broadcast_msg)
        
        await update.message.reply_text(
            f"✅ Gift code claimed successfully!\n\n"
            f"🎁 You received: {result} 🪙\n"
            f"💰 New balance: {users[uid]['credits']} 🪙"
        )
        
        log_audit_event(user_id, "GIFT_CODE_CLAIMED", f"Code: {gift_code}, Amount: {result}")
    else:
        await update.message.reply_text(f"❌ {result}")

async def broadcast_to_all_users(context, message):
    users = load_users()
    
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=message)
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"Failed to send message to {uid}: {e}")

# ==== Fast Animated Spinner ====
async def show_spinner(update, context, message):
    spinner_frames = [
        "🔍 Searching.........",
        "⏳ Analysing Data....."
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
    return user_id == ADMIN_ID

async def notify_user_credits(context, user_id, action, amount, new_balance):
    try:
        message = f"""
💳 [ CREDIT UPDATE ] 💳 

👑 Owner Has {action} {amount} 🪙 To Your Account.

New Balance ➜ {new_balance} 🪙

Thank You For Using Our Service 🙏
"""
        await context.bot.send_message(chat_id=user_id, text=message)
    except Exception as e:
        print(f"Could not notify user {user_id}: {e}")

async def addcredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin Only.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("❌ Use /addcredits <user_id> <amount>")
        return

    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID or Amount")
        return

    users = load_users()
    uid = str(target_user_id)
    
    if uid not in users:
        await update.message.reply_text("❌ User Not Found")
        return

    users[uid]["credits"] += amount
    save_users(users)
    
    log_audit_event(user_id, "ADMIN_ADD_CREDITS", 
                   f"Target: {target_user_id}, Amount: {amount}, New Balance: {users[uid]['credits']}")
    
    await notify_user_credits(context, target_user_id, "added", amount, users[uid]['credits'])
    
    await update.message.reply_text(f"✅ Added {amount} Credits To User {target_user_id}\nNew Balance ➜ {users[uid]['credits']} 🪙")

async def setcredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin Only")
        return

    if len(context.args) != 2:
        await update.message.reply_text("❌ Use /setcredits <user_id> <amount>")
        return

    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID or Amount")
        return

    users = load_users()
    uid = str(target_user_id)
    
    if uid not in users:
        await update.message.reply_text("❌ User Not Found")
        return

    old_balance = users[uid]["credits"]
    users[uid]["credits"] = amount
    save_users(users)
    
    log_audit_event(user_id, "ADMIN_SET_CREDITS", 
                   f"Target: {target_user_id}, New Amount: {amount}")
    
    await notify_user_credits(context, target_user_id, "set", amount, amount)
    
    await update.message.reply_text(f"✅ Set Credits For User {target_user_id} To {amount} 🪙")

async def userinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin Only")
        return

    if len(context.args) != 1:
        await update.message.reply_text("❌ Use /userinfo <user_id>")
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID")
        return

    users = load_users()
    uid = str(target_user_id)
    
    if uid not in users:
        await update.message.reply_text("❌ User Not Found")
        return

    user_data = users[uid]
    info_msg = f"""
📋 [ USER INFO ] 📋 

👤 Name ➜ {user_data.get('name', 'N/A')}
🆔 User ID ➜ {target_user_id}
🔐 User Code ➜ {user_data.get('user_hash', 'N/A')}
🪙 Credit ➜ {user_data.get('credits', 0)}
🤝 Referrals ➜ {user_data.get('referrals', 0)}
🎁 Referral Credits ➜ {user_data.get('referral_credits', 0)}
📅 Joined ➜ {user_data.get('join_date', 'N/A')}
🔄 Updated ➜ {user_data.get('last_update', 'N/A')}
✅ Verified ➜ {user_data.get('last_verified', 'N/A')}

📜 Verification History ➜
"""
    
    for i, record in enumerate(user_data.get('verification_history', [])[-5:]):
        status = "✅" if record.get('success') else "❌"
        info_msg += f"{i+1}. {status} {record.get('timestamp')} - {record.get('details')}\n"

    log_audit_event(user_id, "ADMIN_USERINFO", 
                   f"Viewed info for user: {target_user_id}")
    
    await update.message.reply_text(info_msg)

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin Only")
        return

    if not context.args:
        await update.message.reply_text("❌ Use /broadcast <message>")
        return

    message = " ".join(context.args)
    users = load_users()
    success_count = 0
    fail_count = 0

    broadcast_msg = f"""
📢 [ IMPORTANT NOTICE ] 📢 

{message}

────────────────────
 Thank You For Using Our Service 🙏
"""
    
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=broadcast_msg)
            success_count += 1
        except Exception as e:
            print(f"Failed to send to {uid}: {e}")
            fail_count += 1
        await asyncio.sleep(0.1)

    log_audit_event(user_id, "ADMIN_BROADCAST", 
                   f"Message: {message}, Success: {success_count}, Failed: {fail_count}")
    
    await update.message.reply_text(f"📢 Broadcast Completed!\nSuccess ➜ {success_count}\nFailed ➜ {fail_count}")

# ==== Generate Gift Code Function ====
async def generate_gift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin Only")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Use /gengift <amount> <name>")
        return

    try:
        amount = int(context.args[0])
        name = " ".join(context.args[1:])
        
        code = create_gift_code(amount, name, user_id)
        
        broadcast_msg = f"""
🎉 [ NEW GIFT CODE ] 🎉

🎁 Gift: {name}
💰 Amount: {amount} 🪙
🔑 Code: {code}
⏰ Valid until claimed

📝 How to claim:
1. Click on 🎁 𝐆ɪғᴛ 𝐂ᴏᴅᴇ button
2. Enter the code: {code}
3. Get {amount} 🪙 credits instantly!

Hurry up! First come first served.
"""
        
        await broadcast_to_all_users(context, broadcast_msg)
        
        keyboard = [
            [InlineKeyboardButton("📋 Copy Code", callback_data=f"copy_{code}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Gift code generated successfully!\n\n"
            f"🎁 Name: {name}\n"
            f"💰 Amount: {amount} 🪙\n"
            f"🔑 Code: {code}\n\n"
            f"The code has been broadcasted to all users.",
            reply_markup=reply_markup
        )
        
        log_audit_event(user_id, "GIFT_CODE_GENERATED", f"Code: {code}, Amount: {amount}, Name: {name}")
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please use a number.")

async def handle_copy_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("copy_"):
        code = query.data[5:]
        await query.edit_message_text(
            f"Code: {code}\n\n"
            f"✅ Code copied to clipboard! (Manually select and copy the code)"
        )

# ==== Referral Stats Function ====
async def referral_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin Only")
        return

    users = load_users()
    
    total_referrals = sum(user.get("referrals", 0) for user in users.values())
    total_referral_credits = sum(user.get("referral_credits", 0) for user in users.values())
    
    top_referrers = sorted(
        [(uid, user_data.get("name", "Unknown"), user_data.get("referrals", 0), user_data.get("referral_credits", 0)) 
         for uid, user_data in users.items() if user_data.get("referrals", 0) > 0],
        key=lambda x: x[2],
        reverse=True
    )[:10]

    stats_msg = f"""
📊 [REFERRAL STATS] 📊
────────────────────

📈 Total Referrals: {total_referrals}
🎁 Total Referral Credits: {total_referral_credits}

🏆 Top Referrers:
"""
    
    for i, (uid, name, referrals, credits) in enumerate(top_referrers, 1):
        stats_msg += f"{i}. {name} (ID: {uid}) - {referrals} referrals, {credits} credits\n"
    
    keyboard = [
        [InlineKeyboardButton("📋 Full Referral List", callback_data="full_referral_list_1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(stats_msg, reply_markup=reply_markup)

async def handle_full_referral_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await query.edit_message_text("❌ Admin Only")
        return
    
    page_num = int(query.data.split("_")[-1])
    
    users = load_users()
    
    referrers = [(uid, user_data.get("name", "Unknown"), user_data.get("referrals", 0), user_data.get("referral_credits", 0)) 
                 for uid, user_data in users.items() if user_data.get("referrals", 0) > 0]
    
    referrers.sort(key=lambda x: x[2], reverse=True)
    
    items_per_page = 10
    total_pages = (len(referrers) + items_per_page - 1) // items_per_page
    
    if page_num < 1 or page_num > total_pages:
        await query.answer("❌ Invalid page")
        return
    
    start_idx = (page_num - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(referrers))
    
    list_msg = f"📋 [FULL REFERRAL LIST] 📋\nPage {page_num}/{total_pages}\n────────────────────\n"
    
    for i, (uid, name, referrals, credits) in enumerate(referrers[start_idx:end_idx], start_idx + 1):
        list_msg += f"{i}. {name} (ID: {uid}) - {referrals} referrals, {credits} credits\n"
    
    keyboard = []
    if page_num > 1:
        keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"full_referral_list_{page_num-1}"))
    if page_num < total_pages:
        keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f"full_referral_list_{page_num+1}"))
    
    reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None
    
    await query.edit_message_text(list_msg, reply_markup=reply_markup)

# ==== Ban User Function ====
async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin Only")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Use /ban <user_id> <reason>")
        return

    try:
        target_user_id = int(context.args[0])
        reason = " ".join(context.args[1:])
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID")
        return

    banned_users = load_banned_users()
    uid = str(target_user_id)
    
    banned_users[uid] = {
        "reason": reason,
        "banned_by": user_id,
        "banned_at": datetime.now().isoformat()
    }
    
    save_banned_users(banned_users)
    
    log_audit_event(user_id, "USER_BANNED", f"Banned user: {target_user_id}, Reason: {reason}")
    
    await update.message.reply_text(f"✅ User {target_user_id} has been banned.\nReason: {reason}")

# ==== Lock/Unlock Features Functions ====
async def lock_feature_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin Only")
        return

    if len(context.args) != 1:
        await update.message.reply_text("❌ Use /lock <feature>\nFeatures: phone, email, name")
        return

    feature = context.args[0].lower()
    locked_features = load_locked_features()
    
    if feature not in locked_features:
        await update.message.reply_text("❌ Invalid feature. Use: phone, email, name")
        return
    
    locked_features[feature] = True
    save_locked_features(locked_features)
    
    log_audit_event(user_id, "FEATURE_LOCKED", f"Locked feature: {feature}")
    
    await update.message.reply_text(f"✅ {feature.capitalize()} search has been locked.")

async def unlock_feature_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin Only")
        return

    if len(context.args) != 1:
        await update.message.reply_text("❌ Use /unlock <feature>\nFeatures: phone, email, name")
        return

    feature = context.args[0].lower()
    locked_features = load_locked_features()
    
    if feature not in locked_features:
        await update.message.reply_text("❌ Invalid feature. Use: phone, email, name")
        return
    
    locked_features[feature] = False
    save_locked_features(locked_features)
    
    log_audit_event(user_id, "FEATURE_UNLOCKED", f"Unlocked feature: {feature}")
    
    await update.message.reply_text(f"✅ {feature.capitalize()} search has been unlocked.")

# ==== Bot Stop/Start Functions ====
async def stopbot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin Only")
        return

    status = {"stopped": True}
    save_bot_status(status)
    global BOT_STOPPED
    BOT_STOPPED = True
    
    log_audit_event(user_id, "BOT_STOPPED", "Bot stopped by admin")
    
    await update.message.reply_text("✅ Bot has been stopped. Users will not be able to use it.")

async def startbot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin Only")
        return

    status = {"stopped": False}
    save_bot_status(status)
    global BOT_STOPPED
    BOT_STOPPED = False
    
    log_audit_event(user_id, "BOT_STARTED", "Bot started by admin")
    
    await update.message.reply_text("✅ Bot has been started. Users can now use it.")

# ==== Check if feature is locked ====
def is_feature_locked(feature_type, query):
    locked_features = load_locked_features()
    
    if feature_type == "phone" and locked_features.get("phone", False):
        return True
    elif feature_type == "email" and locked_features.get("email", False) and "@" in query:
        return True
    elif feature_type == "name" and locked_features.get("name", False) and not re.match(r'^[\d+]+$', query) and "@" not in query:
        return True
    
    return False

# ==== Payment Requests Function ====
async def payment_requests_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin Only")
        return

    payment_requests = load_payment_requests()
    
    # Show both pending and under_review requests
    pending_requests = {k: v for k, v in payment_requests.items() if v.get("status") in ["pending", "under_review"]}
    
    if not pending_requests:
        await update.message.reply_text("📋 No pending payment requests.")
        return
    
    requests_msg = "📋 [PENDING PAYMENT REQUESTS]\n────────────────────\n"
    
    for req_id, req_data in list(pending_requests.items())[:5]:
        requests_msg += f"""
Request ID: {req_id}
User: {req_data.get('user_name', 'Unknown')} (ID: {req_data.get('user_id')})
Amount: ₹{req_data.get('amount', 0)}
Credits: {req_data.get('credits', 0)} 🪙
Status: {req_data.get('status', 'N/A')}
Date: {req_data.get('created_at', 'N/A')}
────────────────────
"""
    
    keyboard = []
    for req_id in list(pending_requests.keys())[:3]:
        keyboard.append([
            InlineKeyboardButton(f"✅ Approve {req_id}", callback_data=f"approve_{req_id}"),
            InlineKeyboardButton(f"❌ Reject {req_id}", callback_data=f"reject_{req_id}")
        ])
    
    if len(pending_requests) > 3:
        keyboard.append([InlineKeyboardButton("📄 More Requests", callback_data="more_requests_1")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(requests_msg, reply_markup=reply_markup)

# ==== ADMIN PANEL HANDLERS ====
async def handle_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin Only.")
        return
        
    text = update.message.text
    
    if text == "🃏 𝐀ᴅᴅ 𝐂ʀᴇᴅɪᴛs":
        context.user_data['admin_action'] = 'add_credits'
        await update.message.reply_text("👤 Send User ID and Amount (space separated)\nExample: 123456789 10")
        
    elif text == "💶 𝐒ᴇᴛ 𝐂ʀᴇᴅɪᴛs":
        context.user_data['admin_action'] = 'set_credits'
        await update.message.reply_text("👤 Send User ID and Amount (space separated)\nExample: 123456789 5")
        
    elif text == "🏅 𝐔sᴇʀ 𝐈ɴғᴏ":
        context.user_data['admin_action'] = 'user_info'
        await update.message.reply_text("👤 Send User ID to get info")
        
    elif text == "📮 𝐁ʀᴏᴀᴅᴄᴀsᴛ":
        context.user_data['admin_action'] = 'broadcast'
        await update.message.reply_text("📢 Send Message To Broadcast")
        
    elif text == "🎁 𝐆ᴇɴᴇʀᴀᴛᴇ 𝐆ɪғᴛ":
        context.user_data['admin_action'] = 'generate_gift'
        await update.message.reply_text("🎁 Send Amount and Name (space separated)\nExample: 5 Special Gift")
        
    elif text == "💰 𝐏ᴀʏᴍᴇɴᴛ 𝐑ᴇǫᴜᴇsᴛs":
        await payment_requests_command(update, context)
        
    elif text == "🔒 𝐋ᴏᴄᴋ 𝐅ᴇᴀᴛᴜʀᴇs":
        context.user_data['admin_action'] = 'lock_feature'
        await update.message.reply_text("🔒 Send feature to lock (phone, email, name)")
        
    elif text == "🔓 𝐔ɴʟᴏᴄᴋ 𝐅ᴇᴀᴛᴜʀᴇs":
        context.user_data['admin_action'] = 'unlock_feature'
        await update.message.reply_text("🔓 Send feature to unlock (phone, email, name)")
        
    elif text == "🚫 𝐁ᴀɴ 𝐔sᴇʀ":
        context.user_data['admin_action'] = 'ban_user'
        await update.message.reply_text("🚫 Send User ID and Reason (space separated)\nExample: 123456789 Spamming")
        
    elif text == "🟢 𝐒ᴛᴀʀᴛ 𝐁ᴏᴛ":
        await startbot_command(update, context)
        
    elif text == "🔴 𝐒ᴛᴏᴩ 𝐁ᴏᴛ":
        await stopbot_command(update, context)
        
    elif text == "🎲 𝐌ᴀɪɴ 𝐌ᴇɴᴜ":
        context.user_data['admin_mode'] = False
        if 'admin_action' in context.user_data:
            del context.user_data['admin_action']
        await update.message.reply_text("🔙 Returning to main menu", reply_markup=get_main_keyboard())

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin Only.")
        return
        
    action = context.user_data.get('admin_action')
    text = update.message.text
    
    if not action:
        await update.message.reply_text("❌ No action selected. Use Admin Menu.", reply_markup=get_admin_keyboard())
        return
        
    try:
        if action == 'add_credits':
            parts = text.split()
            if len(parts) != 2:
                await update.message.reply_text("❌ Invalid format. Use: <user_id> <amount>", reply_markup=get_admin_keyboard())
                return
                
            target_user_id = int(parts[0])
            amount = int(parts[1])
            
            users = load_users()
            uid = str(target_user_id)
            
            if uid not in users:
                await update.message.reply_text("❌ User Not Found", reply_markup=get_admin_keyboard())
                return

            users[uid]["credits"] += amount
            save_users(users)
            
            log_audit_event(user_id, "ADMIN_ADD_CREDITS", 
                           f"Target: {target_user_id}, Amount: {amount}, New Balance: {users[uid]['credits']}")
            
            await notify_user_credits(context, target_user_id, "added", amount, users[uid]['credits'])
            
            await update.message.reply_text(f"✅ Added {amount} Credits To User {target_user_id}\nNew Balance ➜ {users[uid]['credits']} 🪙", reply_markup=get_admin_keyboard())
            
        elif action == 'set_credits':
            parts = text.split()
            if len(parts) != 2:
                await update.message.reply_text("❌ Invalid format. Use: <user_id> <amount>", reply_markup=get_admin_keyboard())
                return
                
            target_user_id = int(parts[0])
            amount = int(parts[1])
            
            users = load_users()
            uid = str(target_user_id)
            
            if uid not in users:
                await update.message.reply_text("❌ User Not Found", reply_markup=get_admin_keyboard())
                return

            old_balance = users[uid]["credits"]
            users[uid]["credits"] = amount
            save_users(users)
            
            log_audit_event(user_id, "ADMIN_SET_CREDITS", 
                           f"Target: {target_user_id}, New Amount: {amount}")
            
            await notify_user_credits(context, target_user_id, "set", amount, amount)
            
            await update.message.reply_text(f"✅ Set Credits For User {target_user_id} To {amount} 🪙", reply_markup=get_admin_keyboard())
            
        elif action == 'user_info':
            target_user_id = int(text)
            
            users = load_users()
            uid = str(target_user_id)
            
            if uid not in users:
                await update.message.reply_text("❌ User Not Found", reply_markup=get_admin_keyboard())
                return

            user_data = users[uid]
            info_msg = f"""
📋 [ USER INFO ] 📋 

👤 Name ➜ {user_data.get('name', 'N/A')}
🆔 User ID ➜ {target_user_id}
🔐 User Code ➜ {user_data.get('user_hash', 'N/A')}
🪙 Credit ➜ {user_data.get('credits', 0)}
🤝 Referrals ➜ {user_data.get('referrals', 0)}
🎁 Referral Credits ➜ {user_data.get('referral_credits', 0)}
📅 Joined ➜ {user_data.get('join_date', 'N/A')}
🔄 Updated ➜ {user_data.get('last_update', 'N/A')}
✅ Verified ➜ {user_data.get('last_verified', 'N/A')}

📜 Verification History ➜
"""
            
            for i, record in enumerate(user_data.get('verification_history', [])[-5:]):
                status = "✅" if record.get('success') else "❌"
                info_msg += f"{i+1}. {status} {record.get('timestamp')} - {record.get('details')}\n"

            log_audit_event(user_id, "ADMIN_USERINFO", 
                           f"Viewed info for user: {target_user_id}")
            
            await update.message.reply_text(info_msg, reply_markup=get_admin_keyboard())
            
        elif action == 'broadcast':
            message = text
            users = load_users()
            success_count = 0
            fail_count = 0

            broadcast_msg = f"""
📢 [ IMPORTANT NOTICE ] 📢 

{message}

────────────────────
 Thank You For Using Our Service 🙏
"""
            
            for uid in users:
                try:
                    await context.bot.send_message(chat_id=int(uid), text=broadcast_msg)
                    success_count += 1
                except Exception as e:
                    print(f"Failed to send to {uid}: {e}")
                    fail_count += 1
                await asyncio.sleep(0.1)

            log_audit_event(user_id, "ADMIN_BROADCAST", 
                           f"Message: {message}, Success: {success_count}, Failed: {fail_count}")
            
            await update.message.reply_text(f"📢 Broadcast Completed!\nSuccess ➜ {success_count}\nFailed ➜ {fail_count}", reply_markup=get_admin_keyboard())
            
        elif action == 'generate_gift':
            parts = text.split()
            if len(parts) < 2:
                await update.message.reply_text("❌ Invalid format. Use: <amount> <name>", reply_markup=get_admin_keyboard())
                return
                
            try:
                amount = int(parts[0])
                name = " ".join(parts[1:])
                
                code = create_gift_code(amount, name, user_id)
                
                broadcast_msg = f"""
🎉 [ NEW GIFT CODE ] 🎉

🎁 Gift: {name}
💰 Amount: {amount} 🪙
🔑 Code: {code}
⏰ Valid until claimed

📝 How to claim:
1. Click on 🎁 𝐆ɪғᴛ 𝐂ᴏᴅᴇ button
2. Enter the code: {code}
3. Get {amount} 🪙 credits instantly!

Hurry up! First come first served.
"""
                
                await broadcast_to_all_users(context, broadcast_msg)
                
                keyboard = [
                    [InlineKeyboardButton("📋 Copy Code", callback_data=f"copy_{code}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ Gift code generated successfully!\n\n"
                    f"🎁 Name: {name}\n"
                    f"💰 Amount: {amount} 🪙\n"
                    f"🔑 Code: {code}\n\n"
                    f"The code has been broadcasted to all users.",
                    reply_markup=reply_markup
                )
                
                log_audit_event(user_id, "GIFT_CODE_GENERATED", f"Code: {code}, Amount: {amount}, Name: {name}")
                
            except ValueError:
                await update.message.reply_text("❌ Invalid amount. Please use a number.", reply_markup=get_admin_keyboard())
        
        elif action == 'lock_feature':
            feature = text.lower()
            locked_features = load_locked_features()
            
            if feature not in locked_features:
                await update.message.reply_text("❌ Invalid feature. Use: phone, email, name", reply_markup=get_admin_keyboard())
                return
            
            locked_features[feature] = True
            save_locked_features(locked_features)
            
            log_audit_event(user_id, "FEATURE_LOCKED", f"Locked feature: {feature}")
            
            await update.message.reply_text(f"✅ {feature.capitalize()} search has been locked.", reply_markup=get_admin_keyboard())
        
        elif action == 'unlock_feature':
            feature = text.lower()
            locked_features = load_locked_features()
            
            if feature not in locked_features:
                await update.message.reply_text("❌ Invalid feature. Use: phone, email, name", reply_markup=get_admin_keyboard())
                return
            
            locked_features[feature] = False
            save_locked_features(locked_features)
            
            log_audit_event(user_id, "FEATURE_UNLOCKED", f"Unlocked feature: {feature}")
            
            await update.message.reply_text(f"✅ {feature.capitalize()} search has been unlocked.", reply_markup=get_admin_keyboard())
        
        elif action == 'ban_user':
            parts = text.split()
            if len(parts) < 2:
                await update.message.reply_text("❌ Invalid format. Use: <user_id> <reason>", reply_markup=get_admin_keyboard())
                return
                
            try:
                target_user_id = int(parts[0])
                reason = " ".join(parts[1:])
            except ValueError:
                await update.message.reply_text("❌ Invalid User ID", reply_markup=get_admin_keyboard())
                return

            banned_users = load_banned_users()
            uid = str(target_user_id)
            
            banned_users[uid] = {
                "reason": reason,
                "banned_by": user_id,
                "banned_at": datetime.now().isoformat()
            }
            
            save_banned_users(banned_users)
            
            log_audit_event(user_id, "USER_BANNED", f"Banned user: {target_user_id}, Reason: {reason}")
            
            await update.message.reply_text(f"✅ User {target_user_id} has been banned.\nReason: {reason}", reply_markup=get_admin_keyboard())
            
    except ValueError:
        await update.message.reply_text("❌ Invalid input. Please use the correct format.", reply_markup=get_admin_keyboard())
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", reply_markup=get_admin_keyboard())
    
    context.user_data['admin_action'] = None

# ==== Pagination Functions ====
def create_pagination_keyboard(current_page, total_pages):
    keyboard = []
    
    if current_page > 1:
        keyboard.append(InlineKeyboardButton("⬅️", callback_data=f"page_{current_page-1}"))
    
    keyboard.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="current_page"))
    
    if current_page < total_pages:
        keyboard.append(InlineKeyboardButton("➡️", callback_data=f"page_{current_page+1}"))
    
    return InlineKeyboardMarkup([keyboard])

async def handle_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not query.data.startswith("page_"):
        return
        
    try:
        page_num = int(query.data.split("_")[1])
        
        if 'pagination' not in context.user_data:
            await query.edit_message_text("❌ Session Expired. Please Search Again.")
            return
            
        pagination_data = context.user_data['pagination']
        pages = pagination_data['pages']
        total_pages = len(pages)
        
        if page_num < 1 or page_num > total_pages:
            await query.answer("❌ Invalid Page")
            return
            
        keyboard = create_pagination_keyboard(page_num, total_pages)
        await query.edit_message_text(pages[page_num-1], reply_markup=keyboard)
        
    except (ValueError, IndexError):
        await query.answer("❌ Error Loading Page")

# ==== Handlers ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    
    # Check if bot is stopped
    if is_bot_stopped() and user_id != ADMIN_ID:
        await update.message.reply_photo(
            photo=STOPPED_IMAGE_URL,
            caption="🚫 Bot is currently stopped for maintenance.\n\nServer request is high. Please try again later.\n\nContact owner for more information.",
            reply_markup=get_banned_keyboard()
        )
        return
    
    context.user_data.pop('pagination', None)
    context.user_data.pop('in_search_mode', None)
    context.user_data.pop('waiting_for_gift_code', None)
    context.user_data.pop('admin_mode', None)
    context.user_data.pop('admin_action', None)
    
    if is_user_banned(user_id):
        banned_users = load_banned_users()
        ban_data = banned_users.get(str(user_id), {})
        ban_reason = ban_data.get("reason", "No reason provided")
        
        await update.message.reply_photo(
            photo=BANNED_IMAGE_URL,
            caption=f"🚫 You have been banned from using this bot.\n\nReason: {ban_reason}\n\nContact owner for more information: {OWNER_USERNAME}",
            reply_markup=get_banned_keyboard()
        )
        return
    
    referred_by = None
    if context.args and len(context.args) > 0:
        referral_code = context.args[0]
        
        users = load_users()
        for uid, user_data in users.items():
            if user_data.get("referral_code") == referral_code and int(uid) != user_id:
                referred_by = int(uid)
                break
    
    log_audit_event(user_id, "START_COMMAND", f"User: {name}, Referred by: {referred_by}")
    
    users = load_users()
    user_data = users.get(str(user_id), {})
    
    is_member = await check_membership(update, context, user_id)
    
    if is_member:
        if not user_data:
            user_data = update_user(user_id, credits=2, 
                                  name=name, 
                                  last_verified=datetime.now().isoformat(),
                                  initial_credits_given=True,
                                  referred_by=referred_by)
            
            if referred_by and referred_by != user_id:
                add_referral_credits(referred_by)
                log_audit_event(user_id, "REFERRAL_JOIN", f"Referred by: {referred_by}")
            
            add_verification_record(user_id, True, "New user - initial credits granted")
            message = "✅ Verification Successful! 🎉🎊\n\n🎁You've Received 2 Free Credits\n\nEnjoy Using Our Service 🙏"
            
            await update.message.reply_photo(
                photo=START_IMAGE_URL,
                caption=message,
                reply_markup=get_main_keyboard()
            )
        else:
            user_data = update_user(user_id, name=name)
            add_verification_record(user_id, True, "Existing user - membership verified")
            await update.message.reply_photo(
                photo=START_IMAGE_URL,
                caption="👋 Welcome Back User • Enjoy The Bot 🙏",
                reply_markup=get_main_keyboard()
            )
    else:
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel 1", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 Join Channel 2", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("✅ Verify Membership", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        add_verification_record(user_id, False, "User not member of required channels")
        
        await update.message.reply_photo(
            photo=VERIFY_IMAGE_URL,
            caption="[ 🙏 Please Join Our Channels ]\n\n"
            "📌 To Use This Bot You Must ➜\n\n"
            "🔒 Join Both Official Channels\n"
            "🔓 Click On Verify\n\n"
            "🎁Reward ➜ After Successful Verification You Get\n"
            "🪙 2 Free Credits\n\n"
            "────────────────────\n"
            "💰 Buy Unlimited Credits & Ad 👉 @pvt_s1n",
            reply_markup=reply_markup
        )

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    
    if is_user_banned(user_id):
        banned_users = load_banned_users()
        ban_data = banned_users.get(str(user_id), {})
        ban_reason = ban_data.get("reason", "No reason provided")
        
        await query.message.reply_photo(
            photo=BANNED_IMAGE_URL,
            caption=f"🚫 You have been banned from using this bot.\n\nReason: {ban_reason}\n\nContact owner for more information: {OWNER_USERNAME}",
            reply_markup=get_banned_keyboard()
        )
        return
    
    is_member = await check_membership(update, context, user_id)
    
    users = load_users()
    uid = str(user_id)
    user_data = users.get(uid, {})
    
    if is_member:
        if not user_data:
            user_data = update_user(user_id, credits=2, name=name, 
                                  last_verified=datetime.now().isoformat(),
                                  initial_credits_given=True)
            add_verification_record(user_id, True, "New user - initial credits granted via verify")
            
            try:
                await query.message.edit_caption(
                    caption="✅ Verification Successful! 🎉🎊\n\n"
                    "🎁You've Received 2 Free Credits\n\n"
                    "Enjoy Using Our Service 🙏"
                )
            except:
                await query.message.reply_text(
                    "✅ Verification Successful! 🎉🎊\n\n"
                    "🎁You've Received 2 Free Credits\n\n"
                    "Enjoy Using Our Service 🙏"
                )
            await context.bot.send_message(chat_id=user_id, text="Choose an option:", reply_markup=get_main_keyboard())
        else:
            if not user_data.get("initial_credits_given", False):
                user_data = update_user(user_id, credits=user_data.get("credits", 0) + 2, 
                                      name=name, last_verified=datetime.now().isoformat(),
                                      initial_credits_given=True)
                add_verification_record(user_id, True, "Existing user - initial credits granted via verify")
                
                try:
                    await query.message.edit_caption(
                        caption="✅ Verification Successful! 🎉🎊\n\n"
                        "🎁You've Received 2 Free Credits\n\n"
                        "Enjoy Using Our Service 🙏"
                    )
                except:
                    await query.message.reply_text(
                        "✅ Verification Successful! 🎉🎊\n\n"
                        "🎁You've Received 2 Free Credits\n\n"
                        "Enjoy Using Our Service 🙏"
                    )
            else:
                user_data = update_user(user_id, name=name, 
                                      last_verified=datetime.now().isoformat())
                add_verification_record(user_id, True, "Existing user - reverified")
                
                try:
                    await query.message.edit_caption(
                        caption="👋 Welcome Back User.\n\n"
                        "🔓 Enjoy The Bot 🙏"
                    )
                except:
                    await query.message.reply_text(
                        "👋 Welcome Back User.\n\n"
                        "🔓 Enjoy The Bot 🙏"
                    )
            await context.bot.send_message(chat_id=user_id, text="Choose an option:", reply_markup=get_main_keyboard())
    else:
        add_verification_record(user_id, False, "Verification failed - not member of channels")
        
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel 1", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("📢 Join Channel 2", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("🔄 Retry", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.message.edit_caption(
                caption="❌ [ WARNING ] ❌\n\n"
                "📌 You Have Not Joined Both Channels Yet!\n\n"
                "❌ Please Join Both Channels First ✅\n"
                "🔄 Then Click Retry🔄\n\n"
                "────────────────────",
                reply_markup=reply_markup
            )
        except:
            await query.message.reply_text(
                "❌ [ WARNING ] ❌\n\n"
                "📌 You Have Not Joined Both Channels Yet!\n\n"
                "❌ Please Join Both Channels First ✅\n"
                "🔄 Then Click Retry🔄\n\n"
                "────────────────────",
                reply_markup=reply_markup
            )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "buy":
        await buy_command(update, context)
        
    elif query.data.startswith("buy_"):
        await handle_buy_package(update, context)
        
    elif query.data.startswith("paid_"):
        await handle_payment_confirmation(update, context)
        
    elif query.data.startswith("approve_") or query.data.startswith("reject_"):
        await handle_admin_payment_approval(update, context)
        
    elif query.data == "back_to_packages":
        # Edit the message to show packages again
        await show_packages(update, context)
        
    elif query.data == "back_to_main":
        # Clear any ongoing actions and return to main menu
        context.user_data.pop('pagination', None)
        context.user_data.pop('in_search_mode', None)
        context.user_data.pop('waiting_for_gift_code', None)
        context.user_data.pop('admin_mode', None)
        context.user_data.pop('admin_action', None)
        
        try:
            await query.edit_message_text("Choose an option:", reply_markup=get_main_keyboard())
        except:
            await query.message.reply_text("Choose an option:", reply_markup=get_main_keyboard())
    
    elif query.data == "profile":
        user_id = update.effective_user.id
        users = load_users()
        user_data = users.get(str(user_id), {"credits": 0, "last_update": "N/A", "name": "Unknown"})
        await show_profile(update, context, user_id, user_data, edit_message=True)
    
    elif query.data.startswith("full_referral_list_"):
        await handle_full_referral_list(update, context)
    
    elif query.data.startswith("copy_"):
        await handle_copy_code(update, context)
    
    elif query.data.startswith("page_"):
        await handle_pagination(update, context)

async def show_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    row = []
    
    for i, (amount, details) in enumerate(PAYMENT_PACKAGES.items()):
        row.append(InlineKeyboardButton(f"₹{amount} - {details['credits']}🪙", callback_data=f"buy_{amount}"))
        
        if (i + 1) % 2 == 0:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    buy_message = """
💳 [ BUY CREDITS ] 💳
────────────────────

Choose a payment package:

💰 Payment Options:
- 10 Rs = 100 Credits
- 20 Rs = 200 Credits
- 30 Rs = 300 Credits
- 40 Rs = 400 Credits
- 50 Rs = 500 Credits
- 100 Rs = 1000 Credits
- 200 Rs = 2000 Credits
- 500 Rs = 5000 Credits

📝 How to purchase:
1. Select a package
2. Pay via UPI using the QR code
3. Click "I've Paid" after payment
4. Wait for admin approval

────────────────────
Note: Payments are manually verified by admin. Please be patient.
"""

    # Check if it's a callback query or message
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            text=buy_message,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text=buy_message,
            reply_markup=reply_markup
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Check if bot is stopped
    if is_bot_stopped() and user_id != ADMIN_ID:
        await update.message.reply_photo(
            photo=STOPPED_IMAGE_URL,
            caption="🚫 Bot is currently stopped for maintenance.\n\nServer request is high. Please try again later.\n\nContact owner for more information.",
            reply_markup=get_banned_keyboard()
        )
        return
    
    if is_user_banned(user_id):
        banned_users = load_banned_users()
        ban_data = banned_users.get(str(user_id), {})
        ban_reason = ban_data.get("reason", "No reason provided")
        
        await update.message.reply_photo(
            photo=BANNED_IMAGE_URL,
            caption=f"🚫 You have been banned from using this bot.\n\nReason: {ban_reason}\n\nContact owner for more information: {OWNER_USERNAME}",
            reply_markup=get_banned_keyboard()
        )
        return
    
    if 'pagination' in context.user_data:
        del context.user_data['pagination']
    
    user_menu_buttons = [
        "🔍 𝐒ᴇᴀʀᴄʜ",
        "💎 𝐂ʀᴇᴅɪᴛs",
        "🎁 𝐆ɪғᴛ 𝐂ᴏᴅᴇ",
        "🎖️ 𝐏ʀᴏғɪʟᴇ",
        "🛍️ 𝐒ʜᴏᴘ",
        "💠 𝐑ᴇғᴇʀ",
        "☎️ 𝐇ᴇʟᴘ",
        "🧧 𝐀ᴅᴍɪɴ"
    ]
    
    if context.user_data.get('waiting_for_gift_code', False):
        if text in user_menu_buttons:
            context.user_data['waiting_for_gift_code'] = False
        else:
            await process_gift_code(update, context)
            return
    
    if text in user_menu_buttons:
        context.user_data['in_search_mode'] = False
        context.user_data['waiting_for_gift_code'] = False
        context.user_data['admin_mode'] = False
        if 'admin_action' in context.user_data:
            del context.user_data['admin_action']
    
    is_admin_user = user_id == ADMIN_ID
    admin_mode = context.user_data.get('admin_mode', False)
    
    if is_admin_user and admin_mode:
        admin_buttons = [
            "🃏 𝐀ᴅᴅ 𝐂ʀᴇᴅɪᴛs", "💶 𝐒ᴇᴛ 𝐂ʀᴇᴅɪᴛs", "🏅 𝐔sᴇʀ 𝐈ɴғᴏ", 
            "📮 𝐁ʀᴏᴀᴅᴄᴀsᴛ", "🎁 𝐆ᴇɴᴇʀᴀᴛᴇ 𝐆ɪғᴛ", "💰 𝐏ᴀʏᴍᴇɴᴛ 𝐑ᴇǫᴜᴇsᴛs",
            "🔒 𝐋ᴏᴄᴋ 𝐅ᴇᴀᴛᴜʀᴇs", "🔓 𝐔ɴʟᴏᴄᴋ 𝐅ᴇᴀᴛᴜʀᴇs", "🚫 𝐁ᴀɴ 𝐔sᴇʀ",
            "🟢 𝐒ᴛᴀʀᴛ 𝐁ᴏᴛ", "🔴 𝐒ᴛᴏᴩ 𝐁ᴏᴛ", "🎲 𝐌ᴀɪɴ 𝐌ᴇɴᴜ"
        ]
        
        if text in admin_buttons:
            await handle_admin_panel(update, context)
            return
        elif 'admin_action' in context.user_data:
            await handle_admin_input(update, context)
            return
        else:
            await update.message.reply_text("👑 Admin Panel", reply_markup=get_admin_keyboard())
            return
    
    if context.user_data.get('in_search_mode', False):
        context.user_data['in_search_mode'] = False
        
        # Check if feature is locked
        locked_features = load_locked_features()
        
        if is_feature_locked("phone", text) and re.match(r'^[\d+]+$', text):
            await update.message.reply_photo(
                photo=LOCKED_IMAGE_URL,
                caption="❌ Phone number search is currently locked by admin.\n\nPlease try another search type or contact admin for more information."
            )
            return
        elif is_feature_locked("email", text) and "@" in text:
            await update.message.reply_photo(
                photo=LOCKED_IMAGE_URL,
                caption="❌ Email search is currently locked by admin.\n\nPlease try another search type or contact admin for more information."
            )
            return
        elif is_feature_locked("name", text) and not re.match(r'^[\d+]+$', text) and "@" not in text:
            await update.message.reply_photo(
                photo=LOCKED_IMAGE_URL,
                caption="❌ Name search is currently locked by admin.\n\nPlease try another search type or contact admin for more information."
            )
            return
        
        await search(update, context)
        return
    
    if not await force_membership_check(update, context):
        return
    
    if text == "🔍 𝐒ᴇᴀʀᴄʜ":
        context.user_data['in_search_mode'] = True
        await update.message.reply_photo(
            photo=SEARCH_IMAGE_URL, 
            caption=SEARCH_PROMPT_TEXT
        )
    elif text == "💎 𝐂ʀᴇᴅɪᴛs":
        await credits(update, context)
    elif text == "🎁 𝐆ɪғᴛ 𝐂ᴏᴅᴇ":
        await gift_code_command(update, context)
    elif text == "🎖️ 𝐏ʀᴏғɪʟᴇ":
        await me(update, context)
    elif text == "🛍️ 𝐒ʜᴏᴘ":
        await buy_command(update, context)
    elif text == "💠 𝐑ᴇғᴇʀ":
        await show_referral_info(update, context)
    elif text == "☎️ 𝐇ᴇʟᴘ":
        await update.message.reply_photo(
            photo=HELP_IMAGE_URL, 
            caption=HELP_TEXT
        )
    elif text == "🧧 𝐀ᴅᴍɪɴ":
        await admin_stats(update, context)
    else:
        await update.message.reply_text("Please use the menu buttons to interact with the bot.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_membership_check(update, context):
        return
    await update.message.reply_photo(
        photo=HELP_IMAGE_URL, 
        caption=HELP_TEXT
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await force_membership_check(update, context):
        return
        
    users = load_users()

    if str(user_id) not in users:
        name = update.effective_user.first_name
        update_user(user_id, credits=0, name=name)
        users = load_users()

    if users[str(user_id)]["credits"] <= 0:
        await update.message.reply_text(f"❌ No Credits Left!\n\n💰 Buy Unlimited Credits & Ad 👉 {OWNER_USERNAME}")
        return

    spinner_msg = await show_spinner(update, context, update.message)

    query = update.message.text
    result = query_leakosint(query)
    pages = format_results(result)

    if "SERVER" in pages[0] or "Error" in result:
        await spinner_msg.delete()
        await update.message.reply_text(pages[0])
        return

    if "No Data" not in pages[0] and "SERVER" not in pages[0] and "Error" not in result:
        users[str(user_id)]["credits"] -= 1
        users[str(user_id)]["last_update"] = datetime.now().strftime("%d/%m - %I:%M %p")
        save_users(users)
        
        log_audit_event(user_id, "SEARCH", f"Query: {query}, Success: True, Credits left: {users[str(user_id)]['credits']}")
    else:
        log_audit_event(user_id, "SEARCH", f"Query: {query}, Success: False, Credits left: {users[str(user_id)]['credits']}")

    await spinner_msg.delete()

    credits_left = users[str(user_id)]["credits"]
    for i in range(len(pages)):
        pages[i] += f"\n✅ Credits Left ➜ {credits_left} 🪙"
    
    context.user_data['pagination'] = {
        'pages': pages,
        'current_page': 1
    }
    
    if len(pages) > 1:
        keyboard = create_pagination_keyboard(1, len(pages))
        await update.message.reply_text(pages[0], reply_markup=keyboard)
    else:
        await update.message.reply_text(pages[0])

async def credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await force_membership_check(update, context):
        return
        
    users = load_users()
    
    c = users.get(str(user_id), {}).get("credits", 0)
    await update.message.reply_photo(
        photo=CREDITS_IMAGE_URL, 
        caption=f"✅ Your Credit ➜ {c} 🪙"
    )

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await force_membership_check(update, context):
        return
        
    users = load_users()
    user_data = users.get(str(user_id), {"credits": 0, "last_update": "N/A", "name": "Unknown"})
    await show_profile(update, context, user_id, user_data)

# ==== ADMIN COMMANDS ====
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin Only.")
        return
        
    users = load_users()
    total_users = len(users)
    total_credits = sum(user.get("credits", 0) for user in users.values())
    total_referrals = sum(user.get("referrals", 0) for user in users.values())
    total_referral_credits = sum(user.get("referral_credits", 0) for user in users.values())
    
    banned_users = load_banned_users()
    total_banned = len(banned_users)
    
    payment_requests = load_payment_requests()
    pending_requests = len([r for r in payment_requests.values() if r.get("status") in ["pending", "under_review"]])
    
    locked_features = load_locked_features()
    locked_features_list = [f for f, locked in locked_features.items() if locked]
    
    bot_status = "🟢 Running" if not is_bot_stopped() else "🔴 Stopped"
    
    stats_msg = f"""
📊 [ADMIN PANEL] 📊

👥 Total Users ➜ {total_users}
🚫 Banned Users ➜ {total_banned}
🪙 Total Credits ➜ {total_credits}
🤝 Total Referrals ➜ {total_referrals}
🎁 Total Referral Credits ➜ {total_referral_credits}
💰 Pending Payments ➜ {pending_requests}
🔒 Locked Features ➜ {', '.join(locked_features_list) if locked_features_list else 'None'}
📊 Bot Status ➜ {bot_status}
🔄 Updated ➜ {datetime.now().strftime('%d/%m - %I:%M %p')}

"""

    context.user_data['admin_mode'] = True
    if 'admin_action' in context.user_data:
        del context.user_data['admin_action']
    
    await update.message.reply_photo(
        photo=ADMIN_IMAGE_URL, 
        caption=stats_msg, 
        reply_markup=get_admin_keyboard()
    )

# ==== Error Handler ====
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    # Only send error message to admin
    if ADMIN_ID:
        error_msg = f"An exception was raised while handling an update:\n{context.error}"
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=error_msg)
        except:
            pass  # Avoid infinite loop if sending error message fails

# ==== MAIN ====
def main():
    # Load bot status on startup
    is_bot_stopped()
    
    app = Application.builder().token(BOT_TOKEN).build()

    # Add error handler
    app.add_error_handler(error_handler)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("credits", credits))
    app.add_handler(CommandHandler("me", me))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("adminstats", admin_stats))
    app.add_handler(CommandHandler("addcredits", addcredits_command))
    app.add_handler(CommandHandler("setcredits", setcredits_command))
    app.add_handler(CommandHandler("userinfo", userinfo_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("gengift", generate_gift_command))
    app.add_handler(CommandHandler("referralstats", referral_stats_command))
    app.add_handler(CommandHandler("ban", ban_user_command))
    app.add_handler(CommandHandler("lock", lock_feature_command))
    app.add_handler(CommandHandler("unlock", unlock_feature_command))
    app.add_handler(CommandHandler("stopbot", stopbot_command))
    app.add_handler(CommandHandler("startbot", startbot_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify$"))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🙏 Service Is Running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":

    main()





