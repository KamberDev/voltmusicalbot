import telebot
from telebot import types
import requests
import json
import base64
import random
import time
from datetime import datetime, timedelta

TOKEN = "8751370568:AAERob2JxbvqvUIg_eQWakXEGQANuYd7x_A"
CHANNEL = "@voltmusical"
ADMIN_ID = 8307540389

SPOTIFY_CLIENT_ID = "YOUR_ID"
SPOTIFY_CLIENT_SECRET = "YOUR_SECRET"

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"
user_game = {}

SPOTIFY_TOKEN = None
SPOTIFY_TIME = 0


# ================= DATA =================
def load():
    try:
        with open(DATA_FILE, "r") as f:
            return json.loads(f.read() or "{}")
    except:
        return {}

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load()


# ================= USER =================
def init(uid):
    uid = str(uid)
    if uid not in data:
        data[uid] = {
            "premium_until": None,
            "searches": 0,
            "last_reset": str(datetime.now().date()),
            "likes": [],
            "history": [],
            "autoplay": False,
            "friends": []
        }


# ================= USERS =================
def total_users():
    return len(data)


# ================= SUB =================
def is_subscribed(uid):
    try:
        m = bot.get_chat_member(CHANNEL, uid)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False


# ================= PREMIUM =================
def is_premium(uid):
    u = data[uid]
    if not u.get("premium_until"):
        return False
    try:
        return datetime.strptime(u["premium_until"], "%Y-%m-%d") > datetime.now()
    except:
        return False


def add_premium(uid, days=30):
    init(uid)
    exp = datetime.now() + timedelta(days=days)
    data[str(uid)]["premium_until"] = exp.strftime("%Y-%m-%d")
    save(data)


# ================= RESET =================
def reset(uid):
    u = data[uid]
    if u["last_reset"] != str(datetime.now().date()):
        u["searches"] = 0
        u["last_reset"] = str(datetime.now().date())


# ================= LIMIT =================
def can_search(uid):
    init(uid)
    reset(uid)
    return is_premium(uid) or data[uid]["searches"] < 5


# ================= SPOTIFY TOKEN =================
def get_token():
    global SPOTIFY_TOKEN, SPOTIFY_TIME

    if SPOTIFY_TOKEN and time.time() - SPOTIFY_TIME < 3500:
        return SPOTIFY_TOKEN

    auth = base64.b64encode(
        f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()

    r = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {auth}"},
        data={"grant_type": "client_credentials"}
    )

    SPOTIFY_TOKEN = r.json().get("access_token")
    SPOTIFY_TIME = time.time()

    return SPOTIFY_TOKEN


# ================= SEARCH =================
def search_spotify(q):
    token = get_token()

    r = requests.get(
        f"https://api.spotify.com/v1/search?q={q}&type=track&limit=5",
        headers={"Authorization": f"Bearer {token}"}
    )

    return r.json()["tracks"]["items"]


# ================= MENU =================
def menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("🔎 Пошук", "❤️ Лайки")
    m.add("🎧 Автоплей", "🧠 Рекомендації")
    m.add("🎮 Гра", "📊 Статистика", "💎 Premium")
    return m


# ================= LOG START =================
def log_start(user):
    bot.send_message(
        ADMIN_ID,
        f"👤 START\nID:{user.id}\n@{user.username}\n{user.first_name}"
    )


# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):

    if not is_subscribed(message.chat.id):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📢 Підписатись", url=f"https://t.me/{CHANNEL.replace('@','')}"))
        kb.add(types.InlineKeyboardButton("✅ Я підписаний", callback_data="check"))
        bot.send_message(message.chat.id, "❗ Підпишись", reply_markup=kb)
        return

    init(message.chat.id)
    log_start(message.from_user)

    bot.send_message(
        message.chat.id,
        f"🎧 VOLT MUSIC 10.0\n👥 Users: {total_users()}",
        reply_markup=menu()
    )


