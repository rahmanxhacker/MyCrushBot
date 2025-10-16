import os
import sqlite3
import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
import openai

# --------------------- CONFIG ---------------------
BOT_TOKEN = "8040123895:AAGUQKxnWI1Fjxp4c24xoNjvoU4MwLOdOA4"
OPENAI_API_KEY = ""

CHANNELS = [
    "https://t.me/rahmannumber",
    "https://t.me/mycrashname",
    "https://t.me/mycrashchannel"
]

DAILY_LIMIT = 2  # Free daily limit per user

USDT_ADDRESS = "TP7YngtkkGhZHtYPFFMu424RiHL1A3sEtd"
TON_ADDRESS = "UQDzRnNY7njyIupNIhWbFqkHKE78G8INGEcooQ0AgFg33fiI"

openai.api_key = OPENAI_API_KEY

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# --------------------- DATABASE ---------------------
conn = sqlite3.connect("mycrushbot.db")
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    referrals INTEGER DEFAULT 0,
    daily_predictions INTEGER DEFAULT 0,
    last_prediction_date TEXT,
    premium_expire TEXT,
    balance REAL DEFAULT 0
)
''')
conn.commit()

# --------------------- HELPERS ---------------------
def check_channel_join(user_id):
    # NOTE: Actual channel join check requires extra API (Telethon)
    return True

def get_daily_limit(user):
    limit = DAILY_LIMIT
    limit += user['referrals']  # Add extra from referrals
    return limit

def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        return {
            'user_id': row[0],
            'referrals': row[1],
            'daily_predictions': row[2],
            'last_prediction_date': row[3],
            'premium_expire': row[4],
            'balance': row[5]
        }
    else:
        cursor.execute("INSERT INTO users(user_id) VALUES(?)", (user_id,))
        conn.commit()
        return get_user(user_id)

def update_daily_count(user_id, count):
    today = datetime.date.today().isoformat()
    cursor.execute("UPDATE users SET daily_predictions=?, last_prediction_date=? WHERE user_id=?",
                   (count, today, user_id))
    conn.commit()

def add_referral(user_id):
    cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id=?", (user_id,))
    conn.commit()

def add_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()

# --------------------- INLINE BUTTONS ---------------------
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💘 Find Your Crush", callback_data="crush"),
        InlineKeyboardButton("💬 Analyze Message", callback_data="analyze"),
        InlineKeyboardButton("💎 Buy Premium", callback_data="premium"),
        InlineKeyboardButton("👤 My Profile", callback_data="profile")
    )
    return kb

def premium_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("1️⃣ Weekly — 2 USDT / 1 TON", callback_data="weekly"),
        InlineKeyboardButton("2️⃣ Monthly — 5 USDT / 3 TON", callback_data="monthly"),
        InlineKeyboardButton("3️⃣ Quarterly — 12 USDT / 7 TON", callback_data="quarterly"),
        InlineKeyboardButton("✅ I've Paid", callback_data="paid")
    )
    return kb

# --------------------- HANDLERS ---------------------
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user = get_user(message.from_user.id)
    # Check channel join (placeholder)
    joined = check_channel_join(user['user_id'])
    if not joined:
        text = "⚠️ عزیز user! Bot استعمال کرنے سے پہلے آپ کو ہمارے 3 official channels join کرنا ضروری ہیں:\n\n"
        for ch in CHANNELS:
            text += f"{ch}\n"
        text += "\nبراہ کرم join کریں اور دوبارہ /start دبائیں۔"
        await message.answer(text)
        return
    await message.answer("Welcome! 🤗 Main menu below:", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data)
async def callbacks(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    data = call.data

    # --------------------- CRUSH PREDICTION ---------------------
    if data == "crush":
        today = datetime.date.today().isoformat()
        if user['last_prediction_date'] != today:
            user['daily_predictions'] = 0
        limit = get_daily_limit(user)
        if user['daily_predictions'] >= limit and not user['premium_expire']:
            await call.message.answer("⚠️ Aap aaj ke liye apni free predictions complete kar chuke hain. Refer friends to unlock more!")
            return
        await call.message.answer("Processing your Crush Prediction... 💘")
        prompt = f"Predict crush for user {call.from_user.first_name}"
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        result = response['choices'][0]['message']['content']
        user['daily_predictions'] += 1
        update_daily_count(user['user_id'], user['daily_predictions'])
        await call.message.answer(f"💘 Crush Prediction Result:\n{result}")

    # --------------------- MESSAGE ANALYZER ---------------------
    elif data == "analyze":
        await call.message.answer("Send the message you want to analyze. (AI will predict crush intent etc.)")

    # --------------------- PREMIUM ---------------------
    elif data == "premium":
        await call.message.answer("Choose your premium plan:", reply_markup=premium_menu())
    elif data in ["weekly", "monthly", "quarterly"]:
        await call.message.answer("💳 Please send payment to the following addresses:\n\n"
                                  f"USDT (TRC20): {USDT_ADDRESS}\n"
                                  f"TON: {TON_ADDRESS}\n\n"
                                  "After payment, click 'I've Paid ✅' and submit TXN ID.")
    elif data == "paid":
        await call.message.answer("✅ Payment recorded! Your premium will activate automatically after verification.")

    # --------------------- PROFILE ---------------------
    elif data == "profile":
        text = f"👤 Profile:\nDaily Predictions Used: {user['daily_predictions']}/{get_daily_limit(user)}\n"
        if user['premium_expire']:
            text += f"Premium Expire: {user['premium_expire']}\n"
        text += f"Balance: {user['balance']}"
        await call.message.answer(text)

# --------------------- RUN ---------------------
if __name__ == "__main__":
    print("Bot is starting...")
    executor.start_polling(dp, skip_updates=True)