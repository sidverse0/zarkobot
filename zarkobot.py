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
# Initialize Firebase with environment variable
try:
    firebase_cred = credentials.Certificate(json.loads(os.environ['FIREBASE_CREDENTIALS']))
    firebase_admin.initialize_app(firebase_cred)
    db = firestore.client()
    print("Firebase initialized successfully")
except Exception as e:
    print(f"Firebase initialization error: {e}")
    # Fallback to local storage if Firebase fails
    db = None

# ==== CONFIG ====
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8116705267:AAGVx7azJJMndrXHwzoMnx7angKd0COJWjg")
ADMIN_BOT_TOKEN = "8206411540:AAE6dHEbDOS3mpb3bTGf7YWNFelLMexPv0w"  # Your admin bot token
CHANNEL_USERNAME = "@zarkoworld"   # Main channel
CHANNEL_USERNAME_2 = "@chandhackz_78"  # Second channel
OWNER_USERNAME = "@pvt_s1n"    # Your username
ADMIN_ID = 7975903577  # Your user ID
UPI_ID = "reyazmbi2003@okaxis"  # Your UPI ID

LEAKOSINT_API_TOKEN = os.environ.get('LEAKOSINT_API_TOKEN', "8250754854:64fCZifF")
API_URL = "https://leakosintapi.com/"

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
DEPOSIT_IMAGE_URL = "https://files.catbox.moe/dko70i.png"

# Payment packages (amount in INR : credits)
PAYMENT_PACKAGES = {
    10: 100,
    20: 150,
    30: 200,
    40: 400,
    50: 500
}

# Constants for messages (normalized text)
HELP_TEXT = """Help
search no 91XXXXXXXXXX & 79XXXXXX68
email - example@gmail.com
name - search any name
contact ☎️ @Pvt_s1n
"""

SEARCH_PROMPT_TEXT = """Help
search no 91XXXXXXXXXX & 79XXXXXX68
email - example@gmail.com
name - search any name
contact ☎️ @Pvt_s1n
"""

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
    """Load banned users from Firebase"""
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
    """Save banned users to Firebase"""
    if db is None:
        return
    try:
        for user_id, ban_data in banned_users.items():
            db.collection('banned_users').document(str(user_id)).set(ban_data)
    except Exception as e:
        print(f"Error saving banned users to Firebase: {e}")

def load_search_locks():
    """Load search lock settings from Firebase"""
    if db is None:
        return {"number": False, "email": False, "name": False}
    try:
        locks_ref = db.collection('settings').document('search_locks')
        doc = locks_ref.get()
        if doc.exists:
            return doc.to_dict()
        return {"number": False, "email": False, "name": False}
    except Exception as e:
        print(f"Error loading search locks from Firebase: {e}")
        return {"number": False, "email": False, "name": False}

def save_search_locks(locks):
    """Save search lock settings to Firebase"""
    if db is None:
        return
    try:
        db.collection('settings').document('search_locks').set(locks)
    except Exception as e:
        print(f"Error saving search locks to Firebase: {e}")

def load_pending_payments():
    """Load pending payments from Firebase"""
    if db is None:
        return {}
    try:
        payments_ref = db.collection('pending_payments')
        docs = payments_ref.stream()
        payments = {}
        for doc in docs:
            payments[doc.id] = doc.to_dict()
        return payments
    except Exception as e:
        print(f"Error loading pending payments from Firebase: {e}")
        return {}

def save_pending_payments(payments):
    """Save pending payments to Firebase"""
    if db is None:
        return
    try:
        for payment_id, payment_data in payments.items():
            db.collection('pending_payments').document(payment_id).set(payment_data)
    except Exception as e:
        print(f"Error saving pending payments to Firebase: {e}")

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
            "claimed_gift_codes": []
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
    
    # Log the update
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
        if db is not None:
            db.collection('audit_logs').add(log_entry)
        else:
            # Fallback to local file if Firebase not available
            with open("audit.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Audit log error: {e}")

# ==== Check if user is banned ====
def is_user_banned(user_id):
    """Check if a user is banned"""
    banned_users = load_banned_users()
    return str(user_id) in banned_users

# ==== Check search type lock ====
def check_search_type_locked(query):
    """Check if the search type is locked based on query"""
    locks = load_search_locks()
    
    # Check if query is a phone number
    if re.match(r'^[\d+]+$', query.replace(" ", "")):
        return locks.get("number", False), "Phone number searches are currently locked"
    
    # Check if query is an email
    if '@' in query:
        return locks.get("email", False), "Email searches are currently locked"
    
    # Assume it's a name search
    return locks.get("name", False), "Name searches are currently locked"

