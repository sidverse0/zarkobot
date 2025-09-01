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
        await update.message.reply_text("❌ user not found /start first")
        return
        
    user_data = users[uid]
    referral_code = user_data.get("referral_code", generate_referral_code(user_id))
    referrals = user_data.get("referrals", 0)
    referral_credits = user_data.get("referral_credits", 0)
    
    # Generate referral link
    bot_username = context.bot.username
    referral_link = f"https://t.me/{bot_username}?start={referral_code}"
    
    referral_msg = f"""
refere and earn

your refer link 
{referral_link}

🎯 your refer -
👥 total refer -  {referrals}
💶 total credit - {referral_credits} 💎
"""

    # Send as photo with caption
    await update.message.reply_photo(
        photo=REFER_IMAGE_URL, 
        caption=referral_msg
    )

# ==== Buy Command Function ====
async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
        
    buy_message = """
buy any thing
shop 
contact 
owner - pvt_s1n
"""

    # Send as photo with caption
    await update.message.reply_photo(
        photo=BUY_IMAGE_URL, 
        caption=buy_message
    )

# ==== Gift Code Function ====
async def gift_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle gift code button press"""
    user_id = update.effective_user.id
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
    
    # Clear any existing states
    context.user_data.pop('in_search_mode', None)
    context.user_data.pop('admin_action', None)
    context.user_data.pop('admin_mode', None)
    
    # Set state to wait for gift code
    context.user_data['waiting_for_gift_code'] = True
    
    # Send prompt message
    await update.message.reply_photo(
        photo=GIFT_IMAGE_URL,
        caption="gift code \n\nׂ please enter code"
    )

async def process_gift_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process gift code entered by user"""
    user_id = update.effective_user.id
    gift_code = update.message.text.strip().upper()
    
    # Check if we're waiting for a gift code
    if not context.user_data.get('waiting_for_gift_code', False):
        return
    
    # Clear the state
    context.user_data['waiting_for_gift_code'] = False
    
    # Check if user exists
    users = load_users()
    uid = str(user_id)
    
    if uid not in users:
        await update.message.reply_text("❌ user not found /start first🛑")
        return
    
    # Check if user has already claimed this code
    if gift_code in users[uid].get("claimed_gift_codes", []):
        await update.message.reply_text("🚫 already claimed🥂")
        return
    
    # Try to claim the gift code
    success, result = claim_gift_code(gift_code, user_id, users[uid]["name"])
    
    if success:
        # Add credits to user
        users[uid]["credits"] += result
        users[uid]["last_update"] = datetime.now().strftime("%d/%m - %I:%M %p")
        
        # Add to claimed codes
        if "claimed_gift_codes" not in users[uid]:
            users[uid]["claimed_gift_codes"] = []
        users[uid]["claimed_gift_codes"].append(gift_code)
        
        save_users(users)
        
        # Broadcast the claim
        gift_codes = load_gift_codes()
        gift_name = gift_codes[gift_code].get("name", "Unknown Gift")
        
        broadcast_msg = f"""
🎲 gift {gift_name}
💶 amount {result} 💎
🃏 claimed by {users[uid]['name']}
🎖️ id  {user_id}
"""
        
        # Broadcast to all users
        await broadcast_to_all_users(context, broadcast_msg)
        
        # Send success message to user
        await update.message.reply_text(
            f"🏅 gift claimed successfully!\n\n"
            f"🎁 you received - {result} 💎\n"
            f"💶 new balance - {users[uid]['credits']} 💎"
        )
        
        # Log the claim
        log_audit_event(user_id, "GIFT_CODE_CLAIMED", f"Code: {gift_code}, Amount: {result}")
    else:
        await update.message.reply_text(f"❌ {result}")

async def broadcast_to_all_users(context, message):
    """Broadcast a message to all users"""
    users = load_users()
    
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=message)
            await asyncio.sleep(0.1)  # Prevent flooding
        except Exception as e:
            print(f"Failed to send message to {uid}: {e}")

