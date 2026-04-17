import telebot
from telebot import types
import yt_dlp
import os
import json
import hashlib
import shutil

TOKEN = "8751370568:AAGOvEC4nMTyrD9fsz956RD_e6GpAhV_IvA"
CHANNEL_USERNAME = "@voltmusical"
CHANNEL_LINK = "https://t.me/voltmusical"

bot = telebot.TeleBot(TOKEN)

CACHE_DIR = "cache"
DATA_FILE = "data.json"

os.makedirs(CACHE_DIR, exist_ok=True)

# ---------- DATA ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

user_state = {}
user_last = {}

# ---------- MENU ----------
def menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎵 Знайти музику")
    return markup

# ---------- CHECK SUB ----------
def check_sub(user_id):
    if user_id in data["users"]:
        return True

    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ["member", "creator", "administrator"]:
            data["users"].append(user_id)  # 🔥 одноразова "підписка"
            save_data(data)
            return True
    except:
        pass

    return False

# ---------- START ----------
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Підписатись", url=CHANNEL_LINK))
    markup.add(types.InlineKeyboardButton("✅ Я підписався", callback_data="check"))

    bot.send_message(
        message.chat.id,
        "👋 Щоб користуватись ботом — підпишись на канал",
        reply_markup=markup
    )

# ---------- CHECK ----------
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(call):
    if check_sub(call.message.chat.id):
        bot.send_message(call.message.chat.id, "✅ Доступ відкрито", reply_markup=menu())
    else:
        bot.send_message(call.message.chat.id, "❌ Спочатку підпишись")

# ---------- SEARCH ----------
@bot.message_handler(func=lambda m: m.text == "🎵 Знайти музику")
def ask(message):
    if not check_sub(message.chat.id):
        return

    msg = bot.send_message(message.chat.id, "🎧 Введи назву треку")
    bot.register_next_step_handler(msg, search)

def search(message):
    query = message.text
    bot.send_message(message.chat.id, "🔎 Шукаю...")

    try:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'noplaylist': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)

        video = info["entries"][0]

        title = video["title"]
        url = video["url"] if "url" in video else f"https://soundcloud.com/search?q={query}"

        user_last[message.chat.id] = (title, url)

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬇️ Завантажити MP3", callback_data="dl"))

        bot.send_message(message.chat.id, f"🎵 {title}", reply_markup=markup)

    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, "❌ Помилка пошуку")

# ---------- DOWNLOAD ----------
@bot.callback_query_handler(func=lambda c: c.data == "dl")
def download(call):
    bot.send_message(call.message.chat.id, "⚡ Завантажую...")

    data_track = user_last.get(call.message.chat.id)
    if not data_track:
        return

    title, url = data_track

    file_id = hashlib.md5(url.encode()).hexdigest()
    file_path = f"{CACHE_DIR}/{file_id}.mp3"

    try:
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                bot.send_audio(call.message.chat.id, f, title=title)
            return

        # 🔥 SOUND / VIDEO DOWNLOAD (без cookies)
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{CACHE_DIR}/{file_id}.%(ext)s',
            'quiet': True,
            'noplaylist': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0'
            },
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        for f in os.listdir(CACHE_DIR):
            if f.startswith(file_id) and f.endswith(".mp3"):
                shutil.move(f"{CACHE_DIR}/{f}", file_path)

        with open(file_path, "rb") as f:
            bot.send_audio(call.message.chat.id, f, title=title)

    except Exception as e:
        print("ERROR:", repr(e))
        bot.send_message(call.message.chat.id, "❌ Не вдалося завантажити трек")

# ---------- RUN ----------
bot.polling()