# ================= CHECK =================
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(call):
    if is_subscribed(call.message.chat.id):
        bot.send_message(call.message.chat.id, "✅ OK", reply_markup=menu())
    else:
        bot.send_message(call.message.chat.id, "❌ Нема підписки")


# ================= SEARCH =================
@bot.message_handler(func=lambda m: m.text == "🔎 Пошук")
def ask(m):
    msg = bot.send_message(m.chat.id, "Назва:")
    bot.register_next_step_handler(msg, search)


def search(m):
    uid = str(m.chat.id)
    init(uid)

    if not can_search(uid):
        bot.send_message(m.chat.id, "⛔ Ліміт 5/день")
        return

    tracks = search_spotify(m.text)

    data[uid]["searches"] += 1

    for t in tracks:

        title = t["name"]
        artist = t["artists"][0]["name"]
        cover = t["album"]["images"][0]["url"]
        url = t["external_urls"]["spotify"]
        preview = t.get("preview_url")

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🎧 Spotify", url=url))

        if preview:
            kb.add(types.InlineKeyboardButton("▶️ Stream", callback_data=preview))

        bot.send_photo(
            m.chat.id,
            cover,
            caption=f"🎵 {title}\n👤 {artist}",
            reply_markup=kb
        )

        data[uid]["history"].append(title)

    save(data)


# ================= CALLBACK STREAM =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("http"))
def stream(call):
    bot.send_audio(call.message.chat.id, call.data)


# ================= LIKE =================
@bot.message_handler(func=lambda m: m.text == "❤️ Лайки")
def likes(m):
    uid = str(m.chat.id)
    init(uid)

    for l in data[uid]["likes"][-10:]:
        bot.send_message(m.chat.id, l)


# ================= AUTOPLAY =================
@bot.message_handler(func=lambda m: m.text == "🎧 Автоплей")
def auto(m):
    uid = str(m.chat.id)
    init(uid)

    data[uid]["autoplay"] = not data[uid]["autoplay"]
    save(data)

    bot.send_message(m.chat.id, f"🎧 {data[uid]['autoplay']}")


# ================= RECOMMEND =================
@bot.message_handler(func=lambda m: m.text == "🧠 Рекомендації")
def rec(m):

    t = random.choice(search_spotify("pop"))

    bot.send_message(m.chat.id,
                     f"🧠 {t['name']} - {t['artists'][0]['name']}")


# ================= GAME =================
@bot.message_handler(func=lambda m: m.text == "🎮 Гра")
def game(m):

    t = random.choice(search_spotify("rock"))

    user_game[m.chat.id] = t

    bot.send_audio(m.chat.id, t["preview_url"])
    bot.send_message(m.chat.id, "🎮 Вгадай")


@bot.message_handler(func=lambda m: m.chat.id in user_game)
def guess(m):

    c = user_game[m.chat.id]["artists"][0]["name"].lower()

    if c in m.text.lower():
        bot.send_message(m.chat.id, "✅")
    else:
        bot.send_message(m.chat.id, f"❌ {c}")

    del user_game[m.chat.id]


# ================= PREMIUM =================
@bot.message_handler(func=lambda m: m.text == "💎 Premium")
def premium(m):

    prices = [types.LabeledPrice("Premium", 100)]

    bot.send_invoice(
        m.chat.id,
        "Premium",
        "30 днів",
        "premium",
        "",
        "XTR",
        prices
    )


@bot.pre_checkout_query_handler(func=lambda q: True)
def pre(q):
    bot.answer_pre_checkout_query(q.id, ok=True)


@bot.message_handler(content_types=["successful_payment"])
def pay(m):
    add_premium(m.chat.id, 30)
    bot.send_message(m.chat.id, "💎 OK")


# ================= STATS =================
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(m):

    uid = str(m.chat.id)
    init(uid)

    bot.send_message(m.chat.id,
                     f"👥 {total_users()}\n💎 {is_premium(uid)}")


# ================= RUN =================
bot.polling(none_stop=True)
