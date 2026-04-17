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
PREMIUM_PRICE = 100  # ⭐ Stars


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
def is_subscribed(user_id):
    try:
        m = bot.get_chat_member(CHANNEL, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False


def is_verified(uid):
    return data.get(uid, {}).get("verified", False)


def is_premium(uid):
    return data.get(uid, {}).get("premium", False)


def is_banned(uid):
    return data.get(uid, {}).get("banned", False)


# ================= TRACKS =================
def get_tracks():
    tracks = []
    updates = bot.get_updates(limit=100)

    for u in updates:
        if u.channel_post and u.channel_post.audio:
            p = u.channel_post

            if p.chat.username == CHANNEL.replace("@", ""):
                tracks.append({
                    "title": p.audio.title or "Unknown",
                    "file_id": p.audio.file_id
                })

    return tracks


# ================= MENU =================
def menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("🎧 Плеєр", "🎲 Random")
    m.add("❤️ Лайки", "💎 Premium")
    return m


# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.chat.id)

    if is_banned(uid):
        bot.send_message(message.chat.id, "🚫 Бан")
        return

    if not is_subscribed(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Підписатись", url=f"https://t.me/{CHANNEL.replace('@','')}"))
        markup.add(types.InlineKeyboardButton("🔄 Перевірити", callback_data="check"))

        bot.send_message(message.chat.id, "❗ Спочатку підписка", reply_markup=markup)
        return

    if not is_verified(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔐 Verify", callback_data="verify"))

        bot.send_message(message.chat.id, "🔐 One-time verify", reply_markup=markup)
        return

    bot.send_message(message.chat.id, "🎧 Spotify Bot", reply_markup=menu())


# ================= VERIFY =================
@bot.callback_query_handler(func=lambda c: c.data == "verify")
def verify(call):
    uid = str(call.message.chat.id)

    if not is_subscribed(call.message.chat.id):
        bot.send_message(uid, "❌ Спочатку підписка")
        return

    data.setdefault(uid, {})
    data[uid]["verified"] = True
    data[uid].setdefault("queue", [])
    data[uid]["index"] = 0
    data[uid].setdefault("likes", [])
    data[uid]["premium"] = False

    save_data(data)

    bot.send_message(uid, "✅ Доступ відкрито")
    bot.send_message(uid, "🎧 Меню", reply_markup=menu())


# ================= CHECK =================
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(call):
    if is_subscribed(call.message.chat.id):
        bot.send_message(call.message.chat.id, "✅ OK /start")
    else:
        bot.send_message(call.message.chat.id, "❌ Не підписаний")


# ================= PREMIUM (STARS) =================
@bot.message_handler(func=lambda m: m.text == "💎 Premium")
def premium_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💰 Купити Premium", callback_data="buy_premium"))

    bot.send_message(message.chat.id, "💎 Premium доступ", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data == "buy_premium")
def buy(call):
    bot.send_invoice(
        chat_id=call.message.chat.id,
        title="Premium Spotify Bot",
        description="VIP доступ до функцій",
        invoice_payload="premium",
        provider_token="",
        currency="XTR",
        prices=[types.LabeledPrice("Premium", PREMIUM_PRICE)],
        start_parameter="premium"
    )


@bot.pre_checkout_query_handler(func=lambda q: True)
def checkout(q):
    bot.answer_pre_checkout_query(q.id, ok=True)


@bot.message_handler(content_types=['successful_payment'])
def success(message):
    uid = str(message.chat.id)

    data.setdefault(uid, {})
    data[uid]["premium"] = True
    save_data(data)

    bot.send_message(message.chat.id, "💎 Premium активовано!")


# ================= PLAYER =================
@bot.message_handler(func=lambda m: m.text == "🎧 Плеєр")
def player(message):
    uid = str(message.chat.id)

    if not is_subscribed(message.chat.id):
        return

    tracks = get_tracks()

    if not tracks:
        bot.send_message(message.chat.id, "❌ Нема музики")
        return

    data.setdefault(uid, {})
    data[uid]["queue"] = tracks
    data[uid]["index"] = 0

    save_data(data)

    send_track(message.chat.id)


def send_track(chat_id):
    uid = str(chat_id)
    state = data.get(uid)

    track = state["queue"][state["index"]]

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("⏮", callback_data="prev"),
        types.InlineKeyboardButton("▶️", callback_data="play"),
        types.InlineKeyboardButton("⏭", callback_data="next")
    )
    markup.add(types.InlineKeyboardButton("❤️", callback_data="like"))

    bot.send_message(chat_id, f"🎵 {track['title']}", reply_markup=markup)


# ================= RANDOM =================
@bot.message_handler(func=lambda m: m.text == "🎲 Random")
def random_track(message):
    tracks = get_tracks()

    if not tracks:
        bot.send_message(message.chat.id, "❌ Пусто")
        return

    limit = len(tracks) if is_premium(str(message.chat.id)) else 5

    t = random.choice(tracks[:limit])

    bot.send_audio(message.chat.id, t["file_id"], title=t["title"])


# ================= LIKES =================
@bot.message_handler(func=lambda m: m.text == "❤️ Лайки")
def likes(message):
    uid = str(message.chat.id)

    likes = data.get(uid, {}).get("likes", [])

    bot.send_message(message.chat.id, "\n".join(likes) if likes else "❌ Пусто")


# ================= BUTTONS =================
@bot.callback_query_handler(func=lambda c: True)
def buttons(call):
    uid = str(call.message.chat.id)
    state = data.get(uid)

    if not state:
        return

    queue = state.get("queue", [])

    if call.data == "next":
        state["index"] = (state["index"] + 1) % len(queue)

    elif call.data == "prev":
        state["index"] = (state["index"] - 1) % len(queue)

    elif call.data == "like":
        t = queue[state["index"]]
        state["likes"].append(t["title"])
        bot.send_message(uid, "❤️ saved")

    elif call.data == "play":
        t = queue[state["index"]]
        bot.send_audio(uid, t["file_id"], title=t["title"])

    save_data(data)
    send_track(uid)


# ================= RUN =================
bot.polling(none_stop=True)
