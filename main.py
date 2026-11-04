import discord
import requests
import asyncio
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup


# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CH_ID"))
TARGET_PRICE = float(os.getenv("TARGET"))

# Configure gateway intents
intents = discord.Intents.default()
intents.reactions = True
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)

reaction_message_id = None
DATA_FILE = "subscribers.json"

# Load and save subscribers
def load_subscribers():
    try:
        with open(DATA_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_subscribers(users):
    with open(DATA_FILE, "w") as f:
        json.dump(list(users), f)

subscribed_users = load_subscribers()

# Get the market session (Western Indonesian Time, UTC+7)
def get_session_info():
    now = datetime.now(timezone(timedelta(hours=7)))  # Western Indonesian Time (UTC+7)
    hour, minute = now.hour, now.minute
    time_in_hours = hour + minute / 60

    if time_in_hours < 9:
        return "❌ Market not open yet", False
    elif 9 <= time_in_hours < 12:
        return "🟢 Session 1", True
    elif 12 <= time_in_hours < 13.5:
        return "⏸ Market break", False
    elif 13.5 <= time_in_hours < 15:
        return "🟢 Session 2", True
    else:
        return "🔒 Market closed", False

# Fetch the BBCA price from Google Finance
def get_bbca_price_from_google():
    try:
        url = "https://www.google.com/finance/quote/BBCA:IDX"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        tag = soup.select_one("div.YMlKec.fxKbKc")

        if tag:
            price_text = tag.text.strip().replace("Rp", "").replace(",", "").replace(".", "")
            return float(price_text) / 100  # Google Finance may display prices with fractional currency units
        return None
    except Exception as e:
        print(f"❌ Error fetching price: {e}")
        return None

# Post the initial reaction message
async def post_reaction_message():
    global reaction_message_id
    channel = client.get_channel(CHANNEL_ID)
    msg = await channel.send("React with ✅ to **subscribe to BBCA target price alerts**, or ❌ to unsubscribe.")
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    reaction_message_id = msg.id

@client.event
async def on_ready():
    print(f"✅ Bot logged in as {client.user}")
    await post_reaction_message()
    asyncio.create_task(check_price_hourly())

@client.event
async def on_raw_reaction_add(payload):
    if payload.message_id != reaction_message_id:
        return
    if str(payload.emoji) == "✅":
        subscribed_users.add(payload.user_id)
        save_subscribers(subscribed_users)
        print(f"🟢 User {payload.user_id} subscribed")
    elif str(payload.emoji) == "❌":
        subscribed_users.discard(payload.user_id)
        save_subscribers(subscribed_users)
        print(f"🔴 User {payload.user_id} unsubscribed")

@client.event
async def on_raw_reaction_remove(payload):
    if payload.message_id != reaction_message_id:
        return
    if str(payload.emoji) == "✅":
        subscribed_users.discard(payload.user_id)
        save_subscribers(subscribed_users)
        print(f"🔴 User {payload.user_id} unsubscribed (reaction removed)")

# Check the BBCA price and send an update
async def check_price_hourly():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    while not client.is_closed():
        try:
            now = datetime.now(timezone(timedelta(hours=7)))  # Western Indonesian Time (UTC+7)
            time_str = now.strftime("%H:%M")
            session_status, is_open = get_session_info()

            if is_open:
                price = get_bbca_price_from_google()
                if price:
                    message = f"📊 **BBCA Stock Update [{time_str} WIB]**\n"
                    message += f"- 🕒 Market status: {session_status}\n"
                    message += f"- 🎯 Target: Rp {TARGET_PRICE:,.0f}\n"
                    message += f"- 💰 Current price: **Rp {price:,.0f}**"

                    if price > TARGET_PRICE and subscribed_users:
                        mention = " ".join(f"<@{uid}>" for uid in subscribed_users)
                        message += f"\n🚨 **Price is above Rp {TARGET_PRICE:,.0f}!** {mention}"
                else:
                    message = f"⚠️ Failed to fetch the BBCA price [{time_str} WIB]"
            else:
                message = (
                    f"🔒 **Market Inactive [{time_str} WIB]**\n"
                    f"- 🕒 Status: {session_status}\n"
                    f"- 💤 Price updates will resume when the market opens."
                )

            await channel.send(message)
            await asyncio.sleep(3600)

        except Exception as e:
            print(f"❌ Error in price update loop: {e}")
            await asyncio.sleep(3600)

# Run the bot
async def main():
    async with client:
        await client.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
