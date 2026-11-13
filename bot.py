import os
import re
import random
import string
import requests
from pyrogram import Client, filters
from pyrogram.types import LabeledPrice, Message, PreCheckoutQuery
from database import set_user_vip_tier, save_vip_key, check_user_tier

API_ID = int(os.getenv("API_ID", "1234567"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-100123456789"))
STREAM_SERVER_URL = os.getenv("STREAM_SERVER_URL", "https://your-backend.koyeb.app")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/movies")

app = Client("hkm_unified_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def generate_key(tier: str) -> str:
    prefix = tier[:3].upper()
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"HKM-{prefix}-{random_str}"

def parse_media_filename(filename: str):
    """
    Extracts Show/Movie Title, Category (Action/Series/Anime), Season, and Episode.
    Supports formats like:
    - Stranger.Things.S04E02.1080p.mkv
    - Attack on Titan - S01E05.mp4
    - Naruto Episode 12.mp4
    """
    name_no_ext = re.sub(r'\.(mp4|mkv|avi|webm)$', '', filename, flags=re.IGNORECASE)
    clean_str = re.sub(r'[._]', ' ', name_no_ext).strip()

    # Match S01E02 or S1 E2
    se_match = re.search(r'(.*?)\bS(\d{1,2})\s*E(\d{1,3})\b', clean_str, re.IGNORECASE)
    if se_match:
        title = se_match.group(1).strip(" -")
        season = int(se_match.group(2))
        episode = int(se_match.group(3))
        category = "Anime" if "anime" in clean_str.lower() else "Series"
        return title, category, season, episode

    # Match Episode 05 / Ep 05
    ep_match = re.search(r'(.*?)\b(?:Episode|Ep)\s*(\d{1,3})\b', clean_str, re.IGNORECASE)
    if ep_match:
        title = ep_match.group(1).strip(" -")
        episode = int(ep_match.group(2))
        category = "Anime" if "anime" in clean_str.lower() else "Series"
        return title, category, 1, episode

    # Otherwise treat as a single Movie
    title = re.sub(r'\b(1080p|720p|480p|4K|UHD|HDR|WEB-DL|BluRay|x264|x265)\b.*', '', clean_str, flags=re.IGNORECASE).strip(" -")
    return title or clean_str, "Action", None, None

@app.on_message(filters.chat(CHANNEL_ID) & (filters.video | filters.document))
def auto_sync_media(client, message):
    try:
        media = message.video or message.document
        raw_name = media.file_name if hasattr(media, 'file_name') and media.file_name else f"HKM_{message.id}"
        caption_text = message.caption or raw_name
        
        title, category, season, episode = parse_media_filename(caption_text if ("S0" in caption_text.upper() or "EP" in caption_text.upper()) else raw_name)
        direct_url = f"{STREAM_SERVER_URL}/watch/{message.id}?file_id={media.file_id}"

        payload = {
            "title": title,
            "posterUrl": "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=500",
            "category": category,
            "quality": "1080p",
            "isPremium": False,
            "streamUrl": direct_url,
            "downloadUrl": direct_url
        }

        if season is not None and episode is not None:
            payload["season"] = season
            payload["episode"] = episode
            payload["episodeTitle"] = f"Season {season} • Episode {episode}"

        requests.post(BACKEND_API_URL, json=payload)
        print(f"Synced: {title} | Cat: {category} | S{season}E{episode}")
    except Exception as e:
        print(f"Sync Error: {e}")

@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    args = message.command
    if len(args) > 1:
        param = args[1]
        if param == "buy_basic":
            await send_plan_invoice(message, "Basic VIP Plan (₹49)", "basic", 30)
            return
        elif param == "buy_standard":
            await send_plan_invoice(message, "Standard VIP Plan (₹99)", "standard", 60)
            return
        elif param == "buy_diamond":
            await send_plan_invoice(message, "Diamond VIP Plan (₹299/yr)", "diamond", 180)
            return

    user_info = await check_user_tier(message.from_user.id)
    await message.reply_text(f"🎬 **Welcome to HKM Providers!**\nYour Status: **{user_info['tier'].upper()}**\n\nChoose a plan on our website to get started.")

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
async def checkout_handler(client, query: PreCheckoutQuery):
    await query.answer(ok=True)

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
