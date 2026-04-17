import telebot
from telebot import types
import requests
import json
import base64
import random
from datetime import datetime, timedelta

TOKEN = "8751370568:AAERob2JxbvqvUIg_eQWakXEGQANuYd7x_A"
CHANNEL = "@voltmusical"
ADMIN_ID = 8307540389

SPOTIFY_CLIENT_ID = "YOUR_CLIENT_ID"
SPOTIFY_CLIENT_SECRET = "YOUR_SECRET"

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"


# ================= DATA =================
def load():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load()


# ================= USER INIT =================
def init(uid):
    uid = str(uid)

    if uid not in data:
        data[uid] = {
            "premium_until": None,
            "likes": [],
            "searches": 0,
            "autoplay": False,
            "history": []
        }


# ================= USERS COUNT =================
def total_users():
    return len(data)


# ================= SUB CHECK =================
def is_subscribed(user_id):
    try:
        m = bot.get_chat_member(CHANNEL, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False


# ================= PREMIUM =================
def is_premium(uid):
    user = data[uid]
    if not user.get("premium_until"):
        return False
    try:
        return datetime.strptime(user["premium_until"], "%Y-%m-%d") > datetime.now()
    except:
        return False


def add_premium(uid, days=30):
    init(uid)
    exp = datetime.now() + timedelta(days=days)
    data[str(uid)]["premium_until"] = exp.strftime("%Y-%m-%d")
    save(data)


# ================= SPOTIFY TOKEN =================
def spotify_token():
    auth = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()

    r = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {auth}"},
        data={"grant_type": "client_credentials"}
    )

    return r.json()["access_token"]


SPOTIFY = spotify_token()


# ================= MENU =================
def menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("🔎 Пошук", "❤️ Лайки")
    m.add("🎧 Автоплей", "🧠 Рекомендації")
    m.add("📊 Статистика", "💎 Premium")
    return m


# ================= ADMIN LOG =================
def log_start(user):
    bot.send_message(
        ADMIN_ID,
        f"👤 START\nID: {user.id}\n@{user.username}\n{user.first_name}"
    )


# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):

    if not is_subscribed(message.chat.id):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📢 Підписатись", url=f"https://t.me/{CHANNEL.replace('@','')}"))
        kb.add(types.InlineKeyboardButton("✅ Я підписаний", callback_data="check"))

        bot.send_message(message.chat.id, "❗ Підпишись на канал", reply_markup=kb)
        return

    init(message.chat.id)

    log_start(message.from_user)

    bot.send_message(
        message.chat.id,
        f"🎧 VOLT MUSIC 9.0\n👥 Users: {total_users()}",
        reply_markup=menu()
    )


# ================= CHECK =================
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(call):
    if is_subscribed(call.message.chat.id):
        bot.send_message(call.message.chat.id, "✅ Готово", reply_markup=menu())
    else:
        bot.send_message(call.message.chat.id, "❌ Нема підписки")


# ================= SEARCH SPOTIFY =================
def search_spotify(query):
    r = requests.get(
        f"https://api.spotify.com/v1/search?q={query}&type=track&limit=5",
        headers={"Authorization": f"Bearer {SPOTIFY}"}
    )
    return r.json()["tracks"]["items"]


# ================= SEARCH =================
@bot.message_handler(func=lambda m: m.text == "🔎 Пошук")
def ask(message):
    msg = bot.send_message(message.chat.id, "Введи назву:")
    bot.register_next_step_handler(msg, search)


def search(message):
    uid = str(message.chat.id)
    init(uid)

    tracks = search_spotify(message.text)

    if not tracks:
        bot.send_message(message.chat.id, "❌ Нічого")
        return

    for t in tracks:
        title = t["name"]
        artist = t["artists"][0]["name"]
        cover = t["album"]["images"][0]["url"]
        url = t["external_urls"]["spotify"]
        preview = t.get("preview_url")

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("▶️ Spotify", url=url))

        if preview:
            kb.add(types.InlineKeyboardButton("🎧 Stream", callback_data=preview))

        bot.send_photo(
            message.chat.id,
            cover,
            caption=f"🎵 {title}\n👤 {artist}",
            reply_markup=kb
        )

        data[uid]["history"].append(title)

    save(data)


# ================= STREAM =================
@bot.callback_query_handler(func=lambda c: True)
def stream(call):

    uid = str(call.message.chat.id)
    init(uid)

    if call.data.startswith("http"):
        bot.send_audio(call.message.chat.id, call.data)


# ================= LIKE SYSTEM =================
@bot.message_handler(func=lambda m: m.text == "❤️ Лайки")
def likes(message):
    uid = str(message.chat.id)
    init(uid)

    for l in data[uid]["likes"][-10:]:
        bot.send_message(message.chat.id, f"❤️ {l}")


# ================= AUTOPLAY =================
@bot.message_handler(func=lambda m: m.text == "🎧 Автоплей")
def autoplay(message):
    uid = str(message.chat.id)
    init(uid)

    data[uid]["autoplay"] = not data[uid]["autoplay"]
    save(data)

    bot.send_message(message.chat.id, f"🎧 Autoplay: {data[uid]['autoplay']}")


# ================= RECOMMEND =================
@bot.message_handler(func=lambda m: m.text == "🧠 Рекомендації")
def rec(message):

    tracks = search_spotify("pop")
    t = random.choice(tracks)

    bot.send_message(message.chat.id,
                     f"🧠 {t['name']} - {t['artists'][0]['name']}")


# ================= PREMIUM =================
@bot.message_handler(func=lambda m: m.text == "💎 Premium")
def premium(message):

    prices = [types.LabeledPrice("Premium 30 днів", 100)]

    bot.send_invoice(
        chat_id=message.chat.id,
        title="Premium",
        description="Безліміт музики",
        invoice_payload="premium",
        provider_token="",
        currency="XTR",
        prices=prices
    )


@bot.pre_checkout_query_handler(func=lambda q: True)
def checkout(q):
    bot.answer_pre_checkout_query(q.id, ok=True)


@bot.message_handler(content_types=['successful_payment'])
def success(message):
    add_premium(message.chat.id, 30)
    bot.send_message(message.chat.id, "💎 Premium активовано")


# ================= STATS =================
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(message):
    uid = str(message.chat.id)
    init(uid)

    bot.send_message(message.chat.id, f"""
📊

👥 Users: {total_users()}
💎 Premium: {is_premium(uid)}
❤️ Likes: {len(data[uid]['likes'])}
""")
