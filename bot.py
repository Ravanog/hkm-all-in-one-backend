import os
import re
import random
import string
import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import set_user_vip_tier, save_vip_key, check_user_tier

API_ID = int(os.getenv("API_ID", "25380424"))
API_HASH = os.getenv("API_HASH", "2c434b1c9d15acef0b9ef44b6b96f6c0")
BOT_TOKEN = os.getenv("BOT_TOKEN", "9156008903:AAHMruoUUSyk3eLsQaqk4WOD3F-suEC_LkA")
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1002082701021")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1004332636371"))
STREAM_SERVER_URL = os.getenv("STREAM_SERVER_URL", "https://misty-chelsy-mahaan-c83f919b.apps.mistral.run").rstrip("/")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", f"{STREAM_SERVER_URL}/api/movies")
WEBSITE_URL = os.getenv("FRONTEND_URL", "https://hkm-all-in-one-backend-q2yk.vercel.app")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "6abcb6bb99fb77f33c37016a28866ed2")

UPI_ID = "kushalhari@slc"

app = Client("hkm_unified_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def generate_key(tier: str) -> str:
    prefix = tier[:3].upper()
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"HKM-{prefix}-{random_str}"

def fetch_tmdb_metadata(title: str, category: str):
    clean_title = re.sub(r'\(.*?\)', '', title).strip()
    poster_url = "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=600"
    rating = "8.5"

    if TMDB_API_KEY:
        try:
            search_type = "tv" if category.lower() in ["series", "anime"] else "movie"
            url = f"https://api.themoviedb.org/3/search/{search_type}?api_key={TMDB_API_KEY}&query={requests.utils.quote(clean_title)}"
            res = requests.get(url, timeout=8).json()
            if res.get("results"):
                top = res["results"][0]
                if top.get("poster_path"):
                    poster_url = f"https://image.tmdb.org/t/p/w500{top['poster_path']}"
                if top.get("vote_average"):
                    rating = str(round(float(top["vote_average"]), 1))
        except Exception as e:
            print(f"TMDB Fetch Error: {e}")

    return poster_url, rating

def parse_media_details(text: str):
    name_no_ext = re.sub(r'\.(mp4|mkv|avi|webm)$', '', text, flags=re.IGNORECASE)
    clean_str = re.sub(r'[._]', ' ', name_no_ext).strip()

    qual_match = re.search(r'\b(4K|2160p|1080p|720p|480p|360p|240p)\b', clean_str, re.IGNORECASE)
    quality = qual_match.group(1).upper() if qual_match else "1080p"

    langs = re.findall(r'\b(Tamil|Hindi|Telugu|Malayalam|Kannada|English|Japanese|Korean|Multi Audio|Dual Audio)\b', clean_str, re.IGNORECASE)
    language = " / ".join(dict.fromkeys([l.title() for l in langs])) if langs else "Multi Audio"

    se_match = re.search(r'(.*?)\bS(\d{1,2})\s*E(\d{1,3})\b', clean_str, re.IGNORECASE)
    if se_match:
        title = se_match.group(1).strip(" -")
        season = int(se_match.group(2))
        episode = int(se_match.group(3))
        category = "Anime" if "anime" in clean_str.lower() else "Series"
        return title, category, season, episode, quality, language

    ep_match = re.search(r'(.*?)\b(?:Episode|Ep)\s*(\d{1,3})\b', clean_str, re.IGNORECASE)
    if ep_match:
        title = ep_match.group(1).strip(" -")
        episode = int(ep_match.group(2))
        category = "Anime" if "anime" in clean_str.lower() else "Series"
        return title, category, 1, episode, quality, language

    title = re.sub(r'\b(1080p|720p|480p|360p|240p|2160p|4K|UHD|HDR|WEB-DL|BluRay|x264|x265|Tamil|Hindi|Telugu|English|Dual Audio|Multi Audio)\b.*', '', clean_str, flags=re.IGNORECASE).strip(" -")
    return title or clean_str, "Action", None, None, quality, language

def push_message_to_backend(msg: Message) -> bool:
    media = msg.video or msg.document
    if not media:
        return False

    raw_name = getattr(media, 'file_name', None) or f"HKM_{msg.id}.mp4"
    caption = msg.caption or ""
    source_text = caption if ("S0" in caption.upper() or "EP" in caption.upper() or len(caption) > 3) else raw_name

    title, category, season, episode, quality, language = parse_media_details(source_text)
    poster_url, rating = fetch_tmdb_metadata(title, category)
    direct_url = f"{STREAM_SERVER_URL}/watch/{msg.id}?file_id={media.file_id}"
    is_vip = "#vip" in caption.lower() or "#premium" in caption.lower()

    payload = {
        "title": title,
        "posterUrl": poster_url,
        "category": category,
        "language": language,
        "rating": rating,
        "quality": quality,
        "credit": "Hari_Moviez",
        "isPremium": is_vip,
        "streamUrl": direct_url,
        "downloadUrl": direct_url
    }

    if season is not None and episode is not None:
        payload["season"] = season
        payload["episode"] = episode
        payload["episodeTitle"] = f"Season {season} • Episode {episode}"

    try:
        res = requests.post(BACKEND_API_URL, json=payload, timeout=15)
        return res.status_code in [200, 201]
    except Exception as e:
        print(f"Backend Sync Error: {e}")
        return False

@app.on_message(filters.chat(CHANNEL_ID) & (filters.video | filters.document))
def auto_sync_media(client, message: Message):
    try:
        push_message_to_backend(message)
        print(f"[AUTO-SYNC] Synced message {message.id}")
    except Exception as e:
        print(f"[AUTO-SYNC ERROR]: {e}")

@app.on_message(filters.command("index") & filters.private)
async def index_channel_files(client, message: Message):
    await message.reply_text("ℹ️ **Note:** Standard Telegram bots cannot read full channel history via `/index` due to Telegram restrictions.\n\n✨ **Better Way:** Just post or forward your movies into your storage channel, and they will **automatically sync** to your website instantly!")

@app.on_message(filters.command("delete") & filters.private)
async def delete_movie_cmd(client, message: Message):
    args = message.command
    if len(args) < 2:
        await message.reply_text("❌ **Usage:** `/delete <Movie Title or ID>`")
        return

    query = " ".join(args[1:]).strip()
    try:
        res = requests.get(BACKEND_API_URL, timeout=10)
        if res.status_code != 200:
            await message.reply_text("❌ Failed to fetch movie list from backend.")
            return

        movies = res.json()
        target_movie = None

        for m in movies:
            if m["_id"] == query or m["title"].lower() == query.lower():
                target_movie = m
                break

        if not target_movie:
            await message.reply_text(f"❌ No matching movie found for: `{query}`")
            return

        delete_res = requests.delete(f"{BACKEND_API_URL}/{target_movie['_id']}", timeout=10)
        if delete_res.status_code == 200:
            await message.reply_text(f"✅ **Successfully deleted movie and poster:** {target_movie['title']}")
        else:
            await message.reply_text("❌ Failed to delete movie from database.")
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{e}`")

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    args = message.command
    if len(args) > 1:
        param = args[1]
        if param in ["buy_basic", "buy_standard", "buy_diamond"]:
            tier_name = param.replace("buy_", "").upper()
            price = 49 if param == "buy_basic" else (99 if param == "buy_standard" else 299)
            
            text = (
                f"💎 **Upgrade to {tier_name} VIP Plan**\n\n"
                f"💰 **Amount:** `₹{price}`\n"
                f"📱 **UPI ID:** `{UPI_ID}`\n\n"
                f"1. Open any UPI app (GPay, PhonePe, Paytm, etc.) and send **₹{price}** to:\n"
                f"👉 `{UPI_ID}`\n\n"
                f"2. After payment, send your **Transaction ID / Screenshot** right here in this chat to receive your activation key instantly!"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Open HKM Portal", url=WEBSITE_URL)]
            ])
            await message.reply_text(text, reply_markup=keyboard)
            return

    user_info = await check_user_tier(message.from_user.id)
    
    welcome_text = (
        f"🎬 **Welcome to HKM Providers!**\n\n"
        f"Your Current Status: **{user_info['tier'].upper()}**\n\n"
        f"Explore our full catalog of movies, series, and anime directly on our web portal by clicking the button below!"
    )

    # Only website link button for normal start
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Open HKM Portal", url=WEBSITE_URL)]
    ])

    await message.reply_text(welcome_text, reply_markup=keyboard)

@app.on_message(filters.photo | filters.document | filters.text & filters.private)
async def user_submissions(client, message: Message):
    if not message.from_user or message.chat.id == int(LOG_CHANNEL_ID):
        return
        
    text_content = message.text or message.caption or ""
    if any(keyword in text_content.lower() for keyword in ["upi", "paid", "payment", "transaction", "UTR", "ref", "screenshot"]) or message.photo:
        user = message.from_user
        forward_text = (
            f"🔔 **NEW UPI PAYMENT SUBMISSION**\n\n"
            f"👤 **User:** @{user.username or 'None'} (`{user.id}`)\n"
            f"📝 **Note/Caption:** {text_content}\n\n"
            f"*(Verify payment in your UPI app and generate key for user)*"
        )
        try:
            await client.send_message(chat_id=LOG_CHANNEL_ID, text=forward_text)
            if message.photo:
                await client.forward_messages(chat_id=LOG_CHANNEL_ID, from_chat_id=message.chat.id, message_ids=message.id)
            await message.reply_text("✅ **Payment proof received!** Our admin will verify your transaction and send your VIP key shortly.")
        except Exception as e:
            print(f"Forward Payment Error: {e}")

print("HKM Python Bot Engine running...")
app.run()
