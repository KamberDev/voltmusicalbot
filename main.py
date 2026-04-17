import telebot
from telebot import types
import yt_dlp
import os
import hashlib
import shutil

TOKEN = "8751370568:AAGOvEC4nMTyrD9fsz956RD_e6GpAhV_IvA"

bot = telebot.TeleBot(TOKEN)

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

user_last = {}

# ---------- MENU ----------
def menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎵 Пошук музики")
    return markup

# ---------- START ----------
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "🎧 SoundCloud Music Bot готовий",
        reply_markup=menu()
    )

# ---------- SEARCH ----------
@bot.message_handler(func=lambda m: m.text == "🎵 Пошук музики")
def ask(message):
    msg = bot.send_message(message.chat.id, "🔎 Введи назву треку")
    bot.register_next_step_handler(msg, search)

def search(message):
    query = message.text
    bot.send_message(message.chat.id, "🔎 Шукаю...")

    try:
        ydl_opts = {
            'quiet': True,
            'noplaylist': True,
            'default_search': 'scsearch1',  # 🔥 SOUND CLOUD SEARCH
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)

        if "entries" not in info or not info["entries"]:
            bot.send_message(message.chat.id, "❌ Нічого не знайдено")
            return

        track = info["entries"][0]

        title = track.get("title", "Unknown")
        url = track.get("webpage_url")

        if not url:
            bot.send_message(message.chat.id, "❌ Немає посилання")
            return

        user_last[message.chat.id] = (title, url)

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬇️ Завантажити MP3", callback_data="dl"))

        bot.send_message(message.chat.id, f"🎵 {title}", reply_markup=markup)

    except Exception as e:
        print("SEARCH ERROR:", repr(e))
        bot.send_message(message.chat.id, "❌ Помилка пошуку")

# ---------- DOWNLOAD ----------
@bot.callback_query_handler(func=lambda c: c.data == "dl")
def download(call):
    bot.send_message(call.message.chat.id, "⚡ Завантажую...")

    data = user_last.get(call.message.chat.id)
    if not data:
        return

    title, url = data

    file_id = hashlib.md5(url.encode()).hexdigest()
    file_path = f"{CACHE_DIR}/{file_id}.mp3"

    try:
        # cache
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                bot.send_audio(call.message.chat.id, f, title=title)
            return

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

        # rename safe
        for f in os.listdir(CACHE_DIR):
            if f.startswith(file_id) and f.endswith(".mp3"):
                shutil.move(f"{CACHE_DIR}/{f}", file_path)

        with open(file_path, "rb") as f:
            bot.send_audio(call.message.chat.id, f, title=title)

    except Exception as e:
        print("DOWNLOAD ERROR:", repr(e))
        bot.send_message(call.message.chat.id, "❌ Не вдалося завантажити")

# ---------- RUN ----------
bot.polling()
