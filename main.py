import telebot
from telebot import types
import json
import os
import random

TOKEN = "8751370568:AAERob2JxbvqvUIg_eQWakXEGQANuYd7x_A"
CHANNEL = "@voltmusical"
ADMIN_ID = 8307540389

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"


# ================= DATA =================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


data = load_data()


# ================= CHECKS =================
def is_verified(uid):
    return data.get(uid, {}).get("verified", False)


def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


def is_premium(uid):
    return data.get(uid, {}).get("premium", False)


def is_banned(uid):
    return data.get(uid, {}).get("banned", False)


# ================= TRACKS =================
def get_tracks():
    tracks = []
    updates = bot.get_updates(limit=200)

    for u in updates:
        if u.channel_post:
            p = u.channel_post

            if p.chat.username == CHANNEL.replace("@", "") and p.audio:
                tracks.append({
                    "title": p.audio.title or "Unknown",
                    "file_id": p.audio.file_id
                })

    return tracks


# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.chat.id)

    if is_banned(uid):
        bot.send_message(message.chat.id, "🚫 Ban")
        return

    if not is_subscribed(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Підписатись", url=f"https://t.me/{CHANNEL.replace('@','')}"))
        markup.add(types.InlineKeyboardButton("🔐 Verify", callback_data="verify"))

        bot.send_message(message.chat.id, "❗ Спочатку підписка", reply_markup=markup)
        return

    if not is_verified(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔐 Verify", callback_data="verify"))

        bot.send_message(message.chat.id, "🔐 Одноразова перевірка", reply_markup=markup)
        return

    bot.send_message(message.chat.id, "🎧 Spotify Bot", reply_markup=menu())


# ================= VERIFY =================
@bot.callback_query_handler(func=lambda c: c.data == "verify")
def verify(call):
    uid = str(call.message.chat.id)

    if not is_subscribed(call.message.chat.id):
        bot.send_message(uid, "❌ Спочатку підпишись на канал")
        return

    data.setdefault(uid, {})
    data[uid]["verified"] = True
    save_data(data)

    bot.send_message(uid, "✅ Access granted")
    bot.send_message(uid, "🎧 Menu:", reply_markup=menu())


# ================= MENU =================
def menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("🎧 Пошук", "📊 Топ-10")
    m.add("🎲 Discover", "❤️ Лайки")
    if ADMIN_ID:
        m.add("🛠 Admin")
    return m


# ================= SEARCH =================
@bot.message_handler(func=lambda m: m.text == "🎧 Пошук")
def ask(message):
    uid = str(message.chat.id)
    if not is_verified(uid):
        return

    msg = bot.send_message(message.chat.id, "🔎 Назва:")
    bot.register_next_step_handler(msg, search)


def search(message):
    uid = str(message.chat.id)

    if is_banned(uid):
        return

    query = message.text.lower()
    tracks = get_tracks()

    result = [t for t in tracks if query in t["title"].lower()]

    if not result:
        bot.send_message(message.chat.id, "❌ Не знайдено")
        return

    send_list(message.chat.id, result[:7])


# ================= TOP =================
@bot.message_handler(func=lambda m: m.text == "📊 Топ-10")
def top(message):
    if not is_verified(str(message.chat.id)):
        return

    tracks = get_tracks()[:10]

    if not is_premium(str(message.chat.id)):
        tracks = tracks[:5]

    send_list(message.chat.id, tracks)


# ================= DISCOVER =================
@bot.message_handler(func=lambda m: m.text == "🎲 Discover")
def discover(message):
    if not is_verified(str(message.chat.id)):
        return

    tracks = get_tracks()
    random.shuffle(tracks)

    limit = 7 if is_premium(str(message.chat.id)) else 4

    send_list(message.chat.id, tracks[:limit])


# ================= LIKES =================
@bot.message_handler(func=lambda m: m.text == "❤️ Лайки")
def likes(message):
    uid = str(message.chat.id)

    likes = data.get(uid, {}).get("likes", [])

    bot.send_message(message.chat.id, "❤️\n\n" + "\n".join(likes) if likes else "❌ Пусто")


# ================= ADMIN =================
@bot.message_handler(func=lambda m: m.text == "🛠 Admin")
def admin(message):
    if message.chat.id != ADMIN_ID:
        return

    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("💎 Premium", "🚫 Ban", "📊 Users")
    bot.send_message(message.chat.id, "🛠 Admin Panel", reply_markup=m)


# ================= USERS =================
@bot.message_handler(func=lambda m: m.text == "📊 Users")
def users(message):
    if message.chat.id != ADMIN_ID:
        return

    text = "👥 Users:\n\n"
    for uid, u in data.items():
        text += f"{uid} | 💎 {u.get('premium', False)} | 🚫 {u.get('banned', False)}\n"

    bot.send_message(message.chat.id, text)


# ================= PREMIUM =================
@bot.message_handler(func=lambda m: m.text == "💎 Premium")
def premium(message):
    if message.chat.id != ADMIN_ID:
        return

    msg = bot.send_message(message.chat.id, "User ID:")
    bot.register_next_step_handler(msg, set_premium)


def set_premium(message):
    uid = message.text.strip()

    data.setdefault(uid, {})
    data[uid]["premium"] = not data[uid].get("premium", False)

    save_data(data)

    bot.send_message(message.chat.id, "💎 Updated")


# ================= BAN =================
@bot.message_handler(func=lambda m: m.text == "🚫 Ban")
def ban(message):
    if message.chat.id != ADMIN_ID:
        return

    msg = bot.send_message(message.chat.id, "User ID:")
    bot.register_next_step_handler(msg, set_ban)


def set_ban(message):
    uid = message.text.strip()

    data.setdefault(uid, {})
    data[uid]["banned"] = True

    save_data(data)

    bot.send_message(message.chat.id, "🚫 Banned")


# ================= LIST =================
def send_list(chat_id, tracks):
    uid = str(chat_id)

    data.setdefault(uid, {})
    data[uid]["tracks"] = tracks
    data[uid]["index"] = 0
    data[uid].setdefault("likes", [])

    save_data(data)

    send_track(chat_id)


# ================= TRACK =================
def send_track(chat_id):
    uid = str(chat_id)
    state = data.get(uid)

    track = state["tracks"][state["index"]]

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("⏮", callback_data="prev"),
        types.InlineKeyboardButton("▶️", callback_data="play"),
        types.InlineKeyboardButton("⏭", callback_data="next")
    )
    markup.add(types.InlineKeyboardButton("❤️", callback_data="like"))

    bot.send_message(chat_id, f"🎵 {track['title']}", reply_markup=markup)


# ================= BUTTONS =================
@bot.callback_query_handler(func=lambda c: True)
def buttons(call):
    uid = str(call.message.chat.id)

    state = data.get(uid)
    if not state:
        return

    if call.data == "next":
        state["index"] = (state["index"] + 1) % len(state["tracks"])

    elif call.data == "prev":
        state["index"] = (state["index"] - 1) % len(state["tracks"])

    elif call.data == "like":
        track = state["tracks"][state["index"]]
        state["likes"].append(track["title"])
        bot.send_message(uid, "❤️ Saved")

    elif call.data == "play":
        track = state["tracks"][state["index"]]
        bot.send_audio(uid, track["file_id"], title=track["title"])

    save_data(data)
    send_track(uid)


# ================= RUN =================
bot.polling()
