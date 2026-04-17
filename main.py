import telebot
from telebot import types
import yt_dlp
import json
import os
import hashlib
import shutil

TOKEN = "8751370568:AAGOvEC4nMTyrD9fsz956RD_e6GpAhV_IvA"
CHANNEL_LINK = "https://t.me/voltmusical"
CHANNEL_USERNAME = "@voltmusical"

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"
CACHE_DIR = "cache"

os.makedirs(CACHE_DIR, exist_ok=True)

# ---------- DATA ----------
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

# ---------- MENU ----------
def menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔎 Знайти музику", "🎶 Плейлист")
    return markup

# ---------- SUB CHECK ----------
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

# ---------- START ----------
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Підписатись", url=CHANNEL_LINK))
    markup.add(types.InlineKeyboardButton("✅ Я підписався", callback_data="check"))

    bot.send_message(message.chat.id,
        "👋 Підпишись на канал щоб користуватись ботом",
        reply_markup=markup
    )

# ---------- CHECK ----------
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(call):
    if check_sub(call.message.chat.id):
        bot.send_message(call.message.chat.id, "✅ Доступ відкрито!", reply_markup=menu())
    else:
        bot.send_message(call.message.chat.id, "❌ Підпишись спочатку")

# ---------- SEARCH ----------
@bot.message_handler(func=lambda m: m.text == "🔎 Знайти музику")
def ask(message):
    if not check_sub(message.chat.id):
        return
    user_state[message.chat.id] = "search"
    bot.send_message(message.chat.id, "🎧 Введіть назву пісні")

@bot.message_handler(func=lambda m: True)
def search(message):
    if not check_sub(message.chat.id):
        return
    if user_state.get(message.chat.id) != "search":
        return

    bot.send_message(message.chat.id, "🔎 Шукаю...")

    try:
        ydl_opts = {'quiet': True, 'extract_flat': True}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{message.text}", download=False)

        if not info["entries"]:
            bot.send_message(message.chat.id, "❌ Не знайдено")
            return

        video = info["entries"][0]

        title = video["title"]
        url = f"https://www.youtube.com/watch?v={video['id']}"
        thumb = video.get("thumbnail", "")

        user_last[message.chat.id] = (title, url)

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("⬇️ MP3", callback_data="download"),
            types.InlineKeyboardButton("❤️ В плейлист", callback_data="add")
        )
        markup.add(types.InlineKeyboardButton("▶️ YouTube", url=url))

        if thumb:
            bot.send_photo(message.chat.id, thumb, caption=f"🎵 {title}", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, f"🎵 {title}", reply_markup=markup)

    except Exception as e:
        print("🔥 SEARCH ERROR:", repr(e))
        bot.send_message(message.chat.id, f"❌ Помилка пошуку: {e}")

    user_state[message.chat.id] = None

# ---------- DOWNLOAD ----------
@bot.callback_query_handler(func=lambda c: c.data == "download")
def download(call):
    bot.send_message(call.message.chat.id, "⚡ Завантаження...")
    process_download(call)

def process_download(call):
    data_track = user_last.get(call.message.chat.id)
    if not data_track:
        bot.send_message(call.message.chat.id, "❌ Немає треку")
        return

    title, url = data_track

    file_id = hashlib.md5(url.encode()).hexdigest()
    file_path = f"{CACHE_DIR}/{file_id}.mp3"

    try:
        # кеш
        if os.path.exists(file_path):
            with open(file_path, "rb") as audio:
                bot.send_audio(call.message.chat.id, audio, title=title)
            return

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{CACHE_DIR}/{file_id}.%(ext)s',
            'noplaylist': True,
            'quiet': True,
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

        with open(file_path, "rb") as audio:
            bot.send_audio(call.message.chat.id, audio, title=title)

    except Exception as e:
        print("🔥 DOWNLOAD ERROR FULL:", repr(e))
        bot.send_message(call.message.chat.id, f"❌ Помилка скачування: {e}")

# ---------- PLAYLIST ----------
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

# ---------- RUN ----------
bot.polling()