# ==== Fast Animated Spinner ====
async def show_spinner(update, context, message):
    spinner_frames = [
        "search...",
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
    """Check if user is admin"""
    return user_id == ADMIN_ID

async def notify_user_credits(context, user_id, action, amount, new_balance):
    """Notify user when admin modifies their credits"""
    try:
        message = f"""
credit update 

🧧 owner has {action} {amount} 💎 to your account 

💶 new balance {new_balance} 💎
"""
        await context.bot.send_message(chat_id=user_id, text=message)
    except Exception as e:
        print(f"Could not notify user {user_id}: {e}")

async def addcredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add credits to a user"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
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
    
    # Notify the user
    await notify_user_credits(context, target_user_id, "added", amount, users[uid]['credits'])
    
    await update.message.reply_text(f"✅ Added {amount} Credits To User {target_user_id}\nNew Balance ➜ {users[uid]['credits']} 🪙")

async def setcredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user's credits to specific amount"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
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
    
    # Notify the user
    await notify_user_credits(context, target_user_id, "set", amount, amount)
    
    await update.message.reply_text(f"✅ Set Credits For User {target_user_id} To {amount} 🪙")

async def userinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user information"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
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
    """Broadcast message to all users"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
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
announcements -

{message}

"""
    
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=broadcast_msg)
            success_count += 1
        except Exception as e:
            print(f"Failed to send to {uid}: {e}")
            fail_count += 1
        await asyncio.sleep(0.1)  # Prevent flooding

    log_audit_event(user_id, "ADMIN_BROADCAST", 
                   f"Message: {message}, Success: {success_count}, Failed: {fail_count}")
    
    await update.message.reply_text(f"📢 Broadcast Completed!\nSuccess ➜ {success_count}\nFailed ➜ {fail_count}")

# ==== Generate Gift Code Function ====
async def generate_gift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate a new gift code"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Admin Only")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Use /gengift <amount> <name>")
        return

    try:
        amount = int(context.args[0])
        name = " ".join(context.args[1:])
        
        # Generate gift code
        code = create_gift_code(amount, name, user_id)
        
        # Broadcast the new gift code
        broadcast_msg = f"""
new gift 
🎲  gift  {name}
💶 amount - {amount} 💎
🔑 code -  {code}
⏰ valid until clim
"""
        
        # Broadcast to all users
        await broadcast_to_all_users(context, broadcast_msg)
        
        # Create inline keyboard with copy button
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
    """Handle copy code button click"""
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
    """Show referral statistics for admin"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Admin Only")
        return

    users = load_users()
    
    # Calculate total referrals and credits
    total_referrals = sum(user.get("referrals", 0) for user in users.values())
    total_referral_credits = sum(user.get("referral_credits", 0) for user in users.values())
    
    # Get top referrers
    top_referrers = sorted(
        [(uid, user_data.get("name", "Unknown"), user_data.get("referrals", 0), user_data.get("referral_credits", 0)) 
         for uid, user_data in users.items() if user_data.get("referrals", 0) > 0],
        key=lambda x: x[2],  # Sort by referral count
        reverse=True
    )[:10]  # Top 10 referrers

    stats_msg = f"""
📊 [REFERRAL STATS] 📊
────────────────────

📈 Total Referrals: {total_referrals}
🎁 Total Referral Credits: {total_referral_credits}

