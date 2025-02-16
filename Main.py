import telebot
import sqlite3
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Bot Token from BotFather
BOT_TOKEN = "8120444872:AAF9WXdbG-IfxlrjEf3ld1Ku_oJ4lHjlrxA"
ADMIN_ID = 5716550739
FORCE_JOIN_CHANNEL = "@GOAT_Infinite"

bot = telebot.TeleBot(BOT_TOKEN)

# Database setup
conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        points INTEGER DEFAULT 0,
        referred_by INTEGER DEFAULT NULL
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        service TEXT,
        account TEXT
    )
""")

conn.commit()

# Function to check if user is in the channel
def is_user_in_channel(user_id):
    try:
        chat_member = bot.get_chat_member(FORCE_JOIN_CHANNEL, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except:
        return False

# Start Command
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id
    
    if not is_user_in_channel(user_id):
        bot.send_message(user_id, f"⚠️ You must join {FORCE_JOIN_CHANNEL} to use this bot.")
        return
    
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    # Referral System
    ref_id = message.text.split()[-1] if len(message.text.split()) > 1 else None
    if ref_id and ref_id.isdigit() and int(ref_id) != user_id:
        cursor.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (int(ref_id), user_id))
        conn.commit()
        bot.send_message(int(ref_id), "🎉 Someone joined using your referral link! You earned 1 point.")

    # Create and send menu
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton("Balance"), KeyboardButton("Redeem Account"))
    menu.add(KeyboardButton("Invite"), KeyboardButton("Stats"))
    
    bot.send_message(user_id, "👋 Welcome! Use the menu below:", reply_markup=menu)

# Balance Command
@bot.message_handler(func=lambda message: message.text == "Balance")
def balance(message):
    user_id = message.chat.id
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    points = result[0] if result else 0
    bot.send_message(user_id, f"💰 Your Balance: {points} Points")

# Invite Command
@bot.message_handler(func=lambda message: message.text == "Invite")
def invite(message):
    user_id = message.chat.id
    bot.send_message(user_id, f"📢 Invite your friends and earn points!\n\nYour referral link:\nhttps://t.me/{bot.get_me().username}?start={user_id}")

# Stats Command
@bot.message_handler(func=lambda message: message.text == "Stats")
def stats(message):
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    bot.send_message(message.chat.id, f"📊 Total Users: {total_users}")

# Redeem Account Command
@bot.message_handler(func=lambda message: message.text == "Redeem Account")
def redeem(message):
    user_id = message.chat.id

    # Open a new database connection
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()

    # Check user's points
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    if not result or result[0] < 6:
        bot.send_message(user_id, "❌ You need at least 6 points to redeem an account.")
        conn.close()
        return

    # Fetch an account
    cursor.execute("SELECT service, account FROM accounts LIMIT 1")
    account = cursor.fetchone()

    if not account:
        bot.send_message(user_id, "❌ No accounts available at the moment. Try again later.")
        conn.close()
        return

    service, account_info = account

    # Send account details
    bot.send_message(user_id, f"✅ Here is your {service} account:\n\n{account_info}")

    # Remove the account from the database and deduct points
    cursor.execute("DELETE FROM accounts WHERE service = ? AND account = ?", (service, account_info))
    cursor.execute("UPDATE users SET points = points - 6 WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()

# Admin Commands
@bot.message_handler(commands=["addpoints"])
def add_points(message):
    if message.chat.id != ADMIN_ID:
        return

    args = message.text.split()
    if len(args) != 3:
        bot.send_message(ADMIN_ID, "Usage: /addpoints <user_id> <points>")
        return

    user_id, points = int(args[1]), int(args[2])
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points, user_id))
    conn.commit()
    bot.send_message(user_id, f"✅ You received {points} points!")
    bot.send_message(ADMIN_ID, f"✅ Added {points} points to {user_id}")

@bot.message_handler(commands=["addaccount"])
def add_account(message):
    if message.chat.id != ADMIN_ID:
        return

    args = message.text.split(maxsplit=2)
    if len(args) != 3:
        bot.send_message(ADMIN_ID, "Usage: /addaccount <service> <email:password>")
        return

    service, account_info = args[1], args[2]
    cursor.execute("INSERT INTO accounts (service, account) VALUES (?, ?)", (service, account_info))
    conn.commit()
    bot.send_message(ADMIN_ID, f"✅ Added {service} account: {account_info}")

@bot.message_handler(commands=["broadcast"])
def broadcast(message):
    if message.chat.id != ADMIN_ID:
        return

    text = message.text.replace("/broadcast ", "")
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    for user in users:
        try:
            bot.send_message(user[0], f"📢 Announcement:\n{text}")
        except:
            pass

    bot.send_message(ADMIN_ID, "✅ Broadcast sent.")

# Start bot
bot.polling()
