import os
import telebot
from telebot import types
from pymongo import MongoClient
from dotenv import load_dotenv

# ------------ ENV LOAD ------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "cluster0")

if not BOT_TOKEN or not DATABASE_URL:
    raise RuntimeError("BOT_TOKEN or DATABASE_URL not set in .env")

bot = telebot.TeleBot(BOT_TOKEN)

# ------------ MONGODB SETUP ------------
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client[MONGO_DB_NAME]
users_col = db["users"]

users_col.create_index("user_id", unique=True)

# ------------ CONSTS ------------
OWNER_USERNAME = "Evil_AngeI"        # @ ke bina
BOT_USERNAME   = "YourBotUsernameHere"  # @ ke bina

POINT_PRICES_TEXT = (
    "💰 Point Prices 💰\n\n"
    "🪙 ₹20 = 30 Points ⭐️\n"
    "🪙 ₹30 = 60 Points ⭐️\n"
    "🪙 ₹50 = 120 + 50 Bonus Points ⭐️\n"
    "🪙 ₹100 = 280 + 100 Bonus Points ⭐️\n"
    "🪙 ₹200 = 600 + 200 Bonus Points ⭐️\n"
    "🪙 ₹300 = 1000 + 300 Bonus Points ⭐️\n"
    "🪙 ₹500 = 2000 + 500 Bonus Points ⭐️\n\n"
    f"Dm to Buy :- @{OWNER_USERNAME}"
)

PRIVACY_TEXT = (
    "🔒 Privacy Policy & Disclaimer\n\n"
    "Welcome to Pyaasi Angel Bot. Your privacy, safety, and consent are our top priorities. "
    "Please read this policy carefully before using the bot.\n\n"
    "📌 1. User Data Collection\n"
    "We collect the following data:\n"
    "• Your Telegram User ID\n"
    "• Your name and @username (for referral & reward tracking)\n"
    "• Your point balance and usage stats (non-sensitive)\n"
    "• Timestamps of interactions\n\n"
    "We do not collect or store:\n"
    "• Your private messages or files\n"
    "• Your phone number, contacts, or location\n"
    "• Any personally identifiable data beyond what Telegram provides\n\n"
    "📌 2. Content Policy\n"
    "This bot may deliver adult-themed content. By using this bot, you confirm the following:\n"
    "• You are at least 18 years of age\n"
    "• You are accessing the content voluntarily\n"
    "• You understand that this is intended only for mature audiences\n\n"
    "⚠️ We do not host or create any media. All videos/images are publicly found or shared "
    "from Telegram groups. If any content violates your rights, please report it for removal.\n\n"
    "📌 3. Data Usage\n"
    "User data is used only to:\n"
    "• Track points, referrals, and access controls\n"
    "• Prevent abuse, spam, or bot joins via verification checks\n"
    "• Monitor bot performance and ensure fair use\n\n"
    "We do not sell or share your data with any third party.\n\n"
    "📌 4. Legal Disclaimer\n"
    "This bot operates under Telegram’s Bot API and complies with their technical and content "
    "restrictions. By using this bot, you acknowledge:\n"
    "• You are solely responsible for your actions\n"
    "• Admins are not liable for misuse of the bot or any consequences\n"
    "• You may be restricted if you abuse, spam, or report other users unfairly\n\n"
    "🚫 If you do not agree with this policy, please stop using the bot immediately.\n\n"
    f"📬 For content removal or queries, contact admin: @{OWNER_USERNAME}\n\n"
    "Last updated: June 2025"
)

REFER_TEXT_TEMPLATE = (
    "📢 Share this link to refer your friends and earn points! 🤗\n\n"
    "*1 successful referral = 20 Points!* 🏅\n\n"
    "{ref_link}\n\n"
    "This bot is only for adults (18+).\n"
    "More info: /privacy"
)

# ------------ DB HELPERS ------------
def get_user(user_id: int):
    return users_col.find_one({"user_id": user_id})


def register_user(user_id: int, username: str | None, ref: int | None = None):
    existing = get_user(user_id)
    if existing:
        return False

    doc = {
        "user_id": user_id,
        "username": username,
        "points": 0,
        "referred_by": ref,
    }
    users_col.insert_one(doc)

    # ✅ 20 points per referral
    if ref:
        users_col.update_one(
            {"user_id": ref},
            {"$inc": {"points": 20}}
        )
    return True


def get_points(user_id: int) -> int:
    u = get_user(user_id)
    if not u:
        return 0
    return int(u.get("points", 0))


def add_points(user_id: int, amount: int):
    users_col.update_one(
        {"user_id": user_id},
        {"$inc": {"points": amount}},
        upsert=True
    )

# ------------ KEYBOARDS ------------
def main_menu_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎬 VIDEO", "📸 PHOTO")
    kb.row("🏅 POINTS", "👤 PROFILE")
    kb.row("🔗 REFER", "💰 BUY")
    return kb


