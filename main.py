import telebot
from telebot import types
import yt_dlp
import hashlib

TOKEN = "8751370568:AAGOvEC4nMTyrD9fsz956RD_e6GpAhV_IvA"

bot = telebot.TeleBot(TOKEN)

user_last = {}

# ---------- AI "LOGIC" (простий інтелект без API) ----------
def ai_parse(text):
    text = text.lower()

    moods = {
        "sad": "sad emotional music",
        "drift": "phonk drift music",
        "gym": "gym workout music",
        "love": "romantic music",
        "chill": "chill music",
        "rap": "rap music"
    }

    for key in moods:
        if key in text:
            return moods[key]

    return text  # якщо нічого не знайдено — шукаємо як є

# ---------- START ----------
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "🤖🎧 AI Music Bot готовий\n\nНапиши: 'sad', 'gym', 'phonk' або назву треку"
    )

# ---------- SEARCH ----------
@bot.message_handler(func=lambda m: True)
def search(message):
    query = ai_parse(message.text)

    bot.send_message(message.chat.id, f"🔎 AI шукає: {query}")

    try:
        ydl_opts = {
            'quiet': True,
            'noplaylist': True,
            'default_search': 'scsearch1',  # 🔥 SoundCloud
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
            bot.send_message(message.chat.id, "❌ Немає URL")
            return

        user_last[message.chat.id] = (title, url)

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("▶️ Play / Download", callback_data="play"))

        bot.send_message(message.chat.id, f"🎵 {title}", reply_markup=markup)

    except Exception as e:
        print("SEARCH ERROR:", repr(e))
        bot.send_message(message.chat.id, "❌ Помилка пошуку")

# ---------- PLAY / DOWNLOAD ----------
@bot.callback_query_handler(func=lambda c: c.data == "play")
def play(call):
    bot.send_message(call.message.chat.id, "⚡ Готую трек...")

    data = user_last.get(call.message.chat.id)
    if not data:
        return

    title, url = data

    file_id = hashlib.md5(url.encode()).hexdigest()
    file_path = f"{file_id}.mp3"

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{file_id}.%(ext)s',
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

        with open(file_path, "rb") as audio:
            bot.send_audio(call.message.chat.id, audio, title=title)

    except Exception as e:
        print("DOWNLOAD ERROR:", repr(e))
        bot.send_message(call.message.chat.id, "❌ Не вдалося відтворити трек")

# ---------- RUN ----------
bot.polling()