# ==== Reply Keyboard Setup ====
def get_main_keyboard():
    keyboard = [
        ["🔍 search", "💎 credits", "🎁 gift"],
        ["🎖️ profile", "🛍️ shop", "💠 refer"],
        ["💳 deposit", "☎️ help", "🧧 admin"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, input_field_placeholder="Choose Options")

def get_admin_keyboard():
    keyboard = [
        ["🃏 add credits", "💶 set credits", "🏅 user info"],
        ["📮 broadcast", "🎁 generate gift", "📑 referral"],
        ["⛔ ban user", "🔓 unban user", "🔒 lock search"],
        ["🔓 unlock search", "📊 stats", "🎲 main menu"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, input_field_placeholder="Admin Panel")

# ==== Payment Functions ====
def generate_payment_id():
    """Generate a unique payment ID"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def create_pending_payment(user_id, amount, credits):
    """Create a pending payment record"""
    payment_id = generate_payment_id()
    payments = load_pending_payments()
    
    payments[payment_id] = {
        "user_id": user_id,
        "user_name": get_user_name(user_id),
        "amount": amount,
        "credits": credits,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "processed_at": None,
        "processed_by": None,
        "reason": None
    }
    
    save_pending_payments(payments)
    return payment_id

def update_payment_status(payment_id, status, admin_id, reason=None):
    """Update payment status"""
    payments = load_pending_payments()
    
    if payment_id in payments:
        payments[payment_id]["status"] = status
        payments[payment_id]["processed_at"] = datetime.now().isoformat()
        payments[payment_id]["processed_by"] = admin_id
        if reason:
            payments[payment_id]["reason"] = reason
            
        save_pending_payments(payments)
        return True
    return False

def get_user_name(user_id):
    """Get user name from database"""
    users = load_users()
    uid = str(user_id)
    return users.get(uid, {}).get("name", "Unknown")

def generate_upi_qr(amount, upi_id):
    """Generate a UPI QR code for the given amount"""
    # Create UPI payment URL
    upi_url = f"upi://pay?pa={upi_id}&pn=Bot Owner&am={amount}&cu=INR"
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)
    
    # Create an image from the QR Code instance
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save image to bytes buffer
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    return buf

# ==== Gift Code Functions ====
def generate_gift_code(length=12):
    """Generate a random gift code"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def create_gift_code(amount, name, created_by):
    """Create a new gift code"""
    gift_codes = load_gift_codes()
    
    # Generate a unique code
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
    """Claim a gift code for a user"""
    gift_codes = load_gift_codes()
    
    if code not in gift_codes:
        return False, "Invalid gift code"
    
    gift = gift_codes[code]
    
    if gift["claimed_by"] is not None:
        return False, "Gift code already claimed"
    
    # Mark as claimed
    gift["claimed_by"] = user_id
    gift["claimed_by_name"] = user_name
    gift["claimed_at"] = datetime.now().isoformat()
    
    save_gift_codes(gift_codes)
    return True, gift["amount"]

# ==== Phone Number Normalization Function ====
def normalize_phone_number(query):
    """
    Normalize phone numbers to the format expected by the API (91XXXXXXXXXX)
    Supports various formats: 10-digit, with spaces, with +91, with 91, etc.
    """
    # Remove all non-digit characters except '+' if present
    cleaned = re.sub(r'[^\d+]', '', query)
    
    # Check if it's a phone number (contains only digits or starts with + followed by digits)
    if re.fullmatch(r'[\d+]+', cleaned):
        # Remove any '+' signs
        digits_only = re.sub(r'[^\d]', '', cleaned)
        
        # Handle different cases
        if len(digits_only) == 10:
            # 10-digit number without country code
            return "91" + digits_only
        elif len(digits_only) == 11 and digits_only.startswith('0'):
            # 11-digit number starting with 0 (common in some formats)
            return "91" + digits_only[1:]
        elif len(digits_only) == 12 and digits_only.startswith('91'):
            # 12-digit number with country code
            return digits_only
        elif len(digits_only) > 12:
            # Longer numbers - take first 12 digits
            return digits_only[:12]
        else:
            # Return as is for other cases (let API handle it)
            return digits_only
    else:
        # Not a phone number, return original query (for email/name searches)
        return query

# ==== Query Optimization Functions ====
def optimize_name_query(name):
    """
    Optimize name queries for better search results
    """
    # Remove extra spaces and special characters
    name = re.sub(r'[^\w\s]', '', name.strip())
    
    # Split into words and take first 2-3 words for better matching
    words = name.split()
    if len(words) > 3:
        return " ".join(words[:3])
    return name

def optimize_email_query(email):
    """
    Optimize email queries for better search results
    """
    # Clean email and extract username part for broader search
    email = email.strip().lower()
    return email

# ==== Security Functions ====
def generate_user_hash(user_id):
    """Generate a 6-digit alphanumeric hash for user identification"""
    # Create a consistent but unique 6-digit code for each user
    random.seed(user_id)  # Seed with user_id for consistency
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(6))

def generate_referral_code(user_id):
    """Generate a unique referral code for each user"""
    random.seed(user_id)
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(8))

def add_referral_credits(referrer_id):
    """Add referral credits to referrer and update referral count"""
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
    """Add a verification attempt to user's history"""
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
    
    # Keep only last 10 records
    if len(users[uid]["verification_history"]) > 10:
        users[uid]["verification_history"] = users[uid]["verification_history"][-10:]
    
    save_users(users)
    return True

