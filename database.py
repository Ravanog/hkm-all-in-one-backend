import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://anikush8310_db_user:nPoB0GWMD34X7aeR@cluster0.yvanywe.mongodb.net")
client = AsyncIOMotorClient(MONGO_URI)
db = client.hkmdb
users_collection = db.users
keys_collection = db.vip_keys
movies_collection = db.movies

async def set_user_vip_tier(telegram_id: int, tier: str, duration_days: int = 30):
    expiry_date = datetime.utcnow() + timedelta(days=duration_days)
    is_vip = tier in ["standard", "diamond"]
    
    await users_collection.update_one(
        {"telegramId": telegram_id},
        {
            "$set": {
                "telegramId": telegram_id,
                "tier": tier,
                "isVIP": is_vip,
                "vipExpiry": expiry_date,
                "updatedAt": datetime.utcnow()
            }
        },
        upsert=True
    )
    return expiry_date

async def save_vip_key(key: str, tier: str, telegram_id: int):
    await keys_collection.insert_one({
        "key": key,
        "tier": tier,
        "telegramId": telegram_id,
        "isRedeemed": False,
        "createdAt": datetime.utcnow()
    })

async def check_user_tier(telegram_id: int) -> dict:
    user = await users_collection.find_one({"telegramId": telegram_id})
    if not user:
        return {"tier": "free", "isVIP": False}
    if user.get("vipExpiry") and user["vipExpiry"] < datetime.utcnow():
        await users_collection.update_one({"telegramId": telegram_id}, {"$set": {"tier": "free", "isVIP": False}})
        return {"tier": "free", "isVIP": False}
    return {"tier": user.get("tier", "free"), "isVIP": user.get("isVIP", False)}
    