def buy_menu_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💸 Point Prices", callback_data="buy_prices"))
    kb.add(types.InlineKeyboardButton(
        "💬 Contact owner",
        url=f"https://t.me/{OWNER_USERNAME}"
    ))
    return kb


def buy_back_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 Back", callback_data="buy_back"))
    return kb


def refer_share_kb(ref_link: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🚀 Share Now 🚀", url=ref_link))
    return kb


# ------------ HELPERS ------------
def send_refer_message(chat_id: int):
    ref_link = f"https://t.me/{BOT_USERNAME}?start={chat_id}"
    text = REFER_TEXT_TEMPLATE.format(ref_link=ref_link)
    bot.send_message(
        chat_id,
        text,
        parse_mode="Markdown",
        reply_markup=refer_share_kb(ref_link)
    )

# ------------ /start ------------
@bot.message_handler(commands=["start"])
def start(msg):
    user_id = msg.chat.id
    username = msg.from_user.username

    parts = msg.text.split()
    ref = None
    if len(parts) > 1:
        try:
            ref = int(parts[1])
        except ValueError:
            ref = None

    is_new = register_user(user_id, username, ref)

    welcome_text = "👋 Hey! Welcome.\n"
    if is_new and ref:
        welcome_text += "🎁 You joined via referral, welcome bonus activated!\n"
    elif is_new:
        welcome_text += "🆕 New user registered.\n"

    welcome_text += "\nCommands: /privacy, /stats, /buy, /refer"

    bot.send_message(
        user_id,
        welcome_text + "\n\nUse the buttons below 👇",
        reply_markup=main_menu_kb()
    )

# ------------ /privacy ------------
@bot.message_handler(commands=["privacy"])
def privacy(msg):
    bot.send_message(msg.chat.id, PRIVACY_TEXT)

# ------------ /stats ------------
@bot.message_handler(commands=["stats"])
def stats(msg):
    top = users_col.find().sort("points", -1).limit(5)
    lines = ["🏆 Top 5 Users:"]
    rank = 1
    for u in top:
        name = u.get("username") or u.get("user_id")
        pts = u.get("points", 0)
        lines.append(f"{rank}. {name} — {pts} pts")
        rank += 1
    bot.send_message(msg.chat.id, "\n".join(lines))

# ------------ /buy ------------
@bot.message_handler(commands=["buy"])
def buy_command(msg):
    chat_id = msg.chat.id
    text = (
        "💰 Purchase Points Now! 💰\n\n"
        "✅ Want to buy more points?\n"
        "Check the latest prices and contact the owner for secure purchases.\n\n"
        "🔗 Use the buttons below 👇"
    )
    bot.send_message(
        chat_id,
        text,
        reply_markup=buy_menu_kb()
    )

# ------------ /refer (NEW) ------------
@bot.message_handler(commands=["refer"])
def refer_command(msg):
    send_refer_message(msg.chat.id)

# ------------ BUY CALLBACKS ------------
@bot.callback_query_handler(func=lambda call: call.data in ["buy_prices", "buy_back"])
def buy_callbacks(call):
    if call.data == "buy_prices":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=POINT_PRICES_TEXT,
            reply_markup=buy_back_kb()
        )
    elif call.data == "buy_back":
        text = (
            "💰 Purchase Points Now! 💰\n\n"
            "✅ Want to buy more points?\n"
            "Check the latest prices and contact the owner for secure purchases.\n\n"
            "🔗 Use the buttons below 👇"
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=buy_menu_kb()
        )

    bot.answer_callback_query(call.id)

# ------------ MAIN BUTTON HANDLER ------------
@bot.message_handler(func=lambda m: True)
def buttons(msg):
    chat_id = msg.chat.id
    text = msg.text

    if not get_user(chat_id):
        register_user(chat_id, msg.from_user.username, None)

    if text == "🎬 VIDEO":
        bot.send_message(chat_id, "🎥 Sample video message (yaha tum apna logic lagana).")

    elif text == "📸 PHOTO":
        bot.send_message(chat_id, "🖼 Sample photo message (yaha media bhejna).")

    elif text == "👤 PROFILE":
        pts = get_points(chat_id)
        u = get_user(chat_id)
        username = u.get("username") or "Unknown"
        bot.send_message(
            chat_id,
            f"👤 Profile\nUser: {username}\nID: {chat_id}\nPoints: {pts}"
        )

    elif text == "🏅 POINTS":
        pts = get_points(chat_id)
        bot.send_message(chat_id, f"🏅 Your current points: {pts}")

    elif text == "🔗 REFER":
        # same as /refer
        send_refer_message(chat_id)

    elif text == "💰 BUY":
        buy_command(msg)

    else:
        bot.send_message(chat_id, "Choose an option from the menu 👇")

print("🚀 Bot running with MongoDB + /buy + /privacy + /refer...")
bot.polling(none_stop=True)
