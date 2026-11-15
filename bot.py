import os
from pyrogram import Client, filters
from pyrogram.types import Message
import motor.motor_asyncio

# Configuration
API_ID = int(os.getenv("API_ID", "25380424"))  # Replace with your Telegram API ID
API_HASH = os.getenv("API_HASH", "2c434b1c9d15acef0b9ef44b6b96f6c0")
BOT_TOKEN = os.getenv("BOT_TOKEN", "9156008903:AAHMruoUUSyk3eLsQaqk4WOD3F-suEC_LkA")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://anikush8310_db_user:nPoB0GWMD34X7aeR@cluster0.yvanywe.mongodb.net/")
ADMIN_USER_ID = 836351544  # Hardcoded verified Admin ID

app = Client("hkm_providers_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# MongoDB Connection
db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = db_client["hkm_providers"]
movies_collection = db["movies"]
users_collection = db["users"]
banners_collection = db["banners"]

def parse_custom_format(text):
    """Helper to parse multi-line custom format"""
    data = {}
    lines = text.split("\n")
    for line in lines:
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip().lower()
            val = parts[1].strip()
            data[key] = val
    return data

@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply_text(
        "🎬 **Welcome to HKM Providers Admin & User Bot!**\n\n"
        "Use the web portal or admin commands to manage content."
    )

# 1. /addmovies Command
@app.on_message(filters.command("addmovies") & filters.private)
async def add_movies_cmd(client, message: Message):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply_text("❌ You are not authorized to use this command.")
        return

    # Extract text after command
    command_text = message.text.replace("/addmovies", "").strip()
    data = parse_custom_format(command_text)

    if not data.get("title") or not data.get("stream url"):
        await message.reply_text(
            "❌ **Invalid Format!** Please use the following structure:\n\n"
            "/addmovies\n"
            "Title: Movie Name\n"
            "Year: 2026\n"
            "Posterurl: https://...\n"
            "Resolution: 1080p\n"
            "Credentials rights: Hari_Moviez\n"
            "Launguage: Tamil\n"
            "Download url: https://...\n"
            "Stream url: https://..."
        )
        return

    movie_doc = {
        "title": data.get("title"),
        "year": data.get("year", "N/A"),
        "posterUrl": data.get("posterurl", ""),
        "quality": data.get("resolution", "1080p"),
        "credit": data.get("credentials rights", "Hari_Moviez"),
        "language": data.get("launguage", "Multi Audio"),
        "downloadUrl": data.get("download url", ""),
        "streamUrl": data.get("stream url", ""),
        "category": "Movie",
        "isPremium": False,
        "views": 0
    }

    await movies_collection.insert_one(movie_doc)
    await message.reply_text(f"✅ **Movie Successfully Added!**\n🎬 {data.get('title')} ({data.get('year', 'N/A')})")

# 2. /addseries Command
@app.on_message(filters.command("addseries") & filters.private)
async def add_series_cmd(client, message: Message):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply_text("❌ You are not authorized to use this command.")
        return

    command_text = message.text.replace("/addseries", "").strip()
    data = parse_custom_format(command_text)

    if not data.get("title") or not data.get("stream url"):
        await message.reply_text(
            "❌ **Invalid Format for Series!** Please use:\n\n"
            "/addseries\n"
            "Title: Show Name - S01E01\n"
            "Year: 2026\n"
            "Posterurl: https://...\n"
            "Resolution: 1080p\n"
            "Credentials rights: Hari_Moviez\n"
            "Launguage: Multi Audio\n"
            "Download url: https://...\n"
            "Stream url: https://..."
        )
        return

    series_doc = {
        "title": data.get("title"),
        "year": data.get("year", "N/A"),
        "posterUrl": data.get("posterurl", ""),
        "quality": data.get("resolution", "1080p"),
        "credit": data.get("credentials rights", "Hari_Moviez"),
        "language": data.get("launguage", "Multi Audio"),
        "downloadUrl": data.get("download url", ""),
        "streamUrl": data.get("stream url", ""),
        "category": "Series",
        "isPremium": False,
        "views": 0
    }

    await movies_collection.insert_one(series_doc)
    await message.reply_text(f"✅ **Series Episode Added!**\n📺 {data.get('title')}")

# 3. /addvip Command (Marks content as VIP/Premium-only)
@app.on_message(filters.command("addvip") & filters.private)
async def add_vip_content_cmd(client, message: Message):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply_text("❌ You are not authorized to use this command.")
        return

    command_text = message.text.replace("/addvip", "").strip()
    data = parse_custom_format(command_text)

    if not data.get("title") or not data.get("stream url"):
        await message.reply_text(
            "❌ **Invalid Format for VIP Content!** Use standard format with /addvip."
        )
        return

    vip_doc = {
        "title": data.get("title"),
        "year": data.get("year", "N/A"),
        "posterUrl": data.get("posterurl", ""),
        "quality": data.get("resolution", "1080p"),
        "credit": data.get("credentials rights", "Hari_Moviez"),
        "language": data.get("launguage", "Multi Audio"),
        "downloadUrl": data.get("download url", ""), # Download url only accessible for VIP users on frontend
        "streamUrl": data.get("stream url", ""),
        "category": "Movie",
        "isPremium": True,  # Flagged as VIP Content
        "views": 0
    }

    await movies_collection.insert_one(vip_doc)
    await message.reply_text(f"👑 **VIP Content Added Successfully!**\n🎬 {data.get('title')}")

# 4. /add_premium Command (Grants VIP access to a user)
@app.on_message(filters.command("add_premium") & filters.private)
async def add_premium_user_cmd(client, message: Message):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply_text("❌ You are not authorized to use this command.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("Usage: `/add_premium <telegram_user_id>`", parse_mode="markdown")
        return

    target_user_id = int(args[1])
    await users_collection.update_one(
        {"telegram_id": target_user_id},
        {"$set": {"tier": "standard", "active": True}},
        upsert=True
    )
    await message.reply_text(f"🎉 Successfully upgraded user `{target_user_id}` to VIP Standard tier!", parse_mode="markdown")

# 5. /bannerslides Command (Adds promotional banners for website slider)
@app.on_message(filters.command("bannerslides") & filters.private)
async def banner_slides_cmd(client, message: Message):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply_text("❌ You are not authorized to use this command.")
        return

    command_text = message.text.replace("/bannerslides", "").strip()
    data = parse_custom_format(command_text)

    if not data.get("title") or not data.get("posterurl"):
        await message.reply_text(
            "❌ **Invalid Format!** Use:\n\n"
            "/bannerslides\n"
            "Title: Banner Movie\n"
            "Posterurl: https://...\n"
            "Year: 2026"
        )
        return

    banner_doc = {
        "title": data.get("title"),
        "posterUrl": data.get("posterurl"),
        "year": data.get("year", "2026")
    }

    await banners_collection.insert_one(banner_doc)
    await message.reply_text(f"🌟 **Banner Slide Added:** {data.get('title')}")

if __name__ == "__main__":
    print("Bot started successfully with admin ID: 836351544")
    app.run()