# ==== Send Payment Request to Admin Bot ====
async def send_payment_request_to_admin(payment_id, user_id, user_name, amount, credits):
    """Send payment request to admin bot"""
    try:
        admin_bot_url = f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendMessage"
        
        message = f"""
💳 New Payment Request

🆔 Payment ID: {payment_id}
👤 User: {user_name} (ID: {user_id})
💰 Amount: ₹{amount}
🎁 Credits: {credits} 💎
⏰ Time: {datetime.now().strftime('%d/%m/%Y %I:%M %p')}

Click below to approve or reject:
        """
        
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve", "callback_data": f"approve_{payment_id}"},
                    {"text": "❌ Reject", "callback_data": f"reject_{payment_id}"}
                ]
            ]
        }
        
        payload = {
            "chat_id": ADMIN_ID,
            "text": message,
            "reply_markup": keyboard
        }
        
        response = requests.post(admin_bot_url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending payment request to admin: {e}")
        return False

# ==== Process Payment Approval/Rejection ====
async def process_payment_approval(payment_id, admin_id):
    """Process payment approval"""
    payments = load_pending_payments()
    
    if payment_id not in payments:
        return False, "Payment not found"
    
    payment = payments[payment_id]
    
    if payment["status"] != "pending":
        return False, f"Payment already {payment['status']}"
    
    # Update payment status
    update_payment_status(payment_id, "approved", admin_id)
    
    # Add credits to user
    users = load_users()
    uid = str(payment["user_id"])
    
    if uid not in users:
        return False, "User not found"
    
    users[uid]["credits"] += payment["credits"]
    users[uid]["last_update"] = datetime.now().strftime("%d/%m - %I:%M %p")
    save_users(users)
    
    # Notify user
    try:
        user_bot_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        user_message = f"""
✅ Payment Approved!

💰 Amount: ₹{payment["amount"]}
🎁 Credits Added: {payment["credits"]} 💎
💳 Payment ID: {payment_id}

Your new balance: {users[uid]["credits"]} 💎
"""
        
        payload = {
            "chat_id": payment["user_id"],
            "text": user_message
        }
        
        requests.post(user_bot_url, json=payload)
    except Exception as e:
        print(f"Error notifying user: {e}")
    
    return True, "Payment approved successfully"

async def process_payment_rejection(payment_id, admin_id, reason="No reason provided"):
    """Process payment rejection"""
    payments = load_pending_payments()
    
    if payment_id not in payments:
        return False, "Payment not found"
    
    payment = payments[payment_id]
    
    if payment["status"] != "pending":
        return False, f"Payment already {payment['status']}"
    
    # Update payment status
    update_payment_status(payment_id, "rejected", admin_id, reason)
    
    # Notify user
    try:
        user_bot_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        user_message = f"""
❌ Payment Rejected

💰 Amount: ₹{payment["amount"]}
🎁 Credits: {payment["credits"]} 💎
💳 Payment ID: {payment_id}
📝 Reason: {reason}

Please contact admin if you think this is a mistake.
"""
        
        payload = {
            "chat_id": payment["user_id"],
            "text": user_message
        }
        
        requests.post(user_bot_url, json=payload)
    except Exception as e:
        print(f"Error notifying user: {e}")
    
    return True, "Payment rejected successfully"

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

# ==== Force Membership Check ====
async def force_membership_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force user to join channels before using any feature"""
    user_id = update.effective_user.id
    
    # Check if user is banned
    if is_user_banned(user_id):
        # Send banned message with image
        try:
            await update.message.reply_photo(
                photo=BANNED_IMAGE_URL,
                caption="🚫 You are banned due to Violation of our terms and conditions"
            )
        except:
            await update.message.reply_text("🚫 You are banned due to Violation of our terms and conditions")
        return False
    
    # Check membership
    is_member = await check_membership(update, context, user_id)
    
    if not is_member:
        keyboard = [
            [InlineKeyboardButton("🎲 join", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("🎲 join", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("🟢 verify", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Check if it's a callback query or message
        if hasattr(update, 'callback_query') and update.callback_query:
            try:
                await update.callback_query.message.reply_photo(
                    photo=VERIFY_IMAGE_URL,
                    caption="🛑 join channel and verify🚨",
                    reply_markup=reply_markup
                )
            except Exception as e:
                print(f"Error sending verification message: {e}")
                await update.callback_query.message.reply_text(
                    "🛑 join channel and verify🚨",
                    reply_markup=reply_markup
                )
        else:
            try:
                await update.message.reply_photo(
                    photo=VERIFY_IMAGE_URL,
                    caption="🛑 join channel and verify🚨",
                    reply_markup=reply_markup
                )
            except Exception as e:
                print(f"Error sending verification message: {e}")
                await update.message.reply_text(
                    "🛑 join channel and verify🚨",
                    reply_markup=reply_markup
                )
        return False
    return True

# ==== API Query ====
def query_leakosint(query: str):
    # First try the original query
    normalized_query = normalize_phone_number(query)
    
    # Check if it's a name or email and optimize
    if not re.match(r'^[\d+]+$', query):  # Not a phone number
        if '@' in query:  # Email
            optimized_query = optimize_email_query(query)
        else:  # Name
            optimized_query = optimize_name_query(query)
        
        # Try both original and optimized queries
        results = {}
        
        # Try optimized query first
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
        
        # If optimized query is different from original, try original too
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
            
            # Combine results if both queries returned data
            if "List" in results.get("optimized", {}) and "List" in results.get("original", {}):
                combined_result = {"List": {}}
                
                # Merge results from both queries
                for source in ["optimized", "original"]:
                    for db, data in results[source].get("List", {}).items():
                        if db not in combined_result["List"]:
                            combined_result["List"][db] = data
                        else:
                            # Merge data from same database
                            combined_result["List"][db]["Data"].extend(data["Data"])
                
                return combined_result
            
            # Return whichever has data
            if "List" in results.get("optimized", {}):
                return results["optimized"]
            elif "List" in results.get("original", {}):
                return results["original"]
            else:
                return {"Error": "No data found"}
        
        return results.get("optimized", {})
    
    else:
        # Phone number query - use standard approach
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
        return ["🚧server is maintenance"]

    results = []
    current_result = ""
    results_count = 0
    seen_entries = set()  # Track seen entries to avoid duplicates
    
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
            
            # Create a unique identifier for this entry to check for duplicates
            entry_id = f"{name}|{father}|{mobile}|{doc}|{email}"
            
            # Skip duplicate entries
            if entry_id in seen_entries:
                continue
            seen_entries.add(entry_id)
            
            # Skip empty results (all fields are N/A or empty)
            all_fields_empty = True
            for field in [name, father, mobile, alt1, alt2, alt3, alt4, alt5, doc, email]:
                if field != "N/A" and field.strip() != "":
                    all_fields_empty = False
                    break
            
            if all_fields_empty:
                continue

            result_entry = f"""
👤 name- {name}
👨 father-{father}
📞 mobile- {mobile}
📱 alt number1- {alt1}
📱 alt number2- {alt2}
📱 alt number3- {alt3}
📱 alt number 4- {alt4}
📱 alt number5 - {alt5}
📧 email- {email}
🪪 aadhar- {doc}
🧭 circle- {region}
🏠 address- {address}
"""
            
            # If adding this entry would exceed the max length, start a new message
            if len(current_result) + len(result_entry) > max_length:
                if current_result:
                    results.append(current_result)
                current_result = result_entry
            else:
                current_result += result_entry
                
            results_count += 1

    if results_count == 0:
        return ["🚫 data not found"]
    
    # Add the last result if it exists
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
    
    # Format join date if needed
    if join_date != "N/A":
        try:
            dt = datetime.strptime(join_date, "%Y-%m-%d")
            join_date_display = dt.strftime("%d/%m/%Y")
        except:
            join_date_display = join_date
    else:
        join_date_display = "N/A"

    # Create profile message
    profile_msg = f"""
🃏 name - {name} 
🀄 user ID - {user_id}
🎴 user code - {user_hash}
💎 credit - {credits} 💎
📅 joined : {join_date_display}
🔖 updated : {last_update}
"""

    if edit_message and hasattr(update, 'callback_query'):
        await update.callback_query.edit_message_text(profile_msg)
    elif hasattr(update, 'message'):
        # Send as photo with caption
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
    """Show referral information to user"""
    user_id = update.effective_user.id
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
        
    users = load_users()
    uid = str(user_id)
    
    if uid not in users:
        await update.message.reply_text("Please use /start first to initialize your account.")
        return
    
    user_data = users[uid]
    referral_code = user_data.get("referral_code", generate_referral_code(user_id))
    referrals = user_data.get("referrals", 0)
    referral_credits = user_data.get("referral_credits", 0)
    
    referral_msg = f"""
🎁 Referral Program

Your referral code: `{referral_code}`

👥 People referred: {referrals}
💰 Credits earned: {referral_credits} 💎

Share this link to invite friends:
https://t.me/{(await context.bot.get_me()).username}?start={referral_code}

For each friend who joins and makes a payment, you'll earn 2 💎 credits!
"""
    
    try:
        await update.message.reply_photo(
            photo=REFER_IMAGE_URL,
            caption=referral_msg,
            parse_mode="Markdown"
        )
    except:
        await update.message.reply_text(referral_msg, parse_mode="Markdown")

# ==== Start Command ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name
    
    # Check if user is banned
    if is_user_banned(user_id):
        try:
            await update.message.reply_photo(
                photo=BANNED_IMAGE_URL,
                caption="🚫 You are banned due to Violation of our terms and conditions"
            )
        except:
            await update.message.reply_text("🚫 You are banned due to Violation of our terms and conditions")
        return
    
    # Check for referral code in command arguments
    referred_by = None
    if context.args and len(context.args) > 0:
        referral_code = context.args[0]
        
        # Find user who owns this referral code
        users = load_users()
        for uid, data in users.items():
            if data.get("referral_code") == referral_code:
                referred_by = int(uid)
                break
    
    # Update user data (initialize if new user)
    user_data = update_user(user_id, name=user_name, referred_by=referred_by)
    
    # Give initial credits if this is a new user and hasn't received them yet
    if not user_data.get("initial_credits_given", False):
        user_data["credits"] += 5  # Give 5 initial credits
        user_data["initial_credits_given"] = True
        update_user(user_id, credits=user_data["credits"], initial_credits_given=True)
        
        # Add referral credits to referrer if applicable
        if referred_by:
            add_referral_credits(referred_by)
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
    
    # Send welcome message with image
    welcome_msg = f"""
👋 welcome {user_name} to zarko world
🔍 search any mobile number, email, name
💎 you have {user_data['credits']} credits
    """
    
    try:
        await update.message.reply_photo(
            photo=START_IMAGE_URL,
            caption=welcome_msg,
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        print(f"Error sending photo: {e}")
        await update.message.reply_text(
            welcome_msg,
            reply_markup=get_main_keyboard()
        )
    
    # Log the start event
    log_audit_event(user_id, "START", f"User started bot. Credits: {user_data['credits']}")

# ==== Help Command ====
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
    
    try:
        await update.message.reply_photo(
            photo=HELP_IMAGE_URL,
            caption=HELP_TEXT,
            reply_markup=get_main_keyboard()
        )
    except:
        await update.message.reply_text(
            HELP_TEXT,
            reply_markup=get_main_keyboard()
        )

# ==== Search Command ====
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
    
    try:
        await update.message.reply_photo(
            photo=SEARCH_IMAGE_URL,
            caption=SEARCH_PROMPT_TEXT,
            reply_markup=get_main_keyboard()
        )
    except:
        await update.message.reply_text(
            SEARCH_PROMPT_TEXT,
            reply_markup=get_main_keyboard()
        )

# ==== Credits Command ====
async def credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
    
    users = load_users()
    user_data = users.get(str(user_id), {"credits": 0})
    
    try:
        await update.message.reply_photo(
            photo=CREDITS_IMAGE_URL,
            caption=f"💎 you have {user_data['credits']} credits",
            reply_markup=get_main_keyboard()
        )
    except:
        await update.message.reply_text(
            f"💎 you have {user_data['credits']} credits",
            reply_markup=get_main_keyboard()
        )

# ==== Shop Command ====
async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
    
    # Create inline keyboard for payment packages
    keyboard = []
    for amount, credits in PAYMENT_PACKAGES.items():
        keyboard.append([InlineKeyboardButton(f"₹{amount} - {credits} 💎", callback_data=f"buy_{amount}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await update.message.reply_photo(
            photo=BUY_IMAGE_URL,
            caption="🛍️ Choose a package:",
            reply_markup=reply_markup
        )
    except:
        await update.message.reply_text(
            "🛍️ Choose a package:",
            reply_markup=reply_markup
        )

# ==== Profile Command ====
async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
    
    users = load_users()
    user_data = users.get(str(user_id), {"credits": 0, "last_update": "N/A", "name": "Unknown"})
    
    await show_profile(update, context, user_id, user_data)

# ==== Deposit Command ====
async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
    
    # Create inline keyboard for payment packages
    keyboard = []
    for amount, credits in PAYMENT_PACKAGES.items():
        keyboard.append([InlineKeyboardButton(f"₹{amount} - {credits} 💎", callback_data=f"deposit_{amount}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await update.message.reply_photo(
            photo=DEPOSIT_IMAGE_URL,
            caption="💳 Choose a deposit amount:",
            reply_markup=reply_markup
        )
    except:
        await update.message.reply_text(
            "💳 Choose a deposit amount:",
            reply_markup=reply_markup
        )

# ==== Admin Command ====
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
    
    # Check if user is admin
    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Access denied. Admin only.")
        return
    
    try:
        await update.message.reply_photo(
            photo=ADMIN_IMAGE_URL,
            caption="🧧 Admin Panel",
            reply_markup=get_admin_keyboard()
        )
    except:
        await update.message.reply_text(
            "🧧 Admin Panel",
            reply_markup=get_admin_keyboard()
        )

# ==== Gift Command ====
async def gift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
    
    keyboard = [
        [InlineKeyboardButton("🎁 Claim Gift Code", callback_data="claim_gift")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await update.message.reply_photo(
            photo=GIFT_IMAGE_URL,
            caption="🎁 Gift Center\n\nClaim a gift code or check for available gifts",
            reply_markup=reply_markup
        )
    except:
        await update.message.reply_text(
            "🎁 Gift Center\n\nClaim a gift code or check for available gifts",
            reply_markup=reply_markup
        )

# ==== Refer Command ====
async def refer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
    
    await show_referral_info(update, context)

# ==== Handle Messages ====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Check if user is banned
    if is_user_banned(user_id):
        try:
            await update.message.reply_photo(
                photo=BANNED_IMAGE_URL,
                caption="🚫 You are banned due to Violation of our terms and conditions"
            )
        except:
            await update.message.reply_text("🚫 You are banned due to Violation of our terms and conditions")
        return
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
    
    # Handle button presses
    if message_text == "🔍 search":
        await search_command(update, context)
    elif message_text == "💎 credits":
        await credits_command(update, context)
    elif message_text == "🎖️ profile":
        await profile_command(update, context)
    elif message_text == "🛍️ shop":
        await shop_command(update, context)
    elif message_text == "💠 refer":
        await refer_command(update, context)
    elif message_text == "🎁 gift":
        await gift_command(update, context)
    elif message_text == "💳 deposit":
        await deposit_command(update, context)
    elif message_text == "☎️ help":
        await help_command(update, context)
    elif message_text == "🧧 admin":
        await admin_command(update, context)
    elif message_text == "🎲 main menu":
        await update.message.reply_text(
            "Main Menu",
            reply_markup=get_main_keyboard()
        )
    else:
        # Assume it's a search query
        await process_search_query(update, context, message_text)

# ==== Process Search Query ====
async def process_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    user_id = update.effective_user.id
    users = load_users()
    uid = str(user_id)
    
    # Check if user exists and has credits
    if uid not in users:
        await update.message.reply_text("Please use /start first to initialize your account.")
        return
    
    user_data = users[uid]
    
    # Check if user has enough credits
    if user_data["credits"] < 1:
        await update.message.reply_text("❌ Insufficient credits. Please purchase more credits.")
        return
    
    # Check if this search type is locked
    is_locked, lock_message = check_search_type_locked(query)
    if is_locked:
        await update.message.reply_text(f"🔒 {lock_message}")
        return
    
    # Show searching message
    searching_msg = await update.message.reply_text("🔍 Searching...")
    
    # Query the API
    resp = query_leakosint(query)
    
    # Format results
    results = format_results(resp)
    
    # Deduct credit
    user_data["credits"] -= 1
    user_data["last_update"] = datetime.now().strftime("%d/%m - %I:%M %p")
    update_user(user_id, credits=user_data["credits"])
    
    # Update searching message
    await searching_msg.edit_text(f"✅ Search completed! Used 1 credit. Remaining: {user_data['credits']} 💎")
    
    # Send results
    for result in results:
        await update.message.reply_text(result)
    
    # Log the search
    log_audit_event(user_id, "SEARCH", f"Query: {query}, Results: {len(results)}")

# ==== Handle Callback Queries ====
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    callback_data = query.data
    
    # Check if user is banned
    if is_user_banned(user_id):
        try:
            await query.message.reply_photo(
                photo=BANNED_IMAGE_URL,
                caption="🚫 You are banned due to Violation of our terms and conditions"
            )
        except:
            await query.message.reply_text("🚫 You are banned due to Violation of our terms and conditions")
        return
    
    # Handle verification callback
    if callback_data == "verify":
        is_member = await check_membership(update, context, user_id)
        if is_member:
            await query.edit_message_text("✅ Verification successful! You can now use the bot.")
        else:
            await query.answer("Please join both channels first!", show_alert=True)
    
    # Handle back to main menu
    elif callback_data == "back_to_main":
        await query.edit_message_text(
            "Main Menu",
            reply_markup=get_main_keyboard()
        )
    
    # Handle buy package
    elif callback_data.startswith("buy_"):
        amount = int(callback_data.split("_")[1])
        credits = PAYMENT_PACKAGES[amount]
        
        # Create payment record
        payment_id = create_pending_payment(user_id, amount, credits)
        
        # Generate UPI QR code
        qr_buffer = generate_upi_qr(amount, UPI_ID)
        
        # Create payment message
        payment_msg = f"""
💳 Payment Details

💰 Amount: ₹{amount}
🎁 Credits: {credits} 💎
📱 UPI ID: `{UPI_ID}`
🆔 Payment ID: {payment_id}

1. Send exactly ₹{amount} to the UPI ID above
2. Take a screenshot of the payment
3. Send the screenshot to @{OWNER_USERNAME[1:]}

Your credits will be added after manual verification.
"""
        
        # Send QR code and payment instructions
        await query.message.reply_photo(
            photo=qr_buffer,
            caption=payment_msg,
            parse_mode="Markdown"
        )
        
        # Send payment request to admin bot
        await send_payment_request_to_admin(payment_id, user_id, get_user_name(user_id), amount, credits)
        
        await query.edit_message_caption("✅ Payment instructions sent. Please check your messages.")
    
    # Handle deposit package
    elif callback_data.startswith("deposit_"):
        amount = int(callback_data.split("_")[1])
        credits = PAYMENT_PACKAGES[amount]
        
        # Create payment record
        payment_id = create_pending_payment(user_id, amount, credits)
        
        # Generate UPI QR code
        qr_buffer = generate_upi_qr(amount, UPI_ID)
        
        # Create payment message
        payment_msg = f"""
💳 Payment Details

💰 Amount: ₹{amount}
🎁 Credits: {credits} 💎
📱 UPI ID: `{UPI_ID}`
🆔 Payment ID: {payment_id}

1. Send exactly ₹{amount} to the UPI ID above
2. Take a screenshot of the payment
3. Send the screenshot to @{OWNER_USERNAME[1:]}

Your credits will be added after manual verification.
"""
        
        # Send QR code and payment instructions
        await query.message.reply_photo(
            photo=qr_buffer,
            caption=payment_msg,
            parse_mode="Markdown"
        )
        
        # Send payment request to admin bot
        await send_payment_request_to_admin(payment_id, user_id, get_user_name(user_id), amount, credits)
        
        await query.edit_message_caption("✅ Payment instructions sent. Please check your messages.")
    
    # Handle gift claim
    elif callback_data == "claim_gift":
        await query.edit_message_text(
            "🎁 Enter the gift code:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_gift")]])
        )
        context.user_data["awaiting_gift_code"] = True
    
    # Handle back to gift menu
    elif callback_data == "back_to_gift":
        keyboard = [
            [InlineKeyboardButton("🎁 Claim Gift Code", callback_data="claim_gift")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎁 Gift Center\n\nClaim a gift code or check for available gifts",
            reply_markup=reply_markup
        )
    
    # Handle admin payment approval/rejection
    elif callback_data.startswith("approve_") or callback_data.startswith("reject_"):
        # Check if user is admin
        if user_id != ADMIN_ID:
            await query.answer("🚫 Admin only action", show_alert=True)
            return
        
        action, payment_id = callback_data.split("_", 1)
        
        if action == "approve":
            success, message = await process_payment_approval(payment_id, user_id)
            if success:
                await query.edit_message_text(f"✅ {message}")
            else:
                await query.edit_message_text(f"❌ {message}")
        else:
            # For rejection, we need to ask for reason
            context.user_data["awaiting_rejection_reason"] = payment_id
            await query.edit_message_text("📝 Please provide a reason for rejection:")
    
    # Handle other admin callbacks (simplified for brevity)
    else:
        await query.edit_message_text("❌ Invalid option")

# ==== Handle Admin Messages ====
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Check if user is admin
    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Access denied. Admin only.")
        return
    
    # Handle admin button presses
    if message_text == "🃏 add credits":
        await update.message.reply_text("👤 Enter user ID and credits to add (format: user_id credits):")
        context.user_data["admin_action"] = "add_credits"
    elif message_text == "💶 set credits":
        await update.message.reply_text("👤 Enter user ID and credits to set (format: user_id credits):")
        context.user_data["admin_action"] = "set_credits"
    elif message_text == "🏅 user info":
        await update.message.reply_text("👤 Enter user ID to get info:")
        context.user_data["admin_action"] = "user_info"
    elif message_text == "📮 broadcast":
        await update.message.reply_text("📢 Enter message to broadcast:")
        context.user_data["admin_action"] = "broadcast"
    elif message_text == "🎁 generate gift":
        await update.message.reply_text("🎁 Enter gift amount and name (format: amount name):")
        context.user_data["admin_action"] = "generate_gift"
    elif message_text == "📑 referral":
        await update.message.reply_text("👤 Enter user ID to get referral stats:")
        context.user_data["admin_action"] = "referral_stats"
    elif message_text == "⛔ ban user":
        await update.message.reply_text("👤 Enter user ID to ban:")
        context.user_data["admin_action"] = "ban_user"
    elif message_text == "🔓 unban user":
        await update.message.reply_text("👤 Enter user ID to unban:")
        context.user_data["admin_action"] = "unban_user"
    elif message_text == "🔒 lock search":
        await update.message.reply_text("🔒 Enter search type to lock (number/email/name):")
        context.user_data["admin_action"] = "lock_search"
    elif message_text == "🔓 unlock search":
        await update.message.reply_text("🔓 Enter search type to unlock (number/email/name):")
        context.user_data["admin_action"] = "unlock_search"
    elif message_text == "📊 stats":
        # Show bot statistics
        users = load_users()
        total_users = len(users)
        total_credits = sum(user.get("credits", 0) for user in users.values())
        total_searches = sum(user.get("searches", 0) for user in users.values())
        
        stats_msg = f"""
📊 Bot Statistics

👥 Total Users: {total_users}
💎 Total Credits: {total_credits}
🔍 Total Searches: {total_searches}
"""
        await update.message.reply_text(stats_msg)
    elif message_text == "🎲 main menu":
        await update.message.reply_text(
            "Main Menu",
            reply_markup=get_main_keyboard()
        )

# ==== Handle Admin Input ====
async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Check if user is admin
    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Access denied. Admin only.")
        return
    
    action = context.user_data.get("admin_action")
    
    if not action:
        return
    
    if action == "add_credits":
        try:
            parts = message_text.split()
            target_user_id = int(parts[0])
            credits_to_add = int(parts[1])
            
            users = load_users()
            uid = str(target_user_id)
            
            if uid not in users:
                await update.message.reply_text("❌ User not found")
                return
            
            users[uid]["credits"] += credits_to_add
            save_users(users)
            
            await update.message.reply_text(f"✅ Added {credits_to_add} credits to user {target_user_id}. New balance: {users[uid]['credits']}")
            
            # Log the action
            log_audit_event(user_id, "ADMIN_ADD_CREDITS", f"Target: {target_user_id}, Credits: {credits_to_add}")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    elif action == "set_credits":
        try:
            parts = message_text.split()
            target_user_id = int(parts[0])
            credits_to_set = int(parts[1])
            
            users = load_users()
            uid = str(target_user_id)
            
            if uid not in users:
                await update.message.reply_text("❌ User not found")
                return
            
            users[uid]["credits"] = credits_to_set
            save_users(users)
            
            await update.message.reply_text(f"✅ Set credits for user {target_user_id} to {credits_to_set}")
            
            # Log the action
            log_audit_event(user_id, "ADMIN_SET_CREDITS", f"Target: {target_user_id}, Credits: {credits_to_set}")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    elif action == "user_info":
        try:
            target_user_id = int(message_text)
            users = load_users()
            uid = str(target_user_id)
            
            if uid not in users:
                await update.message.reply_text("❌ User not found")
                return
            
            user_data = users[uid]
            await show_profile(update, context, target_user_id, user_data)
            
            # Log the action
            log_audit_event(user_id, "ADMIN_USER_INFO", f"Target: {target_user_id}")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    elif action == "broadcast":
        # Store the broadcast message and ask for confirmation
        context.user_data["broadcast_message"] = message_text
        context.user_data["admin_action"] = "confirm_broadcast"
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes", callback_data="broadcast_confirm")],
            [InlineKeyboardButton("❌ No", callback_data="broadcast_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📢 Confirm broadcast:\n\n{message_text}",
            reply_markup=reply_markup
        )
    
    elif action == "generate_gift":
        try:
            parts = message_text.split(" ", 1)
            amount = int(parts[0])
            name = parts[1] if len(parts) > 1 else "Anonymous Gift"
            
            code = create_gift_code(amount, name, user_id)
            
            await update.message.reply_text(f"🎁 Gift code created:\n\nCode: `{code}`\nAmount: {amount} 💎\nName: {name}")
            
            # Log the action
            log_audit_event(user_id, "ADMIN_GENERATE_GIFT", f"Code: {code}, Amount: {amount}, Name: {name}")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    elif action == "referral_stats":
        try:
            target_user_id = int(message_text)
            users = load_users()
            uid = str(target_user_id)
            
            if uid not in users:
                await update.message.reply_text("❌ User not found")
                return
            
            user_data = users[uid]
            referrals = user_data.get("referrals", 0)
            referral_credits = user_data.get("referral_credits", 0)
            referral_code = user_data.get("referral_code", "N/A")
            
            stats_msg = f"""
📊 Referral Stats for User {target_user_id}

🎯 Referral Code: {referral_code}
👥 People Referred: {referrals}
💰 Credits Earned: {referral_credits} 💎
"""
            await update.message.reply_text(stats_msg)
            
            # Log the action
            log_audit_event(user_id, "ADMIN_REFERRAL_STATS", f"Target: {target_user_id}")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    elif action == "ban_user":
        try:
            target_user_id = int(message_text)
            banned_users = load_banned_users()
            uid = str(target_user_id)
            
            if uid in banned_users:
                await update.message.reply_text("❌ User is already banned")
                return
            
            banned_users[uid] = {
                "banned_by": user_id,
                "banned_at": datetime.now().isoformat(),
                "reason": "Admin action"
            }
            
            save_banned_users(banned_users)
            await update.message.reply_text(f"✅ User {target_user_id} has been banned")
            
            # Log the action
            log_audit_event(user_id, "ADMIN_BAN_USER", f"Target: {target_user_id}")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    elif action == "unban_user":
        try:
            target_user_id = int(message_text)
            banned_users = load_banned_users()
            uid = str(target_user_id)
            
            if uid not in banned_users:
                await update.message.reply_text("❌ User is not banned")
                return
            
            del banned_users[uid]
            save_banned_users(banned_users)
            await update.message.reply_text(f"✅ User {target_user_id} has been unbanned")
            
            # Log the action
            log_audit_event(user_id, "ADMIN_UNBAN_USER", f"Target: {target_user_id}")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    elif action == "lock_search":
        search_type = message_text.lower().strip()
        locks = load_search_locks()
        
        if search_type not in ["number", "email", "name"]:
            await update.message.reply_text("❌ Invalid search type. Use 'number', 'email', or 'name'")
            return
        
        locks[search_type] = True
        save_search_locks(locks)
        await update.message.reply_text(f"✅ {search_type.capitalize()} searches are now locked")
        
        # Log the action
        log_audit_event(user_id, "ADMIN_LOCK_SEARCH", f"Type: {search_type}")
    
    elif action == "unlock_search":
        search_type = message_text.lower().strip()
        locks = load_search_locks()
        
        if search_type not in ["number", "email", "name"]:
            await update.message.reply_text("❌ Invalid search type. Use 'number', 'email', or 'name'")
            return
        
        locks[search_type] = False
        save_search_locks(locks)
        await update.message.reply_text(f"✅ {search_type.capitalize()} searches are now unlocked")
        
        # Log the action
        log_audit_event(user_id, "ADMIN_UNLOCK_SEARCH", f"Type: {search_type}")
    
    # Clear the action
    context.user_data["admin_action"] = None

# ==== Handle Gift Code Input ====
async def handle_gift_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text
    
    if not context.user_data.get("awaiting_gift_code"):
        return
    
    # Process gift code
    code = message_text.strip().upper()
    success, result = claim_gift_code(code, user_id, update.effective_user.full_name)
    
    if success:
        # Add credits to user
        users = load_users()
        uid = str(user_id)
        
        if uid not in users:
            await update.message.reply_text("Please use /start first to initialize your account.")
            return
        
        users[uid]["credits"] += result
        save_users(users)
        
        await update.message.reply_text(f"🎉 Gift code redeemed! You received {result} 💎 credits.")
        
        # Log the action
        log_audit_event(user_id, "GIFT_CODE_REDEEMED", f"Code: {code}, Credits: {result}")
    else:
        await update.message.reply_text(f"❌ {result}")
    
    # Clear the state
    context.user_data["awaiting_gift_code"] = False

# ==== Handle Rejection Reason Input ====
async def handle_rejection_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text
    
    if not context.user_data.get("awaiting_rejection_reason"):
        return
    
    # Check if user is admin
    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Access denied. Admin only.")
        return
    
    payment_id = context.user_data["awaiting_rejection_reason"]
    success, message = await process_payment_rejection(payment_id, user_id, message_text)
    
    if success:
        await update.message.reply_text(f"✅ {message}")
    else:
        await update.message.reply_text(f"❌ {message}")
    
    # Clear the state
    context.user_data["awaiting_rejection_reason"] = None

# ==== Handle Admin Callback Queries ====
async def handle_admin_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    callback_data = query.data
    
    # Check if user is admin
    if user_id != ADMIN_ID:
        await query.answer("🚫 Admin only action", show_alert=True)
        return
    
    if callback_data == "broadcast_confirm":
        message = context.user_data.get("broadcast_message")
        
        if not message:
            await query.edit_message_text("❌ No broadcast message found")
            return
        
        # Send broadcast to all users
        users = load_users()
        success_count = 0
        fail_count = 0
        
        for uid in users:
            try:
                await context.bot.send_message(chat_id=uid, text=f"📢 Broadcast:\n\n{message}")
                success_count += 1
            except Exception as e:
                print(f"Failed to send broadcast to {uid}: {e}")
                fail_count += 1
        
        await query.edit_message_text(f"✅ Broadcast completed!\n\nSuccess: {success_count}\nFailed: {fail_count}")
        
        # Log the action
        log_audit_event(user_id, "ADMIN_BROADCAST", f"Message: {message[:50]}..., Success: {success_count}, Failed: {fail_count}")
        
    elif callback_data == "broadcast_cancel":
        await query.edit_message_text("❌ Broadcast cancelled")
    
    # Clear the broadcast data
    context.user_data["broadcast_message"] = None
    context.user_data["admin_action"] = None

# ==== Main Function ====
def main():
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("credits", credits_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("shop", shop_command))
    application.add_handler(CommandHandler("deposit", deposit_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("gift", gift_command))
    application.add_handler(CommandHandler("refer", refer_command))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Admin handlers
    application.add_handler(MessageHandler(filters.Regex("^(🃏 add credits|💶 set credits|🏅 user info|📮 broadcast|🎁 generate gift|📑 referral|⛔ ban user|🔓 unban user|🔒 lock search|🔓 unlock search|📊 stats)$"), handle_admin_message))
    application.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), handle_admin_input))
    application.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), handle_rejection_reason))
    
    # Gift code handler
    application.add_handler(MessageHandler(filters.TEXT, handle_gift_code_input))
    
    # Admin callback handler
    application.add_handler(CallbackQueryHandler(handle_admin_callback_query, pattern="^broadcast_"))
    
    # Start the Bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()