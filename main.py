import telebot
from telebot import types
import json
import os
import random

TOKEN = "8751370568:AAERob2JxbvqvUIg_eQWakXEGQANuYd7x_A"
CHANNEL = "@voltmusical"

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"
TRACKS_FILE = "tracks.json"
PREMIUM_PRICE = 100


# ================= LOAD =================
def load_json(file, default):
    if not os.path.exists(file):
        return default
    with open(file, "r") as f:
        return json.load(f)


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)


data = load_json(DATA_FILE, {})
tracks = load_json(TRACKS_FILE, [])


# ================= SUB CHECK =================
def is_subscribed(user_id):
    try:
        m = bot.get_chat_member(CHANNEL, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False


def is_premium(uid):
    return data.get(uid, {}).get("premium", False)


# ================= MENU =================
def menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("🎧 Плеєр", "🎲 Random")
    m.add("📊 Статистика", "💎 Premium")
    return m


# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    if not is_subscribed(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Підписатись", url=f"https://t.me/{CHANNEL.replace('@','')}"))
        markup.add(types.InlineKeyboardButton("✅ Я підписан(а)", callback_data="check"))

        bot.send_message(
            message.chat.id,
            "❗ Щоб користуватись ботом, потрібно підписатись на канал",
            reply_markup=markup
        )
        return

    bot.send_message(message.chat.id, "✅ Готово", reply_markup=menu())


# ================= CHECK =================
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(call):
    if is_subscribed(call.message.chat.id):
        bot.send_message(call.message.chat.id, "✅ Готово", reply_markup=menu())
    else:
        bot.send_message(call.message.chat.id, "❌ Ти не підписаний")


# ================= ADD MUSIC (FORWARD) =================
@bot.message_handler(content_types=['audio'])
def add_music(message):
    if not message.forward_from_chat:
        return

    if message.forward_from_chat.username != CHANNEL.replace("@", ""):
        return

    track = {
        "title": message.audio.title or "Unknown",
        "file_id": message.audio.file_id
    }

    tracks.append(track)
    save_json(TRACKS_FILE, tracks)

    bot.send_message(message.chat.id, f"✅ Додано: {track['title']}")


# ================= PLAYER =================
@bot.message_handler(func=lambda m: m.text == "🎧 Плеєр")
def player(message):
    if not tracks:
        bot.send_message(message.chat.id, "❌ Нема музики")
        return

    uid = str(message.chat.id)

    data.setdefault(uid, {})
    data[uid]["queue"] = tracks
    data[uid]["index"] = 0
    data[uid].setdefault("likes", [])

    save_json(DATA_FILE, data)

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


# ================= BUTTONS =================
@bot.callback_query_handler(func=lambda c: c.data in ["next", "prev", "play", "like"])
def buttons(call):
    uid = str(call.message.chat.id)
    state = data.get(uid)

    if not state:
        return

    queue = state["queue"]

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

    save_json(DATA_FILE, data)
    send_track(uid)


# ================= RANDOM =================
@bot.message_handler(func=lambda m: m.text == "🎲 Random")
def random_track(message):
    if not tracks:
        bot.send_message(message.chat.id, "❌ Пусто")
        return

    limit = len(tracks) if is_premium(str(message.chat.id)) else 5
    t = random.choice(tracks[:limit])

    bot.send_audio(message.chat.id, t["file_id"], title=t["title"])


# ================= STATS =================
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(message):
    uid = str(message.chat.id)

    prem = "💎 Так" if is_premium(uid) else "❌ Ні"
    stars = data.get(uid, {}).get("stars", 0)

    bot.send_message(
        message.chat.id,
        f"📊 Статистика\n\n💎 Premium: {prem}\n⭐ Stars: {stars}"
    )


# ================= PREMIUM =================
@bot.message_handler(func=lambda m: m.text == "💎 Premium")
def premium(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💰 Купити", callback_data="buy"))

    bot.send_message(message.chat.id, "💎 Premium", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data == "buy")
def buy(call):
    bot.send_invoice(
        chat_id=call.message.chat.id,
        title="Premium",
        description="VIP доступ",
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
    data[uid]["stars"] = data[uid].get("stars", 0) + PREMIUM_PRICE

    save_json(DATA_FILE, data)

    bot.send_message(message.chat.id, "💎 Premium активовано!")


# ================= RUN =================
bot.polling(none_stop=True)
