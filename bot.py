import os
import requests
from pyrogram import Client, filters
from pyrogram.types import LabeledPrice, Message, PreCheckoutQuery
from database import set_user_vip_tier, check_user_tier

API_ID = int(os.getenv("API_ID", "1234567"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel")
STREAM_SERVER_URL = os.getenv("STREAM_SERVER_URL", "https://your-backend.koyeb.app")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/movies")

app = Client("hkm_unified_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.chat(CHANNEL_ID) & (filters.video | filters.document))
def auto_sync_movie(client, message):
    try:
        media = message.video or message.document
        file_name = media.file_name if hasattr(media, 'file_name') and media.file_name else f"HKM_{message.id}"
        clean_title = file_name.replace(".mp4", "").replace(".mkv", "").replace(".", " ")
        direct_stream_url = f"{STREAM_SERVER_URL}/watch/{message.id}?file_id={media.file_id}"

        payload = {
            "title": clean_title,
            "posterUrl": "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=500",
            "category": "Action",
            "quality": "1080p",
            "isPremium": False,
            "tgMessageId": message.id,
            "tgFileId": media.file_id,
            "streamUrl": direct_stream_url
        }
        requests.post(BACKEND_API_URL, json=payload)
        print(f"[HKM BOT] Auto-synced: {clean_title}")
    except Exception as e:
        print(f"[HKM BOT ERROR] Sync failed: {e}")

@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    args = message.command
    if len(args) > 1:
        param = args[1]
        if param == "buy_basic":
            await send_plan_invoice(message, "Basic VIP Plan", "basic", 50)
            return
        elif param == "buy_standard":
            await send_plan_invoice(message, "Standard VIP Plan", "standard", 100)
            return
        elif param == "buy_diamond":
            await send_plan_invoice(message, "Diamond VIP Plan", "diamond", 250)
            return

    user_info = await check_user_tier(message.from_user.id)
    await message.reply_text(f"🎬 **Welcome to HKM Providers!**\nYour Status: **{user_info['tier'].upper()}**\n\nUse /premium to check plans.")

@app.on_message(filters.command("premium"))
async def premium_cmd(client, message: Message):
    await message.reply_text("Choose a plan directly on our website or reply with your desired tier.")

async def send_plan_invoice(message: Message, title: str, payload_type: str, price: int):
    await app.send_invoice(
        chat_id=message.chat.id,
        title=title,
        description=f"HKM Providers {title} (30 Days)",
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
    tier = "free"
    if "basic" in payload: tier = "basic"
    elif "standard" in payload: tier = "standard"
    elif "diamond" in payload: tier = "diamond"

    expiry = await set_user_vip_tier(message.from_user.id, tier, duration_days=30)
    await message.reply_text(f"🎉 Payment Successful! Your **{tier.upper()}** plan is active until {expiry.strftime('%Y-%m-%d')}.")

print("HKM Python Bot Engine running...")
app.run()