🏆 Top Referrers:
"""
    
    for i, (uid, name, referrals, credits) in enumerate(top_referrers, 1):
        stats_msg += f"{i}. {name} (ID: {uid}) - {referrals} referrals, {credits} credits\n"
    
    # Add pagination if needed (for full user list)
    keyboard = [
        [InlineKeyboardButton("📋 Full Referral List", callback_data="full_referral_list_1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(stats_msg, reply_markup=reply_markup)

async def handle_full_referral_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show full referral list with pagination"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await query.edit_message_text("❌ Admin Only")
        return
    
    # Get page number from callback data
    page_num = int(query.data.split("_")[-1])
    
    users = load_users()
    
    # Get all users with referrals
    referrers = [(uid, user_data.get("name", "Unknown"), user_data.get("referrals", 0), user_data.get("referral_credits", 0)) 
                 for uid, user_data in users.items() if user_data.get("referrals", 0) > 0]
    
    # Sort by referral count
    referrers.sort(key=lambda x: x[2], reverse=True)
    
    # Pagination
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
    
    # Create pagination buttons
    keyboard = []
    if page_num > 1:
        keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"full_referral_list_{page_num-1}"))
    if page_num < total_pages:
        keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f"full_referral_list_{page_num+1}"))
    
    reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None
    
    await query.edit_message_text(list_msg, reply_markup=reply_markup)

# ==== Ban/Unban User Functions ====
async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user by ID"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Admin Only")
        return

    if len(context.args) < 1:
        await update.message.reply_text("❌ Use /ban <user_id> [reason]")
        return

    try:
        target_user_id = int(context.args[0])
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Violation of terms and conditions"
        
        # Load banned users
        banned_users = load_banned_users()
        
        # Add user to banned list
        banned_users[str(target_user_id)] = {
            "banned_by": user_id,
            "banned_at": datetime.now().isoformat(),
            "reason": reason
        }
        
        save_banned_users(banned_users)
        
        log_audit_event(user_id, "USER_BANNED", f"Target: {target_user_id}, Reason: {reason}")
        
        await update.message.reply_text(f"✅ User {target_user_id} has been banned.\nReason: {reason}")
        
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID")

async def unban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user by ID"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Admin Only")
        return

    if len(context.args) != 1:
        await update.message.reply_text("❌ Use /unban <user_id>")
        return

    try:
        target_user_id = int(context.args[0])
        
        # Load banned users
        banned_users = load_banned_users()
        
        # Remove user from banned list
        if str(target_user_id) in banned_users:
            del banned_users[str(target_user_id)]
            save_banned_users(banned_users)
            
            log_audit_event(user_id, "USER_UNBANNED", f"Target: {target_user_id}")
            
            await update.message.reply_text(f"✅ User {target_user_id} has been unbanned.")
        else:
            await update.message.reply_text("❌ User is not banned.")
        
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID")

# ==== Lock/Unlock Search Functions ====
async def lock_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lock a search type (number, email, name)"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Admin Only")
        return

    if len(context.args) != 1:
        await update.message.reply_text("❌ Use /lock <number|email|name>")
        return

    search_type = context.args[0].lower()
    
    if search_type not in ["number", "email", "name"]:
        await update.message.reply_text("❌ Invalid search type. Use: number, email, or name")
        return
    
    # Load current locks
    locks = load_search_locks()
    
    # Update the lock
    locks[search_type] = True
    save_search_locks(locks)
    
    log_audit_event(user_id, "SEARCH_LOCKED", f"Type: {search_type}")
    
    await update.message.reply_text(f"✅ {search_type.capitalize()} search has been locked.")

async def unlock_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unlock a search type (number, email, name)"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Admin Only")
        return

    if len(context.args) != 1:
        await update.message.reply_text("❌ Use /unlock <number|email|name>")
        return

    search_type = context.args[0].lower()
    
    if search_type not in ["number", "email", "name"]:
        await update.message.reply_text("❌ Invalid search type. Use: number, email, or name")
        return
    
    # Load current locks
    locks = load_search_locks()
    
    # Update the lock
    locks[search_type] = False
    save_search_locks(locks)
    
    log_audit_event(user_id, "SEARCH_UNLOCKED", f"Type: {search_type}")
    
    await update.message.reply_text(f"✅ {search_type.capitalize()} search has been unlocked.")

# ==== Payment Functions ====
async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle deposit button press"""
    user_id = update.effective_user.id
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
    
    # Clear any existing states
    context.user_data.pop('in_search_mode', None)
    context.user_data.pop('waiting_for_gift_code', None)
    context.user_data.pop('admin_action', None)
    context.user_data.pop('admin_mode', None)
    
    # Create inline keyboard for payment packages
    keyboard = []
    for amount, credits in PAYMENT_PACKAGES.items():
        keyboard.append([InlineKeyboardButton(f"₹{amount} - {credits} 💎", callback_data=f"deposit_{amount}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send deposit message with image
    deposit_msg = """
💳 Deposit Credits

Choose a package:

• ₹10 - 100 💎
• ₹20 - 150 💎  
• ₹30 - 200 💎
• ₹40 - 400 💎
• ₹50 - 500 💎

Click on a package to generate payment QR code.
"""
    
    await update.message.reply_photo(
        photo=DEPOSIT_IMAGE_URL,
        caption=deposit_msg,
        reply_markup=reply_markup
    )

async def handle_deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle deposit package selection"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == "back_to_main":
        # Clear any states and return to main menu
        context.user_data.pop('in_search_mode', None)
        context.user_data.pop('waiting_for_gift_code', None)
        context.user_data.pop('admin_action', None)
        context.user_data.pop('admin_mode', None)
        
        await query.message.edit_caption(
            caption="🔙 Returning to main menu",
            reply_markup=None
        )
        await context.bot.send_message(
            chat_id=user_id,
            text="Choose an option:",
            reply_markup=get_main_keyboard()
        )
        return
    
    if not data.startswith("deposit_"):
        return
    
    amount = int(data.split("_")[1])
    credits = PAYMENT_PACKAGES.get(amount, 0)
    
    if credits == 0:
        await query.edit_message_text("❌ Invalid package selected.")
        return
    
    # Generate payment ID
    payment_id = create_pending_payment(user_id, amount, credits)
    
    # Generate QR code
    qr_buffer = generate_upi_qr(amount, UPI_ID)
    
    # Create payment message
    payment_msg = f"""
💳 Payment Details

Amount: ₹{amount}
Credits: {credits} 💎
UPI ID: {UPI_ID}
Payment ID: {payment_id}

Please scan the QR code and send payment to the UPI ID above.

After payment, send screenshot to {OWNER_USERNAME} for verification.
"""
    
    # Send message with QR code
    await query.message.reply_photo(
        photo=qr_buffer,
        caption=payment_msg
    )
    
    # Edit original message to show payment initiated
    await query.edit_message_caption(
        caption=f"Payment initiated for ₹{amount}. Check the QR code below.",
        reply_markup=None
    )

async def handle_cancel_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment cancellation"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_payment":
        await query.edit_message_caption(caption="Payment cancelled.")

# ==== ADMIN PANEL HANDLERS ====
async def handle_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin panel button clicks"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Admin Only.")
        return
        
    # Clear any existing states
    context.user_data.pop('in_search_mode', None)
    context.user_data.pop('waiting_for_gift_code', None)
    
    # Set admin mode
    context.user_data['admin_mode'] = True
    
    text = update.message.text
    
    if text == "🃏 add credits":
        context.user_data['admin_action'] = 'add_credits'
        await update.message.reply_text("👤 Send User ID and Amount (space separated)\nExample: 123456789 10")
        
    elif text == "💶 set credits":
        context.user_data['admin_action'] = 'set_credits'
        await update.message.reply_text("👤 Send User ID and Amount (space separated)\nExample: 123456789 5")
        
    elif text == "🏅 user info":
        context.user_data['admin_action'] = 'user_info'
        await update.message.reply_text("👤 Send User ID to get info")
        
    elif text == "📮 broadcast":
        context.user_data['admin_action'] = 'broadcast'
        await update.message.reply_text("📢 Send Message To Broadcast")
        
    elif text == "🎁 generate gift":
        context.user_data['admin_action'] = 'generate_gift'
        await update.message.reply_text("🎁 Send Amount and Name (space separated)\nExample: 5 Special Gift")
        
    elif text == "📑 referral":
        await referral_stats_command(update, context)
        
    elif text == "⛔ ban user":
        context.user_data['admin_action'] = 'ban_user'
        await update.message.reply_text("👤 Send User ID to ban\nExample: 123456789")
        
    elif text == "🔓 unban user":
        context.user_data['admin_action'] = 'unban_user'
        await update.message.reply_text("👤 Send User ID to unban\nExample: 123456789")
        
    elif text == "🔒 lock search":
        context.user_data['admin_action'] = 'lock_search'
        await update.message.reply_text("🔒 Send search type to lock (number, email, name)")
        
    elif text == "🔓 unlock search":
        context.user_data['admin_action'] = 'unlock_search'
        await update.message.reply_text("🔓 Send search type to unlock (number, email, name)")
        
    elif text == "📊 stats":
        await admin_stats(update, context)
        
    elif text == "🎲 main menu":
        # Clear admin mode and action
        context.user_data.pop('admin_mode', None)
        context.user_data.pop('admin_action', None)
        await update.message.reply_text("🔙 Returning to main menu", reply_markup=get_main_keyboard())

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin input for various actions"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
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
            
            # Notify the user
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
            
            # Notify the user
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
announcements -

{message}

"""
            
            for uid in users:
                try:
                    await context.bot.send_message(chat_id=int(uid), text=broadcast_msg)
                    success_count += 1
                except Exception as e:
                    print(f"Failed to send to {uid}: {e}")
                    fail_count += 1
                await asyncio.sleep(0.1)  # Prevent flooding

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
                
                # Generate gift code
                code = create_gift_code(amount, name, user_id)
                
                # Broadcast the new gift code
                broadcast_msg = f"""
new gift 
🎲  gift  {name}
💶 amount - {amount} 💎
🔑 code -  {code}
⏰ valid until clim
"""
                
                # Broadcast to all users
                await broadcast_to_all_users(context, broadcast_msg)
                
                # Create inline keyboard with copy button
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
        
        elif action == 'ban_user':
            target_user_id = int(text)
            reason = "Violation of terms and conditions"
            
            # Load banned users
            banned_users = load_banned_users()
            
            # Add user to banned list
            banned_users[str(target_user_id)] = {
                "banned_by": user_id,
                "banned_at": datetime.now().isoformat(),
                "reason": reason
            }
            
            save_banned_users(banned_users)
            
            log_audit_event(user_id, "USER_BANNED", f"Target: {target_user_id}, Reason: {reason}")
            
            await update.message.reply_text(f"✅ User {target_user_id} has been banned.\nReason: {reason}", reply_markup=get_admin_keyboard())
            
        elif action == 'unban_user':
            target_user_id = int(text)
            
            # Load banned users
            banned_users = load_banned_users()
            
            # Remove user from banned list
            if str(target_user_id) in banned_users:
                del banned_users[str(target_user_id)]
                save_banned_users(banned_users)
                
                log_audit_event(user_id, "USER_UNBANNED", f"Target: {target_user_id}")
                
                await update.message.reply_text(f"✅ User {target_user_id} has been unbanned.", reply_markup=get_admin_keyboard())
            else:
                await update.message.reply_text("❌ User is not banned.", reply_markup=get_admin_keyboard())
                
        elif action == 'lock_search':
            search_type = text.lower()
            
            if search_type not in ["number", "email", "name"]:
                await update.message.reply_text("❌ Invalid search type. Use: number, email, or name", reply_markup=get_admin_keyboard())
                return
            
            # Load current locks
            locks = load_search_locks()
            
            # Update the lock
            locks[search_type] = True
            save_search_locks(locks)
            
            log_audit_event(user_id, "SEARCH_LOCKED", f"Type: {search_type}")
            
            await update.message.reply_text(f"✅ {search_type.capitalize()} search has been locked.", reply_markup=get_admin_keyboard())
            
        elif action == 'unlock_search':
            search_type = text.lower()
            
            if search_type not in ["number", "email", "name"]:
                await update.message.reply_text("❌ Invalid search type. Use: number, email, or name", reply_markup=get_admin_keyboard())
                return
            
            # Load current locks
            locks = load_search_locks()
            
            # Update the lock
            locks[search_type] = False
            save_search_locks(locks)
            
            log_audit_event(user_id, "SEARCH_UNLOCKED", f"Type: {search_type}")
            
            await update.message.reply_text(f"✅ {search_type.capitalize()} search has been unlocked.", reply_markup=get_admin_keyboard())
            
    except ValueError:
        await update.message.reply_text("❌ Invalid input. Please use the correct format.", reply_markup=get_admin_keyboard())
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", reply_markup=get_admin_keyboard())
    
    # Clear the action
    context.user_data['admin_action'] = None

# ==== Pagination Functions ====
def create_pagination_keyboard(current_page, total_pages):
    keyboard = []
    
    # Previous button
    if current_page > 1:
        keyboard.append(InlineKeyboardButton("⬅️", callback_data=f"page_{current_page-1}"))
    
    # Page indicator
    keyboard.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="current_page"))
    
    # Next button
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
        
        # Get the pagination data from context
        if 'pagination' not in context.user_data:
            await query.edit_message_text("❌ Session Expired. Please Search Again.")
            return
            
        pagination_data = context.user_data['pagination']
        pages = pagination_data['pages']
        total_pages = len(pages)
        
        if page_num < 1 or page_num > total_pages:
            await query.answer("❌ Invalid Page")
            return
            
        # Update the message with the new page
        keyboard = create_pagination_keyboard(page_num, total_pages)
        await query.edit_message_text(pages[page_num-1], reply_markup=keyboard)
        
    except (ValueError, IndexError):
        await query.answer("❌ Error Loading Page")

# ==== Handlers ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    
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
        return
    
    # Clear any existing states
    context.user_data.pop('pagination', None)
    context.user_data.pop('in_search_mode', None)
    context.user_data.pop('waiting_for_gift_code', None)
    context.user_data.pop('admin_mode', None)
    context.user_data.pop('admin_action', None)
    
    # Check for referral code in start parameters
    referred_by = None
    if context.args and len(context.args) > 0:
        referral_code = context.args[0]
        
        # Find user with this referral code
        users = load_users()
        for uid, user_data in users.items():
            if user_data.get("referral_code") == referral_code and int(uid) != user_id:
                referred_by = int(uid)
                break
    
    # Log the start command
    log_audit_event(user_id, "START_COMMAND", f"User: {name}, Referred by: {referred_by}")
    
    # Check if user is already in database
    users = load_users()
    user_data = users.get(str(user_id), {})
    
    # Always check current membership status
    is_member = await check_membership(update, context, user_id)
    
    if is_member:
        # User is a member of channels
        if not user_data:
            # New user - add to database with initial credits
            user_data = update_user(user_id, credits=2, 
                                  name=name, 
                                  last_verified=datetime.now().isoformat(),
                                  initial_credits_given=True,
                                  referred_by=referred_by)
            
            # Add referral credits if applicable
            if referred_by and referred_by != user_id:
                add_referral_credits(referred_by)
                log_audit_event(user_id, "REFERRAL_JOIN", f"Referred by: {referred_by}")
            
            add_verification_record(user_id, True, "New user - initial credits granted")
            message = "🍒 verified successfully 🎉🎊\n\n🎁 received 2 free credit 💎\n\n🍷 𝐄ɴᴊᴏʏ 𝐓ʜᴇ 𝐏ᴏᴡᴇʀFᴜʟ 𝐎sɪɴᴛ 𝐁ᴏᴛ 🥂"
            
            await update.message.reply_photo(
                photo=START_IMAGE_URL,
                caption=message,
                reply_markup=get_main_keyboard()
            )
        else:
            # Existing user - just update name if needed
            user_data = update_user(user_id, name=name)
            add_verification_record(user_id, True, "Existing user - membership verified")
            await update.message.reply_photo(
                photo=START_IMAGE_URL,
                caption="🎖️ welcome back \n\n🍷 enjoy bot🥂",
                reply_markup=get_main_keyboard()
            )
    else:
        # User hasn't joined both channels, show join buttons
        keyboard = [
            [InlineKeyboardButton("🎲 join", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("🎲 join", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("🟢 verify", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        add_verification_record(user_id, False, "User not member of required channels")
        
        await update.message.reply_photo(
            photo=VERIFY_IMAGE_URL,
            caption="zarko bot\n\n"
            "🛡️ use this bot \n\n"
            "🔒 join channel\n"
            "🟢 click on verify\n\n"
            "🎁 reward - 2 credit \n"
            "💶 free credit💎\n\n"
            "──── ୨୧ ──────── ୨୧ ──────── ୨୧ ──────── \n"
            "♈ buy unlimited credit and api contact @pvt_s1n",
            reply_markup=reply_markup
        )

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    
    # Check if user is banned
    if is_user_banned(user_id):
        # Send banned message with image
        try:
            await query.message.reply_photo(
                photo=BANNED_IMAGE_URL,
                caption="🚫 You are banned due to Violation of our terms and conditions"
            )
        except:
            await query.message.reply_text("🚫 You are banned due to Violation of our terms and conditions")
        return
    
    # Check if user has joined both channels
    is_member = await check_membership(update, context, user_id)
    
    users = load_users()
    uid = str(user_id)
    user_data = users.get(uid, {})
    
    if is_member:
        if not user_data:
            # New user - add to database with initial credits
            user_data = update_user(user_id, credits=2, name=name, 
                                  last_verified=datetime.now().isoformat(),
                                  initial_credits_given=True)
            add_verification_record(user_id, True, "New user - initial credits granted via verify")
            
            # Show success message
            try:
                await query.message.edit_caption(
                    caption="🍒 🍒 verify successfull 🎉🎊\n\n"
                    "🎁you received 2 credit 💎\n\n"
                    "🍷 enjoy bot"
                )
            except:
                await query.message.reply_text(
                    "🍒 verify successfull 🎉🎊\n\n"
                    "🎁you received 2 credit 💎\n\n"
                    "🍷 enjoy bot"
                )
            await context.bot.send_message(chat_id=user_id, text="Choose an option:", reply_markup=get_main_keyboard())
        else:
            if not user_data.get("initial_credits_given", False):
                # Give initial credits if not given before
                user_data = update_user(user_id, credits=user_data.get("credits", 0) + 2, 
                                      name=name, last_verified=datetime.now().isoformat(),
                                      initial_credits_given=True)
                add_verification_record(user_id, True, "Existing user - initial credits granted via verify")
                
                try:
                    await query.message.edit_caption(
                        caption="🍒 verify successfull 🎉🎊\n\n"
                    "🎁you received 2 credit 💎\n\n"
                    "🍷 enjoy bot"
                    )
                except:
                    await query.message.reply_text(
                        "🍒 verify successfull 🎉🎊\n\n"
                    "🎁you received 2 credit 💎\n\n"
                    "🍷 enjoy bot"
                    )
            else:
                # Already received credits, just update verification status
                user_data = update_user(user_id, name=name, 
                                      last_verified=datetime.now().isoformat())
                add_verification_record(user_id, True, "Existing user - reverified")
                
                try:
                    await query.message.edit_caption(
                        caption="🎖️ welcome bot\n\n"
                        "🍷 enjoy bot"
                    )
                except:
                    await query.message.reply_text(
                        "🎖️ welcome bot\n\n"
                        "🍷 enjoy bot"
                    )
            await context.bot.send_message(chat_id=user_id, text="Choose an option:", reply_markup=get_main_keyboard())
    else:
        # User hasn't joined both channels
        add_verification_record(user_id, False, "Verification failed - not member of channels")
        
        keyboard = [
            [InlineKeyboardButton("🎲 join", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("🎲 join", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}")],
            [InlineKeyboardButton("🔄 retry", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.message.edit_caption(
                caption="warning 📍\n\n"
                "🛑 you have not join channle\n\n"
                "❌ please join both channel first\n"
                "🔄 click retry 🔄\n\n"
                "____________",
                reply_markup=reply_markup
            )
        except:
            await query.message.reply_text(
                "warning 📍\n\n"
                "🛑 you have not join channle\n\n"
                "❌ please join both channel first\n"
                "🔄 click retry 🔄\n\n"
                "____________",
                reply_markup=reply_markup
            )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "buy":
        buy_message = """
buy anything 
from 
shop
contact 
owner @pvt_s1n
"""
        try:
            await query.edit_message_text(buy_message)
        except:
            await query.message.reply_text(buy_message)
        
    elif query.data == "profile":
        user_id = update.effective_user.id
        users = load_users()
        user_data = users.get(str(user_id), {"credits": 0, "last_update": "N/A", "name": "Unknown"})
        await show_profile(update, context, user_id, user_data, edit_message=True)
    
    elif query.data == "back_to_main":
        # Clear all states and return to main menu
        context.user_data.pop('in_search_mode', None)
        context.user_data.pop('waiting_for_gift_code', None)
        context.user_data.pop('admin_action', None)
        context.user_data.pop('admin_mode', None)
        
        await query.edit_message_text("choose an option:", reply_markup=get_main_keyboard())
    
    elif query.data.startswith("full_referral_list_"):
        await handle_full_referral_list(update, context)
    
    elif query.data.startswith("copy_"):
        await handle_copy_code(update, context)
    
    elif query.data.startswith("page_"):
        await handle_pagination(update, context)
    
    elif query.data.startswith("deposit_"):
        await handle_deposit_callback(update, context)
    
    elif query.data == "cancel_payment":
        await handle_cancel_payment(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
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
        return
    
    # Check if admin is providing rejection reason
    if 'rejecting_payment' in context.user_data and await is_admin(user_id):
        await handle_rejection_reason(update, context)
        return
    
    # Clear any existing pagination data
    if 'pagination' in context.user_data:
        del context.user_data['pagination']
    
    # Define user menu buttons
    user_menu_buttons = [
        "🔍 search",
        "💎 credits",
        "🎁 gift",
        "🎖️ profile",
        "🛍️ shop",
        "💠 refer",
        "💳 deposit",
        "☎️ help",
        "🧧 admin"
    ]
    
    # Check if we're waiting for a gift code
    if context.user_data.get('waiting_for_gift_code', False):
        # If user sends a menu button while waiting for gift code, cancel the gift code state
        if text in user_menu_buttons:
            context.user_data['waiting_for_gift_code'] = False
        else:
            await process_gift_code(update, context)
            return
    
    # If text is a menu button, reset all states
    if text in user_menu_buttons:
        context.user_data['in_search_mode'] = False
        context.user_data['waiting_for_gift_code'] = False
        context.user_data['admin_mode'] = False
        if 'admin_action' in context.user_data:
            del context.user_data['admin_action']
    
    # Check if user is admin and in admin mode
    is_admin_user = await is_admin(user_id)
    admin_mode = context.user_data.get('admin_mode', False)
    
    if is_admin_user and admin_mode:
        # Handle admin panel actions
        if text in ["🃏 add credits", "💶 set credits", "🏅 user info", "📮 broadcast", "🎁 generate gift", "📑 referral", "⛔ ban user", "🔓 unban user", "🔒 lock search", "🔓 unlock search", "📊 stats", "🎲 main menu"]:
            await handle_admin_panel(update, context)
            return
        elif 'admin_action' in context.user_data:
            await handle_admin_input(update, context)
            return
        else:
            # If in admin mode but no action selected, show admin keyboard
            await update.message.reply_text("👑 Admin Panel", reply_markup=get_admin_keyboard())
            return
    
    # Check if we're in search mode
    if context.user_data.get('in_search_mode', False):
        # Check if the search type is locked
        is_locked, lock_message = check_search_type_locked(text)
        
        if is_locked:
            await update.message.reply_text(f"🔒 {lock_message}\n\nPlease try other search options.")
            context.user_data['in_search_mode'] = False
            return
        
        # Clear search mode first
        context.user_data['in_search_mode'] = False
        await search(update, context)
        return
    
    # Force membership check for all user actions
    if not await force_membership_check(update, context):
        return
    
    # Handle menu buttons for all users
    if text == "🔍 search":
        # Set search mode and prompt user
        context.user_data['in_search_mode'] = True
        # Clear other states
        context.user_data.pop('waiting_for_gift_code', None)
        context.user_data.pop('admin_action', None)
        context.user_data.pop('admin_mode', None)
        
        # Send as photo with caption
        await update.message.reply_photo(
            photo=SEARCH_IMAGE_URL, 
            caption=SEARCH_PROMPT_TEXT
        )
    elif text == "💎 credits":
        await credits(update, context)
    elif text == "🎁 gift":
        await gift_code_command(update, context)
    elif text == "🎖️ profile":
        await me(update, context)
    elif text == "🛍️ shop":
        await buy_command(update, context)
    elif text == "💠 refer":
        await show_referral_info(update, context)
    elif text == "💳 deposit":
        await deposit_command(update, context)
    elif text == "☎️ help":
        # Send as photo with caption
        await update.message.reply_photo(
            photo=HELP_IMAGE_URL, 
            caption=HELP_TEXT
        )
    elif text == "🧧 admin":
        await admin_stats(update, context)
    else:
        # If it's not a menu command, show help
        await update.message.reply_text("Please use the menu buttons to interact with the bot.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Force membership check
    if not await force_membership_check(update, context):
        return
    # Send as photo with caption
    await update.message.reply_photo(
        photo=HELP_IMAGE_URL, 
        caption=HELP_TEXT
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
        
    users = load_users()

    if str(user_id) not in users:
        # New user - add to database but don't give credits until they verify
        name = update.effective_user.first_name
        update_user(user_id, credits=0, name=name)
        users = load_users()  # Reload users after update

    if users[str(user_id)]["credits"] <= 0:
        await update.message.reply_text(f"❌ No Credits Left!\n\n💰 Buy Unlimited Credits & Ad 👉 {OWNER_USERNAME}")
        return

    # Show animated spinner
    spinner_msg = await show_spinner(update, context, update.message)

    query = update.message.text
    result = query_leakosint(query)
    pages = format_results(result)

    # Check if server is under construction or API error
    if "SERVER" in pages[0] or "Error" in result:
        await spinner_msg.delete()
        await update.message.reply_text(pages[0])
        return

    # Deduct 1 credit only if search was successful AND has data
    if "No Data" not in pages[0] and "SERVER" not in pages[0] and "Error" not in result:
        users[str(user_id)]["credits"] -= 1
        users[str(user_id)]["last_update"] = datetime.now().strftime("%d/%m - %I:%M %p")
        save_users(users)
        
        # Log the search
        log_audit_event(user_id, "SEARCH", f"Query: {query}, Success: True, Credits left: {users[str(user_id)]['credits']}")
    else:
        # Log failed search
        log_audit_event(user_id, "SEARCH", f"Query: {query}, Success: False, Credits left: {users[str(user_id)]['credits']}")

    # Delete spinner message
    await spinner_msg.delete()

    # Add credits info to each page
    credits_left = users[str(user_id)]["credits"]
    for i in range(len(pages)):
        pages[i] += f"\n💶 credit left -  {credits_left} 💎"
    
    # Store pagination data in context
    context.user_data['pagination'] = {
        'pages': pages,
        'current_page': 1
    }
    
    # Send first page with pagination buttons if multiple pages
    if len(pages) > 1:
        keyboard = create_pagination_keyboard(1, len(pages))
        await update.message.reply_text(pages[0], reply_markup=keyboard)
    else:
        await update.message.reply_text(pages[0])

async def credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
        
    users = load_users()
    
    c = users.get(str(user_id), {}).get("credits", 0)
    # Send as photo with caption
    await update.message.reply_photo(
        photo=CREDITS_IMAGE_URL, 
        caption=f"💶 your credit - {c} 💎"
    )

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Force membership check
    if not await force_membership_check(update, context):
        return
        
    users = load_users()
    user_data = users.get(str(user_id), {"credits": 0, "last_update": "N/A", "name": "Unknown"})
    await show_profile(update, context, user_id, user_data)

# ==== ADMIN COMMANDS ====
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Simple admin check
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin Only.")
        return
        
    users = load_users()
    total_users = len(users)
    total_credits = sum(user.get("credits", 0) for user in users.values())
    total_referrals = sum(user.get("referrals", 0) for user in users.values())
    total_referral_credits = sum(user.get("referral_credits", 0) for user in users.values())
    
    # Load banned users
    banned_users = load_banned_users()
    total_banned = len(banned_users)
    
    # Load search locks
    locks = load_search_locks()
    
    # Load pending payments
    payments = load_pending_payments()
    pending_payments = sum(1 for p in payments.values() if p.get("status") == "pending")
    
    stats_msg = f"""
📊 [ADMIN PANEL] 📊

👥 Total Users ➜ {total_users}
⛔ Banned Users ➜ {total_banned}
🪙 Total Credits ➜ {total_credits}
🤝 Total Referrals ➜ {total_referrals}
🎁 Total Referral Credits ➜ {total_referral_credits}
💰 Pending Payments ➜ {pending_payments}

🔒 Search Locks:
  • Number: {'🔒' if locks.get('number', False) else '🔓'}
  • Email: {'🔒' if locks.get('email', False) else '🔓'}
  • Name: {'🔒' if locks.get('name', False) else '🔓'}

🔄 Updated ➜ {datetime.now().strftime('%d/%m - %I:%M %p')}

"""
    
    # Set admin mode and show admin keyboard
    context.user_data['admin_mode'] = True
    # Clear any previous admin action
    if 'admin_action' in context.user_data:
        del context.user_data['admin_action']
    
    # Send as photo with caption
    await update.message.reply_photo(
        photo=ADMIN_IMAGE_URL, 
        caption=stats_msg, 
        reply_markup=get_admin_keyboard()
    )

# ==== MAIN ====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

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
    app.add_handler(CommandHandler("unban", unban_user_command))
    app.add_handler(CommandHandler("lock", lock_search_command))
    app.add_handler(CommandHandler("unlock", unlock_search_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify$"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(buy|profile|back_to_main|full_referral_list_|copy_|page_|deposit_|cancel_payment)"))
    
    print("bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()