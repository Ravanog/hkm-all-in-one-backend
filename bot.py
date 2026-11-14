import os
import re
import random
import string
import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import set_user_vip_tier, save_vip_key, check_user_tier

# Define custom classes and compatibility patches for older Pyrogram versions
class LabeledPrice:
    def __init__(self, label: str, amount: int):
        self.label = label
        self.amount = amount

class PreCheckoutQuery:
    def __init__(self, id: str, from_user, currency: str, total_amount: int, payload: str):
        self.id = id
        self.from_user = from_user
        self.currency = currency
        self.total_amount = total_amount
        self.payload = payload

API_ID = int(os.getenv("API_ID", "25380424"))
API_HASH = os.getenv("API_HASH", "2c434b1c9d15acef0b9ef44b6b96f6c0")
BOT_TOKEN = os.getenv("BOT_TOKEN", "9156008903:AAHMruoUUSyk3eLsQaqk4WOD3F-suEC_LkA")
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1002082701021")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-100123456789"))
STREAM_SERVER_URL = os.getenv("STREAM_SERVER_URL", "https://misty-chelsy-mahaan-c83f919b.apps.mistral.run").rstrip("/")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", f"{STREAM_SERVER_URL}/api/movies")
WEBSITE_URL = os.getenv("FRONTEND_URL", "https://hkm-all-in-one-backend-q2yk.vercel.app")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "6abcb6bb99fb77f33c37016a28866ed2")

app = Client("hkm_unified_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Add compatibility patch for missing decorator in Pyrogram
if not hasattr(app, 'on_pre_checkout_query'):
    def custom_on_pre_checkout_query():
        def decorator(func):
            return func
        return decorator
    app.on_pre_checkout_query = custom_on_pre_checkout_query

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

    res = requests.post(BACKEND_API_URL, json=payload, timeout=15)
    return res.status_code in [200, 201]

@app.on_message(filters.chat(CHANNEL_ID) & (filters.video | filters.document))
def auto_sync_media(client, message: Message):
    try:
        push_message_to_backend(message)
        print(f"[AUTO-SYNC] Synced message {message.id}")
    except Exception as e:
        print(f"[AUTO-SYNC ERROR]: {e}")

@app.on_message(filters.command("index") & filters.private)
async def index_channel_files(client, message: Message):
    args = message.command
    limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 50
    status_msg = await message.reply_text(f"🔄 **Indexing last {limit} messages from channel...**")

    indexed_count = 0
    try:
        messages_to_process = []
        async for msg in client.get_chat_history(CHANNEL_ID, limit=limit):
            if msg.video or msg.document:
                messages_to_process.append(msg)

        for msg in reversed(messages_to_process):
            if push_message_to_backend(msg):
                indexed_count += 1

        await status_msg.edit_text(f"✅ **Indexing Complete!**\nFiles Indexed: {indexed_count}")
    except Exception as e:
        await status_msg.edit_text(f"❌ **Index Error:** `{e}`")

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    args = message.command
    if len(args) > 1:
        param = args[1]
        if param == "buy_basic":
            await send_plan_invoice(message, "Basic VIP Plan (₹49)", "basic", 49)
            return
        elif param == "buy_standard":
            await send_plan_invoice(message, "Standard VIP Plan (₹99)", "standard", 99)
            return
        elif param == "buy_diamond":
            await send_plan_invoice(message, "Diamond VIP Plan (₹299/yr)", "diamond", 299)
            return

    user_info = await check_user_tier(message.from_user.id)
    
    welcome_text = (
        f"🎬 **Welcome to HKM Providers!**\n\n"
        f"Your Current Status: **{user_info['tier'].upper()}**\n\n"
        f"Explore our full catalog of movies, series, and anime directly on our web portal by clicking the button below!"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🌐 Open HKM Providers Portal", url=WEBSITE_URL)]
        ]
    )

    await message.reply_text(welcome_text, reply_markup=keyboard)

async def send_plan_invoice(message: Message, title: str, payload_type: str, price: int):
    await app.send_invoice(
        chat_id=message.chat.id,
        title=title,
        description=f"HKM Providers {title}",
        payload=f"hkm_{payload_type}_30",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(title, price)],
        start_parameter=payload_type
    )

@app.on_pre_checkout_query()
async def checkout_handler(client, query):
    try:
        if hasattr(query, 'answer'):
            await query.answer(ok=True)
        else:
            await client.answer_pre_checkout_query(query.id, ok=True)
    except Exception as e:
        print(f"Checkout Error: {e}")

@app.on_message(filters.successful_payment)
async def payment_success(client, message: Message):
    payload = message.successful_payment.invoice_payload
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    tier = "free"
    if "basic" in payload: tier = "basic"
    elif "standard" in payload: tier = "standard"
    elif "diamond" in payload: tier = "diamond"

    vip_key = generate_key(tier)
    await save_vip_key(vip_key, tier, user_id)
    await set_user_vip_tier(user_id, tier, duration_days=30)

    await message.reply_text(
        f"🎉 **Payment Successful!**\n\n"
        f"Your Plan: **{tier.upper()}**\n"
        f"🔑 Your VIP Access Key: `{vip_key}`\n\n"
        f"Paste this key into the **Activate Key** button on the website to unlock your session instantly!"
    )

    try:
        log_text = (
            f"🔔 **New Premium Subscription!**\n\n"
            f"👤 User: @{username} (ID: `{user_id}`)\n"
            f"💎 Tier: **{tier.upper()}**\n"
            f"🔑 Generated Key: `{vip_key}`"
        )
        await client.send_message(chat_id=LOG_CHANNEL_ID, text=log_text)
    except Exception as e:
        print(f"Log Error: {e}")

print("HKM Python Bot Engine running...")
app.run()
