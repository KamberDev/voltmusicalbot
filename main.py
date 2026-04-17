import telebot
from telebot import types
from youtubesearchpython import VideosSearch
import yt_dlp
import json
import os
import threading
import hashlib

TOKEN = "8751370568:AAEKV-ZWHwQAXlktBBMrB29AomHCYdXKE6E"
CHANNEL_LINK = "https://t.me/voltmusical"
CHANNEL_USERNAME = "@voltmusical"

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"
CACHE_DIR = "cache"

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": [], "playlist": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()
user_state = {}
user_last = {}

def menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔎 Знайти музику", "🎶 Плейлист")
    return markup

def check_sub(user_id):
    if user_id in data["users"]:
        return True
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ["member", "creator", "administrator"]:
            data["users"].append(user_id)
            save_data(data)
            return True
    except:
        pass
    return False

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Підписатись", url=CHANNEL_LINK))
    markup.add(types.InlineKeyboardButton("✅ Я підписався", callback_data="check"))

    bot.send_message(message.chat.id, "👋 Підпишись на канал", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(call):
    if check_sub(call.message.chat.id):
        bot.send_message(call.message.chat.id, "✅ Готово!", reply_markup=menu())
    else:
        bot.send_message(call.message.chat.id, "❌ Підпишись спочатку")

@bot.message_handler(func=lambda m: m.text == "🔎 Знайти музику")
def ask(message):
    if not check_sub(message.chat.id):
        return
    user_state[message.chat.id] = "search"
    bot.send_message(message.chat.id, "🎧 Введіть назву пісні")

@bot.message_handler(func=lambda m: m.text == "🎶 Плейлист")
def show_playlist(message):
    uid = str(message.chat.id)
    pl = data["playlist"].get(uid, [])

    if not pl:
        bot.send_message(message.chat.id, "📭 Пусто")
        return

    text = "🎶 Плейлист:\n\n"
    for i, t in enumerate(pl, 1):
        text += f"{i}. {t['title']}\n"

    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: True)
def search(message):
    if not check_sub(message.chat.id):
        return
    if user_state.get(message.chat.id) != "search":
        return

    bot.send_message(message.chat.id, "🔎 Шукаю...")

    vs = VideosSearch(message.text, limit=1)
    res = vs.result()

    if not res["result"]:
        bot.send_message(message.chat.id, "❌ Не знайдено")
        return

    v = res["result"][0]
    title = v["title"]
    url = v["link"]
    thumb = v["thumbnails"][0]["url"]

    user_last[message.chat.id] = (title, url)

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("⬇️ MP3", callback_data="download"),
        types.InlineKeyboardButton("❤️ В плейлист", callback_data="add")
    )
    markup.add(types.InlineKeyboardButton("▶️ YouTube", url=url))

    bot.send_photo(message.chat.id, thumb, caption=f"🎵 {title}", reply_markup=markup)

    user_state[message.chat.id] = None

# 🚀 скачування в потоці + кеш
@bot.callback_query_handler(func=lambda c: c.data == "download")
def download(call):
    bot.send_message(call.message.chat.id, "⚡ Обробка...")

    thread = threading.Thread(target=process_download, args=(call,))
    thread.start()

def process_download(call):
    data_track = user_last.get(call.message.chat.id)
    if not data_track:
        return

    title, url = data_track

    # 🔥 унікальне ім’я файлу
    file_id = hashlib.md5(url.encode()).hexdigest()
    file_path = f"{CACHE_DIR}/{file_id}.mp3"

    try:
        # ✅ якщо вже скачано
        if os.path.exists(file_path):
            with open(file_path, "rb") as audio:
                bot.send_audio(call.message.chat.id, audio, title=title)
            return

        # 🧹 чистка старих файлів (якщо більше 20)
        files = os.listdir(CACHE_DIR)
        if len(files) > 20:
            for f in files[:10]:
                os.remove(f"{CACHE_DIR}/{f}")

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{CACHE_DIR}/{file_id}.%(ext)s',
            'quiet': True,
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
                os.rename(f"{CACHE_DIR}/{f}", file_path)

        with open(file_path, "rb") as audio:
            bot.send_audio(call.message.chat.id, audio, title=title)

    except:
        bot.send_message(call.message.chat.id, "❌ Помилка")

@bot.callback_query_handler(func=lambda c: c.data == "add")
def add(call):
    uid = str(call.message.chat.id)
    data_track = user_last.get(call.message.chat.id)

    if not data_track:
        return

    title, url = data_track

    if uid not in data["playlist"]:
        data["playlist"][uid] = []

    data["playlist"][uid].append({"title": title, "url": url})
    save_data(data)

    bot.send_message(call.message.chat.id, "❤️ Додано")

bot.polling()
