import telebot
from telebot import types
import yt_dlp

TOKEN = "8751370568:AAGOvEC4nMTyrD9fsz956RD_e6GpAhV_IvA"

bot = telebot.TeleBot(TOKEN)

user_tracks = {}
user_index = {}
user_likes = {}

# ---------- AI ----------
def ai(text):
    text = text.lower()

    moods = {
        "phonk": "phonk drift music",
        "sad": "sad emotional music",
        "gym": "gym workout music",
        "love": "romantic music",
        "chill": "chill music",
        "rap": "rap music"
    }

    for k in moods:
        if k in text:
            return moods[k]

    return text

# ---------- START ----------
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "🎧 Spotify AI Bot готовий\n\n"
        "Напиши: phonk / gym / sad або будь-який трек"
    )

# ---------- SEARCH ----------
@bot.message_handler(func=lambda m: True)
def search(message):
    query = ai(message.text)

    bot.send_message(message.chat.id, f"🔎 AI шукає: {query}")

    try:
        ydl_opts = {
            'quiet': True,
            'noplaylist': True,
            'default_search': 'ytsearch7',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)

        entries = info.get("entries", [])
        if not entries:
            bot.send_message(message.chat.id, "❌ Нічого не знайдено")
            return

        user_tracks[message.chat.id] = entries
        user_index[message.chat.id] = 0

        send_track(message.chat.id, 0)

    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, "❌ Помилка пошуку")

# ---------- SEND TRACK ----------
def send_track(chat_id, index):
    tracks = user_tracks.get(chat_id)
    if not tracks:
        return

    if index < 0:
        index = 0
    if index >= len(tracks):
        index = len(tracks) - 1

    user_index[chat_id] = index

    track = tracks[index]
    title = track.get("title")
    url = track.get("webpage_url")

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("⏮", callback_data="prev"),
        types.InlineKeyboardButton("▶️", callback_data="play"),
        types.InlineKeyboardButton("⏭", callback_data="next")
    )
    markup.add(
        types.InlineKeyboardButton("❤️ Like", callback_data="like")
    )

    bot.send_message(chat_id, f"🎵 {title}", reply_markup=markup)

# ---------- BUTTONS ----------
@bot.callback_query_handler(func=lambda c: True)
def buttons(call):
    chat_id = call.message.chat.id
    action = call.data

    if chat_id not in user_tracks:
        return

    if action == "next":
        send_track(chat_id, user_index[chat_id] + 1)

    elif action == "prev":
        send_track(chat_id, user_index[chat_id] - 1)

    elif action == "like":
        track = user_tracks[chat_id][user_index[chat_id]]
        user_likes.setdefault(chat_id, []).append(track.get("title"))
        bot.send_message(chat_id, "❤️ Додано в лайки")

    elif action == "play":
        play_track(chat_id)

# ---------- PLAY (STREAM) ----------
def play_track(chat_id):
    track = user_tracks[chat_id][user_index[chat_id]]
    title = track.get("title")
    url = track.get("webpage_url")

    bot.send_message(chat_id, f"▶️ Грає: {title}")

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        audio_url = info["url"]

        bot.send_audio(chat_id, audio_url, title=title)

    except Exception as e:
        print("PLAY ERROR:", e)
        bot.send_message(chat_id, "❌ Не вдалося відтворити")

# ---------- RUN ----------
bot.polling()
