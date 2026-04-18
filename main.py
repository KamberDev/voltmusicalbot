import telebot
from telebot import types
import requests
import base64
import json
import random
from datetime import datetime

# ===== CONFIG =====
TOKEN = "8751370568:AAERob2JxbvqvUIg_eQWakXEGQANuYd7x_A"
CHANNEL = "@voltmusical"
ADMIN_ID = 8307540389

SPOTIFY_ID = "14419ee2c4084925852e81427aa2436e"
SPOTIFY_SECRET = "21f33ce309ae4c67b0570d9251fdb60a"

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"

# ===== DATABASE =====
def load():
    try:
        with open(DATA_FILE, "r") as f:
            return json.loads(f.read() or "{}")
    except:
        return {}

def save():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load()

def init(uid):
    uid = str(uid)
    if uid not in data:
        data[uid] = {
            "likes": [],
            "playlist": [],
            "friends": [],
            "searches": 0,
            "date": str(datetime.now().date()),
            "premium": False,
            "last_seen": str(datetime.now()),
            "now_playing": None
        }

# ===== SUB CHECK =====
def check_sub(uid):
    try:
        m = bot.get_chat_member(CHANNEL, uid)
        return m.status in ["member","administrator","creator"]
    except:
        return False

# ===== LIMIT =====
def can_use(uid):
    u = data[uid]

    if u["premium"]:
        return True

    if u["date"] != str(datetime.now().date()):
        u["searches"] = 0
        u["date"] = str(datetime.now().date())

    return u["searches"] < 5

# ===== SPOTIFY =====
token_cache = None

def get_token():
    global token_cache

    if token_cache:
        return token_cache

    auth = base64.b64encode(
        f"{SPOTIFY_ID}:{SPOTIFY_SECRET}".encode()
    ).decode()

    r = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {auth}"},
        data={"grant_type": "client_credentials"}
    )

    token_cache = r.json()["access_token"]
    return token_cache

def search(q):
    t = get_token()

    r = requests.get(
        f"https://api.spotify.com/v1/search?q={q}&type=track&limit=5",
        headers={"Authorization": f"Bearer {t}"}
    )

    return r.json()["tracks"]["items"]

# ===== MENU =====
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔎 Пошук", "❤️ Лайки")
    kb.add("📁 Плейлист", "👥 Друзі")
    kb.add("🧠 Рекомендації", "🎮 Гра")
    kb.add("📊 Статистика")
    return kb

# ===== START =====
@bot.message_handler(commands=['start'])
def start(m):

    if not check_sub(m.chat.id):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📢 Підписка", url="https://t.me/voltmusical"))
        kb.add(types.InlineKeyboardButton("✅ Я підписався", callback_data="check"))
        bot.send_message(m.chat.id, "Підпишись на канал", reply_markup=kb)
        return

    init(m.chat.id)

    bot.send_message(
        m.chat.id,
        f"🎧 Volt Music\n👥 Users: {len(data)}",
        reply_markup=menu()
    )

    bot.send_message(ADMIN_ID, f"START {m.chat.id}")

# ===== CHECK =====
@bot.callback_query_handler(func=lambda c: c.data=="check")
def check(c):
    if check_sub(c.message.chat.id):
        bot.send_message(c.message.chat.id, "✅ Готово", reply_markup=menu())
    else:
        bot.send_message(c.message.chat.id, "❌ Не підписаний")

# ===== SEARCH =====
@bot.message_handler(func=lambda m: m.text=="🔎 Пошук")
def ask(m):
    msg = bot.send_message(m.chat.id, "Введи назву:")
    bot.register_next_step_handler(msg, do_search)

def do_search(m):
    uid = str(m.chat.id)
    init(uid)

    data[uid]["last_seen"] = str(datetime.now())

    if not can_use(uid):
        bot.send_message(m.chat.id, "⛔ Ліміт 5/день")
        return

    data[uid]["searches"] += 1

    tracks = search(m.text)

    for t in tracks:
        name = t["name"]
        artist = t["artists"][0]["name"]
        cover = t["album"]["images"][0]["url"]
        url = t["external_urls"]["spotify"]

        track_id = f"{name}|{artist}"
        data[uid]["now_playing"] = track_id

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("▶️ Слухати", url=url))
        kb.add(types.InlineKeyboardButton("❤️ Лайк", callback_data=f"like|{track_id}"))
        kb.add(types.InlineKeyboardButton("➕ В плейлист", callback_data=f"pl|{track_id}"))

        bot.send_photo(
            m.chat.id,
            cover,
            caption=f"{name}\n{artist}",
            reply_markup=kb
        )

    save()

# ===== LIKE =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("like"))
def like(c):
    uid = str(c.message.chat.id)
    init(uid)

    track = c.data.split("|",1)[1]

    if track not in data[uid]["likes"]:
        data[uid]["likes"].append(track)
        bot.answer_callback_query(c.id, "❤️ Додано")

    save()

