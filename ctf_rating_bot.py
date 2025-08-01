import telebot
import sqlite3
from dotenv import load_dotenv
import os
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

conn = sqlite3.connect('rating.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    nickname TEXT,
    points INTEGER DEFAULT 0
)
''')
conn.commit()

pending_registration = {}

def add_points(user_id, amount):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE users SET points = points + ? WHERE user_id=?", (amount, user_id))
    conn.commit()

def get_points(user_id):
    cursor.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

def get_nickname(user_id):
    cursor.execute("SELECT nickname FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else "nameless"

def show_main_menu(chat_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    btn1 = KeyboardButton("1 🚀")
    btn2 = KeyboardButton("2 🏆")
    btn3 = KeyboardButton("3 🎖")
    markup.add(btn1, btn2, btn3)

    bot.send_message(
        chat_id,
        "1. Посмотреть мои очки.\n"
        "2. Топ игроков.\n"
        "3. Мой ранг.",
        reply_markup=markup
    )

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone():
        show_main_menu(message.chat.id)
        return

    pending_registration[user_id] = True
    bot.send_message(message.chat.id, "Привет!\nЯ — бот для подсчета твоего CTF-рейтинга.\nДля начала напиши свой никнейм.\nОн будет отображаться в топе игроков и будет виден другим пользователям. Его можно будет изменить.")

@bot.message_handler(func=lambda message: message.from_user.id in pending_registration)
def handle_nickname(message):
    user_id = message.from_user.id
    nickname = message.text.strip()

    if not nickname:
        bot.send_message(message.chat.id, "Никнейм не может быть пустым. Попробуй снова:")
        return

    cursor.execute("INSERT INTO users (user_id, nickname) VALUES (?, ?)", (user_id, nickname))
    conn.commit()
    del pending_registration[user_id]

    bot.send_message(message.chat.id, f"Отлично, {nickname}! Регистрация успешна. Удачи в мире CTF!")
    show_main_menu(message.chat.id)

@bot.message_handler(commands=['addpoints'])
def addpoints(message):
    if message.from_user.username != "EIWisee":
        bot.reply_to(message, "Request rejected.")
        return
    try:
        parts = message.text.split()
        nickname = parts[1]
        points = int(parts[2])
        cursor.execute("SELECT user_id FROM users WHERE nickname=?", (nickname,))
        row = cursor.fetchone()
        if row:
            add_points(row[0], points)
            bot.reply_to(message, f"Points awarded: {points}. User: {nickname}.")
        else:
            bot.reply_to(message, "User with this nickname not found.")
    except:
        bot.reply_to(message, "Use the format: /addpoints nickname x")

@bot.message_handler(func=lambda message: message.text in ["1 🚀", "2 🏆", "3 🎖"])
def handle_reply_buttons(message):
    user_id = message.from_user.id
    nickname = get_nickname(user_id)

    if message.text == "1 🚀":
        points = get_points(user_id)
        cursor.execute("SELECT user_id, points FROM users ORDER BY points DESC")
        rows = cursor.fetchall()
        place = 1
        for row in rows:
            if row[0] == user_id:
                break
            place += 1
        bot.send_message(message.chat.id, f"📊 {nickname}, у тебя {points} очков. Ты на {place} месте.")

    elif message.text == "2 🏆":
        cursor.execute("SELECT nickname, points FROM users ORDER BY points DESC LIMIT 10")
        rows = cursor.fetchall()
        msg = "🏆 Глобальный топ игроков:\n"
        for i, row in enumerate(rows):
            msg += f"{i+1}. {row[0]} — {row[1]} pts.\n"
        bot.send_message(message.chat.id, msg)

    elif message.text == "3 🎖":
        points = get_points(user_id)
        if points < 50:
            rank = "Новичок 🐣"
        elif points < 150:
            rank = "Падаван 🥋"
        elif points < 300:
            rank = "Хакер 💻"
        elif points < 500:
            rank = "Кибер-ниндзя 🥷"
        else:
            rank = "Легенда 🔥"
        bot.send_message(message.chat.id, f"🎖 {nickname}, твой ранг:\n{rank}.")

print("Бот запущен успешно.")
bot.infinity_polling()
