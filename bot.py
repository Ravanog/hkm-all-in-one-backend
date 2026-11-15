import os
import re
import random
import string
import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import set_user_vip_tier, save_vip_key, check_user_tier

API_ID = int(os.getenv("API_ID", "25380424"))
API_HASH = os.getenv("API_HASH", "2c434b1c9d15acef0b9ef44b6b96f6c0")
BOT_TOKEN = os.getenv("BOT_TOKEN", "9156008903:AAHMruoUUSyk3eLsQaqk4WOD3F-suEC_LkA")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-100123456789"))
STREAM_SERVER_URL = os.getenv("STREAM_SERVER_URL", "https://misty-chelsy-mahaan-c83f919b.apps.mistral.run").rstrip("/")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", f"{STREAM_SERVER_URL}/api/movies")
WEBSITE_URL = os.getenv("FRONTEND_URL", "https://hkm-all-in-one-backend-q2yk.vercel.app")

UPI_ID = "kushalhari@slc"
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "836351544"))

app = Client("hkm_unified_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def generate_key(tier: str) -> str:
    prefix = tier[:3].upper()
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"HKM-{prefix}-{random_str}"

@app.on_message(filters.command("delete") & filters.private)
async def delete_movie_cmd(client, message: Message):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply_text("❌ You are not authorized to use this command.")
        return

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

@app.on_message(filters.command("grant") & filters.private)
async def grant_premium_cmd(client, message: Message):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply_text("❌ You are not authorized to use this command.")
        return

    args = message.command
    if len(args) < 3:
        await message.reply_text("❌ **Usage:** `/grant <Telegram_User_ID> <basic/standard/diamond>`")
        return

    try:
        target_user_id = int(args[1])
        tier = args[2].lower()
        if tier not in ["basic", "standard", "diamond", "free"]:
            await message.reply_text("❌ Invalid tier.")
            return

        vip_key = generate_key(tier) if tier != "free" else "FREE-PLAN"
        if tier != "free":
            await save_vip_key(vip_key, tier, target_user_id)
        
        await set_user_vip_tier(target_user_id, tier, duration_days=30)
        await message.reply_text(f"✅ **Granted {tier.upper()} to `{target_user_id}`!**\nKey: `{vip_key}`")
        
        try:
            await client.send_message(
                chat_id=target_user_id,
                text=f"🎉 **Your payment was approved!**\nPlan: **{tier.upper()}**\n🔑 Activation Key: `{vip_key}`\n\nPaste this key into the portal to unlock your session."
            )
        except Exception:
            pass
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{e}`")

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    user = message.from_user
    
    try:
        log_text = (
            f"🚀 **User Started Bot (`/start`)**\n\n"
            f"👤 **Name:** {user.first_name} {user.last_name or ''}\n"
            f"🔗 **Username:** @{user.username or 'None'}\n"
            f"🆔 **User ID:** `{user.id}`"
        )
        await client.send_message(chat_id=LOG_CHANNEL_ID, text=log_text)
    except Exception as e:
        print(f"Start Log Error: {e}")

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
                f"1. Send **₹{price}** to:\n👉 `{UPI_ID}`\n\n"
                f"2. Send your **Transaction ID / Screenshot** right here in this chat for instant verification!"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Open HKM Portal", url=WEBSITE_URL)]
            ])
            await message.reply_text(text, reply_markup=keyboard)
            return

    user_info = await check_user_tier(user.id)
    
    welcome_text = (
        f"🎬 **Welcome to HKM Providers!**\n\n"
        f"Your Current Status: **{user_info['tier'].upper()}**\n\n"
        f"Explore our full catalog of movies, series, and anime directly on our web portal by clicking the button below!"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Open HKM Portal", url=WEBSITE_URL)]
    ])

    await message.reply_text(welcome_text, reply_markup=keyboard)

@app.on_message(filters.photo | filters.document | filters.text & filters.private)
async def user_submissions(client, message: Message):
    if not message.from_user or message.chat.id == int(LOG_CHANNEL_ID):
        return
        
    text_content = message.text or message.caption or ""
    if any(keyword in text_content.lower() for keyword in ["upi", "paid", "payment", "transaction", "utr", "ref", "screenshot", "gpay", "phonepe", "paytm"]) or message.photo:
        user = message.from_user
        
        approval_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve (Standard)", callback_data=f"app_{user.id}_standard"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user.id}")
            ],
            [
                InlineKeyboardButton("⚡ Approve (Basic ₹49)", callback_data=f"app_{user.id}_basic"),
                InlineKeyboardButton("👑 Approve (Diamond ₹299)", callback_data=f"app_{user.id}_diamond")
            ]
        ])

        forward_text = (
            f"🔔 **NEW UPI PAYMENT SUBMISSION**\n\n"
            f"👤 **User:** @{user.username or 'None'} (`{user.id}`)\n"
            f"👤 **Name:** {user.first_name}\n"
            f"📝 **Details:** {text_content or 'Screenshot attached'}\n\n"
            f"👇 **Click below to approve or reject:**"
        )
        try:
            if message.photo:
                await client.send_photo(
                    chat_id=LOG_CHANNEL_ID,
                    photo=message.photo.file_id,
                    caption=forward_text,
                    reply_markup=approval_keyboard
                )
            else:
                await client.send_message(
                    chat_id=LOG_CHANNEL_ID,
                    text=forward_text,
                    reply_markup=approval_keyboard
                )
            await message.reply_text("✅ **Payment proof received!** Sent to admin for verification. You will receive your activation key shortly.")
        except Exception as e:
            print(f"Forward Payment Error: {e}")

@app.on_callback_query()
async def admin_approval_callback(client, query: CallbackQuery):
    is_admin = (query.from_user.id == ADMIN_USER_ID)
    if not is_admin:
        try:
            member = await client.get_chat_member(LOG_CHANNEL_ID, query.from_user.id)
            if member.status in ["creator", "administrator"]:
                is_admin = True
        except Exception:
            pass

    if not is_admin:
        await query.answer("❌ Only admins can perform this action.", show_alert=True)
        return

    data = query.data
    if data.startswith("app_") or data.startswith("rej_"):
        parts = data.split("_")
        action = parts[0]
        target_user_id = int(parts[1])

        if action == "app":
            tier = parts[2]
            vip_key = generate_key(tier)
            await save_vip_key(vip_key, tier, target_user_id)
            await set_user_vip_tier(target_user_id, tier, duration_days=30)

            try:
                await client.send_message(
                    chat_id=target_user_id,
                    text=f"🎉 **Your Payment has been Approved!**\n\n"
                         f"💎 Plan: **{tier.upper()}**\n"
                         f"🔑 Your VIP Access Key: `{vip_key}`\n\n"
                         f"Paste this key into the **Activate Key** button on the website to unlock your session instantly!"
                )
            except Exception:
                pass

            new_caption = (query.message.caption or query.message.text) + f"\n\n✅ **STATUS: APPROVED ({tier.upper()})**\n🔑 Key Generated: `{vip_key}`"
            if query.message.photo:
                await query.message.edit_caption(caption=new_caption)
            else:
                await query.message.edit_text(text=new_caption)
            await query.answer("✅ Payment approved and key sent to user!")

        elif action == "rej":
            try:
                await client.send_message(
                    chat_id=target_user_id,
                    text="❌ **Your Payment Submission was Rejected.**\n\nPlease ensure your transaction ID or screenshot is valid and try submitting again, or contact support."
                )
            except Exception:
                pass

            new_caption = (query.message.caption or query.message.text) + "\n\n❌ **STATUS: REJECTED BY ADMIN**"
            if query.message.photo:
                await query.message.edit_caption(caption=new_caption)
            else:
                await query.message.edit_text(text=new_caption)
            await query.answer("❌ Payment rejected and user notified.")

print("HKM Python Bot Engine running...")
app.run()
