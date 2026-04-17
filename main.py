import telebot
from telebot import types
import requests
import random
import json
from datetime import datetime, timedelta

TOKEN = "8751370568:AAERob2JxbvqvUIg_eQWakXEGQANuYd7x_A"
CHANNEL = "@voltmusical"
ADMIN_ID = 8307540389

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"
user_game = {}


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
            "searches": 0,
            "last_reset": str(datetime.now().date()),
            "likes": [],
            "playlist": [],
            "friends": [],
            "now_playing": None,
            "history": []
        }


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
    expire = datetime.now() + timedelta(days=days)
    data[str(uid)]["premium_until"] = expire.strftime("%Y-%m-%d")
    save(data)


# ================= RESET =================
def reset(uid):
    user = data[uid]
    today = str(datetime.now().date())

    if user["last_reset"] != today:
        user["searches"] = 0
        user["last_reset"] = today


# ================= LIMIT =================
def can_search(uid):
    init(uid)
    reset(uid)

    if is_premium(uid):
        return True

    return data[uid]["searches"] < 5


# ================= SUB CHECK =================
def is_subscribed(user_id):
    try:
        m = bot.get_chat_member(CHANNEL, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False


# ================= MENU =================
def menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("🔎 Пошук", "🎧 Плейлист")
    m.add("❤️ Улюблені", "🎲 Рекомендації")
    m.add("👥 Друзі", "🎮 Гра")
    m.add("📊 Статистика", "💎 Premium")
    return m


# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):

    if not is_subscribed(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Підписатись", url=f"https://t.me/{CHANNEL.replace('@','')}"))
        markup.add(types.InlineKeyboardButton("✅ Я підписаний", callback_data="check"))

        bot.send_message(message.chat.id, "❗ Підпишись на канал", reply_markup=markup)
        return

    init(message.chat.id)
    bot.send_message(message.chat.id, "🎧 VOLT MUSIC BOT 6.0", reply_markup=menu())


# ================= CHECK =================
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(call):

    if is_subscribed(call.message.chat.id):
        bot.send_message(call.message.chat.id, "✅ Готово", reply_markup=menu())
    else:
        bot.send_message(call.message.chat.id, "❌ Не підписаний")


# ================= SEARCH =================
@bot.message_handler(func=lambda m: m.text == "🔎 Пошук")
def ask(message):
    msg = bot.send_message(message.chat.id, "Введи назву:")
    bot.register_next_step_handler(msg, search)


def search(message):
    uid = str(message.chat.id)
    init(uid)

    if not can_search(uid):
        bot.send_message(message.chat.id, "⛔ Ліміт 5/день")
        return

    query = message.text

    url = f"https://itunes.apple.com/search?term={query}&limit=5"
    r = requests.get(url).json()

    if not r["results"]:
        bot.send_message(message.chat.id, "❌ Нічого")
        return

    data[uid]["searches"] += 1

    for item in r["results"]:
        title = item.get("trackName")
        artist = item.get("artistName")
        preview = item.get("previewUrl")
        cover = item.get("artworkUrl100")

        if not preview:
            continue

        data[uid]["history"].append(title)

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("▶️ Play", callback_data=preview),
            types.InlineKeyboardButton("❤️ Like", callback_data=f"like|{title}|{artist}|{preview}")
        )

        text = f"🎵 {title}\n👤 {artist}"

        if cover:
            bot.send_photo(message.chat.id, cover, caption=text, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, text, reply_markup=markup)

    save(data)


# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    uid = str(call.message.chat.id)
    init(uid)

    if call.data.startswith("http"):
        data[uid]["now_playing"] = call.data
        bot.send_audio(call.message.chat.id, call.data)

    if call.data.startswith("like"):
        _, title, artist, url = call.data.split("|")

        data[uid]["likes"].append({
            "title": title,
            "artist": artist,
            "url": url
        })

        save(data)
        bot.send_message(call.message.chat.id, "❤️ Додано")


# ================= PLAYLIST =================
@bot.message_handler(func=lambda m: m.text == "🎧 Плейлист")
def playlist(message):
    uid = str(message.chat.id)
    init(uid)

    for t in data[uid]["playlist"][-10:]:
        bot.send_message(message.chat.id, f"🎵 {t['title']}")


# ================= LIKES =================
@bot.message_handler(func=lambda m: m.text == "❤️ Улюблені")
def likes(message):
    uid = str(message.chat.id)
    init(uid)

    for t in data[uid]["likes"][-10:]:
        bot.send_message(message.chat.id, f"❤️ {t['title']} - {t['artist']}")


# ================= FRIENDS =================
@bot.message_handler(func=lambda m: m.text == "👥 Друзі")
def friends(message):
    uid = str(message.chat.id)
    init(uid)

    text = "👥 Друзі:\n\n"

    for f in data[uid]["friends"]:
        u = data.get(str(f), {})
        status = "🟢 online" if u.get("now_playing") else "⚪ offline"
        text += f"{f} - {status}\n"

    bot.send_message(message.chat.id, text)


# ================= GAME =================
@bot.message_handler(func=lambda m: m.text == "🎮 Гра")
def game(message):

    url = "https://itunes.apple.com/search?term=rock&limit=10"
    r = requests.get(url).json()

    item = random.choice(r["results"])

    user_game[message.chat.id] = item

    bot.send_audio(message.chat.id, item["previewUrl"])
    bot.send_message(message.chat.id, "🎮 Вгадай виконавця")


@bot.message_handler(func=lambda m: m.chat.id in user_game)
def guess(message):

    correct = user_game[message.chat.id]["artistName"].lower()

    if correct in message.text.lower():
        bot.send_message(message.chat.id, "✅ правильно")
    else:
        bot.send_message(message.chat.id, f"❌ {correct}")

    del user_game[message.chat.id]


# ================= PREMIUM (STARS) =================
@bot.message_handler(func=lambda m: m.text == "💎 Premium")
def premium(message):

    prices = [
        types.LabeledPrice(label="Premium 30 днів", amount=100)
    ]

    bot.send_invoice(
        chat_id=message.chat.id,
        title="Premium",
        description="Безліміт музики",
        invoice_payload=f"premium_{message.chat.id}",
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="premium"
    )


@bot.pre_checkout_query_handler(func=lambda q: True)
def checkout(q):
    bot.answer_pre_checkout_query(q.id, ok=True)


@bot.message_handler(content_types=['successful_payment'])
def success(message):

    add_premium(message.chat.id, 30)

    bot.send_message(message.chat.id, "💎 Premium активовано на 30 днів!")


# ================= STATS =================
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(message):
    uid = str(message.chat.id)
    init(uid)

    user = data[uid]

    bot.send_message(message.chat.id, f"""
📊 Статистика

💎 Premium: {is_premium(uid)}
❤️ Likes: {len(user['likes'])}
🔎 Searches: {user['searches']}/5
📚 History: {len(user['history'])}
""")


# ================= RUN =================
bot.polling(none_stop=True)
