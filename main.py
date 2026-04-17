from flask import Flask, render_template, request, jsonify
import telebot
import requests
import base64
import json
from datetime import datetime
import threading

# ================= CONFIG =================
TOKEN = "8751370568:AAERob2JxbvqvUIg_eQWakXEGQANuYd7x_A"
ADMIN_ID = 8307540389
CHANNEL = "@voltmusical"

SPOTIFY_ID = "ID"
SPOTIFY_SECRET = "SECRET"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

DATA_FILE = "data.json"


# ================= DATABASE =================
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


# ================= USER INIT =================
def init(uid):
    uid = str(uid)
    if uid not in data:
        data[uid] = {
            "searches": 0,
            "likes": [],
            "history": [],
            "premium": False
        }


# ================= SPOTIFY =================
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


def search_music(q):
    t = get_token()

    r = requests.get(
        f"https://api.spotify.com/v1/search?q={q}&type=track&limit=6",
        headers={"Authorization": f"Bearer {t}"}
    )

    return r.json()["tracks"]["items"]


# ================= BOT MENU =================
from telebot import types

def menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("🔎 Пошук", "❤️ Лайки")
    m.add("🧠 AI", "📊 Статистика")
    return m


# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):

    init(m.chat.id)

    bot.send_message(
        m.chat.id,
        "🎧 VOLT MUSIC SYSTEM 16.1",
        reply_markup=menu()
    )

    bot.send_message(ADMIN_ID, f"START {m.chat.id}")


# ================= SEARCH FLOW =================
@bot.message_handler(func=lambda m: m.text == "🔎 Пошук")
def ask(m):
    msg = bot.send_message(m.chat.id, "Введи назву:")
    bot.register_next_step_handler(msg, search)


def search(m):

    uid = str(m.chat.id)
    init(uid)

    tracks = search_music(m.text)

    for t in tracks:

        name = t["name"]
        artist = t["artists"][0]["name"]
        cover = t["album"]["images"][0]["url"]
        url = t["external_urls"]["spotify"]

        data[uid]["history"].append(name)

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("▶ Play", url=url))

        bot.send_photo(
            m.chat.id,
            cover,
            caption=f"{name}\n{artist}",
            reply_markup=kb
        )

    save()


# ================= AI =================
@bot.message_handler(func=lambda m: m.text == "🧠 AI")
def ai(m):

    t = search_music("pop")[0]

    bot.send_message(
        m.chat.id,
        f"{t['name']} - {t['artists'][0]['name']}"
    )


# ================= STATS =================
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(m):

    uid = str(m.chat.id)
    init(uid)

    bot.send_message(
        m.chat.id,
        f"""
👥 Users: {len(data)}
🔎 Searches: {data[uid]['searches']}
❤️ Likes: {len(data[uid]['likes'])}
"""
    )


# ================= WEB =================
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search")
def api():
    q = request.args.get("q")
    return jsonify(search_music(q))


# ================= RUN BOT =================
def run_bot():
    bot.polling(none_stop=True)


# ================= START APP =================
if __name__ == "__main__":

    print("🎧 Volt Music Starting...")

    threading.Thread(target=run_bot).start()

    app.run(host="0.0.0.0", port=5000)