# ===== PLAYLIST =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("pl"))
def playlist_add(c):
    uid = str(c.message.chat.id)
    init(uid)

    track = c.data.split("|",1)[1]

    if track not in data[uid]["playlist"]:
        data[uid]["playlist"].append(track)
        bot.answer_callback_query(c.id, "📁 Додано")

    save()

@bot.message_handler(func=lambda m: m.text=="📁 Плейлист")
def show_pl(m):
    uid = str(m.chat.id)
    init(uid)

    if not data[uid]["playlist"]:
        bot.send_message(m.chat.id, "Пусто")
        return

    bot.send_message(m.chat.id, "\n".join(data[uid]["playlist"]))

# ===== FRIENDS =====
@bot.message_handler(func=lambda m: m.text=="👥 Друзі")
def friends(m):
    uid = str(m.chat.id)
    init(uid)

    text = "👥 Друзі:\n\n"

    for f in data[uid]["friends"]:
        if f in data:
            text += f"{f} — 🟢 {data[f]['last_seen']}\n"
        else:
            text += f"{f} — ❌ нема даних\n"

    bot.send_message(m.chat.id, text if data[uid]["friends"] else "Нема друзів")

    msg = bot.send_message(m.chat.id, "Введи ID друга:")
    bot.register_next_step_handler(msg, add_friend)

def add_friend(m):
    uid = str(m.chat.id)
    init(uid)

    if m.text not in data[uid]["friends"]:
        data[uid]["friends"].append(m.text)
        bot.send_message(m.chat.id, "✔ Додано")

    save()

# ===== NOW =====
@bot.message_handler(commands=['now'])
def now(m):
    uid = str(m.chat.id)
    init(uid)

    track = data[uid].get("now_playing")

    if track:
        bot.send_message(m.chat.id, f"🎧 {track}")
    else:
        bot.send_message(m.chat.id, "Нічого не слухаєш")

# ===== TOP =====
@bot.message_handler(commands=['top'])
def top(m):

    all_tracks = []

    for u in data:
        all_tracks += data[u].get("likes", [])

    if not all_tracks:
        bot.send_message(m.chat.id, "Нема даних")
        return

    top = {}
    for t in all_tracks:
        top[t] = top.get(t, 0) + 1

    sorted_top = sorted(top.items(), key=lambda x: x[1], reverse=True)[:5]

    text = "🔝 ТОП:\n\n"
    for t,c in sorted_top:
        text += f"{t} — ❤️ {c}\n"

    bot.send_message(m.chat.id, text)

# ===== RECOMMEND =====
@bot.message_handler(func=lambda m: m.text=="🧠 Рекомендації")
def rec(m):
    t = random.choice(search("pop"))
    bot.send_message(m.chat.id, f"{t['name']} - {t['artists'][0]['name']}")

# ===== GAME =====
game = {}

@bot.message_handler(func=lambda m: m.text=="🎮 Гра")
def game_start(m):
    t = random.choice(search("rock"))
    game[m.chat.id] = t["artists"][0]["name"].lower()
    bot.send_message(m.chat.id, "Вгадай виконавця")

@bot.message_handler(func=lambda m: m.chat.id in game)
def guess(m):
    if game[m.chat.id] in m.text.lower():
        bot.send_message(m.chat.id, "✔ правильно")
    else:
        bot.send_message(m.chat.id, f"❌ {game[m.chat.id]}")
    del game[m.chat.id]

# ===== STATS =====
@bot.message_handler(func=lambda m: m.text=="📊 Статистика")
def stats(m):
    uid = str(m.chat.id)
    init(uid)

    bot.send_message(
        m.chat.id,
        f"""
👥 Users: {len(data)}
🔎 {data[uid]['searches']}/5
❤️ {len(data[uid]['likes'])}
📁 {len(data[uid]['playlist'])}
💎 Premium: {data[uid]['premium']}
"""
    )

# ===== PREMIUM ADMIN =====
@bot.message_handler(commands=['premium'])
def premium(m):
    if m.chat.id != ADMIN_ID:
        return

    try:
        uid = m.text.split()[1]
        init(uid)
        data[uid]["premium"] = True
        save()
        bot.send_message(m.chat.id, "✔ Premium видано")
    except:
        bot.send_message(m.chat.id, "Помилка")

# ===== BUY PREMIUM =====
@bot.message_handler(commands=['buy'])
def buy(m):
    prices = [types.LabeledPrice("Premium 30 днів", 100)]

    bot.send_invoice(
        m.chat.id,
        "Volt Premium",
        "Безліміт музики",
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
    uid = str(m.chat.id)
    init(uid)
    data[uid]["premium"] = True
    save()

    bot.send_message(m.chat.id, "💎 Premium активовано!")

# ===== RUN =====
print("Bot started...")
bot.polling(none_stop=True)
